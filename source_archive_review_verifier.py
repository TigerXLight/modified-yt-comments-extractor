from __future__ import annotations

import re
from typing import Any, Mapping

SCHEMA_VERSION = "source_archive_review_verifier_v1"
_ALLOWED_DECISIONS = {"APPROVED", "REJECTED", "REVISION_REQUESTED"}
_SAFE_NAME_RE = re.compile(r"^[^/\\:]+$")
_URL_RE = re.compile(r"^https?://", re.IGNORECASE)


def _issue(issues: list[str], message: str) -> None:
    issues.append(message)


def _is_safe_filename(value: object) -> bool:
    text = str(value or "")
    return not text or bool(_SAFE_NAME_RE.match(text))


def verify_source_archive_review(
    archive_review_package: Mapping[str, Any],
    archive_review_checklist: Mapping[str, Any] | None = None,
    archive_review_decision: Mapping[str, Any] | None = None,
    archive_review_closeout: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    issues: list[str] = []
    package = dict(archive_review_package or {})
    checklist = dict(archive_review_checklist or {})
    decision_record = dict(archive_review_decision or {})
    closeout = dict(archive_review_closeout or {})

    if package.get("schema_version") != "source_archive_review_v1":
        _issue(issues, "archive review package schema_version must be source_archive_review_v1")
    if package.get("review_status") != "ARCHIVE_REVIEW_COMPLETE":
        _issue(issues, "archive review package must be ARCHIVE_REVIEW_COMPLETE")
    decision = str(package.get("decision") or "")
    if decision not in _ALLOWED_DECISIONS:
        _issue(issues, "archive review decision must be APPROVED, REJECTED, or REVISION_REQUESTED")
    for key in (
        "archive_review_package_id",
        "archive_result_intake_id",
        "archive_handoff_id",
        "release_audit_id",
        "release_index_id",
        "approved_release_id",
        "queue_item_id",
        "adapter_id",
        "source_url",
    ):
        if not package.get(key):
            _issue(issues, f"archive review package must include {key}")
    if package.get("online_validation_performed") is True:
        _issue(issues, "archive review must not mark online validation performed")
    if package.get("archive_submission_performed_by_app") is True:
        _issue(issues, "archive review must not mark archive submission performed by app")
    if package.get("manual_or_live_actions_started_by_app") is True:
        _issue(issues, "archive review must not mark manual/live actions started by app")
    if package.get("release_upload_performed") is True:
        _issue(issues, "archive review must not mark release upload performed")
    if package.get("mutates_archive_result_intake") is True:
        _issue(issues, "archive review must not mutate the original archive result intake")

    receipts = package.get("archive_receipts")
    if not isinstance(receipts, list) or not receipts:
        _issue(issues, "archive review package must include archive_receipts")
    else:
        for index, receipt in enumerate(receipts):
            if not isinstance(receipt, Mapping):
                _issue(issues, f"archive_receipts[{index}] must be an object")
                continue
            if not receipt.get("archive_receipt_id"):
                _issue(issues, f"archive_receipts[{index}] must include archive_receipt_id")
            if not receipt.get("provider_id"):
                _issue(issues, f"archive_receipts[{index}] must include provider_id")
            if not _URL_RE.match(str(receipt.get("archive_url") or "")):
                _issue(issues, f"archive_receipts[{index}].archive_url must be http(s)")
            if not _is_safe_filename(receipt.get("archive_receipt_filename")):
                _issue(issues, f"archive_receipts[{index}].archive_receipt_filename must be a safe basename")
            if not _is_safe_filename(receipt.get("archive_screenshot_filename")):
                _issue(issues, f"archive_receipts[{index}].archive_screenshot_filename must be a safe basename")
            if receipt.get("online_validation_performed") is True:
                _issue(issues, f"archive_receipts[{index}] must not mark online validation performed")
            if receipt.get("archive_submission_performed_by_app") is True:
                _issue(issues, f"archive_receipts[{index}] must not mark archive submission by app")

    if checklist:
        if checklist.get("schema_version") != "source_archive_review_checklist_v1":
            _issue(issues, "archive review checklist schema_version mismatch")
        if checklist.get("archive_review_package_id") != package.get("archive_review_package_id"):
            _issue(issues, "archive review checklist package id mismatch")
        if checklist.get("checklist_status") != "COMPLETE":
            _issue(issues, "archive review checklist must be COMPLETE")
        if checklist.get("online_validation_performed") is True:
            _issue(issues, "archive review checklist must not mark online validation performed")
        checks = checklist.get("checks")
        if not isinstance(checks, list) or not checks:
            _issue(issues, "archive review checklist must include checks")

    if decision_record:
        if decision_record.get("schema_version") != "source_archive_review_decision_v1":
            _issue(issues, "archive review decision schema_version mismatch")
        if decision_record.get("archive_review_package_id") != package.get("archive_review_package_id"):
            _issue(issues, "archive review decision package id mismatch")
        if decision_record.get("decision") != decision:
            _issue(issues, "archive review decision mismatch")
        if decision == "APPROVED" and decision_record.get("ready_for_final_closeout") is not True:
            _issue(issues, "APPROVED archive review must be ready_for_final_closeout")
        if decision_record.get("online_validation_performed") is True:
            _issue(issues, "archive review decision must not mark online validation performed")
        if decision_record.get("archive_submission_performed_by_app") is True:
            _issue(issues, "archive review decision must not mark archive submission performed by app")

    if closeout:
        if closeout.get("schema_version") != "source_archive_review_closeout_v1":
            _issue(issues, "archive review closeout schema_version mismatch")
        if closeout.get("archive_review_package_id") != package.get("archive_review_package_id"):
            _issue(issues, "archive review closeout package id mismatch")
        if closeout.get("decision") != decision:
            _issue(issues, "archive review closeout decision mismatch")
        if decision == "APPROVED":
            if closeout.get("closeout_status") != "ARCHIVE_COMPLETE":
                _issue(issues, "APPROVED archive review closeout must be ARCHIVE_COMPLETE")
            if closeout.get("required_next_stage") != "NONE":
                _issue(issues, "APPROVED archive review closeout required_next_stage must be NONE")
        if closeout.get("online_validation_performed") is True:
            _issue(issues, "archive review closeout must not mark online validation performed")
        if closeout.get("archive_submission_performed_by_app") is True:
            _issue(issues, "archive review closeout must not mark archive submission performed by app")
        if closeout.get("release_upload_performed") is True:
            _issue(issues, "archive review closeout must not mark release upload performed")

    return {
        "schema_version": SCHEMA_VERSION,
        "verified": not issues,
        "issue_count": len(issues),
        "issues": issues,
        "archive_review_package_id": str(package.get("archive_review_package_id") or ""),
        "archive_result_intake_id": str(package.get("archive_result_intake_id") or ""),
        "archive_handoff_id": str(package.get("archive_handoff_id") or ""),
        "release_audit_id": str(package.get("release_audit_id") or ""),
        "release_index_id": str(package.get("release_index_id") or ""),
        "approved_release_id": str(package.get("approved_release_id") or ""),
        "queue_item_id": str(package.get("queue_item_id") or ""),
        "adapter_id": str(package.get("adapter_id") or ""),
        "source_url": str(package.get("source_url") or ""),
        "decision": decision,
    }
