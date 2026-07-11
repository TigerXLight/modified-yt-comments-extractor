from __future__ import annotations

from dataclasses import asdict, dataclass, field, is_dataclass
from enum import Enum
from typing import Any, Dict, Optional

from evidence_schema import utc_now_iso


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
