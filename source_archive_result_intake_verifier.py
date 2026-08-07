from __future__ import annotations

import re
from typing import Any, Mapping

SCHEMA_VERSION = "source_archive_result_intake_verifier_v1"
_SAFE_NAME_RE = re.compile(r"^[^/\\:]+$")
_URL_RE = re.compile(r"^https?://", re.IGNORECASE)


def _issue(issues: list[str], message: str) -> None:
    issues.append(message)


def _is_safe_filename(value: object) -> bool:
    text = str(value or "")
    return not text or bool(_SAFE_NAME_RE.match(text))


def verify_source_archive_result_intake(
    archive_result_intake_record: Mapping[str, Any],
    archive_receipt_index: Mapping[str, Any] | None = None,
    archive_review_handoff: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    issues: list[str] = []
    record = dict(archive_result_intake_record or {})
    receipt_index = dict(archive_receipt_index or {})
    review_handoff = dict(archive_review_handoff or {})

    if record.get("schema_version") != "source_archive_result_intake_v1":
        _issue(issues, "archive result intake record schema_version must be source_archive_result_intake_v1")
    if record.get("intake_status") != "READY_FOR_ARCHIVE_REVIEW":
        _issue(issues, "archive result intake record must be READY_FOR_ARCHIVE_REVIEW")
    for key in ("archive_result_intake_id", "archive_handoff_id", "release_audit_id", "release_index_id", "approved_release_id", "queue_item_id", "adapter_id", "source_url"):
        if not record.get(key):
            _issue(issues, f"archive result intake record must include {key}")
    if record.get("operator_supplied_results_received") is not True:
        _issue(issues, "archive result intake must record operator-supplied results")
    if record.get("online_validation_performed") is True:
        _issue(issues, "archive result intake must not mark online validation performed")
    if record.get("archive_submission_performed_by_app") is True:
        _issue(issues, "archive result intake must not mark archive submission performed by app")
    if record.get("manual_or_live_actions_started_by_app") is True:
        _issue(issues, "archive result intake must not mark manual/live actions started by app")
    if record.get("required_next_stage") != "source_archive_review":
        _issue(issues, "archive result intake required_next_stage must be source_archive_review")

    results = record.get("operator_archive_results")
    if not isinstance(results, list) or not results:
        _issue(issues, "archive result intake must include operator_archive_results")
    else:
        for index, result in enumerate(results):
            if not isinstance(result, Mapping):
                _issue(issues, f"operator_archive_results[{index}] must be an object")
                continue
            if result.get("result_status") != "OPERATOR_SUPPLIED_PENDING_REVIEW":
                _issue(issues, f"operator_archive_results[{index}] must be OPERATOR_SUPPLIED_PENDING_REVIEW")
            if not _URL_RE.match(str(result.get("archive_url") or "")):
                _issue(issues, f"operator_archive_results[{index}].archive_url must be http(s)")
            if not _is_safe_filename(result.get("archive_receipt_filename")):
                _issue(issues, f"operator_archive_results[{index}].archive_receipt_filename must be a safe basename")
            if not _is_safe_filename(result.get("archive_screenshot_filename")):
                _issue(issues, f"operator_archive_results[{index}].archive_screenshot_filename must be a safe basename")
            if "path" in result or "absolute_path" in result or "local_path" in result:
                _issue(issues, f"operator_archive_results[{index}] must not include local path fields")
            if result.get("online_validation_performed") is True:
                _issue(issues, f"operator_archive_results[{index}] must not mark online validation performed")
            if result.get("archive_submission_performed_by_app") is True:
                _issue(issues, f"operator_archive_results[{index}] must not mark archive submission performed by app")

    if receipt_index:
        if receipt_index.get("schema_version") != "source_archive_receipt_index_v1":
            _issue(issues, "archive receipt index schema_version mismatch")
        if receipt_index.get("archive_result_intake_id") != record.get("archive_result_intake_id"):
            _issue(issues, "archive receipt index archive_result_intake_id mismatch")
        if receipt_index.get("receipt_status") != "RECEIVED_PENDING_ARCHIVE_REVIEW":
            _issue(issues, "archive receipt index must be RECEIVED_PENDING_ARCHIVE_REVIEW")
        if receipt_index.get("online_validation_performed") is True:
            _issue(issues, "archive receipt index must not mark online validation performed")
        entries = receipt_index.get("receipt_entries")
        if not isinstance(entries, list) or not entries:
            _issue(issues, "archive receipt index must include receipt_entries")
        else:
            for index, entry in enumerate(entries):
                if not isinstance(entry, Mapping):
                    _issue(issues, f"receipt_entries[{index}] must be an object")
                    continue
                if not entry.get("archive_receipt_id"):
                    _issue(issues, f"receipt_entries[{index}] must include archive_receipt_id")
                if not _URL_RE.match(str(entry.get("archive_url") or "")):
                    _issue(issues, f"receipt_entries[{index}].archive_url must be http(s)")
                if not _is_safe_filename(entry.get("archive_receipt_filename")):
                    _issue(issues, f"receipt_entries[{index}].archive_receipt_filename must be a safe basename")
                if entry.get("receipt_status") != "RECEIVED_PENDING_ARCHIVE_REVIEW":
                    _issue(issues, f"receipt_entries[{index}] must be RECEIVED_PENDING_ARCHIVE_REVIEW")

    if review_handoff:
        if review_handoff.get("schema_version") != "source_archive_review_handoff_v1":
            _issue(issues, "archive review handoff schema_version mismatch")
        if review_handoff.get("archive_result_intake_id") != record.get("archive_result_intake_id"):
            _issue(issues, "archive review handoff archive_result_intake_id mismatch")
        if review_handoff.get("handoff_status") != "READY_FOR_ARCHIVE_REVIEW":
            _issue(issues, "archive review handoff must be READY_FOR_ARCHIVE_REVIEW")
        if review_handoff.get("required_next_stage") != "source_archive_review":
            _issue(issues, "archive review handoff required_next_stage must be source_archive_review")
        if review_handoff.get("online_validation_performed") is True:
            _issue(issues, "archive review handoff must not mark online validation performed")

    return {
        "schema_version": SCHEMA_VERSION,
        "verified": not issues,
        "issue_count": len(issues),
        "issues": issues,
        "archive_result_intake_id": str(record.get("archive_result_intake_id") or ""),
        "archive_handoff_id": str(record.get("archive_handoff_id") or ""),
        "release_audit_id": str(record.get("release_audit_id") or ""),
        "release_index_id": str(record.get("release_index_id") or ""),
        "approved_release_id": str(record.get("approved_release_id") or ""),
        "queue_item_id": str(record.get("queue_item_id") or ""),
        "adapter_id": str(record.get("adapter_id") or ""),
        "source_url": str(record.get("source_url") or ""),
    }
