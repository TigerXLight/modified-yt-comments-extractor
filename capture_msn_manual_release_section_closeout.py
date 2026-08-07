from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass, field
from typing import Any, Mapping, Sequence

MSN_MANUAL_RELEASE_SECTION_CLOSEOUT_SCHEMA_VERSION = "msn_manual_release_section_closeout_v1"
MSN_MANUAL_RELEASE_EXPORT_BUNDLE_SCHEMA_VERSION = "msn_manual_release_export_bundle_v1"
MSN_MANUAL_RELEASE_SECTION_CLOSEOUT_STATUS_READY = "MSN_MANUAL_RELEASE_SECTION_CLOSED"
MSN_MANUAL_RELEASE_SECTION_CLOSEOUT_STATUS_NEEDS_REVIEW = "MSN_MANUAL_RELEASE_SECTION_NEEDS_REVIEW"

_SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9_.-]+")
_PATH_RE = re.compile(r"(?:(?<![A-Za-z])[A-Za-z]:\\|(?<![A-Za-z])[A-Za-z]:/|\\\\|/(?:home|mnt|Users|Volumes|tmp|var)/)")


@dataclass(frozen=True)
class MSNManualReleaseSectionCloseoutAsset:
    role: str
    filename: str
    sha256: str = ""
    byte_count: int = 0
    source: str = "release_export_bundle"


@dataclass(frozen=True)
class MSNManualReleaseSectionCloseoutReport:
    schema_version: str
    closeout_id: str
    export_bundle_id: str
    index_id: str
    release_id: str
    queue_item_id: str
    source_url: str
    named_site: str
    named_action: str
    article_title: str
    closeout_status: str
    ready_for_section_closeout: bool
    ready_for_total_export_release_record: bool
    issue_count: int
    issues: list[str] = field(default_factory=list)
    assets: list[MSNManualReleaseSectionCloseoutAsset] = field(default_factory=list)
    final_release_checklist: dict[str, bool] = field(default_factory=dict)
    total_export_release_record: dict[str, Any] = field(default_factory=dict)
    evidence_queue_closeout_update: dict[str, str] = field(default_factory=dict)
    safety_flags: dict[str, bool] = field(default_factory=dict)
    closeout_hash: str = ""


class MSNManualReleaseSectionCloseoutError(ValueError):
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


def _normalise_asset(raw: Mapping[str, Any], *, source: str, index: int) -> MSNManualReleaseSectionCloseoutAsset:
    role = _safe_id(raw.get("role", raw.get("file_role", raw.get("asset_role", f"asset_{index}"))), default=f"asset_{index}")
    filename = _safe_filename(
        raw.get("filename", raw.get("safe_filename", raw.get("relative_path", raw.get("name", f"asset_{index}.json")))),
        fallback=f"asset_{index}.json",
    )
    return MSNManualReleaseSectionCloseoutAsset(
        role=role,
        filename=filename,
        sha256=_safe_text(raw.get("sha256", raw.get("hash", raw.get("content_sha256", "")))),
        byte_count=_read_int(raw.get("byte_count", raw.get("bytes", raw.get("size", 0)))),
        source=source,
    )


def _normalise_assets(raw_assets: Any, *, source: str) -> list[MSNManualReleaseSectionCloseoutAsset]:
    if not isinstance(raw_assets, Sequence) or isinstance(raw_assets, (str, bytes, bytearray)):
        return []
    assets: list[MSNManualReleaseSectionCloseoutAsset] = []
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


def _bundle_assets(bundle_report: Mapping[str, Any]) -> list[MSNManualReleaseSectionCloseoutAsset]:
    assets = _normalise_assets(bundle_report.get("assets", []), source="release_export_bundle")
    checksum = bundle_report.get("checksum_manifest")
    if isinstance(checksum, Mapping):
        checksum_assets = []
        for filename, sha256 in dict(checksum.get("sha256_by_filename", {})).items():
            checksum_assets.append({"role": "checksum_manifest_entry", "filename": filename, "sha256": sha256})
        assets.extend(_normalise_assets(checksum_assets, source="checksum_manifest"))
    seen: set[tuple[str, str, str, str]] = set()
    unique: list[MSNManualReleaseSectionCloseoutAsset] = []
    for asset in assets:
        key = (asset.role, asset.filename, asset.sha256, asset.source)
        if key not in seen:
            seen.add(key)
            unique.append(asset)
    return unique


def _store_assets(store_report: Mapping[str, Any] | None) -> list[MSNManualReleaseSectionCloseoutAsset]:
    if not isinstance(store_report, Mapping):
        return []
    return _normalise_assets(store_report.get("stored_files", []), source="release_export_bundle_store")


def build_msn_manual_release_section_closeout(
    release_export_bundle: Mapping[str, Any],
    *,
    release_export_bundle_store_report: Mapping[str, Any] | None = None,
    closeout_label: str = "operator_release_section_closeout",
) -> MSNManualReleaseSectionCloseoutReport:
    if not isinstance(release_export_bundle, Mapping):
        raise MSNManualReleaseSectionCloseoutError("release_export_bundle must be a JSON object")
    if _contains_path_like(release_export_bundle) or _contains_path_like(release_export_bundle_store_report or {}):
        raise MSNManualReleaseSectionCloseoutError("release section closeout inputs must not include full local paths")

    issues: list[str] = []
    if release_export_bundle.get("schema_version") != MSN_MANUAL_RELEASE_EXPORT_BUNDLE_SCHEMA_VERSION:
        issues.append("release export bundle schema_version mismatch")
    if release_export_bundle.get("export_bundle_status") != "MSN_MANUAL_RELEASE_EXPORT_BUNDLE_READY":
        issues.append("release export bundle status is not MSN_MANUAL_RELEASE_EXPORT_BUNDLE_READY")
    if release_export_bundle.get("ready_for_total_export_handoff") is not True:
        issues.append("release export bundle is not ready_for_total_export_handoff")
    if _read_int(release_export_bundle.get("issue_count", 0)) != 0:
        issues.append("release export bundle issue_count is non-zero")

    handoff_manifest = release_export_bundle.get("total_export_handoff_manifest")
    if not isinstance(handoff_manifest, Mapping) or handoff_manifest.get("handoff_status") != "TOTAL_EXPORT_HANDOFF_READY":
        issues.append("Total Export handoff manifest is not TOTAL_EXPORT_HANDOFF_READY")

    queue_update = release_export_bundle.get("evidence_queue_final_update")
    if not isinstance(queue_update, Mapping) or queue_update.get("queue_status") != "TOTAL_EXPORT_HANDOFF_READY":
        issues.append("evidence queue final update is not TOTAL_EXPORT_HANDOFF_READY")

    checksum_manifest = release_export_bundle.get("checksum_manifest")
    if not isinstance(checksum_manifest, Mapping) or checksum_manifest.get("checksum_status") != "CHECKSUMS_READY":
        issues.append("checksum manifest is not CHECKSUMS_READY")

    flags = release_export_bundle.get("safety_flags")
    if not isinstance(flags, Mapping):
        issues.append("release export bundle missing safety_flags")
    else:
        for flag in (
            "metadata_only_export_bundle",
            "explicit_release_index_json_only",
            "no_live_http",
            "no_browser_automation",
            "no_archive_submission",
            "no_media_downloads",
            "no_credential_reads",
            "no_folder_scans",
            "no_file_moves",
            "no_full_local_paths",
        ):
            if flags.get(flag) is not True:
                issues.append(f"release export bundle safety flag not true: {flag}")

    export_bundle_id = _safe_id(release_export_bundle.get("export_bundle_id"), default="msn_manual_release_export_bundle")
    index_id = _safe_id(release_export_bundle.get("index_id"), default="msn_manual_release_index")
    release_id = _safe_id(release_export_bundle.get("release_id"), default="msn_manual_release")
    queue_item_id = _safe_id(release_export_bundle.get("queue_item_id"), default="msn_manual_queue_item")
    source_url = _safe_text(release_export_bundle.get("source_url"))
    named_site = _safe_text(release_export_bundle.get("named_site"), default="msn")
    named_action = _safe_text(release_export_bundle.get("named_action"), default="msn_manual_capture")
    article_title = _safe_text(release_export_bundle.get("article_title"), default="MSN manual capture")
    label = _safe_id(closeout_label, default="operator_release_section_closeout")

    if isinstance(release_export_bundle_store_report, Mapping):
        if release_export_bundle_store_report.get("store_status") != "STORED":
            issues.append("release export bundle store report is not STORED")
        if release_export_bundle_store_report.get("export_bundle_id") != export_bundle_id:
            issues.append("release export bundle store export_bundle_id does not match bundle")
        if _read_int(release_export_bundle_store_report.get("output_file_count", 0)) < 3:
            issues.append("release export bundle store is missing expected output files")

    for key, value in {
        "export_bundle_id": export_bundle_id,
        "index_id": index_id,
        "release_id": release_id,
        "queue_item_id": queue_item_id,
        "source_url": source_url,
        "article_title": article_title,
    }.items():
        if not _safe_text(value):
            issues.append(f"missing {key}")

    assets = _bundle_assets(release_export_bundle) + _store_assets(release_export_bundle_store_report)
    if not assets:
        issues.append("release section closeout has no asset metadata")
    if not any(asset.role == "msn_manual_release_export_bundle" for asset in assets):
        issues.append("release section closeout missing release export bundle stored asset")
    if not any(asset.role == "msn_manual_release_export_manifest" for asset in assets):
        issues.append("release section closeout missing release export manifest stored asset")
    if not any(asset.sha256 for asset in assets):
        issues.append("release section closeout has no asset hashes")

    closeout_id = f"{release_id}.closeout.{_sha256_json({'export_bundle_id': export_bundle_id, 'label': label})[:12]}"
    final_release_checklist = {
        "release_export_bundle_ready": "release export bundle status is not MSN_MANUAL_RELEASE_EXPORT_BUNDLE_READY" not in issues,
        "total_export_handoff_ready": isinstance(handoff_manifest, Mapping) and handoff_manifest.get("handoff_status") == "TOTAL_EXPORT_HANDOFF_READY",
        "evidence_queue_final_update_ready": isinstance(queue_update, Mapping) and queue_update.get("queue_status") == "TOTAL_EXPORT_HANDOFF_READY",
        "checksums_ready": isinstance(checksum_manifest, Mapping) and checksum_manifest.get("checksum_status") == "CHECKSUMS_READY",
        "asset_hashes_present": any(asset.sha256 for asset in assets),
        "safe_metadata_only": not _contains_path_like(release_export_bundle),
        "store_report_ready": not isinstance(release_export_bundle_store_report, Mapping) or release_export_bundle_store_report.get("store_status") == "STORED",
    }
    ready = not issues
    total_export_release_record = {
        "release_record_status": "TOTAL_EXPORT_RELEASE_RECORD_READY" if ready else "TOTAL_EXPORT_RELEASE_RECORD_NEEDS_REVIEW",
        "closeout_id": closeout_id,
        "export_bundle_id": export_bundle_id,
        "release_id": release_id,
        "index_id": index_id,
        "queue_item_id": queue_item_id,
        "source_url": source_url,
        "named_site": named_site,
        "named_action": named_action,
        "article_title": article_title,
        "required_operator_action": "attach_closeout_to_total_export_release_record" if ready else "review_release_section_closeout_issues",
        "asset_count": len(assets),
        "asset_roles": sorted({asset.role for asset in assets}),
    }
    evidence_queue_closeout_update = {
        "queue_item_id": queue_item_id,
        "queue_status": "TOTAL_EXPORT_RELEASE_CLOSED" if ready else "TOTAL_EXPORT_RELEASE_CLOSEOUT_NEEDS_REVIEW",
        "release_id": release_id,
        "index_id": index_id,
        "export_bundle_id": export_bundle_id,
        "closeout_id": closeout_id,
        "next_action": "release_record_import" if ready else "review_release_section_closeout_issues",
    }
    safety_flags = {
        "metadata_only_release_closeout": True,
        "explicit_release_export_bundle_json_only": True,
        "no_live_http": True,
        "no_browser_automation": True,
        "no_archive_submission": True,
        "no_media_downloads": True,
        "no_credential_reads": True,
        "no_folder_scans": True,
        "no_file_moves": True,
        "no_full_local_paths": True,
    }
    status = MSN_MANUAL_RELEASE_SECTION_CLOSEOUT_STATUS_READY if ready else MSN_MANUAL_RELEASE_SECTION_CLOSEOUT_STATUS_NEEDS_REVIEW
    report = MSNManualReleaseSectionCloseoutReport(
        schema_version=MSN_MANUAL_RELEASE_SECTION_CLOSEOUT_SCHEMA_VERSION,
        closeout_id=closeout_id,
        export_bundle_id=export_bundle_id,
        index_id=index_id,
        release_id=release_id,
        queue_item_id=queue_item_id,
        source_url=source_url,
        named_site=named_site,
        named_action=named_action,
        article_title=article_title,
        closeout_status=status,
        ready_for_section_closeout=ready,
        ready_for_total_export_release_record=ready,
        issue_count=len(issues),
        issues=issues,
        assets=assets,
        final_release_checklist=final_release_checklist,
        total_export_release_record=total_export_release_record,
        evidence_queue_closeout_update=evidence_queue_closeout_update,
        safety_flags=safety_flags,
    )
    payload = asdict(report)
    payload.pop("closeout_hash", None)
    return MSNManualReleaseSectionCloseoutReport(**{**payload, "closeout_hash": _sha256_json(payload)})


def msn_manual_release_section_closeout_to_json(report: MSNManualReleaseSectionCloseoutReport) -> dict[str, Any]:
    return asdict(report)
