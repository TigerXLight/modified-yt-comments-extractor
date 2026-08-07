from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

SCHEMA_VERSION = "source_archive_review_v1"
CHECKLIST_SCHEMA_VERSION = "source_archive_review_checklist_v1"
DECISION_SCHEMA_VERSION = "source_archive_review_decision_v1"
CLOSEOUT_SCHEMA_VERSION = "source_archive_review_closeout_v1"
SUMMARY_SCHEMA_VERSION = "source_archive_review_operator_summary_v1"

_ALLOWED_DECISIONS = {"APPROVED", "REJECTED", "REVISION_REQUESTED"}
_SAFE_ID_RE = re.compile(r"[^a-zA-Z0-9_.-]+")
_SAFE_NAME_RE = re.compile(r"^[^/\\:]+$")
_URL_RE = re.compile(r"^https?://", re.IGNORECASE)


def _json_bytes(data: Mapping[str, Any]) -> bytes:
    return json.dumps(data, sort_keys=True, indent=2, ensure_ascii=False).encode("utf-8") + b"\n"


def _stable_hash(data: Mapping[str, Any], *, length: int = 12) -> str:
    return hashlib.sha256(_json_bytes(data)).hexdigest()[:length]


def _clean_identifier(value: object, *, fallback: str) -> str:
    text = str(value or "").strip() or fallback
    text = _SAFE_ID_RE.sub(".", text).strip("._-")
    return text or fallback


def _coerce_mapping(value: Mapping[str, Any] | None, *, name: str) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise TypeError(f"{name} must be a JSON object")
    return dict(value)


def _normalise_notes(*note_sources: Iterable[str] | None) -> list[str]:
    notes: list[str] = []
    seen: set[str] = set()
    for source in note_sources:
        if not source:
            continue
        for note in source:
            text = str(note or "").strip()
            if not text or text in seen:
                continue
            seen.add(text)
            notes.append(text)
    return notes


def _safe_basename(value: object) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    if not _SAFE_NAME_RE.match(text):
        raise ValueError("archive review filenames must be safe basenames, not paths")
    return text


def _ensure_no_local_paths(mapping: Mapping[str, Any], *, name: str) -> None:
    forbidden = {"path", "absolute_path", "local_path", "filesystem_path"}
    present = sorted(forbidden.intersection(mapping.keys()))
    if present:
        raise ValueError(f"{name} must not include local path fields: {', '.join(present)}")


def _normalise_decision(value: str) -> str:
    decision = str(value or "").strip().upper()
    if decision not in _ALLOWED_DECISIONS:
        raise ValueError("archive review decision must be APPROVED, REJECTED, or REVISION_REQUESTED")
    return decision


def _extract_receipts(record: Mapping[str, Any], receipt_index: Mapping[str, Any]) -> list[dict[str, Any]]:
    source_entries = receipt_index.get("receipt_entries") if receipt_index else None
    if source_entries is None:
        source_entries = record.get("operator_archive_results")
    if not isinstance(source_entries, list) or not source_entries:
        raise ValueError("archive review requires at least one archive receipt/result entry")

    receipts: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for index, raw_entry in enumerate(source_entries):
        if not isinstance(raw_entry, Mapping):
            raise TypeError(f"archive receipt entry {index} must be a JSON object")
        entry = dict(raw_entry)
        _ensure_no_local_paths(entry, name=f"archive receipt entry {index}")
        provider_id = _clean_identifier(entry.get("provider_id"), fallback="archive_provider")
        archive_url = str(entry.get("archive_url") or "").strip()
        if not _URL_RE.match(archive_url):
            raise ValueError(f"archive receipt entry {index}.archive_url must start with http:// or https://")
        receipt_filename = _safe_basename(entry.get("archive_receipt_filename") or entry.get("receipt_filename"))
        screenshot_filename = _safe_basename(entry.get("archive_screenshot_filename") or entry.get("screenshot_filename"))
        receipt_id = _clean_identifier(entry.get("archive_receipt_id"), fallback=f"{provider_id}.archive_receipt.{_stable_hash({'provider_id': provider_id, 'archive_url': archive_url})}")
        key = (provider_id, archive_url)
        if key in seen:
            continue
        seen.add(key)
        receipts.append(
            {
                "archive_receipt_id": receipt_id,
                "provider_id": provider_id,
                "archive_url": archive_url,
                "archive_receipt_filename": receipt_filename,
                "archive_screenshot_filename": screenshot_filename,
                "receipt_status_before_review": str(entry.get("receipt_status") or entry.get("result_status") or "RECEIVED_PENDING_ARCHIVE_REVIEW"),
                "operator_result_supplied": bool(entry.get("operator_result_supplied", True)),
                "online_validation_performed": False,
                "archive_submission_performed_by_app": False,
                "manual_or_live_actions_started_by_app": False,
            }
        )
    if not receipts:
        raise ValueError("archive review requires at least one unique archive receipt")
    receipts.sort(key=lambda item: (item["provider_id"], item["archive_url"]))
    return receipts


@dataclass(frozen=True)
class SourceArchiveReviewOutputs:
    archive_review_package: dict[str, Any]
    archive_review_checklist: dict[str, Any]
    archive_review_decision: dict[str, Any]
    archive_review_closeout: dict[str, Any]
    operator_summary: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {
            "archive_review_package": self.archive_review_package,
            "archive_review_checklist": self.archive_review_checklist,
            "archive_review_decision": self.archive_review_decision,
            "archive_review_closeout": self.archive_review_closeout,
            "operator_summary": self.operator_summary,
        }


def build_source_archive_review(
    *,
    archive_result_intake_record: Mapping[str, Any],
    archive_receipt_index: Mapping[str, Any] | None = None,
    archive_review_handoff: Mapping[str, Any] | None = None,
    reviewer_id: str = "manual_archive_reviewer",
    decision: str = "APPROVED",
    review_notes: Iterable[str] | None = None,
) -> SourceArchiveReviewOutputs:
    record = _coerce_mapping(archive_result_intake_record, name="archive_result_intake_record")
    receipt_index = _coerce_mapping(archive_receipt_index, name="archive_receipt_index") if archive_receipt_index else {}
    handoff = _coerce_mapping(archive_review_handoff, name="archive_review_handoff") if archive_review_handoff else {}

    if record.get("schema_version") != "source_archive_result_intake_v1":
        raise ValueError("archive_result_intake_record schema_version must be source_archive_result_intake_v1")
    if record.get("intake_status") != "READY_FOR_ARCHIVE_REVIEW":
        raise ValueError("archive_result_intake_record.intake_status must be READY_FOR_ARCHIVE_REVIEW")
    if record.get("operator_supplied_results_received") is not True:
        raise ValueError("archive result intake must include operator-supplied archive results")
    if record.get("online_validation_performed") is True:
        raise ValueError("archive result intake must not mark online validation performed")
    if record.get("archive_submission_performed_by_app") is True:
        raise ValueError("archive result intake must not mark archive submission performed by app")
    if record.get("manual_or_live_actions_started_by_app") is True:
        raise ValueError("archive result intake must not mark manual/live actions started by app")

    if receipt_index:
        if receipt_index.get("schema_version") != "source_archive_receipt_index_v1":
            raise ValueError("archive_receipt_index schema_version must be source_archive_receipt_index_v1")
        if receipt_index.get("archive_result_intake_id") != record.get("archive_result_intake_id"):
            raise ValueError("archive_receipt_index archive_result_intake_id mismatch")
        if receipt_index.get("receipt_status") != "RECEIVED_PENDING_ARCHIVE_REVIEW":
            raise ValueError("archive_receipt_index.receipt_status must be RECEIVED_PENDING_ARCHIVE_REVIEW")
    if handoff:
        if handoff.get("schema_version") != "source_archive_review_handoff_v1":
            raise ValueError("archive_review_handoff schema_version must be source_archive_review_handoff_v1")
        if handoff.get("archive_result_intake_id") != record.get("archive_result_intake_id"):
            raise ValueError("archive_review_handoff archive_result_intake_id mismatch")
        if handoff.get("handoff_status") != "READY_FOR_ARCHIVE_REVIEW":
            raise ValueError("archive_review_handoff.handoff_status must be READY_FOR_ARCHIVE_REVIEW")

    review_decision = _normalise_decision(decision)
    receipts = _extract_receipts(record, receipt_index)

    adapter_id = _clean_identifier(record.get("adapter_id"), fallback="source")
    archive_result_intake_id = _clean_identifier(record.get("archive_result_intake_id"), fallback="source.archive_result_intake")
    archive_handoff_id = _clean_identifier(record.get("archive_handoff_id"), fallback="source.archive_handoff")
    release_audit_id = _clean_identifier(record.get("release_audit_id"), fallback="source.release_audit")
    release_index_id = _clean_identifier(record.get("release_index_id"), fallback="source.release_index")
    approved_release_id = _clean_identifier(record.get("approved_release_id"), fallback="source.approved_release")
    evidence_review_package_id = _clean_identifier(record.get("evidence_review_package_id"), fallback="source.evidence_review")
    queue_item_id = _clean_identifier(record.get("queue_item_id"), fallback="source.evidence_queue")
    total_export_package_id = _clean_identifier(record.get("total_export_package_id"), fallback="source.total_export_package")
    capture_bundle_id = _clean_identifier(record.get("capture_bundle_id"), fallback="source.capture_bundle")
    source_url = str(record.get("source_url") or "").strip()
    if not source_url:
        raise ValueError("archive result intake record source_url is required")

    review_seed = {
        "archive_result_intake_id": archive_result_intake_id,
        "receipt_count": len(receipts),
        "decision": review_decision,
        "receipts": receipts,
    }
    archive_review_package_id = f"{adapter_id}.archive_review.{_stable_hash(review_seed)}"
    approved_receipt_count = len(receipts) if review_decision == "APPROVED" else 0
    needs_followup = review_decision != "APPROVED"

    common_ids = {
        "adapter_id": adapter_id,
        "source_url": source_url,
        "queue_item_id": queue_item_id,
        "capture_bundle_id": capture_bundle_id,
        "total_export_package_id": total_export_package_id,
        "evidence_review_package_id": evidence_review_package_id,
        "approved_release_id": approved_release_id,
        "release_index_id": release_index_id,
        "release_audit_id": release_audit_id,
        "archive_handoff_id": archive_handoff_id,
        "archive_result_intake_id": archive_result_intake_id,
        "archive_review_package_id": archive_review_package_id,
    }

    archive_review_package = {
        "schema_version": SCHEMA_VERSION,
        **common_ids,
        "review_status": "ARCHIVE_REVIEW_COMPLETE",
        "decision": review_decision,
        "reviewer_id": _clean_identifier(reviewer_id, fallback="manual_archive_reviewer"),
        "receipt_count": len(receipts),
        "approved_receipt_count": approved_receipt_count,
        "rejected_receipt_count": 0 if review_decision == "APPROVED" else len(receipts),
        "archive_receipts": receipts,
        "review_notes": _normalise_notes(review_notes),
        "online_validation_performed": False,
        "archive_submission_performed_by_app": False,
        "manual_or_live_actions_started_by_app": False,
        "release_upload_performed": False,
        "mutates_archive_result_intake": False,
        "required_next_stage": "COMPLETE" if review_decision == "APPROVED" else "ARCHIVE_REVIEW_FOLLOWUP",
    }

    checklist_items = [
        {
            "check_id": "archive_result_is_operator_supplied",
            "status": "PASS",
            "detail": "Archive receipt URLs came from explicit operator-supplied result JSON, not from app submission.",
        },
        {
            "check_id": "no_online_archive_validation_claimed",
            "status": "PASS",
            "detail": "This shared stage records review decisions without re-fetching or validating online archive contents.",
        },
        {
            "check_id": "safe_receipt_filenames_only",
            "status": "PASS",
            "detail": "Receipt and screenshot filenames are safe basenames only.",
        },
        {
            "check_id": "release_traceability_preserved",
            "status": "PASS",
            "detail": "Review output preserves queue, Total Export, release, audit, and archive intake identifiers.",
        },
    ]
    archive_review_checklist = {
        "schema_version": CHECKLIST_SCHEMA_VERSION,
        **common_ids,
        "checklist_status": "COMPLETE",
        "decision": review_decision,
        "check_count": len(checklist_items),
        "checks": checklist_items,
        "online_validation_performed": False,
    }

    archive_review_decision = {
        "schema_version": DECISION_SCHEMA_VERSION,
        **common_ids,
        "decision": review_decision,
        "decision_status": "FINAL" if review_decision == "APPROVED" else "FOLLOWUP_REQUIRED",
        "reviewer_id": _clean_identifier(reviewer_id, fallback="manual_archive_reviewer"),
        "review_notes": _normalise_notes(review_notes),
        "approved_receipt_count": approved_receipt_count,
        "receipt_count": len(receipts),
        "ready_for_final_closeout": review_decision == "APPROVED",
        "requires_revision": review_decision == "REVISION_REQUESTED",
        "rejected": review_decision == "REJECTED",
        "online_validation_performed": False,
        "archive_submission_performed_by_app": False,
        "manual_or_live_actions_started_by_app": False,
        "mutates_archive_result_intake": False,
    }

    archive_review_closeout = {
        "schema_version": CLOSEOUT_SCHEMA_VERSION,
        **common_ids,
        "closeout_status": "ARCHIVE_COMPLETE" if review_decision == "APPROVED" else "ARCHIVE_REVIEW_FOLLOWUP_REQUIRED",
        "decision": review_decision,
        "source_pipeline_status": "COMPLETE" if review_decision == "APPROVED" else "NEEDS_OPERATOR_FOLLOWUP",
        "approved_release_archived": review_decision == "APPROVED",
        "archive_receipt_count": len(receipts),
        "approved_receipt_count": approved_receipt_count,
        "manual_or_live_actions_started_by_app": False,
        "archive_submission_performed_by_app": False,
        "online_validation_performed": False,
        "release_upload_performed": False,
        "required_next_stage": "NONE" if review_decision == "APPROVED" else "source_archive_result_intake_or_review_retry",
    }

    operator_summary = {
        "schema_version": SUMMARY_SCHEMA_VERSION,
        **common_ids,
        "status": archive_review_closeout["closeout_status"],
        "decision": review_decision,
        "receipt_count": len(receipts),
        "approved_receipt_count": approved_receipt_count,
        "needs_operator_followup": needs_followup,
        "manual_or_live_actions_started_by_app": False,
        "archive_submission_performed_by_app": False,
        "online_validation_performed": False,
        "release_upload_performed": False,
        "next_actions": [] if review_decision == "APPROVED" else [
            "Resolve the archive review decision outside this stage.",
            "Provide corrected archive result JSON through the shared archive result intake boundary if needed.",
        ],
    }

    return SourceArchiveReviewOutputs(
        archive_review_package=archive_review_package,
        archive_review_checklist=archive_review_checklist,
        archive_review_decision=archive_review_decision,
        archive_review_closeout=archive_review_closeout,
        operator_summary=operator_summary,
    )


def dump_json(data: Mapping[str, Any]) -> str:
    return _json_bytes(data).decode("utf-8")


def load_json_file(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data
