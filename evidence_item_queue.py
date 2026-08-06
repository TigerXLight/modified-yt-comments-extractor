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


class ManualMediaSourceChainRelationKind(_StringEnum):
    SAME_MEDIA = "SAME_MEDIA"
    DERIVATIVE = "DERIVATIVE"
    EXCERPT = "EXCERPT"
    REPOST = "REPOST"
    RELATED = "RELATED"
    UNKNOWN = "UNKNOWN"
    OTHER = "OTHER"


class ManualMediaSourceChainDirection(_StringEnum):
    SOURCE_TO_DERIVATIVE = "SOURCE_TO_DERIVATIVE"
    DERIVATIVE_TO_SOURCE = "DERIVATIVE_TO_SOURCE"
    RELATED_UNDIRECTED = "RELATED_UNDIRECTED"
    UNKNOWN = "UNKNOWN"


class ManualPublisherFramingCorrectionKind(_StringEnum):
    SOURCE_AUTHOR_CORRECTION = "SOURCE_AUTHOR_CORRECTION"
    DISPUTED_FRAMING = "DISPUTED_FRAMING"
    PUBLISHER_CREDIT_NOTE = "PUBLISHER_CREDIT_NOTE"
    COMPETING_CLAIM = "COMPETING_CLAIM"
    CONTEXT_CORRECTION = "CONTEXT_CORRECTION"
    UNKNOWN = "UNKNOWN"
    OTHER = "OTHER"


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
class ManualMediaSourceChainLink:
    source_item_id: str
    target_item_id: str
    relation_kind: ManualMediaSourceChainRelationKind = (
        ManualMediaSourceChainRelationKind.UNKNOWN
    )
    direction: ManualMediaSourceChainDirection = ManualMediaSourceChainDirection.UNKNOWN
    review_status: str = "USER_REVIEW_REQUIRED"
    provenance: str = "MANUAL_OPERATOR_SUPPLIED"
    operator_note_category: str = ""
    operator_note_recorded: bool = False
    created_at_utc: str = ""
    user_review_required: bool = True
    automated_matching: bool = False
    fingerprint_matching: bool = False
    automatic_duplicate_detection: bool = False
    automatic_classification: bool = False
    sensitive_inference_prohibited: bool = True
    raw_media_payload_included: bool = False
    raw_evidence_payload_included: bool = False
    full_local_path_included: bool = False
    completed_evidence_claimed: bool = False
    verified_evidence_claimed: bool = False
    live_capture_claimed: bool = False
    api_provider_capture_claimed: bool = False
    browser_automation_claimed: bool = False
    archive_download_ocr_warc_wacz_claimed: bool = False

    def to_dict(self) -> Dict[str, Any]:
        data = _dataclass_to_dict(self)
        data["manual_link_id"] = manual_media_source_chain_link_id(self)
        return data


@dataclass(frozen=True)
class ManualMediaSourceChainReviewRow:
    manual_link_id: str
    source_item_id: str
    target_item_id: str
    relation_kind: ManualMediaSourceChainRelationKind = (
        ManualMediaSourceChainRelationKind.UNKNOWN
    )
    direction: ManualMediaSourceChainDirection = ManualMediaSourceChainDirection.UNKNOWN
    review_status: str = "USER_REVIEW_REQUIRED"
    provenance: str = "MANUAL_OPERATOR_SUPPLIED"
    operator_note_category: str = ""
    operator_note_recorded: bool = False
    user_review_required: bool = True
    automated_matching: bool = False
    fingerprint_matching: bool = False
    automatic_duplicate_detection: bool = False
    automatic_classification: bool = False
    sensitive_inference_prohibited: bool = True
    raw_media_payload_included: bool = False
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
class ManualPublisherFramingCorrectionNote:
    queue_item_id: str
    related_item_id: str = ""
    correction_kind: ManualPublisherFramingCorrectionKind = (
        ManualPublisherFramingCorrectionKind.UNKNOWN
    )
    review_status: str = "USER_REVIEW_REQUIRED"
    provenance: str = "MANUAL_OPERATOR_SUPPLIED"
    source_author_name_recorded: bool = False
    source_author_url_recorded: bool = False
    correction_text_recorded: bool = False
    correction_source_url_recorded: bool = False
    disputed_framing_recorded: bool = False
    competing_claim_recorded: bool = False
    note_category: str = ""
    created_at_utc: str = ""
    user_review_required: bool = True
    metadata_only: bool = True
    automated_source_author_detection: bool = False
    automated_matching: bool = False
    fingerprint_matching: bool = False
    automatic_duplicate_detection: bool = False
    automatic_classification: bool = False
    sensitive_inference_prohibited: bool = True
    raw_correction_payload_included: bool = False
    raw_media_payload_included: bool = False
    raw_evidence_payload_included: bool = False
    full_local_path_included: bool = False
    completed_evidence_claimed: bool = False
    verified_evidence_claimed: bool = False
    live_capture_claimed: bool = False
    api_provider_capture_claimed: bool = False
    browser_automation_claimed: bool = False
    archive_download_ocr_warc_wacz_claimed: bool = False

    def to_dict(self) -> Dict[str, Any]:
        data = _dataclass_to_dict(self)
        data["correction_note_id"] = manual_publisher_framing_correction_note_id(self)
        return data


@dataclass(frozen=True)
class ManualPublisherFramingCorrectionReviewRow:
    correction_note_id: str
    queue_item_id: str
    related_item_id: str = ""
    correction_kind: ManualPublisherFramingCorrectionKind = (
        ManualPublisherFramingCorrectionKind.UNKNOWN
    )
    review_status: str = "USER_REVIEW_REQUIRED"
    provenance: str = "MANUAL_OPERATOR_SUPPLIED"
    source_author_name_recorded: bool = False
    source_author_url_recorded: bool = False
    correction_text_recorded: bool = False
    correction_source_url_recorded: bool = False
    disputed_framing_recorded: bool = False
    competing_claim_recorded: bool = False
    note_category: str = ""
    user_review_required: bool = True
    metadata_only: bool = True
    automated_source_author_detection: bool = False
    automated_matching: bool = False
    fingerprint_matching: bool = False
    automatic_duplicate_detection: bool = False
    automatic_classification: bool = False
    sensitive_inference_prohibited: bool = True
    raw_correction_payload_included: bool = False
    raw_media_payload_included: bool = False
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
class SourceRoleReviewFlowSummary:
    flow_id: str
    status: str
    review_status: str = "USER_REVIEW_REQUIRED"
    metadata_only: bool = True
    user_review_required: bool = True
    source_role_review_count: int = 0
    claim_note_count: int = 0
    ui_row_count: int = 0
    provenance_receipt_count: int = 0
    queue_item_ids: tuple[str, ...] = ()
    source_roles: tuple[str, ...] = ()
    primary_source_statuses: tuple[str, ...] = ()
    currentness_statuses: tuple[str, ...] = ()
    receipt_ids: tuple[str, ...] = ()
    receipt_event_ids: tuple[str, ...] = ()
    receipt_event_hashes: tuple[str, ...] = ()
    automatic_classification: bool = False
    sensitive_inference_prohibited: bool = True
    raw_evidence_payload_included: bool = False
    full_local_path_included: bool = False
    runtime_or_completion_claimed: bool = False
    final_evidence_state_recorded: bool = False
    note: str = "Manual review metadata only; no final-evidence state is recorded."

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass(frozen=True)
class ClosedLoopSourceChainReviewSummary:
    summary_id: str
    status: str
    review_status: str = "USER_REVIEW_REQUIRED"
    metadata_only: bool = True
    explicit_metadata_only: bool = True
    user_review_required: bool = True
    total_source_role_review_count: int = 0
    flagged_review_count: int = 0
    propagated_source_review_count: int = 0
    source_chain_gap_count: int = 0
    closed_loop_reporting_flag_count: int = 0
    flagged_queue_item_ids: tuple[str, ...] = ()
    source_roles: tuple[str, ...] = ()
    primary_source_statuses: tuple[str, ...] = ()
    currentness_statuses: tuple[str, ...] = ()
    automatic_classification: bool = False
    sensitive_inference_prohibited: bool = True
    inference_performed: bool = False
    duplicate_detection_performed: bool = False
    raw_evidence_payload_included: bool = False
    full_local_path_included: bool = False
    completed_evidence_claimed: bool = False
    note: str = (
        "Summary-only review metadata based on explicit propagated-source, "
        "source-chain-gap, and closed-loop flags already recorded on queue items."
    )

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass(frozen=True)
class ManualMediaSourceChainReviewSummary:
    summary_id: str
    status: str
    review_status: str = "USER_REVIEW_REQUIRED"
    metadata_only: bool = True
    manual_operator_supplied: bool = True
    user_review_required: bool = True
    manual_link_count: int = 0
    source_item_ids: tuple[str, ...] = ()
    target_item_ids: tuple[str, ...] = ()
    manual_link_ids: tuple[str, ...] = ()
    relation_kinds: tuple[str, ...] = ()
    directions: tuple[str, ...] = ()
    provenance_values: tuple[str, ...] = ()
    operator_note_count: int = 0
    automated_matching: bool = False
    fingerprint_matching: bool = False
    automatic_duplicate_detection: bool = False
    automatic_classification: bool = False
    sensitive_inference_prohibited: bool = True
    raw_media_payload_included: bool = False
    raw_evidence_payload_included: bool = False
    full_local_path_included: bool = False
    completed_evidence_claimed: bool = False
    verified_evidence_claimed: bool = False
    live_capture_claimed: bool = False
    api_provider_capture_claimed: bool = False
    browser_automation_claimed: bool = False
    archive_download_ocr_warc_wacz_claimed: bool = False
    note: str = (
        "Manual/operator-supplied media source-chain links for review metadata only."
    )

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass(frozen=True)
class ManualMediaSourceChainReviewFlowSummary:
    flow_id: str
    status: str
    review_status: str = "USER_REVIEW_REQUIRED"
    metadata_only: bool = True
    manual_operator_supplied: bool = True
    user_review_required: bool = True
    manual_link_count: int = 0
    review_row_count: int = 0
    review_summary_count: int = 0
    provenance_receipt_count: int = 0
    manual_link_ids: tuple[str, ...] = ()
    source_item_ids: tuple[str, ...] = ()
    target_item_ids: tuple[str, ...] = ()
    relation_kinds: tuple[str, ...] = ()
    directions: tuple[str, ...] = ()
    summary_ids: tuple[str, ...] = ()
    receipt_ids: tuple[str, ...] = ()
    receipt_event_ids: tuple[str, ...] = ()
    receipt_event_hashes: tuple[str, ...] = ()
    automated_matching: bool = False
    fingerprint_matching: bool = False
    automatic_duplicate_detection: bool = False
    automatic_classification: bool = False
    sensitive_inference_prohibited: bool = True
    raw_media_payload_included: bool = False
    raw_evidence_payload_included: bool = False
    full_local_path_included: bool = False
    runtime_or_completion_claimed: bool = False
    final_evidence_state_recorded: bool = False
    completed_evidence_claimed: bool = False
    verified_evidence_claimed: bool = False
    note: str = (
        "Manual media source-chain review metadata only; no final-evidence "
        "state is recorded."
    )

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass(frozen=True)
class ManualPublisherFramingCorrectionReviewSummary:
    summary_id: str
    status: str
    review_status: str = "USER_REVIEW_REQUIRED"
    metadata_only: bool = True
    manual_operator_supplied: bool = True
    user_review_required: bool = True
    correction_note_count: int = 0
    queue_item_ids: tuple[str, ...] = ()
    related_item_ids: tuple[str, ...] = ()
    correction_note_ids: tuple[str, ...] = ()
    correction_kinds: tuple[str, ...] = ()
    source_author_name_recorded_count: int = 0
    source_author_url_recorded_count: int = 0
    correction_text_recorded_count: int = 0
    correction_source_url_recorded_count: int = 0
    disputed_framing_recorded_count: int = 0
    competing_claim_recorded_count: int = 0
    automated_source_author_detection: bool = False
    automated_matching: bool = False
    fingerprint_matching: bool = False
    automatic_duplicate_detection: bool = False
    automatic_classification: bool = False
    sensitive_inference_prohibited: bool = True
    raw_correction_payload_included: bool = False
    raw_media_payload_included: bool = False
    raw_evidence_payload_included: bool = False
    full_local_path_included: bool = False
    completed_evidence_claimed: bool = False
    verified_evidence_claimed: bool = False
    note: str = (
        "Manual disputed-framing/source-author correction metadata only; "
        "no final-evidence state is recorded."
    )

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass(frozen=True)
class ManualPublisherFramingCorrectionReviewFlowSummary:
    flow_id: str
    status: str
    review_status: str = "USER_REVIEW_REQUIRED"
    metadata_only: bool = True
    manual_operator_supplied: bool = True
    user_review_required: bool = True
    correction_note_count: int = 0
    review_row_count: int = 0
    review_summary_count: int = 0
    provenance_receipt_count: int = 0
    correction_note_ids: tuple[str, ...] = ()
    queue_item_ids: tuple[str, ...] = ()
    related_item_ids: tuple[str, ...] = ()
    correction_kinds: tuple[str, ...] = ()
    summary_ids: tuple[str, ...] = ()
    receipt_ids: tuple[str, ...] = ()
    receipt_event_ids: tuple[str, ...] = ()
    receipt_event_hashes: tuple[str, ...] = ()
    automated_source_author_detection: bool = False
    automatic_publisher_framing_analysis: bool = False
    automatic_correction: bool = False
    automated_matching: bool = False
    fingerprint_matching: bool = False
    automatic_duplicate_detection: bool = False
    automatic_classification: bool = False
    sensitive_inference_prohibited: bool = True
    raw_correction_payload_included: bool = False
    raw_media_payload_included: bool = False
    raw_evidence_payload_included: bool = False
    full_local_path_included: bool = False
    runtime_or_completion_claimed: bool = False
    final_evidence_state_recorded: bool = False
    completed_evidence_claimed: bool = False
    verified_evidence_claimed: bool = False
    note: str = (
        "Manual publisher-framing/source-author correction review metadata only; "
        "no final-evidence state is recorded."
    )

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
    manual_media_source_chain_links: tuple[ManualMediaSourceChainLink, ...] = field(
        default_factory=tuple
    )
    manual_publisher_framing_corrections: tuple[
        ManualPublisherFramingCorrectionNote, ...
    ] = field(default_factory=tuple)

    def to_dict(self) -> Dict[str, Any]:
        data = _dataclass_to_dict(self)
        data["manual_media_source_chain_links"] = [
            link.to_dict() for link in self.manual_media_source_chain_links
        ]
        data["manual_publisher_framing_corrections"] = [
            note.to_dict() for note in self.manual_publisher_framing_corrections
        ]
        return data


def manual_publisher_framing_correction_note_id(
    note: ManualPublisherFramingCorrectionNote,
) -> str:
    payload = {
        "competing_claim_recorded": note.competing_claim_recorded,
        "correction_kind": note.correction_kind.value,
        "correction_source_url_recorded": note.correction_source_url_recorded,
        "correction_text_recorded": note.correction_text_recorded,
        "created_at_utc": note.created_at_utc,
        "disputed_framing_recorded": note.disputed_framing_recorded,
        "note_category": note.note_category,
        "provenance": note.provenance,
        "queue_item_id": note.queue_item_id,
        "related_item_id": note.related_item_id,
        "review_status": note.review_status,
        "source_author_name_recorded": note.source_author_name_recorded,
        "source_author_url_recorded": note.source_author_url_recorded,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return "manual_publisher_framing_correction_" + hashlib.sha256(
        encoded.encode("utf-8")
    ).hexdigest()[:16]


def manual_publisher_framing_corrections_to_ui_rows(
    queue: EvidenceItemQueue,
) -> tuple[ManualPublisherFramingCorrectionReviewRow, ...]:
    return tuple(
        ManualPublisherFramingCorrectionReviewRow(
            correction_note_id=manual_publisher_framing_correction_note_id(note),
            queue_item_id=note.queue_item_id,
            related_item_id=note.related_item_id,
            correction_kind=note.correction_kind,
            review_status=note.review_status,
            provenance=note.provenance,
            source_author_name_recorded=note.source_author_name_recorded,
            source_author_url_recorded=note.source_author_url_recorded,
            correction_text_recorded=note.correction_text_recorded,
            correction_source_url_recorded=note.correction_source_url_recorded,
            disputed_framing_recorded=note.disputed_framing_recorded,
            competing_claim_recorded=note.competing_claim_recorded,
            note_category=note.note_category,
            user_review_required=note.user_review_required,
            metadata_only=note.metadata_only,
            automated_source_author_detection=note.automated_source_author_detection,
            automated_matching=note.automated_matching,
            fingerprint_matching=note.fingerprint_matching,
            automatic_duplicate_detection=note.automatic_duplicate_detection,
            automatic_classification=note.automatic_classification,
            sensitive_inference_prohibited=note.sensitive_inference_prohibited,
            raw_correction_payload_included=note.raw_correction_payload_included,
            raw_media_payload_included=note.raw_media_payload_included,
            raw_evidence_payload_included=note.raw_evidence_payload_included,
            full_local_path_included=note.full_local_path_included,
            completed_evidence_claimed=note.completed_evidence_claimed,
            verified_evidence_claimed=note.verified_evidence_claimed,
            live_capture_claimed=note.live_capture_claimed,
            api_provider_capture_claimed=note.api_provider_capture_claimed,
            browser_automation_claimed=note.browser_automation_claimed,
            archive_download_ocr_warc_wacz_claimed=(
                note.archive_download_ocr_warc_wacz_claimed
            ),
        )
        for note in sorted(
            queue.manual_publisher_framing_corrections,
            key=lambda note: (
                note.queue_item_id,
                note.related_item_id,
                note.correction_kind.value,
                note.created_at_utc,
                note.note_category,
            ),
        )
    )


def _manual_publisher_framing_summary_rows(
    rows: tuple[ManualPublisherFramingCorrectionReviewRow, ...],
) -> tuple[dict[str, Any], ...]:
    return tuple(
        {
            "competing_claim_recorded": row.competing_claim_recorded,
            "correction_kind": row.correction_kind.value,
            "correction_note_id": row.correction_note_id,
            "correction_source_url_recorded": row.correction_source_url_recorded,
            "correction_text_recorded": row.correction_text_recorded,
            "disputed_framing_recorded": row.disputed_framing_recorded,
            "metadata_only": row.metadata_only,
            "note_category": row.note_category,
            "provenance": row.provenance,
            "queue_item_id": row.queue_item_id,
            "related_item_id": row.related_item_id,
            "review_status": row.review_status,
            "source_author_name_recorded": row.source_author_name_recorded,
            "source_author_url_recorded": row.source_author_url_recorded,
            "user_review_required": row.user_review_required,
        }
        for row in rows
    )


def manual_publisher_framing_correction_review_summary_id(
    rows: tuple[ManualPublisherFramingCorrectionReviewRow, ...],
) -> str:
    payload = {
        "review_summary_kind": "manual_publisher_framing_corrections",
        "rows": list(_manual_publisher_framing_summary_rows(rows)),
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return "manual_publisher_framing_review_" + hashlib.sha256(
        encoded.encode("utf-8")
    ).hexdigest()[:16]


def build_manual_publisher_framing_correction_review_summary(
    queue: EvidenceItemQueue,
) -> ManualPublisherFramingCorrectionReviewSummary:
    rows = manual_publisher_framing_corrections_to_ui_rows(queue)
    return ManualPublisherFramingCorrectionReviewSummary(
        summary_id=manual_publisher_framing_correction_review_summary_id(rows),
        status=(
            "USER_REVIEW_REQUIRED"
            if rows
            else "NO_MANUAL_PUBLISHER_FRAMING_CORRECTIONS"
        ),
        correction_note_count=len(rows),
        queue_item_ids=tuple(row.queue_item_id for row in rows),
        related_item_ids=tuple(row.related_item_id for row in rows),
        correction_note_ids=tuple(row.correction_note_id for row in rows),
        correction_kinds=tuple(row.correction_kind.value for row in rows),
        source_author_name_recorded_count=sum(
            1 for row in rows if row.source_author_name_recorded
        ),
        source_author_url_recorded_count=sum(
            1 for row in rows if row.source_author_url_recorded
        ),
        correction_text_recorded_count=sum(
            1 for row in rows if row.correction_text_recorded
        ),
        correction_source_url_recorded_count=sum(
            1 for row in rows if row.correction_source_url_recorded
        ),
        disputed_framing_recorded_count=sum(
            1 for row in rows if row.disputed_framing_recorded
        ),
        competing_claim_recorded_count=sum(
            1 for row in rows if row.competing_claim_recorded
        ),
    )


def manual_publisher_framing_correction_review_summary_to_json(
    summary: ManualPublisherFramingCorrectionReviewSummary,
) -> str:
    return json.dumps(summary.to_dict(), indent=2, sort_keys=True)


def build_manual_publisher_framing_correction_review_summary_text(
    summary: ManualPublisherFramingCorrectionReviewSummary,
) -> str:
    return "\n".join(
        [
            "Manual publisher framing/source-author correction review summary",
            f"Summary ID: {summary.summary_id}",
            f"Status: {summary.status}",
            f"Review status: {summary.review_status}",
            f"Correction notes: {summary.correction_note_count}",
            f"Source-author names recorded: {summary.source_author_name_recorded_count}",
            f"Source-author URLs recorded: {summary.source_author_url_recorded_count}",
            f"Correction text recorded: {summary.correction_text_recorded_count}",
            f"Correction source URLs recorded: {summary.correction_source_url_recorded_count}",
            f"Disputed framing notes: {summary.disputed_framing_recorded_count}",
            f"Competing claim notes: {summary.competing_claim_recorded_count}",
            "Metadata only: yes",
            "Manual/operator supplied: yes",
            "Automated source-author detection: false",
            "Automated media matching: false",
            "Fingerprint comparison: false",
            "Automatic duplicate detection: false",
            "Auto-classify flag: false",
            "Sensitive inference prohibited: true",
            "Runtime/completion claim flags: false",
        ]
    )


def _safe_manual_publisher_framing_correction_receipt_rows(
    rows: tuple[ManualPublisherFramingCorrectionReviewRow, ...],
) -> tuple[dict[str, Any], ...]:
    return tuple(
        {
            "automatic_classification": row.automatic_classification,
            "automatic_correction": False,
            "automatic_duplicate_detection": row.automatic_duplicate_detection,
            "automatic_publisher_framing_analysis": False,
            "automated_matching": row.automated_matching,
            "automated_source_author_detection": (
                row.automated_source_author_detection
            ),
            "competing_claim_recorded": row.competing_claim_recorded,
            "correction_kind": row.correction_kind.value,
            "correction_note_id": row.correction_note_id,
            "correction_source_url_recorded": row.correction_source_url_recorded,
            "correction_text_recorded": row.correction_text_recorded,
            "disputed_framing_recorded": row.disputed_framing_recorded,
            "fingerprint_matching": row.fingerprint_matching,
            "metadata_only": row.metadata_only,
            "note_category": row.note_category,
            "provenance": row.provenance,
            "queue_item_id": row.queue_item_id,
            "related_item_id": row.related_item_id,
            "review_status": row.review_status,
            "sensitive_inference_prohibited": row.sensitive_inference_prohibited,
            "source_author_name_recorded": row.source_author_name_recorded,
            "source_author_url_recorded": row.source_author_url_recorded,
            "user_review_required": row.user_review_required,
        }
        for row in rows
    )


def manual_publisher_framing_correction_receipt_id(
    queue: EvidenceItemQueue,
) -> str:
    rows = manual_publisher_framing_corrections_to_ui_rows(queue)
    payload = {
        "receipt_kind": "manual_publisher_framing_correction_review",
        "rows": list(_safe_manual_publisher_framing_correction_receipt_rows(rows)),
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return "manual_publisher_framing_receipt_" + hashlib.sha256(
        encoded.encode("utf-8")
    ).hexdigest()[:16]


def manual_publisher_framing_corrections_to_action_log_events(
    queue: EvidenceItemQueue,
    *,
    session_id: str,
    timestamp_utc: str,
    previous_event_hash: str = "",
    actor_id: str = "",
    app_version: str = "",
) -> tuple[CaptureActionLogEvent, ...]:
    if not session_id:
        raise ValueError(
            "session_id is required for manual publisher-framing correction receipts"
        )
    if not timestamp_utc:
        raise ValueError(
            "timestamp_utc is required for deterministic manual publisher-framing "
            "correction receipts"
        )

    rows = manual_publisher_framing_corrections_to_ui_rows(queue)
    if not rows:
        return ()

    summary = build_manual_publisher_framing_correction_review_summary(queue)
    receipt_id = manual_publisher_framing_correction_receipt_id(queue)
    request_summary = {
        "automatic_classification": False,
        "automatic_correction": False,
        "automatic_duplicate_detection": False,
        "automatic_publisher_framing_analysis": False,
        "automated_matching": False,
        "automated_source_author_detection": False,
        "completed_evidence_claimed": False,
        "correction_note_count": len(rows),
        "fingerprint_matching": False,
        "manual_operator_supplied": True,
        "metadata_only": True,
        "receipt_id": receipt_id,
        "review_required": True,
        "review_status": "USER_REVIEW_REQUIRED",
        "runtime_or_completion_claimed": False,
        "safe_metadata_rows": list(
            _safe_manual_publisher_framing_correction_receipt_rows(rows)
        ),
        "sensitive_inference_prohibited": True,
        "summary_id": summary.summary_id,
        "verified_evidence_claimed": False,
    }
    event = build_action_log_event(
        session_id=session_id,
        actor_type=ACTOR_TYPE_APPLICATION,
        actor_id=actor_id,
        action_type="manual_publisher_framing_correction_review",
        result="USER_REVIEW_REQUIRED",
        timestamp_utc=timestamp_utc,
        previous_event_hash=previous_event_hash,
        target_id=receipt_id,
        request_summary=request_summary,
        artifact_ids=summary.correction_note_ids,
        warnings=(
            "Manual publisher-framing/source-author correction metadata; manual review required.",
            "Review-only metadata; no final-evidence state is recorded.",
        ),
        app_version=app_version,
    )
    return (event,)


def manual_publisher_framing_correction_review_flow_id(
    *,
    rows: tuple[ManualPublisherFramingCorrectionReviewRow, ...],
    summary_ids: tuple[str, ...],
    receipt_ids: tuple[str, ...],
) -> str:
    payload = {
        "receipt_ids": list(receipt_ids),
        "review_flow_kind": "manual_publisher_framing_corrections",
        "rows": list(_safe_manual_publisher_framing_correction_receipt_rows(rows)),
        "summary_ids": list(summary_ids),
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return "manual_publisher_framing_flow_" + hashlib.sha256(
        encoded.encode("utf-8")
    ).hexdigest()[:16]


def build_manual_publisher_framing_correction_review_flow_summary(
    queue: EvidenceItemQueue,
    *,
    session_id: str,
    timestamp_utc: str,
    previous_event_hash: str = "",
    actor_id: str = "",
    app_version: str = "",
) -> ManualPublisherFramingCorrectionReviewFlowSummary:
    rows = manual_publisher_framing_corrections_to_ui_rows(queue)
    summary = build_manual_publisher_framing_correction_review_summary(queue)
    receipt_events = manual_publisher_framing_corrections_to_action_log_events(
        queue,
        session_id=session_id,
        timestamp_utc=timestamp_utc,
        previous_event_hash=previous_event_hash,
        actor_id=actor_id,
        app_version=app_version,
    )
    receipt_ids = tuple(event.target_id for event in receipt_events)
    summary_ids = (summary.summary_id,) if rows else ()
    return ManualPublisherFramingCorrectionReviewFlowSummary(
        flow_id=manual_publisher_framing_correction_review_flow_id(
            rows=rows,
            summary_ids=summary_ids,
            receipt_ids=receipt_ids,
        ),
        status=(
            "USER_REVIEW_REQUIRED"
            if rows
            else "NO_MANUAL_PUBLISHER_FRAMING_CORRECTIONS"
        ),
        correction_note_count=len(rows),
        review_row_count=len(rows),
        review_summary_count=1 if rows else 0,
        provenance_receipt_count=len(receipt_events),
        correction_note_ids=summary.correction_note_ids,
        queue_item_ids=summary.queue_item_ids,
        related_item_ids=summary.related_item_ids,
        correction_kinds=summary.correction_kinds,
        summary_ids=summary_ids,
        receipt_ids=receipt_ids,
        receipt_event_ids=tuple(event.event_id for event in receipt_events),
        receipt_event_hashes=tuple(event.event_hash for event in receipt_events),
        automated_source_author_detection=False,
        automatic_publisher_framing_analysis=False,
        automatic_correction=False,
        automated_matching=False,
        fingerprint_matching=False,
        automatic_duplicate_detection=False,
        automatic_classification=False,
        sensitive_inference_prohibited=True,
    )


def manual_publisher_framing_correction_review_flow_summary_to_json(
    summary: ManualPublisherFramingCorrectionReviewFlowSummary,
) -> str:
    return json.dumps(summary.to_dict(), indent=2, sort_keys=True)


def build_manual_publisher_framing_correction_review_flow_summary_text(
    summary: ManualPublisherFramingCorrectionReviewFlowSummary,
) -> str:
    return "\n".join(
        [
            "Manual publisher framing/source-author correction review flow summary",
            f"Flow ID: {summary.flow_id}",
            f"Status: {summary.status}",
            f"Review status: {summary.review_status}",
            f"Correction notes: {summary.correction_note_count}",
            f"Review rows: {summary.review_row_count}",
            f"Review summaries: {summary.review_summary_count}",
            f"Provenance receipts: {summary.provenance_receipt_count}",
            "Metadata only: yes",
            "Manual/operator supplied: yes",
            "Automated source-author detection: false",
            "Automated publisher-framing analysis: false",
            "Auto-correction flag: false",
            "Automated media matching: false",
            "Fingerprint comparison: false",
            "Automatic duplicate detection: false",
            "Auto-classify flag: false",
            "Sensitive inference prohibited: true",
            "Runtime/completion claim flags: false",
        ]
    )


def manual_media_source_chain_link_id(link: ManualMediaSourceChainLink) -> str:
    payload = {
        "created_at_utc": link.created_at_utc,
        "direction": link.direction.value,
        "operator_note_category": link.operator_note_category,
        "operator_note_recorded": link.operator_note_recorded,
        "provenance": link.provenance,
        "relation_kind": link.relation_kind.value,
        "review_status": link.review_status,
        "source_item_id": link.source_item_id,
        "target_item_id": link.target_item_id,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return "manual_media_source_chain_link_" + hashlib.sha256(
        encoded.encode("utf-8")
    ).hexdigest()[:16]


def manual_media_source_chain_links_to_ui_rows(
    queue: EvidenceItemQueue,
) -> tuple[ManualMediaSourceChainReviewRow, ...]:
    rows = tuple(
        ManualMediaSourceChainReviewRow(
            manual_link_id=manual_media_source_chain_link_id(link),
            source_item_id=link.source_item_id,
            target_item_id=link.target_item_id,
            relation_kind=link.relation_kind,
            direction=link.direction,
            review_status=link.review_status,
            provenance=link.provenance,
            operator_note_category=link.operator_note_category,
            operator_note_recorded=link.operator_note_recorded,
            user_review_required=link.user_review_required,
            automated_matching=link.automated_matching,
            fingerprint_matching=link.fingerprint_matching,
            automatic_duplicate_detection=link.automatic_duplicate_detection,
            automatic_classification=link.automatic_classification,
            sensitive_inference_prohibited=link.sensitive_inference_prohibited,
            raw_media_payload_included=link.raw_media_payload_included,
            raw_evidence_payload_included=link.raw_evidence_payload_included,
            full_local_path_included=link.full_local_path_included,
            completed_evidence_claimed=link.completed_evidence_claimed,
            verified_evidence_claimed=link.verified_evidence_claimed,
            live_capture_claimed=link.live_capture_claimed,
            api_provider_capture_claimed=link.api_provider_capture_claimed,
            browser_automation_claimed=link.browser_automation_claimed,
            archive_download_ocr_warc_wacz_claimed=(
                link.archive_download_ocr_warc_wacz_claimed
            ),
        )
        for link in queue.manual_media_source_chain_links
    )
    return tuple(
        sorted(
            rows,
            key=lambda row: (
                row.source_item_id,
                row.target_item_id,
                row.relation_kind.value,
                row.direction.value,
                row.manual_link_id,
            ),
        )
    )


def _manual_media_source_chain_summary_rows(
    rows: tuple[ManualMediaSourceChainReviewRow, ...],
) -> tuple[dict[str, Any], ...]:
    return tuple(
        {
            "direction": row.direction.value,
            "manual_link_id": row.manual_link_id,
            "operator_note_category": row.operator_note_category,
            "operator_note_recorded": row.operator_note_recorded,
            "provenance": row.provenance,
            "relation_kind": row.relation_kind.value,
            "review_status": row.review_status,
            "source_item_id": row.source_item_id,
            "target_item_id": row.target_item_id,
        }
        for row in rows
    )


def manual_media_source_chain_review_summary_id(
    rows: tuple[ManualMediaSourceChainReviewRow, ...],
) -> str:
    payload = {
        "review_summary_kind": "manual_media_source_chain_links",
        "rows": list(_manual_media_source_chain_summary_rows(rows)),
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return "manual_media_source_chain_review_" + hashlib.sha256(
        encoded.encode("utf-8")
    ).hexdigest()[:16]


def build_manual_media_source_chain_review_summary(
    queue: EvidenceItemQueue,
) -> ManualMediaSourceChainReviewSummary:
    rows = manual_media_source_chain_links_to_ui_rows(queue)
    return ManualMediaSourceChainReviewSummary(
        summary_id=manual_media_source_chain_review_summary_id(rows),
        status="USER_REVIEW_REQUIRED" if rows else "NO_MANUAL_MEDIA_SOURCE_CHAIN_LINKS",
        manual_link_count=len(rows),
        source_item_ids=tuple(row.source_item_id for row in rows),
        target_item_ids=tuple(row.target_item_id for row in rows),
        manual_link_ids=tuple(row.manual_link_id for row in rows),
        relation_kinds=tuple(row.relation_kind.value for row in rows),
        directions=tuple(row.direction.value for row in rows),
        provenance_values=tuple(row.provenance for row in rows),
        operator_note_count=sum(1 for row in rows if row.operator_note_recorded),
    )


def manual_media_source_chain_review_summary_to_json(
    summary: ManualMediaSourceChainReviewSummary,
) -> str:
    return json.dumps(summary.to_dict(), indent=2, sort_keys=True)


def build_manual_media_source_chain_review_summary_text(
    summary: ManualMediaSourceChainReviewSummary,
) -> str:
    return "\n".join(
        [
            "Manual media source-chain review summary",
            f"Summary ID: {summary.summary_id}",
            f"Status: {summary.status}",
            f"Review status: {summary.review_status}",
            f"Manual links: {summary.manual_link_count}",
            f"Operator-note records: {summary.operator_note_count}",
            "Metadata only: yes",
            "Manual/operator supplied: yes",
            "Automated media matching: false",
            "Fingerprint comparison: false",
            "Automatic duplicate detection: false",
            "Auto-classify flag: false",
            "Sensitive inference prohibited: true",
            "Runtime/completion claim flags: false",
        ]
    )


def _safe_manual_media_source_chain_receipt_rows(
    rows: tuple[ManualMediaSourceChainReviewRow, ...],
) -> tuple[dict[str, Any], ...]:
    return tuple(
        {
            "automatic_classification": row.automatic_classification,
            "automatic_duplicate_detection": row.automatic_duplicate_detection,
            "automated_matching": row.automated_matching,
            "direction": row.direction.value,
            "fingerprint_matching": row.fingerprint_matching,
            "manual_link_id": row.manual_link_id,
            "operator_note_category": row.operator_note_category,
            "operator_note_recorded": row.operator_note_recorded,
            "provenance": row.provenance,
            "relation_kind": row.relation_kind.value,
            "review_status": row.review_status,
            "sensitive_inference_prohibited": row.sensitive_inference_prohibited,
            "source_item_id": row.source_item_id,
            "target_item_id": row.target_item_id,
            "user_review_required": row.user_review_required,
        }
        for row in rows
    )


def manual_media_source_chain_receipt_id(queue: EvidenceItemQueue) -> str:
    rows = manual_media_source_chain_links_to_ui_rows(queue)
    payload = {
        "receipt_kind": "manual_media_source_chain_link_review",
        "rows": list(_safe_manual_media_source_chain_receipt_rows(rows)),
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return "manual_media_source_chain_receipt_" + hashlib.sha256(
        encoded.encode("utf-8")
    ).hexdigest()[:16]


def manual_media_source_chain_links_to_action_log_events(
    queue: EvidenceItemQueue,
    *,
    session_id: str,
    timestamp_utc: str,
    previous_event_hash: str = "",
    actor_id: str = "",
    app_version: str = "",
) -> tuple[CaptureActionLogEvent, ...]:
    if not session_id:
        raise ValueError("session_id is required for manual media source-chain receipts")
    if not timestamp_utc:
        raise ValueError(
            "timestamp_utc is required for deterministic manual media source-chain receipts"
        )

    rows = manual_media_source_chain_links_to_ui_rows(queue)
    if not rows:
        return ()

    summary = build_manual_media_source_chain_review_summary(queue)
    receipt_id = manual_media_source_chain_receipt_id(queue)
    request_summary = {
        "automatic_classification": False,
        "automatic_duplicate_detection": False,
        "automated_matching": False,
        "completed_evidence_claimed": False,
        "fingerprint_matching": False,
        "manual_link_count": len(rows),
        "manual_operator_supplied": True,
        "metadata_only": True,
        "receipt_id": receipt_id,
        "review_required": True,
        "review_status": "USER_REVIEW_REQUIRED",
        "runtime_or_completion_claimed": False,
        "safe_metadata_rows": list(_safe_manual_media_source_chain_receipt_rows(rows)),
        "sensitive_inference_prohibited": True,
        "summary_id": summary.summary_id,
    }
    event = build_action_log_event(
        session_id=session_id,
        actor_type=ACTOR_TYPE_APPLICATION,
        actor_id=actor_id,
        action_type="manual_media_source_chain_link_review",
        result="USER_REVIEW_REQUIRED",
        timestamp_utc=timestamp_utc,
        previous_event_hash=previous_event_hash,
        target_id=receipt_id,
        request_summary=request_summary,
        artifact_ids=summary.manual_link_ids,
        warnings=(
            "Manual media source-chain link metadata; manual review required.",
            "Review-only metadata; no final-evidence state is recorded.",
        ),
        app_version=app_version,
    )
    return (event,)


def manual_media_source_chain_review_flow_id(
    *,
    rows: tuple[ManualMediaSourceChainReviewRow, ...],
    summary_ids: tuple[str, ...],
    receipt_ids: tuple[str, ...],
) -> str:
    payload = {
        "receipt_ids": list(receipt_ids),
        "review_flow_kind": "manual_media_source_chain_links",
        "rows": list(_safe_manual_media_source_chain_receipt_rows(rows)),
        "summary_ids": list(summary_ids),
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return "manual_media_source_chain_flow_" + hashlib.sha256(
        encoded.encode("utf-8")
    ).hexdigest()[:16]


def build_manual_media_source_chain_review_flow_summary(
    queue: EvidenceItemQueue,
    *,
    session_id: str,
    timestamp_utc: str,
    previous_event_hash: str = "",
    actor_id: str = "",
    app_version: str = "",
) -> ManualMediaSourceChainReviewFlowSummary:
    rows = manual_media_source_chain_links_to_ui_rows(queue)
    summary = build_manual_media_source_chain_review_summary(queue)
    receipt_events = manual_media_source_chain_links_to_action_log_events(
        queue,
        session_id=session_id,
        timestamp_utc=timestamp_utc,
        previous_event_hash=previous_event_hash,
        actor_id=actor_id,
        app_version=app_version,
    )
    receipt_ids = tuple(event.target_id for event in receipt_events)
    summary_ids = (summary.summary_id,) if rows else ()
    return ManualMediaSourceChainReviewFlowSummary(
        flow_id=manual_media_source_chain_review_flow_id(
            rows=rows,
            summary_ids=summary_ids,
            receipt_ids=receipt_ids,
        ),
        status=(
            "USER_REVIEW_REQUIRED"
            if rows
            else "NO_MANUAL_MEDIA_SOURCE_CHAIN_LINKS"
        ),
        manual_link_count=len(rows),
        review_row_count=len(rows),
        review_summary_count=1 if rows else 0,
        provenance_receipt_count=len(receipt_events),
        manual_link_ids=summary.manual_link_ids,
        source_item_ids=summary.source_item_ids,
        target_item_ids=summary.target_item_ids,
        relation_kinds=summary.relation_kinds,
        directions=summary.directions,
        summary_ids=summary_ids,
        receipt_ids=receipt_ids,
        receipt_event_ids=tuple(event.event_id for event in receipt_events),
        receipt_event_hashes=tuple(event.event_hash for event in receipt_events),
        automated_matching=False,
        fingerprint_matching=False,
        automatic_duplicate_detection=False,
        automatic_classification=False,
        sensitive_inference_prohibited=True,
    )


def manual_media_source_chain_review_flow_summary_to_json(
    summary: ManualMediaSourceChainReviewFlowSummary,
) -> str:
    return json.dumps(summary.to_dict(), indent=2, sort_keys=True)


def build_manual_media_source_chain_review_flow_summary_text(
    summary: ManualMediaSourceChainReviewFlowSummary,
) -> str:
    return "\n".join(
        [
            "Manual media source-chain review flow summary",
            f"Flow ID: {summary.flow_id}",
            f"Status: {summary.status}",
            f"Review status: {summary.review_status}",
            f"Manual links: {summary.manual_link_count}",
            f"Review rows: {summary.review_row_count}",
            f"Review summaries: {summary.review_summary_count}",
            f"Provenance receipts: {summary.provenance_receipt_count}",
            "Metadata only: yes",
            "Manual/operator supplied: yes",
            "Automated media matching: false",
            "Fingerprint comparison: false",
            "Automatic duplicate detection: false",
            "Auto-classify flag: false",
            "Sensitive inference prohibited: true",
            "Runtime/completion claim flags: false",
        ]
    )


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


def source_role_review_flow_id(
    *,
    rows: tuple[SourceRoleReviewUIRow, ...],
    receipt_ids: tuple[str, ...],
) -> str:
    payload = {
        "receipt_ids": list(receipt_ids),
        "review_flow_kind": "source_role_review_metadata",
        "rows": list(_safe_source_role_review_receipt_rows(rows)),
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return "source_role_review_flow_" + hashlib.sha256(
        encoded.encode("utf-8")
    ).hexdigest()[:16]


def build_source_role_review_flow_summary(
    queue: EvidenceItemQueue,
    *,
    session_id: str,
    timestamp_utc: str,
    previous_event_hash: str = "",
    actor_id: str = "",
    app_version: str = "",
) -> SourceRoleReviewFlowSummary:
    rows = queue_source_role_reviews_to_ui_rows(queue)
    claim_notes = queue_source_role_reviews_to_claim_notes(queue)
    receipt_events = queue_source_role_reviews_to_action_log_events(
        queue,
        session_id=session_id,
        timestamp_utc=timestamp_utc,
        previous_event_hash=previous_event_hash,
        actor_id=actor_id,
        app_version=app_version,
    )
    receipt_ids = tuple(event.target_id for event in receipt_events)
    return SourceRoleReviewFlowSummary(
        flow_id=source_role_review_flow_id(rows=rows, receipt_ids=receipt_ids),
        status="USER_REVIEW_REQUIRED" if rows else "NO_SOURCE_ROLE_REVIEWS",
        source_role_review_count=len(rows),
        claim_note_count=len(claim_notes),
        ui_row_count=len(rows),
        provenance_receipt_count=len(receipt_events),
        queue_item_ids=tuple(row.queue_item_id for row in rows),
        source_roles=tuple(row.source_role.value for row in rows),
        primary_source_statuses=tuple(row.primary_source_status.value for row in rows),
        currentness_statuses=tuple(row.currentness_status.value for row in rows),
        receipt_ids=receipt_ids,
        receipt_event_ids=tuple(event.event_id for event in receipt_events),
        receipt_event_hashes=tuple(event.event_hash for event in receipt_events),
        automatic_classification=False,
        sensitive_inference_prohibited=True,
    )


def source_role_review_flow_summary_to_json(
    summary: SourceRoleReviewFlowSummary,
) -> str:
    return json.dumps(summary.to_dict(), indent=2, sort_keys=True)


def build_source_role_review_flow_summary_text(
    summary: SourceRoleReviewFlowSummary,
) -> str:
    return "\n".join(
        [
            "Source-role review flow summary",
            f"Flow ID: {summary.flow_id}",
            f"Status: {summary.status}",
            f"Review status: {summary.review_status}",
            f"Review rows: {summary.source_role_review_count}",
            f"Claim notes: {summary.claim_note_count}",
            f"UI rows: {summary.ui_row_count}",
            f"Provenance receipts: {summary.provenance_receipt_count}",
            "Metadata only: yes",
            "Auto-classify flag: false",
            "Sensitive inference prohibited: true",
            "Runtime/completion claim flags: false",
        ]
    )


def _closed_loop_source_chain_summary_rows(
    rows: tuple[SourceRoleReviewUIRow, ...],
) -> tuple[dict[str, Any], ...]:
    return tuple(
        {
            "claim_type": row.claim_type,
            "closed_loop_reporting_flag": row.closed_loop_reporting_flag,
            "currentness_status": row.currentness_status.value,
            "primary_source_status": row.primary_source_status.value,
            "queue_item_id": row.queue_item_id,
            "queue_item_role": row.queue_item_role,
            "review_index": row.review_index,
            "review_status": row.review_status,
            "source_chain_gap": row.source_chain_gap,
            "source_role": row.source_role.value,
        }
        for row in rows
    )


def closed_loop_source_chain_review_summary_id(
    rows: tuple[SourceRoleReviewUIRow, ...],
) -> str:
    payload = {
        "review_summary_kind": "closed_loop_source_chain_review",
        "rows": list(_closed_loop_source_chain_summary_rows(rows)),
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return "closed_loop_source_chain_review_" + hashlib.sha256(
        encoded.encode("utf-8")
    ).hexdigest()[:16]


def _is_closed_loop_source_chain_flagged(row: SourceRoleReviewUIRow) -> bool:
    return (
        row.source_role == SourceRole.TERTIARY_PROPAGATED_SOURCE
        or row.primary_source_status == PrimarySourceStatus.TERTIARY_PROPAGATED_CLAIM
        or row.source_chain_gap
        or row.closed_loop_reporting_flag
    )


def build_closed_loop_source_chain_review_summary(
    queue: EvidenceItemQueue,
) -> ClosedLoopSourceChainReviewSummary:
    rows = queue_source_role_reviews_to_ui_rows(queue)
    flagged_rows = tuple(row for row in rows if _is_closed_loop_source_chain_flagged(row))
    propagated_rows = tuple(
        row
        for row in rows
        if (
            row.source_role == SourceRole.TERTIARY_PROPAGATED_SOURCE
            or row.primary_source_status == PrimarySourceStatus.TERTIARY_PROPAGATED_CLAIM
        )
    )
    return ClosedLoopSourceChainReviewSummary(
        summary_id=closed_loop_source_chain_review_summary_id(flagged_rows),
        status=(
            "USER_REVIEW_REQUIRED"
            if flagged_rows
            else "NO_CLOSED_LOOP_OR_PROPAGATED_SOURCE_FLAGS"
        ),
        total_source_role_review_count=len(rows),
        flagged_review_count=len(flagged_rows),
        propagated_source_review_count=len(propagated_rows),
        source_chain_gap_count=sum(1 for row in rows if row.source_chain_gap),
        closed_loop_reporting_flag_count=sum(
            1 for row in rows if row.closed_loop_reporting_flag
        ),
        flagged_queue_item_ids=tuple(row.queue_item_id for row in flagged_rows),
        source_roles=tuple(row.source_role.value for row in flagged_rows),
        primary_source_statuses=tuple(
            row.primary_source_status.value for row in flagged_rows
        ),
        currentness_statuses=tuple(row.currentness_status.value for row in flagged_rows),
    )


def closed_loop_source_chain_review_summary_to_json(
    summary: ClosedLoopSourceChainReviewSummary,
) -> str:
    return json.dumps(summary.to_dict(), indent=2, sort_keys=True)


def build_closed_loop_source_chain_review_summary_text(
    summary: ClosedLoopSourceChainReviewSummary,
) -> str:
    return "\n".join(
        [
            "Closed-loop / propagated-source review summary",
            f"Summary ID: {summary.summary_id}",
            f"Status: {summary.status}",
            f"Review status: {summary.review_status}",
            f"Total source-role reviews: {summary.total_source_role_review_count}",
            f"Flagged reviews: {summary.flagged_review_count}",
            f"Propagated-source reviews: {summary.propagated_source_review_count}",
            f"Source-chain gaps: {summary.source_chain_gap_count}",
            f"Closed-loop flags: {summary.closed_loop_reporting_flag_count}",
            "Metadata only: yes",
            "Explicit recorded flags only: yes",
            "Auto-classify flag: false",
            "Sensitive inference prohibited: true",
            "Runtime/completion claim flags: false",
        ]
    )
