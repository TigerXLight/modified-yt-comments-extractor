from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass, field
from typing import Any, Mapping, Sequence

MSN_MANUAL_RELEASE_INDEX_SCHEMA_VERSION = "msn_manual_release_index_v1"
MSN_MANUAL_APPROVED_RELEASE_PACKAGE_SCHEMA_VERSION = "msn_manual_approved_release_package_v1"
MSN_MANUAL_RELEASE_INDEX_STATUS_READY = "MSN_MANUAL_RELEASE_INDEX_READY"
MSN_MANUAL_RELEASE_INDEX_STATUS_NEEDS_REVIEW = "MSN_MANUAL_RELEASE_INDEX_NEEDS_REVIEW"

_SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9_.-]+")
_PATH_RE = re.compile(r"(?:(?<![A-Za-z])[A-Za-z]:\\|(?<![A-Za-z])[A-Za-z]:/|\\\\|/(?:home|mnt|Users|Volumes|tmp|var)/)")


@dataclass(frozen=True)
class MSNManualReleaseIndexAsset:
    role: str
    filename: str
    sha256: str = ""
    byte_count: int = 0
    source: str = "approved_release_package"


@dataclass(frozen=True)
class MSNManualReleaseLineageEntry:
    role: str
    identifier: str
    status: str


@dataclass(frozen=True)
class MSNManualReleaseIndexReport:
    schema_version: str
    index_id: str
    index_label: str
    release_id: str
    queue_item_id: str
    handoff_id: str
    decision_id: str
    source_url: str
    named_site: str
    named_action: str
    article_title: str
    release_index_status: str
    ready_for_total_export_release_index: bool
    issue_count: int
    issues: list[str] = field(default_factory=list)
    assets: list[MSNManualReleaseIndexAsset] = field(default_factory=list)
    lineage: list[MSNManualReleaseLineageEntry] = field(default_factory=list)
    evidence_queue_release_update: dict[str, str] = field(default_factory=dict)
    total_export_release_handoff: dict[str, Any] = field(default_factory=dict)
    safety_flags: dict[str, bool] = field(default_factory=dict)
    index_hash: str = ""


class MSNManualReleaseIndexError(ValueError):
    pass


def _safe_text(value: Any, *, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


def _safe_id(value: Any, *, default: str) -> str:
    raw = _safe_text(value, default=default)
    safe = _SAFE_NAME_RE.sub("_", raw).strip("._")
    return safe or default


def _safe_filename(value: Any, *, fallback: str) -> str:
    raw = _safe_text(value, default=fallback).replace("\\", "/").split("/")[-1]
    safe = _SAFE_NAME_RE.sub("_", raw).strip("._")
    return safe or fallback


def _read_int(value: Any) -> int:
    try:
        return max(int(value), 0)
    except (TypeError, ValueError):
        return 0


def _contains_path_like(value: Any) -> bool:
    if isinstance(value, str):
        return bool(_PATH_RE.search(value))
    if isinstance(value, Mapping):
        return any(_contains_path_like(child) for child in value.values())
    if isinstance(value, (list, tuple)):
        return any(_contains_path_like(child) for child in value)
    return False


def _sha256_json(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _normalise_asset(raw: Mapping[str, Any], *, source: str, index: int) -> MSNManualReleaseIndexAsset:
    role = _safe_id(raw.get("role", raw.get("file_role", raw.get("asset_role", f"asset_{index}"))), default=f"asset_{index}")
    filename = _safe_filename(
        raw.get("filename", raw.get("safe_filename", raw.get("relative_path", raw.get("name", f"asset_{index}.json")))),
        fallback=f"asset_{index}.json",
    )
    return MSNManualReleaseIndexAsset(
        role=role,
        filename=filename,
        sha256=_safe_text(raw.get("sha256", raw.get("hash", raw.get("content_sha256", "")))),
        byte_count=_read_int(raw.get("byte_count", raw.get("bytes", raw.get("size", 0)))),
        source=source,
    )


def _normalise_assets(raw_assets: Any, *, source: str) -> list[MSNManualReleaseIndexAsset]:
    if not isinstance(raw_assets, Sequence) or isinstance(raw_assets, (str, bytes, bytearray)):
        return []
    assets: list[MSNManualReleaseIndexAsset] = []
    seen: set[tuple[str, str, str, str]] = set()
    for index, raw in enumerate(raw_assets, start=1):
        if not isinstance(raw, Mapping):
            continue
        asset = _normalise_asset(raw, source=source, index=index)
        key = (asset.role, asset.filename, asset.sha256, asset.source)
        if key in seen:
            continue
        seen.add(key)
        assets.append(asset)
    return assets


def _store_assets(package_store_report: Mapping[str, Any] | None) -> list[MSNManualReleaseIndexAsset]:
    if not isinstance(package_store_report, Mapping):
        return []
    return _normalise_assets(package_store_report.get("stored_files", package_store_report.get("files", [])), source="approved_release_package_store")


def _release_package_assets(approved_release_package: Mapping[str, Any]) -> list[MSNManualReleaseIndexAsset]:
    return _normalise_assets(approved_release_package.get("assets", []), source="approved_release_package")


def _lineage_entry(role: str, identifier: Any, status: Any) -> MSNManualReleaseLineageEntry:
    return MSNManualReleaseLineageEntry(
        role=_safe_id(role, default="lineage"),
        identifier=_safe_id(identifier, default=f"missing_{role}"),
        status=_safe_text(status, default="UNKNOWN"),
    )


def build_msn_manual_release_index(
    approved_release_package: Mapping[str, Any],
    *,
    release_package_store_report: Mapping[str, Any] | None = None,
    index_label: str = "operator_release_index",
) -> MSNManualReleaseIndexReport:
    if not isinstance(approved_release_package, Mapping):
        raise MSNManualReleaseIndexError("approved_release_package must be a JSON object")
    if _contains_path_like(approved_release_package) or _contains_path_like(release_package_store_report or {}):
        raise MSNManualReleaseIndexError("release index inputs must not include full local paths")

    issues: list[str] = []
    if approved_release_package.get("schema_version") != MSN_MANUAL_APPROVED_RELEASE_PACKAGE_SCHEMA_VERSION:
        issues.append("approved release package schema_version mismatch")
    if approved_release_package.get("release_status") != "TOTAL_EXPORT_RELEASE_PACKAGE_READY":
        issues.append("approved release package status is not TOTAL_EXPORT_RELEASE_PACKAGE_READY")
    if approved_release_package.get("ready_for_total_export_release") is not True:
        issues.append("approved release package is not ready_for_total_export_release")
    if _read_int(approved_release_package.get("issue_count", 0)) != 0:
        issues.append("approved release package issue_count is non-zero")

    queue_update = approved_release_package.get("evidence_queue_update")
    if not isinstance(queue_update, Mapping) or queue_update.get("queue_status") != "TOTAL_EXPORT_RELEASE_READY":
        issues.append("approved release evidence queue update is not TOTAL_EXPORT_RELEASE_READY")
    release_manifest = approved_release_package.get("total_export_release_manifest")
    if not isinstance(release_manifest, Mapping) or release_manifest.get("release_status") != "TOTAL_EXPORT_RELEASE_PACKAGE_READY":
        issues.append("approved release manifest is not TOTAL_EXPORT_RELEASE_PACKAGE_READY")

    flags = approved_release_package.get("safety_flags")
    if not isinstance(flags, Mapping):
        issues.append("approved release package missing safety_flags")
    else:
        for flag in (
            "metadata_only_release_package",
            "explicit_approved_handoff_json_only",
            "no_live_http",
            "no_browser_automation",
            "no_full_local_paths",
            "no_credential_reads",
        ):
            if flags.get(flag) is not True:
                issues.append(f"approved release package safety flag not true: {flag}")

    if isinstance(release_package_store_report, Mapping):
        if release_package_store_report.get("store_status") not in {"STORED", "READY", "PACKAGE_STORED"}:
            issues.append("release package store status is not recognised")
        stored_release_id = _safe_text(release_package_store_report.get("release_id"))
        if stored_release_id and stored_release_id != _safe_text(approved_release_package.get("release_id")):
            issues.append("release package store release_id does not match approved release package")

    release_id = _safe_id(approved_release_package.get("release_id"), default="msn_manual_release")
    queue_item_id = _safe_id(approved_release_package.get("queue_item_id"), default="msn_manual_queue_item")
    handoff_id = _safe_id(approved_release_package.get("handoff_id"), default="msn_manual_handoff")
    decision_id = _safe_id(approved_release_package.get("decision_id"), default="msn_manual_decision")
    source_url = _safe_text(approved_release_package.get("source_url"))
    named_site = _safe_text(approved_release_package.get("named_site"), default="msn")
    named_action = _safe_text(approved_release_package.get("named_action"), default="msn_manual_capture")
    article_title = _safe_text(approved_release_package.get("article_title"), default="MSN manual capture")
    label = _safe_id(index_label, default="operator_release_index")

    for key, value in {
        "release_id": release_id,
        "queue_item_id": queue_item_id,
        "handoff_id": handoff_id,
        "decision_id": decision_id,
        "source_url": source_url,
        "article_title": article_title,
    }.items():
        if not value:
            issues.append(f"missing {key}")

    assets = _release_package_assets(approved_release_package)
    assets.extend(_store_assets(release_package_store_report))
    if not assets:
        issues.append("release index has no assets")
    for asset in assets:
        if not asset.filename:
            issues.append(f"asset missing filename for role {asset.role}")
        if not asset.sha256:
            issues.append(f"asset missing sha256 for role {asset.role}")
        if asset.byte_count <= 0:
            issues.append(f"asset missing byte_count for role {asset.role}")

    ready = not issues
    status = MSN_MANUAL_RELEASE_INDEX_STATUS_READY if ready else MSN_MANUAL_RELEASE_INDEX_STATUS_NEEDS_REVIEW
    index_seed = {
        "release_id": release_id,
        "queue_item_id": queue_item_id,
        "handoff_id": handoff_id,
        "decision_id": decision_id,
        "index_label": label,
        "asset_hashes": sorted(asset.sha256 for asset in assets if asset.sha256),
    }
    index_id = f"{release_id}.index.{_sha256_json(index_seed)[:12]}"

    lineage = [
        _lineage_entry("approved_release_package", release_id, approved_release_package.get("release_status")),
        _lineage_entry("approved_export_handoff", handoff_id, "APPROVED_EXPORT_HANDOFF_READY"),
        _lineage_entry("evidence_review_decision", decision_id, "APPROVED"),
        _lineage_entry("evidence_queue_item", queue_item_id, "TOTAL_EXPORT_RELEASE_READY"),
    ]

    report_without_hash: dict[str, Any] = {
        "schema_version": MSN_MANUAL_RELEASE_INDEX_SCHEMA_VERSION,
        "index_id": index_id,
        "index_label": label,
        "release_id": release_id,
        "queue_item_id": queue_item_id,
        "handoff_id": handoff_id,
        "decision_id": decision_id,
        "source_url": source_url,
        "named_site": named_site,
        "named_action": named_action,
        "article_title": article_title,
        "release_index_status": status,
        "ready_for_total_export_release_index": ready,
        "issue_count": len(issues),
        "issues": issues,
        "assets": [asdict(asset) for asset in assets],
        "lineage": [asdict(entry) for entry in lineage],
        "evidence_queue_release_update": {
            "queue_item_id": queue_item_id,
            "queue_status": "RELEASE_INDEX_READY" if ready else "BLOCKED_PENDING_RELEASE_INDEX_REVIEW",
            "release_id": release_id,
            "index_id": index_id,
            "handoff_id": handoff_id,
            "decision_id": decision_id,
        },
        "total_export_release_handoff": {
            "release_id": release_id,
            "index_id": index_id,
            "release_handoff_status": "READY_FOR_RELEASE_INDEX_CONSUMPTION" if ready else "BLOCKED_PENDING_RELEASE_INDEX_REVIEW",
            "asset_count": len(assets),
            "asset_roles": [asset.role for asset in assets],
        },
        "safety_flags": {
            "metadata_only_release_index": True,
            "explicit_approved_release_json_only": True,
            "explicit_release_store_json_only": True,
            "no_live_http": True,
            "no_browser_automation": True,
            "no_archive_submission": True,
            "no_media_downloads": True,
            "no_credential_reads": True,
            "no_folder_scans": True,
            "no_full_local_paths": True,
            "no_completed_live_capture_claim": True,
        },
    }
    index_hash = _sha256_json(report_without_hash)
    return MSNManualReleaseIndexReport(
        schema_version=MSN_MANUAL_RELEASE_INDEX_SCHEMA_VERSION,
        index_id=index_id,
        index_label=label,
        release_id=release_id,
        queue_item_id=queue_item_id,
        handoff_id=handoff_id,
        decision_id=decision_id,
        source_url=source_url,
        named_site=named_site,
        named_action=named_action,
        article_title=article_title,
        release_index_status=status,
        ready_for_total_export_release_index=ready,
        issue_count=len(issues),
        issues=issues,
        assets=assets,
        lineage=lineage,
        evidence_queue_release_update=report_without_hash["evidence_queue_release_update"],
        total_export_release_handoff=report_without_hash["total_export_release_handoff"],
        safety_flags=report_without_hash["safety_flags"],
        index_hash=index_hash,
    )


def msn_manual_release_index_to_json(report: MSNManualReleaseIndexReport) -> str:
    return json.dumps(asdict(report), indent=2, sort_keys=True, ensure_ascii=False) + "\n"
