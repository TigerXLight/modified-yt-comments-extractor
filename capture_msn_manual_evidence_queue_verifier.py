from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from typing import Any, Mapping

MSN_MANUAL_EVIDENCE_QUEUE_VERIFIER_SCHEMA_VERSION = "msn_manual_evidence_queue_verifier_v1"
_SECRET_RE = re.compile(r"(?:api[_-]?key|secret|token|password|credential|bearer|authorization)", re.I)
_FULL_PATH_RE = re.compile(r"(?:^|[\s'\"])(?:[A-Za-z]:[\\/]|\\\\|/(?:home|mnt|Users|Volumes|tmp|var)/)")
_REQUIRED_ROLES = {"article_text", "capture_bundle_json", "total_export_manifest_json", "total_export_packet_json"}


def _walk(value: Any, issues: list[str], path: str = "payload") -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            key_text = str(key)
            _walk(child, issues, f"{path}.{key_text}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _walk(child, issues, f"{path}[{index}]")
    elif isinstance(value, str):
        if _SECRET_RE.search(value) or _FULL_PATH_RE.search(value):
            issues.append(f"unsafe string at {path}")


@dataclass(frozen=True)
class MSNManualEvidenceQueueVerificationReport:
    schema_version: str
    queue_item_id: str | None
    issue_count: int
    issues: tuple[str, ...]
    ready_for_evidence_queue_review: bool
    required_asset_roles_present: bool
    safety_flags_clear: bool
    full_local_path_serialized: bool = False
    completed_capture_claimed: bool = False
    verified_capture_claimed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def verify_msn_manual_evidence_queue_item_payload(payload: Mapping[str, Any]) -> MSNManualEvidenceQueueVerificationReport:
    issues: list[str] = []
    _walk(payload, issues)
    if payload.get("schema_version") != "msn_manual_evidence_queue_item_v1":
        issues.append("unsupported schema_version")
    if payload.get("ready_for_evidence_queue_review") is not True:
        issues.append("ready_for_evidence_queue_review must be true")
    if payload.get("review_required") is not True:
        issues.append("review_required must be true")
    roles = set(payload.get("asset_roles") or [])
    missing = sorted(_REQUIRED_ROLES - roles)
    if missing:
        issues.append("missing asset roles: " + ", ".join(missing))
    for flag in [
        "live_network_request_performed_by_tool",
        "browser_automation_performed_by_tool",
        "archive_submission_performed_by_tool",
        "media_download_performed_by_tool",
        "credential_value_read",
        "raw_media_payload_included",
        "full_local_path_serialized",
        "completed_capture_claimed",
        "verified_capture_claimed",
    ]:
        if payload.get(flag) is True:
            issues.append(f"unsafe true flag: {flag}")
    return MSNManualEvidenceQueueVerificationReport(
        schema_version=MSN_MANUAL_EVIDENCE_QUEUE_VERIFIER_SCHEMA_VERSION,
        queue_item_id=payload.get("queue_item_id") if isinstance(payload.get("queue_item_id"), str) else None,
        issue_count=len(issues),
        issues=tuple(issues),
        ready_for_evidence_queue_review=not issues,
        required_asset_roles_present=not missing,
        safety_flags_clear=not any(issue.startswith("unsafe true flag") for issue in issues),
        full_local_path_serialized=any("unsafe string" in issue or "unsafe key" in issue for issue in issues),
        completed_capture_claimed=payload.get("completed_capture_claimed") is True,
        verified_capture_claimed=payload.get("verified_capture_claimed") is True,
    )


def msn_manual_evidence_queue_verification_report_to_json(report: MSNManualEvidenceQueueVerificationReport) -> str:
    return json.dumps(report.to_dict(), sort_keys=True, indent=2, ensure_ascii=False)
