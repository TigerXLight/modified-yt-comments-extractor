from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass, field
from typing import Any, Mapping, Sequence

MSN_MANUAL_RELEASE_EXPORT_BUNDLE_SCHEMA_VERSION = "msn_manual_release_export_bundle_v1"
MSN_MANUAL_RELEASE_INDEX_SCHEMA_VERSION = "msn_manual_release_index_v1"
MSN_MANUAL_RELEASE_EXPORT_BUNDLE_STATUS_READY = "MSN_MANUAL_RELEASE_EXPORT_BUNDLE_READY"
MSN_MANUAL_RELEASE_EXPORT_BUNDLE_STATUS_NEEDS_REVIEW = "MSN_MANUAL_RELEASE_EXPORT_BUNDLE_NEEDS_REVIEW"

_SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9_.-]+")
_PATH_RE = re.compile(r"(?:(?<![A-Za-z])[A-Za-z]:\\|(?<![A-Za-z])[A-Za-z]:/|\\\\|/(?:home|mnt|Users|Volumes|tmp|var)/)")


@dataclass(frozen=True)
class MSNManualReleaseExportBundleAsset:
    role: str
    filename: str
    sha256: str = ""
    byte_count: int = 0
    source: str = "release_index"


@dataclass(frozen=True)
class MSNManualReleaseExportBundleReport:
    schema_version: str
    export_bundle_id: str
    export_label: str
    index_id: str
    release_id: str
    queue_item_id: str
    source_url: str
    named_site: str
    named_action: str
    article_title: str
    export_bundle_status: str
    ready_for_total_export_handoff: bool
    issue_count: int
    issues: list[str] = field(default_factory=list)
    assets: list[MSNManualReleaseExportBundleAsset] = field(default_factory=list)
    total_export_handoff_manifest: dict[str, Any] = field(default_factory=dict)
    evidence_queue_final_update: dict[str, str] = field(default_factory=dict)
    checksum_manifest: dict[str, Any] = field(default_factory=dict)
    safety_flags: dict[str, bool] = field(default_factory=dict)
    export_bundle_hash: str = ""


class MSNManualReleaseExportBundleError(ValueError):
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


def _normalise_asset(raw: Mapping[str, Any], *, source: str, index: int) -> MSNManualReleaseExportBundleAsset:
    role = _safe_id(raw.get("role", raw.get("file_role", raw.get("asset_role", f"asset_{index}"))), default=f"asset_{index}")
    filename = _safe_filename(
        raw.get("filename", raw.get("safe_filename", raw.get("relative_path", raw.get("name", f"asset_{index}.json")))),
        fallback=f"asset_{index}.json",
    )
    return MSNManualReleaseExportBundleAsset(
        role=role,
        filename=filename,
        sha256=_safe_text(raw.get("sha256", raw.get("hash", raw.get("content_sha256", "")))),
        byte_count=_read_int(raw.get("byte_count", raw.get("bytes", raw.get("size", 0)))),
        source=source,
    )


def _normalise_assets(raw_assets: Any, *, source: str) -> list[MSNManualReleaseExportBundleAsset]:
    if not isinstance(raw_assets, Sequence) or isinstance(raw_assets, (str, bytes, bytearray)):
        return []
    assets: list[MSNManualReleaseExportBundleAsset] = []
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


def _release_index_assets(release_index: Mapping[str, Any]) -> list[MSNManualReleaseExportBundleAsset]:
    assets = _normalise_assets(release_index.get("assets", []), source="release_index")
    inventory = release_index.get("total_export_release_handoff", {})
    if isinstance(inventory, Mapping):
        assets.extend(_normalise_assets(inventory.get("assets", []), source="total_export_release_handoff"))
    seen: set[tuple[str, str, str, str]] = set()
    unique: list[MSNManualReleaseExportBundleAsset] = []
    for asset in assets:
        key = (asset.role, asset.filename, asset.sha256, asset.source)
        if key not in seen:
            seen.add(key)
            unique.append(asset)
    return unique


def _stored_index_assets(release_index_store_report: Mapping[str, Any] | None) -> list[MSNManualReleaseExportBundleAsset]:
    if not isinstance(release_index_store_report, Mapping):
        return []
    return _normalise_assets(release_index_store_report.get("stored_files", []), source="release_index_store")


def build_msn_manual_release_export_bundle(
    release_index: Mapping[str, Any],
    *,
    release_index_store_report: Mapping[str, Any] | None = None,
    export_label: str = "operator_total_export_handoff",
) -> MSNManualReleaseExportBundleReport:
    if not isinstance(release_index, Mapping):
        raise MSNManualReleaseExportBundleError("release_index must be a JSON object")
    if _contains_path_like(release_index) or _contains_path_like(release_index_store_report or {}):
        raise MSNManualReleaseExportBundleError("release export bundle inputs must not include full local paths")

    issues: list[str] = []
    if release_index.get("schema_version") != MSN_MANUAL_RELEASE_INDEX_SCHEMA_VERSION:
        issues.append("release index schema_version mismatch")
    if release_index.get("release_index_status") != "MSN_MANUAL_RELEASE_INDEX_READY":
        issues.append("release index status is not MSN_MANUAL_RELEASE_INDEX_READY")
    if release_index.get("ready_for_total_export_release_index") is not True:
        issues.append("release index is not ready_for_total_export_release_index")
    if _read_int(release_index.get("issue_count", 0)) != 0:
        issues.append("release index issue_count is non-zero")

    queue_update = release_index.get("evidence_queue_release_update")
    if not isinstance(queue_update, Mapping) or queue_update.get("queue_status") != "TOTAL_EXPORT_RELEASE_INDEXED":
        issues.append("release index evidence queue update is not TOTAL_EXPORT_RELEASE_INDEXED")

    handoff = release_index.get("total_export_release_handoff")
    if not isinstance(handoff, Mapping) or handoff.get("handoff_status") != "TOTAL_EXPORT_RELEASE_INDEX_READY":
        issues.append("release index Total Export handoff is not TOTAL_EXPORT_RELEASE_INDEX_READY")

    flags = release_index.get("safety_flags")
    if not isinstance(flags, Mapping):
        issues.append("release index missing safety_flags")
    else:
        for flag in (
            "metadata_only_release_index",
            "explicit_release_package_json_only",
            "no_live_http",
            "no_browser_automation",
            "no_full_local_paths",
            "no_credential_reads",
        ):
            if flags.get(flag) is not True:
                issues.append(f"release index safety flag not true: {flag}")

    if isinstance(release_index_store_report, Mapping):
        if release_index_store_report.get("store_status") not in {"STORED", "READY", "INDEX_STORED"}:
            issues.append("release index store status is not recognised")
        stored_index_id = _safe_text(release_index_store_report.get("index_id"))
        if stored_index_id and stored_index_id != _safe_text(release_index.get("index_id")):
            issues.append("release index store index_id does not match release index")

    index_id = _safe_id(release_index.get("index_id"), default="msn_manual_release_index")
    release_id = _safe_id(release_index.get("release_id"), default="msn_manual_release")
    queue_item_id = _safe_id(release_index.get("queue_item_id"), default="msn_manual_queue_item")
    source_url = _safe_text(release_index.get("source_url"))
    named_site = _safe_text(release_index.get("named_site"), default="msn")
    named_action = _safe_text(release_index.get("named_action"), default="msn_manual_capture")
    article_title = _safe_text(release_index.get("article_title"), default="MSN manual capture")
    label = _safe_id(export_label, default="operator_total_export_handoff")

    for key, value in {
        "index_id": index_id,
        "release_id": release_id,
        "queue_item_id": queue_item_id,
        "source_url": source_url,
        "article_title": article_title,
    }.items():
        if not _safe_text(value):
            issues.append(f"missing {key}")

    assets = _release_index_assets(release_index) + _stored_index_assets(release_index_store_report)
    if not assets:
        issues.append("release export bundle has no safe assets")
    if not any(asset.role == "msn_manual_release_index" for asset in assets):
        issues.append("release export bundle missing msn_manual_release_index asset")
    if not any(asset.role == "msn_manual_release_inventory" for asset in assets):
        issues.append("release export bundle missing msn_manual_release_inventory asset")
    if not any(asset.role == "msn_manual_release_queue_update" for asset in assets):
        issues.append("release export bundle missing msn_manual_release_queue_update asset")

    export_bundle_id = f"{release_id}.export_bundle.{_sha256_json({'index_id': index_id, 'release_id': release_id, 'label': label})[:12]}"
    checksum_manifest = {
        "checksum_status": "CHECKSUMS_READY" if assets else "CHECKSUMS_NEED_REVIEW",
        "asset_count": len(assets),
        "sha256_by_filename": {asset.filename: asset.sha256 for asset in assets if asset.sha256},
    }
    total_export_handoff_manifest = {
        "handoff_status": "TOTAL_EXPORT_HANDOFF_READY" if not issues else "TOTAL_EXPORT_HANDOFF_NEEDS_REVIEW",
        "export_bundle_id": export_bundle_id,
        "index_id": index_id,
        "release_id": release_id,
        "queue_item_id": queue_item_id,
        "source_url": source_url,
        "named_site": named_site,
        "named_action": named_action,
        "article_title": article_title,
        "required_operator_action": "import_release_bundle_into_total_export",
        "asset_roles": sorted({asset.role for asset in assets}),
    }
    evidence_queue_final_update = {
        "queue_item_id": queue_item_id,
        "queue_status": "TOTAL_EXPORT_HANDOFF_READY" if not issues else "TOTAL_EXPORT_HANDOFF_NEEDS_REVIEW",
        "release_id": release_id,
        "index_id": index_id,
        "export_bundle_id": export_bundle_id,
        "next_action": "total_export_release_import" if not issues else "review_release_export_bundle_issues",
    }
    safety_flags = {
        "metadata_only_export_bundle": True,
        "explicit_release_index_json_only": True,
        "no_live_http": True,
        "no_browser_automation": True,
        "no_archive_submission": True,
        "no_media_downloads": True,
        "no_credential_reads": True,
        "no_folder_scans": True,
        "no_file_moves": True,
        "no_full_local_paths": True,
    }

    status = MSN_MANUAL_RELEASE_EXPORT_BUNDLE_STATUS_READY if not issues else MSN_MANUAL_RELEASE_EXPORT_BUNDLE_STATUS_NEEDS_REVIEW
    report = MSNManualReleaseExportBundleReport(
        schema_version=MSN_MANUAL_RELEASE_EXPORT_BUNDLE_SCHEMA_VERSION,
        export_bundle_id=export_bundle_id,
        export_label=label,
        index_id=index_id,
        release_id=release_id,
        queue_item_id=queue_item_id,
        source_url=source_url,
        named_site=named_site,
        named_action=named_action,
        article_title=article_title,
        export_bundle_status=status,
        ready_for_total_export_handoff=not issues,
        issue_count=len(issues),
        issues=issues,
        assets=assets,
        total_export_handoff_manifest=total_export_handoff_manifest,
        evidence_queue_final_update=evidence_queue_final_update,
        checksum_manifest=checksum_manifest,
        safety_flags=safety_flags,
    )
    payload = asdict(report)
    payload.pop("export_bundle_hash", None)
    return MSNManualReleaseExportBundleReport(**{**payload, "export_bundle_hash": _sha256_json(payload)})


def msn_manual_release_export_bundle_to_json(report: MSNManualReleaseExportBundleReport) -> dict[str, Any]:
    return asdict(report)
