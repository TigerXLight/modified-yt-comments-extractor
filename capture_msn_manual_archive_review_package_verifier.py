from __future__ import annotations

from typing import Any, Mapping

from capture_msn_manual_archive_review_package import ARCHIVE_REVIEW_STATUS_READY, SCHEMA_VERSION

VERIFIER_SCHEMA_VERSION = "msn_manual_archive_review_package_verifier_v1"


def verify_msn_manual_archive_review_package(package: Mapping[str, Any]) -> dict[str, Any]:
    issues: list[str] = []
    if package.get("schema_version") != SCHEMA_VERSION:
        issues.append("unexpected_schema_version")
    if package.get("archive_review_status") != ARCHIVE_REVIEW_STATUS_READY:
        issues.append("archive_review_status_not_ready")
    if package.get("readiness_issues"):
        issues.append("readiness_issues_present")
    if not package.get("archive_review_package_id"):
        issues.append("missing_archive_review_package_id")
    if not package.get("archive_result_intake_id"):
        issues.append("missing_archive_result_intake_id")
    if not package.get("queue_item_id"):
        issues.append("missing_queue_item_id")
    if not package.get("release_id"):
        issues.append("missing_release_id")
    successful = package.get("successful_archive_receipts")
    if not isinstance(successful, list) or not successful:
        issues.append("missing_successful_archive_receipts")
    index = package.get("archive_receipt_index") or {}
    if not isinstance(index, Mapping) or index.get("successful_receipt_count", 0) < 1:
        issues.append("archive_receipt_index_missing_success")
    queue_update = package.get("archive_review_queue_update") or {}
    if not isinstance(queue_update, Mapping) or not queue_update.get("ready_for_archive_review_decision"):
        issues.append("queue_update_not_ready_for_archive_review_decision")
    actions = package.get("required_review_actions")
    if not isinstance(actions, list) or len(actions) < 3:
        issues.append("missing_required_review_actions")
    return {
        "schema_version": VERIFIER_SCHEMA_VERSION,
        "verified": not issues,
        "issue_count": len(issues),
        "issues": issues,
        "archive_review_package_id": package.get("archive_review_package_id"),
        "archive_result_intake_id": package.get("archive_result_intake_id"),
        "queue_item_id": package.get("queue_item_id"),
        "release_id": package.get("release_id"),
    }


__all__ = ["VERIFIER_SCHEMA_VERSION", "verify_msn_manual_archive_review_package"]
