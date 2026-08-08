from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Sequence


class SourceRole(str, Enum):
    PRIMARY_ORIGINAL_AUTHORED_SOURCE = "PRIMARY_ORIGINAL_AUTHORED_SOURCE"
    SECONDARY_OUTSIDE_PERSPECTIVE_SOURCE = "SECONDARY_OUTSIDE_PERSPECTIVE_SOURCE"
    TERTIARY_PROPAGATED_SOURCE = "TERTIARY_PROPAGATED_SOURCE"
    IRRELEVANT_TO_CLAIM = "IRRELEVANT_TO_CLAIM"
    TEMPORALLY_LIMITED_SOURCE = "TEMPORALLY_LIMITED_SOURCE"


class PrimarySourceStatus(str, Enum):
    PRIMARY_SOURCE_LOCATED = "PRIMARY_SOURCE_LOCATED"
    PRIMARY_SOURCE_NOT_LOCATED = "PRIMARY_SOURCE_NOT_LOCATED"
    PRIMARY_SOURCE_CLAIMED_BUT_UNVERIFIED = "PRIMARY_SOURCE_CLAIMED_BUT_UNVERIFIED"
    PRIMARY_SOURCE_DISPUTED = "PRIMARY_SOURCE_DISPUTED"
    SECONDARY_FRAMING_ONLY = "SECONDARY_FRAMING_ONLY"
    TERTIARY_PROPAGATED_CLAIM = "TERTIARY_PROPAGATED_CLAIM"
    MANUAL_SOURCE_NOTE = "MANUAL_SOURCE_NOTE"


class CurrentnessStatus(str, Enum):
    CURRENT = "CURRENT"
    HISTORICAL = "HISTORICAL"
    UNKNOWN = "UNKNOWN"
    REPOSTED = "REPOSTED"
    UNDATED = "UNDATED"


@dataclass(frozen=True)
class ClaimSourceRolePlan:
    claim_text: str
    claim_type: str
    claim_source_role: SourceRole
    source_role_scope: str
    source_role_limitation: str
    authored_or_posted_at: str | None = None
    captured_at_utc: str | None = None
    event_time_or_claim_time: str | None = None
    temporal_gap_note: str = ""
    currentness_status: CurrentnessStatus = CurrentnessStatus.UNKNOWN
    primary_source_status: PrimarySourceStatus = PrimarySourceStatus.MANUAL_SOURCE_NOTE
    source_chain_gap: str = ""
    closed_loop_reporting_flag: bool = False
    first_uploader_known: bool = False
    first_uploader_url: str | None = None
    first_seen_by_user_utc: str | None = None
    media_acquired_at_utc: str | None = None
    file_obtained_delay_note: str = ""
    publisher_framing_summary: str = ""
    removed_or_missing_context_note: str = ""
    identity_claim_basis: str = ""
    appearance_claim_basis: str = ""
    forensic_claim_basis: str = ""
    family_or_authority_claim_basis: str = ""
    open_source_media_available: bool | None = None
    corroborating_sources: tuple[str, ...] = ()
    contradicting_sources: tuple[str, ...] = ()
    verification_notes: str = ""

    def to_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["claim_source_role"] = self.claim_source_role.value
        data["currentness_status"] = self.currentness_status.value
        data["primary_source_status"] = self.primary_source_status.value
        return data

    def validates_exact_claim_scope(self) -> bool:
        return bool(self.claim_text.strip() and self.source_role_scope.strip() and self.source_role_limitation.strip())


@dataclass(frozen=True)
class MediaSourceChainPlan:
    media_observed_on_url: str
    publisher_page_url: str
    publisher_name: str
    publisher_headline_or_caption: str = ""
    publisher_framing_summary: str = ""
    visible_source_credit: str = ""
    claimed_original_source: str = ""
    original_source_url: str | None = None
    original_author_or_uploader: str | None = None
    primary_source_status: PrimarySourceStatus = PrimarySourceStatus.PRIMARY_SOURCE_NOT_LOCATED
    source_role: SourceRole = SourceRole.SECONDARY_OUTSIDE_PERSPECTIVE_SOURCE
    source_chain_gap: str = ""
    social_source_url: str | None = None
    wire_or_agency_source_credit: str = ""
    caption_context_around_media: str = ""
    first_seen_by_user_utc: str | None = None
    capture_time_utc: str | None = None
    media_hash_checksum: str | None = None
    perceptual_hash_fingerprint_future: str | None = None
    same_media_seen_on_other_urls: tuple[str, ...] = ()
    repost_platform: str = ""
    repost_uploader_account: str = ""
    repost_timestamp: str | None = None
    source_author_correction_url: str | None = None
    source_author_correction_text_or_path: str = ""
    notes_on_context_dispute: str = ""
    confidence_verification_notes: str = ""

    def to_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["primary_source_status"] = self.primary_source_status.value
        data["source_role"] = self.source_role.value
        return data

    def publisher_is_not_automatically_primary(self) -> bool:
        return self.publisher_page_url != (self.original_source_url or "") or self.primary_source_status != PrimarySourceStatus.PRIMARY_SOURCE_LOCATED


def build_self_authored_appearance_claim_plan(
    *,
    claim_text: str,
    post_url: str,
    authored_or_posted_at: str | None,
    captured_at_utc: str,
    event_time_or_claim_time: str | None,
    temporal_gap_note: str,
) -> ClaimSourceRolePlan:
    currentness = CurrentnessStatus.UNKNOWN
    if authored_or_posted_at and event_time_or_claim_time and authored_or_posted_at <= event_time_or_claim_time:
        currentness = CurrentnessStatus.HISTORICAL
    elif authored_or_posted_at:
        currentness = CurrentnessStatus.CURRENT
    return ClaimSourceRolePlan(
        claim_text=claim_text,
        claim_type="appearance_or_self_presentation",
        claim_source_role=SourceRole.PRIMARY_ORIGINAL_AUTHORED_SOURCE,
        source_role_scope="Primary only for what the self-authored post directly shows or states.",
        source_role_limitation="Does not prove unrelated event, identity, forensic or third-party claims.",
        authored_or_posted_at=authored_or_posted_at,
        captured_at_utc=captured_at_utc,
        event_time_or_claim_time=event_time_or_claim_time,
        temporal_gap_note=temporal_gap_note,
        currentness_status=currentness,
        primary_source_status=PrimarySourceStatus.PRIMARY_SOURCE_LOCATED,
        first_uploader_known=True,
        first_uploader_url=post_url,
        appearance_claim_basis="Self-authored post used for appearance/self-presentation scope only.",
        verification_notes="Preserve timing/currentness instead of downgrading the source for unrelated claims.",
    )


def detect_closed_loop_reporting(plans: Sequence[ClaimSourceRolePlan]) -> bool:
    propagated = [p for p in plans if p.primary_source_status == PrimarySourceStatus.TERTIARY_PROPAGATED_CLAIM]
    missing_primary = [p for p in plans if p.primary_source_status in {PrimarySourceStatus.PRIMARY_SOURCE_NOT_LOCATED, PrimarySourceStatus.PRIMARY_SOURCE_CLAIMED_BUT_UNVERIFIED}]
    return bool(propagated and missing_primary)


def claim_role_summary(plan: ClaimSourceRolePlan) -> str:
    return (
        f"{plan.claim_source_role.value}: {plan.primary_source_status.value}; "
        f"scope={plan.source_role_scope}; limitation={plan.source_role_limitation}"
    )
