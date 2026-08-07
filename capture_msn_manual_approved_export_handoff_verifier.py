from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from typing import Any, Mapping

from capture_msn_manual_approved_export_handoff import (
    MSN_MANUAL_APPROVED_EXPORT_HANDOFF_SCHEMA_VERSION,
    MSN_MANUAL_APPROVED_EXPORT_HANDOFF_STATUS_READY,
)

MSN_MANUAL_APPROVED_EXPORT_HANDOFF_VERIFIER_SCHEMA_VERSION = "msn_manual_approved_export_handoff_verifier_v1"
MSN_MANUAL_APPROVED_EXPORT_HANDOFF_VERDICT_READY = "APPROVED_EXPORT_HANDOFF_READY"
MSN_MANUAL_APPROVED_EXPORT_HANDOFF_VERDICT_NEEDS_REVIEW = "APPROVED_EXPORT_HANDOFF_NEEDS_REVIEW"
_PATH_RE = re.compile(r"(?:(?<![A-Za-z])[A-Za-z]:\\|(?<![A-Za-z])[A-Za-z]:/|\\\\|/(?:home|mnt|Users|Volumes|tmp|var)/)")


@dataclass(frozen=True)
class MSNManualApprovedExportHandoffVerificationReport:
    schema_version: str
    verdict: str
    issue_count: int
    issues: list[str]
    handoff_id: str = ""
    queue_item_id: str = ""
    decision_id: str = ""
    ready_for_total_export_release: bool = False


def _contains_path_like(value: Any) -> bool:
    if isinstance(value, str):
        return bool(_PATH_RE.search(value))
    if isinstance(value, Mapping):
        return any(_contains_path_like(child) for child in value.values())
    if isinstance(value, list):
        return any(_contains_path_like(child) for child in value)
    return False


def verify_msn_manual_approved_export_handoff(handoff: Mapping[str, Any]) -> MSNManualApprovedExportHandoffVerificationReport:
    issues: list[str] = []
    if handoff.get("schema_version") != MSN_MANUAL_APPROVED_EXPORT_HANDOFF_SCHEMA_VERSION:
        issues.append("schema_version mismatch")
    for key in ("handoff_id", "queue_item_id", "decision_id", "source_url", "named_site", "named_action", "handoff_hash"):
        if not handoff.get(key):
            issues.append(f"missing {key}")
    if handoff.get("review_decision") != "APPROVED":
        issues.append("review_decision is not APPROVED")
    if handoff.get("handoff_status") != MSN_MANUAL_APPROVED_EXPORT_HANDOFF_STATUS_READY:
        issues.append("handoff_status is not ready")
    if handoff.get("ready_for_total_export_release") is not True:
        issues.append("not ready_for_total_export_release")
    if int(handoff.get("issue_count", 0) or 0) != 0:
        issues.append("handoff issue_count is non-zero")
    assets = handoff.get("assets")
    if not isinstance(assets, list) or not assets:
        issues.append("missing assets")
    else:
        for index, asset in enumerate(assets, start=1):
            if not isinstance(asset, Mapping):
                issues.append(f"asset {index} is not an object")
                continue
            if not asset.get("filename"):
                issues.append(f"asset {index} missing filename")
            if not asset.get("sha256"):
                issues.append(f"asset {index} missing sha256")
    steps = handoff.get("release_steps")
    if not isinstance(steps, list) or len(steps) < 3:
        issues.append("release_steps incomplete")
    queue_update = handoff.get("evidence_queue_update")
    if not isinstance(queue_update, Mapping) or queue_update.get("queue_status") != "READY_FOR_TOTAL_EXPORT_RELEASE":
        issues.append("evidence_queue_update is not release-ready")
    flags = handoff.get("safety_flags")
    if not isinstance(flags, Mapping):
        issues.append("missing safety_flags")
    else:
        for flag in ("metadata_only_handoff", "explicit_decision_json_only", "explicit_package_store_json_only", "no_live_http", "no_browser_automation", "no_full_local_paths", "no_credential_reads", "no_folder_scans"):
            if flags.get(flag) is not True:
                issues.append(f"safety flag not true: {flag}")
    if _contains_path_like(handoff):
        issues.append("handoff contains full local path-like text")
    verdict = MSN_MANUAL_APPROVED_EXPORT_HANDOFF_VERDICT_READY if not issues else MSN_MANUAL_APPROVED_EXPORT_HANDOFF_VERDICT_NEEDS_REVIEW
    return MSNManualApprovedExportHandoffVerificationReport(
        schema_version=MSN_MANUAL_APPROVED_EXPORT_HANDOFF_VERIFIER_SCHEMA_VERSION,
        verdict=verdict,
        issue_count=len(issues),
        issues=issues,
        handoff_id=str(handoff.get("handoff_id", "")),
        queue_item_id=str(handoff.get("queue_item_id", "")),
        decision_id=str(handoff.get("decision_id", "")),
        ready_for_total_export_release=bool(handoff.get("ready_for_total_export_release", False)),
    )


def msn_manual_approved_export_handoff_verification_report_to_json(report: MSNManualApprovedExportHandoffVerificationReport) -> str:
    return json.dumps(asdict(report), indent=2, sort_keys=True, ensure_ascii=False) + "\n"
