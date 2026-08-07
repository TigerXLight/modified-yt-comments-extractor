from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

MSN_MANUAL_RELEASE_INDEX_SCHEMA_VERSION = "msn_manual_release_index_v1"
MSN_MANUAL_RELEASE_INDEX_VERDICT_READY = "MSN_MANUAL_RELEASE_INDEX_READY"
MSN_MANUAL_RELEASE_INDEX_VERDICT_NEEDS_REVIEW = "MSN_MANUAL_RELEASE_INDEX_NEEDS_REVIEW"


@dataclass(frozen=True)
class MSNManualReleaseIndexVerification:
    verdict: str
    index_id: str
    release_id: str
    queue_item_id: str
    issue_count: int
    issues: list[str] = field(default_factory=list)


def _asset_issues(raw_assets: Any) -> list[str]:
    issues: list[str] = []
    if not isinstance(raw_assets, Sequence) or isinstance(raw_assets, (str, bytes, bytearray)):
        return ["assets must be a list"]
    if not raw_assets:
        return ["assets are empty"]
    for index, raw in enumerate(raw_assets, start=1):
        if not isinstance(raw, Mapping):
            issues.append(f"asset {index} is not an object")
            continue
        if not raw.get("filename"):
            issues.append(f"asset {index} missing filename")
        if not raw.get("sha256"):
            issues.append(f"asset {index} missing sha256")
        if int(raw.get("byte_count", 0) or 0) <= 0:
            issues.append(f"asset {index} missing byte_count")
    return issues


def verify_msn_manual_release_index(report: Mapping[str, Any]) -> MSNManualReleaseIndexVerification:
    if not isinstance(report, Mapping):
        raise ValueError("release index report must be a JSON object")
    issues: list[str] = []
    if report.get("schema_version") != MSN_MANUAL_RELEASE_INDEX_SCHEMA_VERSION:
        issues.append("schema_version mismatch")
    if report.get("release_index_status") != "MSN_MANUAL_RELEASE_INDEX_READY":
        issues.append("release_index_status is not MSN_MANUAL_RELEASE_INDEX_READY")
    if report.get("ready_for_total_export_release_index") is not True:
        issues.append("ready_for_total_export_release_index is not true")
    if int(report.get("issue_count", 0) or 0) != 0:
        issues.append("reported issue_count is non-zero")
    issues.extend(_asset_issues(report.get("assets")))
    queue_update = report.get("evidence_queue_release_update")
    if not isinstance(queue_update, Mapping) or queue_update.get("queue_status") != "RELEASE_INDEX_READY":
        issues.append("evidence queue release update is not RELEASE_INDEX_READY")
    handoff = report.get("total_export_release_handoff")
    if not isinstance(handoff, Mapping) or handoff.get("release_handoff_status") != "READY_FOR_RELEASE_INDEX_CONSUMPTION":
        issues.append("Total Export release handoff is not ready")
    flags = report.get("safety_flags")
    if not isinstance(flags, Mapping):
        issues.append("missing safety_flags")
    else:
        for flag in (
            "metadata_only_release_index",
            "explicit_approved_release_json_only",
            "no_live_http",
            "no_browser_automation",
            "no_full_local_paths",
            "no_credential_reads",
        ):
            if flags.get(flag) is not True:
                issues.append(f"safety flag not true: {flag}")
    verdict = MSN_MANUAL_RELEASE_INDEX_VERDICT_READY if not issues else MSN_MANUAL_RELEASE_INDEX_VERDICT_NEEDS_REVIEW
    return MSNManualReleaseIndexVerification(
        verdict=verdict,
        index_id=str(report.get("index_id", "")),
        release_id=str(report.get("release_id", "")),
        queue_item_id=str(report.get("queue_item_id", "")),
        issue_count=len(issues),
        issues=issues,
    )


def msn_manual_release_index_verification_to_json(verification: MSNManualReleaseIndexVerification) -> str:
    return json.dumps(
        {
            "verdict": verification.verdict,
            "index_id": verification.index_id,
            "release_id": verification.release_id,
            "queue_item_id": verification.queue_item_id,
            "issue_count": verification.issue_count,
            "issues": verification.issues,
        },
        indent=2,
        sort_keys=True,
        ensure_ascii=False,
    ) + "\n"
