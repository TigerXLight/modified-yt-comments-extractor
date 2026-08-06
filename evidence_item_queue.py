from __future__ import annotations

from dataclasses import asdict, dataclass, field, is_dataclass
from enum import Enum
from typing import Any, Dict, Optional

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
