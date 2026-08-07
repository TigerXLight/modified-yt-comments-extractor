from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass, field
from typing import Any, Mapping, Sequence

MSN_MANUAL_APPROVED_RELEASE_PACKAGE_SCHEMA_VERSION = "msn_manual_approved_release_package_v1"
MSN_MANUAL_APPROVED_EXPORT_HANDOFF_SCHEMA_VERSION = "msn_manual_approved_export_handoff_v1"
MSN_MANUAL_APPROVED_RELEASE_PACKAGE_STATUS_READY = "TOTAL_EXPORT_RELEASE_PACKAGE_READY"
MSN_MANUAL_APPROVED_RELEASE_PACKAGE_STATUS_NEEDS_REVIEW = "TOTAL_EXPORT_RELEASE_PACKAGE_NEEDS_REVIEW"

_SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9_.-]+")
_PATH_RE = re.compile(r"(?:(?<![A-Za-z])[A-Za-z]:\\|(?<![A-Za-z])[A-Za-z]:/|\\\\|/(?:home|mnt|Users|Volumes|tmp|var)/)")


@dataclass(frozen=True)
class MSNManualApprovedReleaseAsset:
    role: str
    filename: str
    sha256: str = ""
    byte_count: int = 0
    source: str = "approved_handoff"


@dataclass(frozen=True)
class MSNManualApprovedReleaseStep:
    step_id: str
    label: str
    command_hint: str
    required: bool = True


@dataclass(frozen=True)
class MSNManualApprovedReleasePackageReport:
    schema_version: str
    release_id: str
    release_label: str
    queue_item_id: str
    handoff_id: str
    decision_id: str
    source_url: str
    named_site: str
    named_action: str
    article_title: str
    release_status: str
    ready_for_total_export_release: bool
    issue_count: int
    issues: list[str] = field(default_factory=list)
    assets: list[MSNManualApprovedReleaseAsset] = field(default_factory=list)
    release_steps: list[MSNManualApprovedReleaseStep] = field(default_factory=list)
    evidence_queue_update: dict[str, str] = field(default_factory=dict)
    total_export_release_manifest: dict[str, Any] = field(default_factory=dict)
    safety_flags: dict[str, bool] = field(default_factory=dict)
    release_hash: str = ""


class MSNManualApprovedReleasePackageError(ValueError):
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


def _normalise_asset(raw: Mapping[str, Any], *, source: str, index: int) -> MSNManualApprovedReleaseAsset:
    role = _safe_id(raw.get("role", raw.get("file_role", raw.get("asset_role", f"asset_{index}"))), default=f"asset_{index}")
    filename = _safe_filename(
        raw.get("filename", raw.get("safe_filename", raw.get("relative_path", raw.get("name", f"asset_{index}.json")))),
        fallback=f"asset_{index}.json",
    )
    return MSNManualApprovedReleaseAsset(
        role=role,
        filename=filename,
        sha256=_safe_text(raw.get("sha256", raw.get("hash", raw.get("content_sha256", "")))),
        byte_count=_read_int(raw.get("byte_count", raw.get("bytes", raw.get("size", 0)))),
        source=source,
    )


def _normalise_assets(raw_assets: Any, *, source: str) -> list[MSNManualApprovedReleaseAsset]:
    if not isinstance(raw_assets, Sequence) or isinstance(raw_assets, (str, bytes, bytearray)):
        return []
    assets: list[MSNManualApprovedReleaseAsset] = []
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


def _package_store_assets(package_store_report: Mapping[str, Any] | None) -> list[MSNManualApprovedReleaseAsset]:
    if not isinstance(package_store_report, Mapping):
        return []
    raw_files = package_store_report.get("stored_files", package_store_report.get("files", []))
    return _normalise_assets(raw_files, source="total_export_package_store")


def _release_steps() -> list[MSNManualApprovedReleaseStep]:
    return [
        MSNManualApprovedReleaseStep(
            step_id="verify_approved_export_handoff",
            label="Verify the approved Evidence Review handoff is release-ready",
            command_hint="capture_msn_manual_approved_export_handoff_verifier.py",
        ),
        MSNManualApprovedReleaseStep(
            step_id="verify_package_file_hashes",
            label="Verify safe package filenames, byte counts, and sha256 hashes",
            command_hint="capture_msn_manual_total_export_verifier.py",
        ),
        MSNManualApprovedReleaseStep(
            step_id="write_release_manifest",
            label="Write the release manifest and evidence queue release update JSON",
            command_hint="capture_msn_manual_approved_release_package_cli.py",
        ),
        MSNManualApprovedReleaseStep(
            step_id="handoff_to_total_export_release",
            label="Make the approved MSN manual capture package available to the Total Export release flow",
            command_hint="total_export_prepare_cli.py --source-mode msn_manual_approved_release_package",
        ),
    ]


def build_msn_manual_approved_release_package(
    approved_handoff: Mapping[str, Any],
    *,
    package_store_report: Mapping[str, Any] | None = None,
    release_label: str = "operator_release",
) -> MSNManualApprovedReleasePackageReport:
    if not isinstance(approved_handoff, Mapping):
        raise MSNManualApprovedReleasePackageError("approved_handoff must be a JSON object")
    if _contains_path_like(approved_handoff) or _contains_path_like(package_store_report or {}):
        raise MSNManualApprovedReleasePackageError("approved release inputs must not include full local paths")

    issues: list[str] = []
    if approved_handoff.get("schema_version") != MSN_MANUAL_APPROVED_EXPORT_HANDOFF_SCHEMA_VERSION:
        issues.append("approved handoff schema_version mismatch")
    if approved_handoff.get("handoff_status") != "APPROVED_EXPORT_HANDOFF_READY":
        issues.append("approved handoff status is not APPROVED_EXPORT_HANDOFF_READY")
    if approved_handoff.get("ready_for_total_export_release") is not True:
        issues.append("approved handoff is not ready_for_total_export_release")
    if _read_int(approved_handoff.get("issue_count", 0)) != 0:
        issues.append("approved handoff issue_count is non-zero")
    if approved_handoff.get("review_decision") != "APPROVED":
        issues.append("approved handoff review_decision is not APPROVED")

    queue_item_id = _safe_id(approved_handoff.get("queue_item_id"), default="msn_manual_queue_item")
    handoff_id = _safe_id(approved_handoff.get("handoff_id"), default="msn_manual_approved_handoff")
    decision_id = _safe_id(approved_handoff.get("decision_id"), default="msn_manual_decision")
    source_url = _safe_text(approved_handoff.get("source_url"))
    named_site = _safe_text(approved_handoff.get("named_site"), default="msn")
    named_action = _safe_text(approved_handoff.get("named_action"), default="msn_manual_capture")
    article_title = _safe_text(approved_handoff.get("article_title"), default="MSN manual capture")
    label = _safe_id(release_label, default="operator_release")

    for key, value in {
        "queue_item_id": queue_item_id,
        "handoff_id": handoff_id,
        "decision_id": decision_id,
        "source_url": source_url,
        "article_title": article_title,
    }.items():
        if not value:
            issues.append(f"missing {key}")

    queue_update = approved_handoff.get("evidence_queue_update")
    if not isinstance(queue_update, Mapping) or queue_update.get("queue_status") != "READY_FOR_TOTAL_EXPORT_RELEASE":
        issues.append("approved handoff evidence queue update is not READY_FOR_TOTAL_EXPORT_RELEASE")
    total_handoff = approved_handoff.get("total_export_handoff")
    if not isinstance(total_handoff, Mapping) or total_handoff.get("handoff_status") != "READY_FOR_TOTAL_EXPORT_RELEASE":
        issues.append("approved handoff Total Export status is not READY_FOR_TOTAL_EXPORT_RELEASE")

    flags = approved_handoff.get("safety_flags")
    if not isinstance(flags, Mapping):
        issues.append("approved handoff missing safety_flags")
    else:
        for flag in (
            "metadata_only_handoff",
            "explicit_decision_json_only",
            "no_live_http",
            "no_browser_automation",
            "no_full_local_paths",
            "no_credential_reads",
        ):
            if flags.get(flag) is not True:
                issues.append(f"approved handoff safety flag not true: {flag}")

    assets = _normalise_assets(approved_handoff.get("assets", []), source="approved_handoff")
    assets.extend(_package_store_assets(package_store_report))
    if not assets:
        issues.append("approved release package has no assets")
    for asset in assets:
        if not asset.filename:
            issues.append(f"asset missing filename for role {asset.role}")
        if not asset.sha256:
            issues.append(f"asset missing sha256 for role {asset.role}")

    if isinstance(package_store_report, Mapping):
        if not _package_store_assets(package_store_report):
            issues.append("package_store_report has no stored files")
        store_status = _safe_text(package_store_report.get("store_status"), default="STORED")
        if store_status not in {"STORED", "READY", "PACKAGE_STORED"}:
            issues.append("package_store_report store_status is not recognised")

    ready = not issues
    release_status = MSN_MANUAL_APPROVED_RELEASE_PACKAGE_STATUS_READY if ready else MSN_MANUAL_APPROVED_RELEASE_PACKAGE_STATUS_NEEDS_REVIEW
    release_seed = {
        "queue_item_id": queue_item_id,
        "handoff_id": handoff_id,
        "decision_id": decision_id,
        "release_label": label,
        "asset_hashes": sorted(asset.sha256 for asset in assets if asset.sha256),
    }
    release_id = f"{queue_item_id}.release.{_sha256_json(release_seed)[:12]}"

    report_without_hash: dict[str, Any] = {
        "schema_version": MSN_MANUAL_APPROVED_RELEASE_PACKAGE_SCHEMA_VERSION,
        "release_id": release_id,
        "release_label": label,
        "queue_item_id": queue_item_id,
        "handoff_id": handoff_id,
        "decision_id": decision_id,
        "source_url": source_url,
        "named_site": named_site,
        "named_action": named_action,
        "article_title": article_title,
        "release_status": release_status,
        "ready_for_total_export_release": ready,
        "issue_count": len(issues),
        "issues": issues,
        "assets": [asdict(asset) for asset in assets],
        "release_steps": [asdict(step) for step in _release_steps()],
        "evidence_queue_update": {
            "queue_item_id": queue_item_id,
            "queue_status": "TOTAL_EXPORT_RELEASE_READY" if ready else "BLOCKED_PENDING_RELEASE_REVIEW",
            "source_handoff_id": handoff_id,
            "source_decision_id": decision_id,
            "release_id": release_id,
        },
        "total_export_release_manifest": {
            "release_id": release_id,
            "queue_item_id": queue_item_id,
            "handoff_id": handoff_id,
            "decision_id": decision_id,
            "release_status": release_status,
            "asset_count": len(assets),
            "asset_filenames": [asset.filename for asset in assets],
            "next_cli": "total_export_prepare_cli.py",
        },
        "safety_flags": {
            "metadata_only_release_package": True,
            "explicit_approved_handoff_json_only": True,
            "explicit_package_store_json_only": True,
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
    release_hash = _sha256_json(report_without_hash)
    return MSNManualApprovedReleasePackageReport(
        schema_version=MSN_MANUAL_APPROVED_RELEASE_PACKAGE_SCHEMA_VERSION,
        release_id=release_id,
        release_label=label,
        queue_item_id=queue_item_id,
        handoff_id=handoff_id,
        decision_id=decision_id,
        source_url=source_url,
        named_site=named_site,
        named_action=named_action,
        article_title=article_title,
        release_status=release_status,
        ready_for_total_export_release=ready,
        issue_count=len(issues),
        issues=issues,
        assets=assets,
        release_steps=_release_steps(),
        evidence_queue_update=report_without_hash["evidence_queue_update"],
        total_export_release_manifest=report_without_hash["total_export_release_manifest"],
        safety_flags=report_without_hash["safety_flags"],
        release_hash=release_hash,
    )


def msn_manual_approved_release_package_to_json(report: MSNManualApprovedReleasePackageReport) -> str:
    return json.dumps(asdict(report), indent=2, sort_keys=True, ensure_ascii=False) + "\n"
