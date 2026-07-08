from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Sequence


class _StringEnum(str, Enum):
    def __str__(self) -> str:
        return self.value


class AccessMode(_StringEnum):
    PUBLIC_ACCESS = "PUBLIC_ACCESS"
    USER_AUTHENTICATED_ACCESS = "USER_AUTHENTICATED_ACCESS"
    METERED_OR_PREVIEW_ACCESS = "METERED_OR_PREVIEW_ACCESS"
    BLOCKED_OR_PAYWALLED = "BLOCKED_OR_PAYWALLED"
    ARCHIVED_COPY = "ARCHIVED_COPY"
    MANUAL_IMPORT = "MANUAL_IMPORT"


class SourceRole(_StringEnum):
    PRIMARY_ORIGINAL_AUTHORED = "PRIMARY_ORIGINAL_AUTHORED"
    SECONDARY_OUTSIDE_PERSPECTIVE = "SECONDARY_OUTSIDE_PERSPECTIVE"
    TERTIARY_PROPAGATED_SOURCE = "TERTIARY_PROPAGATED_SOURCE"
    UNKNOWN_SOURCE_ROLE = "UNKNOWN_SOURCE_ROLE"


class PrimarySourceStatus(_StringEnum):
    PRIMARY_SOURCE_LOCATED = "PRIMARY_SOURCE_LOCATED"
    PRIMARY_SOURCE_NOT_LOCATED = "PRIMARY_SOURCE_NOT_LOCATED"
    PRIMARY_SOURCE_CLAIMED_BUT_UNVERIFIED = "PRIMARY_SOURCE_CLAIMED_BUT_UNVERIFIED"
    PRIMARY_SOURCE_DISPUTED = "PRIMARY_SOURCE_DISPUTED"
    SECONDARY_FRAMING_ONLY = "SECONDARY_FRAMING_ONLY"
    TERTIARY_PROPAGATED_CLAIM = "TERTIARY_PROPAGATED_CLAIM"
    MANUAL_SOURCE_NOTE = "MANUAL_SOURCE_NOTE"


class CaptureMethod(_StringEnum):
    API = "API"
    BROWSER = "BROWSER"
    MANUAL_IMPORT = "MANUAL_IMPORT"
    ARCHIVE = "ARCHIVE"
    UNKNOWN = "UNKNOWN"


class CurrentnessStatus(_StringEnum):
    CURRENT = "CURRENT"
    HISTORICAL = "HISTORICAL"
    UNKNOWN = "UNKNOWN"
    REPOSTED = "REPOSTED"
    UNDATED = "UNDATED"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _value_for_dict(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, tuple):
        return [_value_for_dict(item) for item in value]
    if isinstance(value, list):
        return [_value_for_dict(item) for item in value]
    if isinstance(value, dict):
        return {key: _value_for_dict(item) for key, item in value.items()}
    return value


def _dataclass_to_dict(instance: Any) -> Dict[str, Any]:
    return {key: _value_for_dict(value) for key, value in asdict(instance).items()}


@dataclass
class EvidenceProvenance:
    source_url: str = ""
    canonical_url: str = ""
    source_platform: str = ""
    adapter_name: str = ""
    access_mode: AccessMode = AccessMode.PUBLIC_ACCESS
    capture_method: CaptureMethod = CaptureMethod.UNKNOWN
    capture_purpose: str = ""
    source_role: SourceRole = SourceRole.UNKNOWN_SOURCE_ROLE
    primary_source_status: PrimarySourceStatus = PrimarySourceStatus.MANUAL_SOURCE_NOTE
    source_chain_gap: bool = False
    capture_time_utc: str = field(default_factory=utc_now_iso)
    item_id: str = ""
    parent_id: str = ""
    author_display_name: str = ""
    author_profile_id: str = ""
    posted_at: str = ""
    permalink: str = ""
    archive_url: str = ""
    archive_service: str = ""
    archive_checked_at_utc: str = ""
    archive_status: str = ""
    media_url: str = ""
    local_media_path: str = ""
    local_file_hash: str = ""
    screenshot_path: str = ""
    extracted_text_path: str = ""
    raw_sidecar_path: str = ""
    capture_session_id: str = ""
    verification_notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class ClaimEvidenceNote:
    claim_text: str = ""
    claim_type: str = ""
    claim_source_role: SourceRole = SourceRole.UNKNOWN_SOURCE_ROLE
    source_role_scope: str = ""
    source_role_limitation: str = ""
    authored_or_posted_at: str = ""
    captured_at_utc: str = field(default_factory=utc_now_iso)
    event_time_or_claim_time: str = ""
    temporal_gap_note: str = ""
    currentness_status: CurrentnessStatus = CurrentnessStatus.UNKNOWN
    primary_source_status: PrimarySourceStatus = PrimarySourceStatus.MANUAL_SOURCE_NOTE
    source_chain_gap: bool = False
    closed_loop_reporting_flag: bool = False
    verification_notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class MediaSourceChainNote:
    media_observed_on_url: str = ""
    publisher_page_url: str = ""
    publisher_name: str = ""
    publisher_headline_or_caption: str = ""
    publisher_framing_summary: str = ""
    visible_source_credit: str = ""
    claimed_original_source: str = ""
    original_source_url: str = ""
    original_author_or_uploader: str = ""
    social_source_url: str = ""
    wire_agency_source_credit: str = ""
    first_seen_by_user_utc: str = ""
    capture_time_utc: str = field(default_factory=utc_now_iso)
    media_hash: str = ""
    same_media_seen_on_other_urls: Sequence[str] = field(default_factory=tuple)
    repost_platform: str = ""
    repost_uploader_account: str = ""
    repost_timestamp: str = ""
    source_author_correction_url: str = ""
    source_author_correction_text_path: str = ""
    notes_on_context_dispute: str = ""
    confidence_or_verification_notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)
