"""Formal Profile/Media claim-span role policy.

This policy intentionally separates media/source provenance roles from
claim/span semantic roles.  Unknown is an assigned claim role; it is not the
same as review/unassigned.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final


POLICY_VERSION: Final[str] = "profile-media-claim-role-policy-v9-semantic-policy-pass3e-final-edge-cleanup-20260827"

CLAIM_ROLES: Final[tuple[str, ...]] = ("PRIMARY", "SECONDARY", "TERTIARY", "UNKNOWN", "BLANK")
REVIEW_STATES: Final[tuple[str, ...]] = ("assigned", "unassigned")

MEDIA_SOURCE_ROLES: Final[tuple[str, ...]] = (
    "PRIMARY_SOURCE_EVIDENCE",
    "SECONDARY_MEDIA_COPY",
    "TERTIARY_REPORT",
    "UNKNOWN_PROVENANCE",
)

DESIGNATIONS: Final[tuple[str, ...]] = (
    "self-action",
    "self-belief",
    "self-intent",
    "self-feeling",
    "self-biographical",
    "speaker-owned-imperative",
    "speaker-owned-institutional-action",
    "witness-event",
    "witness-reaction",
    "direct-attribution",
    "direct-quote",
    "document-witness",
    "document-based-interpretation",
    "hearsay-report",
    "written-source-report",
    "social-post-report",
    "group-claim",
    "institution-claim",
    "motive-claim",
    "historic-claim",
    "numeric-claim",
    "family-claim",
    "biographical-claim-about-other",
    "inner-state-claim-about-other",
    "class-definition",
    "slur-label",
    "external-object-label",
    "external-classification",
    "external-person-label",
    "question",
    "filler",
    "embedded-claim-in-question",
)

PRIMARY_TRIGGER_PHRASES: Final[tuple[str, ...]] = (
    "i",
    "i'm",
    "i've",
    "i was",
    "i felt",
    "i believe",
    "i want",
    "i decided",
    "i started",
    "i run",
    "my red line was",
    "we moved",
    "we have",
    "we run",
    "we've preached",
    "we offer",
    "we saved",
    "we need to",
    "we should",
    "we will",
    "us",
)

SECONDARY_TRIGGER_PHRASES: Final[tuple[str, ...]] = (
    "i saw",
    "i heard",
    "i was standing there when",
    "told me",
    "said to me",
    "or so",
    "tells me",
    "i've spoken to",
    "like you said",
    "we've had",
    "we've seen",
    "i read this document",
    "i read that cover to cover",
)

TERTIARY_TRIGGER_PHRASES: Final[tuple[str, ...]] = (
    "he said",
    "she said",
    "wrote",
    "posted",
    "shared",
    "reported",
    "had written",
    "had messaged",
    "i heard it from",
    "i heard that",
    "i read that",
    "according to",
    "the report says",
    "people say",
)

UNKNOWN_TRIGGER_PHRASES: Final[tuple[str, ...]] = (
    "they",
    "it's",
    "which",
    "who",
    "my wife",
    "my dad",
    "my grandfather",
    "it is",
    "he was",
    "there are",
    "millions of",
    "they want",
    "some of them",
    "has",
    "it was",
)

BLANK_TRIGGER_PHRASES: Final[tuple[str, ...]] = ("yes", "mhm", "yeah", "what happened", "why", "and then")


@dataclass(frozen=True)
class ClaimRolePolicySummary:
    schema_version: str = POLICY_VERSION
    claim_roles: tuple[str, ...] = CLAIM_ROLES
    media_source_roles: tuple[str, ...] = MEDIA_SOURCE_ROLES
    designations: tuple[str, ...] = DESIGNATIONS
    unknown_is_assigned: bool = True
    blank_is_assigned: bool = True
    media_source_role_is_separate_from_claim_span_role: bool = True

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "claim_roles": list(self.claim_roles),
            "media_source_roles": list(self.media_source_roles),
            "designations": list(self.designations),
            "unknown_is_assigned": self.unknown_is_assigned,
            "blank_is_assigned": self.blank_is_assigned,
            "media_source_role_is_separate_from_claim_span_role": self.media_source_role_is_separate_from_claim_span_role,
        }


def normalize_media_source_role(value: object) -> str:
    text = str(value or "").strip().upper()
    aliases = {
        "PRIMARY": "PRIMARY_SOURCE_EVIDENCE",
        "PRIMARY_SOURCE": "PRIMARY_SOURCE_EVIDENCE",
        "ORIGINAL": "PRIMARY_SOURCE_EVIDENCE",
        "SECONDARY": "SECONDARY_MEDIA_COPY",
        "COPY": "SECONDARY_MEDIA_COPY",
        "REPOST": "SECONDARY_MEDIA_COPY",
        "MIRROR": "SECONDARY_MEDIA_COPY",
        "TERTIARY": "TERTIARY_REPORT",
        "REPORT": "TERTIARY_REPORT",
        "ARTICLE": "TERTIARY_REPORT",
        "UNKNOWN": "UNKNOWN_PROVENANCE",
        "": "UNKNOWN_PROVENANCE",
    }
    return text if text in MEDIA_SOURCE_ROLES else aliases.get(text, "UNKNOWN_PROVENANCE")


def claim_span_edit_key(source_id: object, timestamp_start: object, timestamp_end: object, char_start: int, char_end: int) -> str:
    return "|".join(
        (
            str(source_id or ""),
            str(timestamp_start or ""),
            str(timestamp_end or ""),
            str(int(char_start)),
            str(int(char_end)),
        )
    )


def build_claim_role_worker_progress_steps() -> tuple[str, ...]:
    return (
        "parsing source text",
        "extracting sections",
        "classifying claim spans",
        "matching article claims",
        "building review rows",
    )


def should_use_background_worker(text_length: int, *, threshold: int = 20_000) -> bool:
    return int(text_length) >= threshold

