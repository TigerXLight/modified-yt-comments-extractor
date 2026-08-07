from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass, field
from typing import Any, Mapping, Sequence

MSN_MANUAL_APPROVED_EXPORT_HANDOFF_SCHEMA_VERSION = "msn_manual_approved_export_handoff_v1"
MSN_MANUAL_EVIDENCE_REVIEW_DECISION_SCHEMA_VERSION = "msn_manual_evidence_review_decision_v1"
MSN_MANUAL_APPROVED_EXPORT_HANDOFF_STATUS_READY = "APPROVED_EXPORT_HANDOFF_READY"
MSN_MANUAL_APPROVED_EXPORT_HANDOFF_STATUS_NEEDS_REVIEW = "APPROVED_EXPORT_HANDOFF_NEEDS_REVIEW"

_SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9_.-]+")
_PATH_RE = re.compile(r"(?:(?<![A-Za-z])[A-Za-z]:\\|(?<![A-Za-z])[A-Za-z]:/|\\\\|/(?:home|mnt|Users|Volumes|tmp|var)/)")


@dataclass(frozen=True)
class MSNManualApprovedExportHandoffAsset:
    role: str
    filename: str
    sha256: str = ""
    byte_count: int = 0
    source: str = "decision"


@dataclass(frozen=True)
class MSNManualApprovedExportHandoffStep:
    step_id: str
    label: str
    command_hint: str
    required: bool = True


@dataclass(frozen=True)
class MSNManualApprovedExportHandoffReport:
    schema_version: str
    handoff_id: str
    queue_item_id: str
    decision_id: str
    source_url: str
    named_site: str
    named_action: str
    article_title: str
    reviewer_id: str
    review_decision: str
    handoff_status: str
    ready_for_total_export_release: bool
    issue_count: int
    issues: list[str] = field(default_factory=list)
    assets: list[MSNManualApprovedExportHandoffAsset] = field(default_factory=list)
    release_steps: list[MSNManualApprovedExportHandoffStep] = field(default_factory=list)
    evidence_queue_update: dict[str, str] = field(default_factory=dict)
    total_export_handoff: dict[str, str] = field(default_factory=dict)
    safety_flags: dict[str, bool] = field(default_factory=dict)
    handoff_hash: str = ""


class MSNManualApprovedExportHandoffError(ValueError):
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


def _normalise_asset(raw: Mapping[str, Any], *, source: str, index: int) -> MSNManualApprovedExportHandoffAsset:
    role = _safe_id(raw.get("role", raw.get("file_role", raw.get("asset_role", f"asset_{index}"))), default=f"asset_{index}")
    filename = _safe_filename(
        raw.get("filename", raw.get("safe_filename", raw.get("relative_path", raw.get("name", f"asset_{index}.json")))),
        fallback=f"asset_{index}.json",
    )
    sha256 = _safe_text(raw.get("sha256", raw.get("hash", raw.get("content_sha256", ""))))
    byte_count = _read_int(raw.get("byte_count", raw.get("bytes", raw.get("size", 0))))
    return MSNManualApprovedExportHandoffAsset(role=role, filename=filename, sha256=sha256, byte_count=byte_count, source=source)


def _normalise_assets(raw_assets: Any, *, source: str) -> list[MSNManualApprovedExportHandoffAsset]:
    if not isinstance(raw_assets, Sequence) or isinstance(raw_assets, (str, bytes, bytearray)):
        return []
    assets: list[MSNManualApprovedExportHandoffAsset] = []
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


def _store_assets(package_store_report: Mapping[str, Any] | None) -> list[MSNManualApprovedExportHandoffAsset]:
    if not isinstance(package_store_report, Mapping):
        return []
    raw_files = package_store_report.get("stored_files", package_store_report.get("files", []))
    return _normalise_assets(raw_files, source="total_export_package_store")


def _release_steps() -> list[MSNManualApprovedExportHandoffStep]:
    return [
        MSNManualApprovedExportHandoffStep(
            step_id="verify_review_decision",
            label="Verify approved Evidence Review decision and zero source issues",
            command_hint="capture_msn_manual_evidence_review_decision_verifier.py",
        ),
        MSNManualApprovedExportHandoffStep(
            step_id="verify_total_export_package",
            label="Verify the MSN manual Total Export package files and hashes",
            command_hint="capture_msn_manual_total_export_verifier.py",
        ),
        MSNManualApprovedExportHandoffStep(
            step_id="attach_to_review_queue",
            label="Attach safe package filenames and hashes to the evidence review queue item",
            command_hint="capture_msn_manual_evidence_queue_cli.py",
        ),
        MSNManualApprovedExportHandoffStep(
            step_id="release_total_export_package",
            label="Mark the approved MSN manual capture package ready for Total Export release",
            command_hint="capture_msn_manual_approved_export_handoff_cli.py",
        ),
    ]


def build_msn_manual_approved_export_handoff(
    decision_report: Mapping[str, Any],
    *,
    package_store_report: Mapping[str, Any] | None = None,
    operator_run_id: str = "operator_run",
) -> MSNManualApprovedExportHandoffReport:
    if not isinstance(decision_report, Mapping):
        raise MSNManualApprovedExportHandoffError("decision_report must be a JSON object")
    if _contains_path_like(decision_report) or _contains_path_like(package_store_report or {}):
        raise MSNManualApprovedExportHandoffError("approved export handoff inputs must not include full local paths")

    issues: list[str] = []
    if decision_report.get("schema_version") != MSN_MANUAL_EVIDENCE_REVIEW_DECISION_SCHEMA_VERSION:
        issues.append("decision schema_version mismatch")
    if decision_report.get("review_decision") != "APPROVED":
        issues.append("decision is not APPROVED")
    if decision_report.get("decision_status") != "DECISION_READY":
        issues.append("decision_status is not DECISION_READY")
    if decision_report.get("approved_for_total_export") is not True:
        issues.append("decision is not approved_for_total_export")
    if _read_int(decision_report.get("issue_count", 0)) != 0:
        issues.append("decision issue_count is non-zero")

    queue_item_id = _safe_id(decision_report.get("queue_item_id"), default="msn_manual_queue_item")
    decision_id = _safe_id(decision_report.get("decision_id"), default="msn_manual_decision")
    source_url = _safe_text(decision_report.get("source_url"))
    named_site = _safe_text(decision_report.get("named_site"), default="msn")
    named_action = _safe_text(decision_report.get("named_action"), default="msn_manual_capture")
    article_title = _safe_text(decision_report.get("article_title"), default="MSN manual capture")
    reviewer_id = _safe_id(decision_report.get("reviewer_id"), default="operator")
    operator_id = _safe_id(operator_run_id, default="operator_run")

    for key, value in {
        "source_url": source_url,
        "decision_id": decision_id,
        "queue_item_id": queue_item_id,
        "article_title": article_title,
    }.items():
        if not value:
            issues.append(f"missing {key}")

    assets = _normalise_assets(decision_report.get("assets", []), source="decision")
    assets.extend(_store_assets(package_store_report))
    if not assets:
        issues.append("no handoff assets found")
    for asset in assets:
        if not asset.filename:
            issues.append(f"asset missing filename for role {asset.role}")
        if not asset.sha256:
            issues.append(f"asset missing sha256 for role {asset.role}")

    flags = decision_report.get("safety_flags")
    if not isinstance(flags, Mapping):
        issues.append("decision missing safety_flags")
    else:
        for flag in ("metadata_only_decision", "explicit_review_package_only", "no_live_http", "no_browser_automation", "no_full_local_paths"):
            if flags.get(flag) is not True:
                issues.append(f"decision safety flag not true: {flag}")

    queue_update = dict(decision_report.get("evidence_queue_update", {}) if isinstance(decision_report.get("evidence_queue_update"), Mapping) else {})
    total_handoff = dict(decision_report.get("total_export_handoff", {}) if isinstance(decision_report.get("total_export_handoff"), Mapping) else {})
    if queue_update.get("queue_status") != "REVIEW_APPROVED":
        issues.append("evidence queue update is not REVIEW_APPROVED")
    if total_handoff.get("handoff_status") != "READY_FOR_TOTAL_EXPORT":
        issues.append("decision total_export_handoff is not READY_FOR_TOTAL_EXPORT")

    ready = not issues
    handoff_status = MSN_MANUAL_APPROVED_EXPORT_HANDOFF_STATUS_READY if ready else MSN_MANUAL_APPROVED_EXPORT_HANDOFF_STATUS_NEEDS_REVIEW
    handoff_seed = {
        "queue_item_id": queue_item_id,
        "decision_id": decision_id,
        "operator_run_id": operator_id,
        "asset_hashes": sorted(asset.sha256 for asset in assets if asset.sha256),
    }
    handoff_id = f"{queue_item_id}.approved_export.{_sha256_json(handoff_seed)[:12]}"

    report_without_hash: dict[str, Any] = {
        "schema_version": MSN_MANUAL_APPROVED_EXPORT_HANDOFF_SCHEMA_VERSION,
        "handoff_id": handoff_id,
        "queue_item_id": queue_item_id,
        "decision_id": decision_id,
        "source_url": source_url,
        "named_site": named_site,
        "named_action": named_action,
        "article_title": article_title,
        "reviewer_id": reviewer_id,
        "review_decision": "APPROVED",
        "handoff_status": handoff_status,
        "ready_for_total_export_release": ready,
        "issue_count": len(issues),
        "issues": issues,
        "assets": [asdict(asset) for asset in assets],
        "release_steps": [asdict(step) for step in _release_steps()],
        "evidence_queue_update": {
            "queue_item_id": queue_item_id,
            "queue_status": "READY_FOR_TOTAL_EXPORT_RELEASE" if ready else "BLOCKED_PENDING_REVIEW",
            "source_decision_id": decision_id,
        },
        "total_export_handoff": {
            "queue_item_id": queue_item_id,
            "handoff_status": "READY_FOR_TOTAL_EXPORT_RELEASE" if ready else "BLOCKED_PENDING_REVIEW",
            "source_decision_id": decision_id,
            "next_cli": "capture_msn_manual_total_export_cli.py",
        },
        "safety_flags": {
            "metadata_only_handoff": True,
            "explicit_decision_json_only": True,
            "explicit_package_store_json_only": True,
            "no_live_http": True,
            "no_browser_automation": True,
            "no_full_local_paths": True,
            "no_credential_reads": True,
            "no_folder_scans": True,
        },
    }
    handoff_hash = _sha256_json(report_without_hash)
    return MSNManualApprovedExportHandoffReport(
        schema_version=MSN_MANUAL_APPROVED_EXPORT_HANDOFF_SCHEMA_VERSION,
        handoff_id=handoff_id,
        queue_item_id=queue_item_id,
        decision_id=decision_id,
        source_url=source_url,
        named_site=named_site,
        named_action=named_action,
        article_title=article_title,
        reviewer_id=reviewer_id,
        review_decision="APPROVED",
        handoff_status=handoff_status,
        ready_for_total_export_release=ready,
        issue_count=len(issues),
        issues=issues,
        assets=assets,
        release_steps=_release_steps(),
        evidence_queue_update=report_without_hash["evidence_queue_update"],
        total_export_handoff=report_without_hash["total_export_handoff"],
        safety_flags=report_without_hash["safety_flags"],
        handoff_hash=handoff_hash,
    )


def msn_manual_approved_export_handoff_to_json(report: MSNManualApprovedExportHandoffReport) -> str:
    return json.dumps(asdict(report), indent=2, sort_keys=True, ensure_ascii=False) + "\n"
