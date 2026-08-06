from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field, is_dataclass
from enum import Enum
from typing import Any, Dict, Optional

from capture_action_log import (
    ACTOR_TYPE_APPLICATION,
    CaptureActionLogEvent,
    build_action_log_event,
)
from evidence_schema import (
    ClaimEvidenceNote,
    CurrentnessStatus,
    PrimarySourceStatus,
    SourceRole,
    utc_now_iso,
)


class _StringEnum(str, Enum):
    def __str__(self) -> str:
        return self.value


class EvidenceItemRole(_StringEnum):
    SOURCE_URL = "SOURCE_URL"
    LOCAL_MEDIA = "LOCAL_MEDIA"
    REFERENCE_TEXT = "REFERENCE_TEXT"
    SUBTITLE_FILE = "SUBTITLE_FILE"
    TRANSCRIPT_FILE = "TRANSCRIPT_FILE"
    SCREENSHOT = "SCREENSHOT"
    HTML_SNAPSHOT = "HTML_SNAPSHOT"
    VISIBLE_TEXT_SNAPSHOT = "VISIBLE_TEXT_SNAPSHOT"
    ARCHIVE_URL = "ARCHIVE_URL"
    MANUAL_EVIDENCE_NOTE = "MANUAL_EVIDENCE_NOTE"
    ASR_RESULT = "ASR_RESULT"
    TOTAL_EXPORT_PACKAGE = "TOTAL_EXPORT_PACKAGE"
    DATABASE_CATEGORY_SUGGESTION = "DATABASE_CATEGORY_SUGGESTION"


class EvidenceItemStatus(_StringEnum):
    ADDED = "ADDED"
    LINKED = "LINKED"
    READY = "READY"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    MISSING_LOCAL_FILE = "MISSING_LOCAL_FILE"
    DUPLICATE_CANDIDATE = "DUPLICATE_CANDIDATE"
    EXCLUDED_FROM_EXPORT = "EXCLUDED_FROM_EXPORT"
    INCLUDED_IN_EXPORT = "INCLUDED_IN_EXPORT"
    REMOVED_FROM_WORKING_SET = "REMOVED_FROM_WORKING_SET"


class EvidenceLinkOrigin(_StringEnum):
    EXPLICIT = "EXPLICIT"
    DERIVED_FROM_APP_STATE = "DERIVED_FROM_APP_STATE"


def _value_for_dict(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return {
            key: _value_for_dict(item)
            for key, item in asdict(value).items()
        }
    if isinstance(value, tuple):
        return [_value_for_dict(item) for item in value]
    if isinstance(value, list):
        return [_value_for_dict(item) for item in value]
    if isinstance(value, dict):
        return {key: _value_for_dict(item) for key, item in value.items()}
    return value


def _dataclass_to_dict(instance: Any) -> Dict[str, Any]:
    return _value_for_dict(instance)


@dataclass(frozen=True)
class EvidenceItemLink:
    source_item_id: str
    target_item_id: str
    relationship: str = ""
    link_origin: EvidenceLinkOrigin = EvidenceLinkOrigin.EXPLICIT
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass(frozen=True)
class ASRPairingMetadata:
    media_item_id: str = ""
    reference_text_item_id: str = ""
    candidate_subtitle_or_transcript_item_id: str = ""
    asr_result_item_id: str = ""
    asr_engine_or_provider: str = ""
    scoring_window: str = ""
    reference_accuracy_percent: Optional[float] = None
    reference_score_path: str = ""
    term_coverage_path: str = ""
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass(frozen=True)
class SourceRoleReviewMetadata:
    claim_text: str = ""
    claim_type: str = ""
    claim_source_role: SourceRole = SourceRole.UNKNOWN_SOURCE_ROLE
    source_role_scope: str = ""
    source_role_limitation: str = ""
    authored_or_posted_at: str = ""
    captured_at_utc: str = ""
    event_time_or_claim_time: str = ""
    temporal_gap_note: str = ""
    currentness_status: CurrentnessStatus = CurrentnessStatus.UNKNOWN
    primary_source_status: PrimarySourceStatus = PrimarySourceStatus.MANUAL_SOURCE_NOTE
    source_chain_gap: bool = False
    closed_loop_reporting_flag: bool = False
    evidence_basis: str = ""
    reviewer_notes: str = ""
    review_required: bool = True
    user_confirmed: bool = False
    automatic_classification: bool = False
    sensitive_inference_prohibited: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)

    def to_claim_evidence_note(self) -> ClaimEvidenceNote:
        return ClaimEvidenceNote(
            claim_text=self.claim_text,
            claim_type=self.claim_type,
            claim_source_role=self.claim_source_role,
            source_role_scope=self.source_role_scope,
            source_role_limitation=self.source_role_limitation,
            authored_or_posted_at=self.authored_or_posted_at,
            captured_at_utc=self.captured_at_utc,
            event_time_or_claim_time=self.event_time_or_claim_time,
            temporal_gap_note=self.temporal_gap_note,
            currentness_status=self.currentness_status,
            primary_source_status=self.primary_source_status,
            source_chain_gap=self.source_chain_gap,
            closed_loop_reporting_flag=self.closed_loop_reporting_flag,
            verification_notes=self.reviewer_notes or self.evidence_basis,
        )


@dataclass(frozen=True)
class SourceRoleReviewUIRow:
    queue_item_id: str
    queue_item_role: str
    review_index: int
    review_status: str = "USER_REVIEW_REQUIRED"
    claim_type: str = ""
    claim_text_recorded: bool = False
    claim_text_display: str = "not shown in summary; open the source item for manual review"
    source_role: SourceRole = SourceRole.UNKNOWN_SOURCE_ROLE
    source_role_scope: str = ""
    source_role_limitation: str = ""
    currentness_status: CurrentnessStatus = CurrentnessStatus.UNKNOWN
    primary_source_status: PrimarySourceStatus = PrimarySourceStatus.MANUAL_SOURCE_NOTE
    source_chain_gap: bool = False
    closed_loop_reporting_flag: bool = False
    evidence_basis_recorded: bool = False
    reviewer_notes_recorded: bool = False
    review_required: bool = True
    user_confirmed: bool = False
    automatic_classification: bool = False
    sensitive_inference_prohibited: bool = True
    raw_evidence_payload_included: bool = False
    full_local_path_included: bool = False
    completed_evidence_claimed: bool = False
    verified_evidence_claimed: bool = False
    live_capture_claimed: bool = False
    api_provider_capture_claimed: bool = False
    browser_automation_claimed: bool = False
    archive_download_ocr_warc_wacz_claimed: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass(frozen=True)
class EvidenceQueueItem:
    item_id: str
    item_role: EvidenceItemRole
    display_name: str = ""
    source_url: str = ""
    linked_source_id: str = ""
    local_path: str = ""
    media_type: str = ""
    mime_type: str = ""
    file_size_bytes: Optional[int] = None
    file_hash: str = ""
    is_manual_import: bool = False
    linked_item_ids: tuple[str, ...] = field(default_factory=tuple)
    linked_reference_text_path: str = ""
    linked_subtitle_path: str = ""
    linked_transcript_path: str = ""
    linked_screenshot_path: str = ""
    linked_archive_url: str = ""
    asr_engine_or_provider: str = ""
    asr_result_path: str = ""
    reference_score_path: str = ""
    scoring_window: str = ""
    term_coverage_path: str = ""
    total_export_include: bool = False
    total_export_output_kind: str = ""
    total_export_output_path: str = ""
    total_export_exclusion_reason: str = ""
    source_role_reviews: tuple[SourceRoleReviewMetadata, ...] = field(default_factory=tuple)
    item_status: EvidenceItemStatus = EvidenceItemStatus.ADDED
    created_at_utc: str = field(default_factory=utc_now_iso)
    updated_at_utc: str = field(default_factory=utc_now_iso)
    user_notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass(frozen=True)
class EvidenceItemQueue:
    items: tuple[EvidenceQueueItem, ...] = field(default_factory=tuple)
    links: tuple[EvidenceItemLink, ...] = field(default_factory=tuple)
    asr_pairings: tuple[ASRPairingMetadata, ...] = field(default_factory=tuple)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


def queue_source_role_reviews_to_claim_notes(
    queue: EvidenceItemQueue,
) -> tuple[ClaimEvidenceNote, ...]:
    notes: list[ClaimEvidenceNote] = []
    for item in queue.items:
        for review in item.source_role_reviews:
            notes.append(review.to_claim_evidence_note())
    return tuple(notes)


def queue_source_role_reviews_to_ui_rows(
    queue: EvidenceItemQueue,
) -> tuple[SourceRoleReviewUIRow, ...]:
    rows: list[SourceRoleReviewUIRow] = []
    for item in queue.items:
        for review_index, review in enumerate(item.source_role_reviews):
            rows.append(
                SourceRoleReviewUIRow(
                    queue_item_id=item.item_id,
                    queue_item_role=item.item_role.value,
                    review_index=review_index,
                    claim_type=review.claim_type,
                    claim_text_recorded=bool(review.claim_text),
                    source_role=review.claim_source_role,
                    source_role_scope=review.source_role_scope,
                    source_role_limitation=review.source_role_limitation,
                    currentness_status=review.currentness_status,
                    primary_source_status=review.primary_source_status,
                    source_chain_gap=review.source_chain_gap,
                    closed_loop_reporting_flag=review.closed_loop_reporting_flag,
                    evidence_basis_recorded=bool(review.evidence_basis),
                    reviewer_notes_recorded=bool(review.reviewer_notes),
                    review_required=review.review_required,
                    user_confirmed=review.user_confirmed,
                    automatic_classification=review.automatic_classification,
                    sensitive_inference_prohibited=review.sensitive_inference_prohibited,
                )
            )
    return tuple(rows)


def build_source_role_review_ui_summary(queue: EvidenceItemQueue) -> str:
    rows = queue_source_role_reviews_to_ui_rows(queue)
    lines = [
        "Source-role / claim-level review metadata",
        f"Review rows: {len(rows)}",
        "Status: USER_REVIEW_REQUIRED",
        "Metadata only: yes",
        "Auto-classify flag: false",
        "Sensitive inference prohibited: true",
        "Runtime/capture/completion claim flags: false",
    ]
    if not rows:
        lines.append("- (none)")
    for row in rows:
        lines.append(
            "- "
            f"{row.queue_item_id} [{row.queue_item_role}] "
            f"role={row.source_role.value}; "
            f"primary_status={row.primary_source_status.value}; "
            f"currentness={row.currentness_status.value}; "
            f"claim_text_recorded={str(row.claim_text_recorded).lower()}; "
            "claim_text_display=not shown"
        )
    return "\n".join(lines)


def _safe_source_role_review_receipt_rows(
    rows: tuple[SourceRoleReviewUIRow, ...],
) -> tuple[dict[str, Any], ...]:
    return tuple(
        {
            "automatic_classification": row.automatic_classification,
            "claim_text_recorded": row.claim_text_recorded,
            "claim_type": row.claim_type,
            "closed_loop_reporting_flag": row.closed_loop_reporting_flag,
            "currentness_status": row.currentness_status.value,
            "evidence_basis_recorded": row.evidence_basis_recorded,
            "primary_source_status": row.primary_source_status.value,
            "queue_item_id": row.queue_item_id,
            "queue_item_role": row.queue_item_role,
            "review_index": row.review_index,
            "review_required": row.review_required,
            "review_status": row.review_status,
            "reviewer_notes_recorded": row.reviewer_notes_recorded,
            "sensitive_inference_prohibited": row.sensitive_inference_prohibited,
            "source_chain_gap": row.source_chain_gap,
            "source_role": row.source_role.value,
            "source_role_limitation_recorded": bool(row.source_role_limitation),
            "source_role_scope_recorded": bool(row.source_role_scope),
            "user_confirmed": row.user_confirmed,
        }
        for row in rows
    )


def source_role_review_receipt_id(queue: EvidenceItemQueue) -> str:
    rows = queue_source_role_reviews_to_ui_rows(queue)
    payload = {
        "receipt_kind": "source_role_review_metadata",
        "rows": list(_safe_source_role_review_receipt_rows(rows)),
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return "source_role_review_receipt_" + hashlib.sha256(
        encoded.encode("utf-8")
    ).hexdigest()[:16]


def queue_source_role_reviews_to_action_log_events(
    queue: EvidenceItemQueue,
    *,
    session_id: str,
    timestamp_utc: str,
    previous_event_hash: str = "",
    actor_id: str = "",
    app_version: str = "",
) -> tuple[CaptureActionLogEvent, ...]:
    if not session_id:
        raise ValueError("session_id is required for source-role review receipts")
    if not timestamp_utc:
        raise ValueError("timestamp_utc is required for deterministic source-role review receipts")

    rows = queue_source_role_reviews_to_ui_rows(queue)
    if not rows:
        return ()

    claim_notes = queue_source_role_reviews_to_claim_notes(queue)
    receipt_id = source_role_review_receipt_id(queue)
    request_summary = {
        "automatic_classification": False,
        "claim_note_count": len(claim_notes),
        "metadata_only": True,
        "receipt_id": receipt_id,
        "review_required": True,
        "review_status": "USER_REVIEW_REQUIRED",
        "runtime_or_completion_claimed": False,
        "safe_metadata_rows": list(_safe_source_role_review_receipt_rows(rows)),
        "sensitive_inference_prohibited": True,
        "source_role_review_row_count": len(rows),
        "ui_row_count": len(rows),
    }
    event = build_action_log_event(
        session_id=session_id,
        actor_type=ACTOR_TYPE_APPLICATION,
        actor_id=actor_id,
        action_type="source_role_review_metadata_receipt",
        result="USER_REVIEW_REQUIRED",
        timestamp_utc=timestamp_utc,
        previous_event_hash=previous_event_hash,
        target_id=receipt_id,
        request_summary=request_summary,
        warnings=(
            "Metadata-only source-role review receipt; manual review required.",
            "Review-only metadata; no final-evidence state is recorded.",
        ),
        app_version=app_version,
    )
    return (event,)
