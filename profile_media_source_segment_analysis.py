"""Segment-level source-role review for Profile/Media HOME source folders.

The analyzer is deliberately conservative: it splits supplied local text into
reviewable segments and records role candidates/lane flags without finalizing a
Primary/Secondary/Tertiary decision.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import re
from typing import Any, Iterable

PROFILE_MEDIA_SOURCE_SEGMENT_ANALYSIS_SCHEMA_VERSION = "profile-media-source-segment-analysis-v76p"

FIRST_PERSON_RE = re.compile(r"\b(i|i'm|i've|i'd|my|me|mine|we|we're|we've|our|ours)\b", re.IGNORECASE)
OTHER_PEOPLE_RE = re.compile(r"\b(he|she|they|them|his|her|their|man|woman|people|person|victim|suspect|officer|police)\b", re.IGNORECASE)
AUTHORITY_RE = re.compile(r"\b(police|court|judge|jury|officer|authority|authorities|official|agency|family|statement|charged|arrested)\b", re.IGNORECASE)
DIRECT_QUOTE_RE = re.compile(r"\b(told|interviewed|said|stated|wrote|posted|claimed|according to)\b", re.IGNORECASE)
DIRECT_WITNESS_RE = re.compile(r"\b(i saw|i heard|i filmed|i recorded|i witnessed|direct witness|witnessed first hand)\b", re.IGNORECASE)
DIRECT_INTERVIEWER_RE = re.compile(r"\b(i interviewed|interviewed by me|told me|told us|we interviewed|exclusive interview)\b", re.IGNORECASE)
DIRECT_RECORDER_RE = re.compile(r"\b(i recorded|i filmed|we recorded|we filmed|recorded by me|filmed by me)\b", re.IGNORECASE)
COURT_OBSERVER_RE = re.compile(r"\b(i attended court|i attended the hearing|court observer|from court|in court)\b", re.IGNORECASE)
DIRECT_HOLDER_RE = re.compile(r"\b(i received|i hold|i have the original|sent to me|provided to me|my footage|my recording)\b", re.IGNORECASE)
URL_RE = re.compile(r"https?://[^\s<>()\"']+", re.IGNORECASE)
QUOTE_SOURCE_RE = re.compile(r"\b(quoted post|tweet|x\.com|twitter\.com|post by|posted by|account)\b", re.IGNORECASE)


@dataclass(frozen=True)
class SourceSegmentReview:
    segment_id: str
    segment_text_preview: str
    segment_type: str
    speaker_or_author_candidate: str = ""
    source_role_candidate: str = "REVIEW_REQUIRED"
    role_scope: str = "segment_requires_review"
    basis: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    review_lanes: tuple[str, ...] = ()
    first_person_author_self_claim_review: bool = False
    author_identity_needed: bool = False
    author_scope_only: bool = False
    witness_connectivity_status: str = "review_required"
    direct_witness_basis: bool = False
    direct_interviewer_basis: bool = False
    direct_recorder_basis: bool = False
    court_observer_basis: bool = False
    direct_holder_basis: bool = False
    no_witness_connectivity_found: bool = True
    quoted_post_present: bool = False
    quoted_post_source_url: str = ""
    quoted_post_account: str = ""
    quoted_post_preserved: bool = False
    quoted_post_primary_for_poster_only: bool = False
    quoted_post_connection_review: str = "not_triggered"
    final_source_role_decision: bool = False
    automatic_classification_performed: bool = False
    sensitive_identifier_inference_performed: bool = False
    schema_version: str = PROFILE_MEDIA_SOURCE_SEGMENT_ANALYSIS_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["basis"] = list(self.basis)
        payload["warnings"] = list(self.warnings)
        payload["review_lanes"] = list(self.review_lanes)
        return payload


def _dedupe(values: Iterable[object]) -> tuple[str, ...]:
    seen: set[str] = set()
    output: list[str] = []
    for value in values:
        text = str(value or "").strip()
        if text and text not in seen:
            seen.add(text)
            output.append(text)
    return tuple(output)


def split_text_into_source_segments(text: object) -> tuple[str, ...]:
    raw = str(text or "").replace("\r\n", "\n").replace("\r", "\n")
    blocks = [part.strip() for part in re.split(r"\n\s*\n+", raw) if part.strip()]
    if len(blocks) <= 1:
        blocks = [part.strip() for part in re.split(r"(?<=[.!?])\s+", raw) if part.strip()]
    return tuple(blocks)


def _first_url(text: str) -> str:
    match = URL_RE.search(text)
    return match.group(0).rstrip(".,;]") if match else ""


def _quoted_account(text: str) -> str:
    for pattern in (
        r"(?:account|posted by|post by|tweet by)\s*[:=-]\s*(@?[A-Za-z0-9_.-]+)",
        r"https?://(?:www\.)?(?:x|twitter)\.com/([A-Za-z0-9_]+)/",
    ):
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1)
    return ""


def analyze_source_segment(text: object, *, index: int = 1) -> SourceSegmentReview:
    segment_text = re.sub(r"\s+", " ", str(text or "").strip())
    preview = segment_text[:500]
    basis: list[str] = []
    warnings: list[str] = []
    lanes: list[str] = []

    first_person = bool(FIRST_PERSON_RE.search(segment_text))
    talks_about_others = bool(OTHER_PEOPLE_RE.search(segment_text))
    authority = bool(AUTHORITY_RE.search(segment_text))
    direct_quote = bool(DIRECT_QUOTE_RE.search(segment_text))
    direct_witness = bool(DIRECT_WITNESS_RE.search(segment_text))
    direct_interviewer = bool(DIRECT_INTERVIEWER_RE.search(segment_text))
    direct_recorder = bool(DIRECT_RECORDER_RE.search(segment_text))
    court_observer = bool(COURT_OBSERVER_RE.search(segment_text))
    direct_holder = bool(DIRECT_HOLDER_RE.search(segment_text))
    witness_connected = direct_witness or direct_interviewer or direct_recorder or court_observer or direct_holder
    quoted_post = bool(QUOTE_SOURCE_RE.search(segment_text))
    quoted_url = _first_url(segment_text) if quoted_post else ""
    quoted_account = _quoted_account(segment_text) if quoted_post else ""
    quoted_preserved = bool(quoted_url and quoted_account)

    segment_type = "statement"
    role = "REVIEW_REQUIRED"
    role_scope = "segment_requires_review"

    if first_person:
        lanes.append("first_person_author_self_claim_review")
        basis.append("first_person_marker_present")
        role = "PRIMARY_SELF_AUTHORED_SCOPE_REVIEW"
        role_scope = "author_or_speaker_own_claimed_experience_only"
        if talks_about_others:
            warnings.append("first_person_claim_about_other_people_not_primary_for_them")
        warnings.append("author_identity_needed")

    if authority:
        lanes.append("source_chain_basis_review")
        basis.append("authority_court_family_or_agency_language")
        if not witness_connected:
            role = "TERTIARY_PROPAGATED_SOURCE_REVIEW_REQUIRED"
            role_scope = "repeated_authority_or_publisher_claim_not_primary"

    if direct_quote:
        lanes.append("direct_quote_or_interview_review")
        basis.append("quote_or_interview_language_present")
        if direct_interviewer:
            role = "SECONDARY_WITNESS_ACCOUNT_REVIEW"
            role_scope = "possible_direct_interviewer_basis_requires_review"

    if quoted_post:
        lanes.append("quoted_social_post_connection_review")
        segment_type = "quoted_social_media_post"
        basis.append("quoted_social_post_marker_present")
        if quoted_preserved:
            role = "PRIMARY_SELF_AUTHORED_SCOPE_REVIEW"
            role_scope = "poster_authored_post_only_not_underlying_event"
        else:
            warnings.append("quoted_post_source_or_account_not_preserved")

    if not witness_connected:
        lanes.append("witness_connectivity_review")
        warnings.append("no_witness_connectivity_found")

    if not lanes:
        lanes.append("source_role_review")

    return SourceSegmentReview(
        segment_id=f"S{index:04d}",
        segment_text_preview=preview,
        segment_type=segment_type,
        source_role_candidate=role,
        role_scope=role_scope,
        basis=_dedupe(basis),
        warnings=_dedupe(warnings),
        review_lanes=_dedupe(lanes),
        first_person_author_self_claim_review=first_person,
        author_identity_needed=first_person,
        author_scope_only=first_person,
        witness_connectivity_status="witness_connectivity_found" if witness_connected else "review_required_witness_connectivity_not_established",
        direct_witness_basis=direct_witness,
        direct_interviewer_basis=direct_interviewer,
        direct_recorder_basis=direct_recorder,
        court_observer_basis=court_observer,
        direct_holder_basis=direct_holder,
        no_witness_connectivity_found=not witness_connected,
        quoted_post_present=quoted_post,
        quoted_post_source_url=quoted_url,
        quoted_post_account=quoted_account,
        quoted_post_preserved=quoted_preserved,
        quoted_post_primary_for_poster_only=quoted_preserved,
        quoted_post_connection_review="preserved_for_poster_scope_only" if quoted_preserved else ("review_required_missing_post_connection" if quoted_post else "not_triggered"),
    )


def analyze_source_segments(text: object, *, max_segments: int = 80) -> tuple[SourceSegmentReview, ...]:
    segments = split_text_into_source_segments(text)
    return tuple(analyze_source_segment(segment, index=index) for index, segment in enumerate(segments[:max_segments], start=1))


def source_segments_to_dicts(segments: Iterable[SourceSegmentReview]) -> list[dict[str, Any]]:
    return [segment.to_dict() for segment in segments]
