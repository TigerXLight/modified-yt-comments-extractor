"""Source-reference candidate policy for Profile/Media review.

This layer is separate from media/source provenance and claim/span semantic
roles.  It only asks whether a span points at another source object that should
be resolved, preserved, or reviewed.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final


POLICY_VERSION: Final[str] = "profile-media-source-reference-policy-v83a-source-chain-definition-set-20260827"

SOURCE_REFERENCE_STATUSES: Final[tuple[str, ...]] = (
    "RESOLVED_PRIMARY_SOURCE",
    "RESOLVED_SECONDARY_SOURCE",
    "RESOLVED_TERTIARY_SOURCE",
    "UNRESOLVED_SOURCE_REFERENCE",
    "NOT_A_SOURCE_REFERENCE",
)

SOURCE_POINTER_TYPES: Final[tuple[str, ...]] = (
    "quote_or_interview",
    "witness",
    "report_or_statement",
    "study_or_analysis",
    "poll_or_survey",
    "measurement_or_dataset",
    "monitoring_or_records",
    "media_channel_or_post",
    "comment_corpus",
    "citation_or_reference",
    "document_witness",
    "not_source_reference",
)

SOURCE_OBJECT_TYPES: Final[tuple[str, ...]] = (
    "quote",
    "interview",
    "witness",
    "report",
    "study",
    "poll",
    "survey",
    "dataset",
    "figures",
    "statistics",
    "records",
    "measurement",
    "monitoring exercise",
    "video",
    "audio",
    "channel",
    "clip",
    "post",
    "tweet/X post",
    "article",
    "paper",
    "document",
    "court filing",
    "judgment",
    "statement",
    "press release",
    "complaint",
    "email",
    "letter",
)

TRANSCRIPT_PROVENANCE_ROLES: Final[tuple[str, ...]] = (
    "PRIMARY_MEDIA_URL",
    "SECONDARY_TRANSCRIPT",
    "VERIFIED_SECONDARY_TRANSCRIPT",
    "TERTIARY_TRANSCRIPT",
    "UNKNOWN_TRANSCRIPT_PROVENANCE",
)


@dataclass(frozen=True)
class SourceReferencePolicySummary:
    schema_version: str = POLICY_VERSION

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "source_reference_statuses": list(SOURCE_REFERENCE_STATUSES),
            "source_pointer_types": list(SOURCE_POINTER_TYPES),
            "source_object_types": list(SOURCE_OBJECT_TYPES),
            "transcript_provenance_roles": list(TRANSCRIPT_PROVENANCE_ROLES),
            "ordinary_unknown_claim_span_goes_to_main_sourcing_card": False,
            "source_reference_candidate_goes_to_main_sourcing_card": True,
        }
