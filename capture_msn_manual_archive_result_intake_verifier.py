from __future__ import annotations

import re
from typing import Any, Mapping

SCHEMA_VERSION = "msn_manual_archive_result_intake_verifier_v1"
_SECRET_FIELD_RE = re.compile(r"(?:api[_-]?key|secret|token|password|credential|bearer|authorization)", re.I)
_ABSOLUTE_PATH_RE = re.compile(r"(?:(?<![A-Za-z])[A-Za-z]:[\\/]|\\\\|/(?:home|mnt|Users|Volumes|tmp|var)/)")


def _all_nested_values(value: Any) -> list[Any]:
    values: list[Any] = []
    if isinstance(value, Mapping):
        for key, item in value.items():
            values.append(key)
            values.extend(_all_nested_values(item))
    elif isinstance(value, list):
        for item in value:
            values.extend(_all_nested_values(item))
    else:
        values.append(value)
    return values


def _has_secret_field(value: Any) -> bool:
    if isinstance(value, Mapping):
        for key, item in value.items():
            if _SECRET_FIELD_RE.search(str(key)) or _has_secret_field(item):
                return True
    elif isinstance(value, list):
        return any(_has_secret_field(item) for item in value)
    return False


def _has_absolute_path(value: Any) -> bool:
    return any(_ABSOLUTE_PATH_RE.search(str(item)) for item in _all_nested_values(value))


def verify_msn_manual_archive_result_intake(intake: Mapping[str, Any]) -> dict[str, Any]:
    issues: list[str] = []
    if intake.get("schema_version") != "msn_manual_archive_result_intake_v1":
        issues.append("unexpected_archive_result_intake_schema")
    if intake.get("archive_result_status") != "MSN_MANUAL_ARCHIVE_RESULTS_READY":
        issues.append("archive_result_intake_not_ready")
    if intake.get("readiness_issues"):
        issues.append("archive_result_intake_has_readiness_issues")
    if not intake.get("archive_result_intake_id"):
        issues.append("missing_archive_result_intake_id")
    if not intake.get("archive_handoff_id"):
        issues.append("missing_archive_handoff_id")
    if not intake.get("queue_item_id"):
        issues.append("missing_queue_item_id")
    if not intake.get("release_id"):
        issues.append("missing_release_id")
    receipts = list(intake.get("archive_result_receipts", []) or [])
    if not receipts:
        issues.append("missing_archive_result_receipts")
    if not any(receipt.get("result_status") == "ARCHIVED" for receipt in receipts if isinstance(receipt, Mapping)):
        issues.append("missing_successful_archive_receipt")
    if any(receipt.get("external_call_performed_by_code") for receipt in receipts if isinstance(receipt, Mapping)):
        issues.append("external_call_claim_detected")
    queue_update = intake.get("archive_result_queue_update", {}) or {}
    if not isinstance(queue_update, Mapping) or not queue_update.get("ready_for_post_archive_review"):
        issues.append("queue_update_not_ready_for_post_archive_review")
    if _has_secret_field(intake):
        issues.append("secret_like_field_detected")
    if _has_absolute_path(intake):
        issues.append("absolute_path_detected")
    return {
        "schema_version": SCHEMA_VERSION,
        "verified": not issues,
        "issue_count": len(issues),
        "issues": issues,
        "archive_result_intake_id": intake.get("archive_result_intake_id"),
        "archive_handoff_id": intake.get("archive_handoff_id"),
        "queue_item_id": intake.get("queue_item_id"),
        "release_id": intake.get("release_id"),
    }


__all__ = ["SCHEMA_VERSION", "verify_msn_manual_archive_result_intake"]
