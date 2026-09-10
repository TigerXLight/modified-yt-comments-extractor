"""Source-role matching workflow for Profile/Media review.

This module turns local article/transcript text into explainable candidate
matches.  It does not fetch, crawl, infer sensitive identity, or finalize
Primary/Secondary/Tertiary roles automatically.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Iterable

from profile_media_matching_backend import MatchResult, MatcherRegistry, default_matcher_registry, normalize_match_text
from profile_media_source_text_sections import sections_by_type, split_source_text_sections


@dataclass(frozen=True)
class ArticleClaim:
    claim_id: str
    text: str
    source_scope_id: str = "article"
    source_url: str = ""


@dataclass(frozen=True)
class TranscriptPassage:
    passage_id: str
    text: str
    section_type: str = "transcript"
    speaker: str = ""
    source_scope_id: str = "transcript"


@dataclass(frozen=True)
class SourceRoleMatch:
    claim_id: str
    passage_id: str
    claim_text: str
    passage_text: str
    role_candidate: str
    confidence: float
    matcher_name: str
    explanation: str
    quote_attribution: dict[str, str]
    source_trigger_phrases: tuple[str, ...]
    source_chain_gap: bool
    final_source_role_decision: bool
    review_lanes: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "claim_id": self.claim_id,
            "passage_id": self.passage_id,
            "claim_text": self.claim_text,
            "passage_text": self.passage_text,
            "role_candidate": self.role_candidate,
            "confidence": round(self.confidence, 3),
            "matcher_name": self.matcher_name,
            "explanation": self.explanation,
            "quote_attribution": dict(self.quote_attribution),
            "source_trigger_phrases": list(self.source_trigger_phrases),
            "source_chain_gap": self.source_chain_gap,
            "final_source_role_decision": self.final_source_role_decision,
            "review_lanes": list(self.review_lanes),
        }


SOURCE_TRIGGER_PATTERNS: tuple[tuple[str, str], ...] = (
    ("told", r"\btold\s+[A-Z][A-Za-z0-9 .'-]{2,80}"),
    ("said", r"\bsaid\b|\bsays\b|\baccording\s+to\b"),
    ("police_authority", r"\bpolice\b|\bauthorit(?:y|ies)\b|\bcourt\b|\bagency\b|\bfamily\s+statement\b"),
    ("video_source", r"\bvideo\b|\bYouTube\b|\bbroadcast\b|\bprogramme\b|\bchannel\b"),
    ("source_url", r"https?://\S+"),
)


def split_article_claims(text: object) -> tuple[ArticleClaim, ...]:
    normal = " ".join(str(text or "").replace("\r", "\n").split())
    chunks = [chunk.strip() for chunk in re.split(r"(?<=[.!?])\s+", normal) if chunk.strip()]
    return tuple(ArticleClaim(f"C{idx:04d}", chunk) for idx, chunk in enumerate(chunks, start=1))


def extract_transcript_claim_spans(source_text: object) -> tuple[TranscriptPassage, ...]:
    sections = sections_by_type(split_source_text_sections(source_text))
    transcript = sections.get("transcript", "")
    output: list[TranscriptPassage] = []
    for idx, raw_line in enumerate(transcript.splitlines(), start=1):
        line = " ".join(raw_line.split())
        if not line:
            continue
        speaker = ""
        speaker_match = re.search(r"\[([^\]]{2,80})\]", line)
        if speaker_match:
            speaker = speaker_match.group(1).strip()
        cleaned = re.sub(r"^\d{1,2}:\d{2}(?::\d{2})?\s*(?:-\s*\d{1,2}:\d{2}(?::\d{2})?)?\s*", "", line)
        cleaned = re.sub(r"\[[^\]]+\]", "", cleaned).strip(" -")
        if cleaned:
            output.append(TranscriptPassage(f"T{idx:04d}", cleaned, "transcript", speaker))
    return tuple(output)


def detect_source_trigger_phrases(text: object) -> tuple[str, ...]:
    value = str(text or "")
    hits: list[str] = []
    for label, pattern in SOURCE_TRIGGER_PATTERNS:
        if re.search(pattern, value, flags=re.IGNORECASE):
            hits.append(label)
    return tuple(dict.fromkeys(hits))


def attribute_quotes(text: object) -> dict[str, str]:
    value = str(text or "")
    patterns = (
        r"[\"'‘“](?P<quote>[^\"'‘’“”]{6,220}?)[\"'’”]\s*,?\s*(?:said|told|wrote|claimed|added)\s+(?P<speaker>[A-Z][A-Za-z .'-]{2,80})",
        r"(?P<speaker>[A-Z][A-Za-z .'-]{2,80})\s+(?:said|told|wrote|claimed|added)\s+[\"'‘“](?P<quote>[^\"'‘’“”]{6,220}?)[\"'’”]",
    )
    for pattern in patterns:
        found = re.search(pattern, value, flags=re.IGNORECASE | re.DOTALL)
        if found:
            return {"speaker": " ".join(found.group("speaker").split()), "quote": " ".join(found.group("quote").split())}
    return {}


def role_candidate_for_match(claim: ArticleClaim, passage: TranscriptPassage) -> tuple[str, tuple[str, ...], bool]:
    combined = f"{claim.text}\n{passage.text}"
    triggers = set(detect_source_trigger_phrases(combined))
    review_lanes = ["source_role_review"]
    source_chain_gap = True
    role = "TERTIARY_OR_RELAYED_CLAIM_REVIEW"
    if {"video_source", "said"}.intersection(triggers) and passage.speaker:
        role = "DIRECT_INTERVIEW_STATEMENT_CAPTURED_IN_TRANSCRIPT_REVIEW"
        review_lanes.extend(["speaker_statement_review", "witness_connectivity_review"])
    elif "police_authority" in triggers:
        role = "TERTIARY_PROPAGATED_AUTHORITY_CLAIM_REVIEW"
        review_lanes.extend(["authority_source_chain_review", "witness_connectivity_review"])
    elif re.search(r"\bI\b|\bmy\b|\bme\b", passage.text):
        role = "PRIMARY_ORIGINAL_AUTHORED_SOURCE_FOR_SPEAKER_SELF_CLAIM_ONLY_REVIEW"
        review_lanes.extend(["first_person_author_self_claim_review", "author_scope_only_review"])
    return role, tuple(dict.fromkeys(review_lanes)), source_chain_gap


def match_article_claims_to_transcript(
    article_claims: Iterable[ArticleClaim],
    transcript_passages: Iterable[TranscriptPassage],
    *,
    registry: MatcherRegistry | None = None,
) -> tuple[SourceRoleMatch, ...]:
    matcher = registry or default_matcher_registry()
    passages = tuple(transcript_passages)
    passage_texts = [item.text for item in passages]
    output: list[SourceRoleMatch] = []
    for claim in article_claims:
        matches = matcher.match(
            claim.text,
            passage_texts,
            policy="source_role_claim_to_transcript",
            context={
                "minimum_score": 38,
                "patterns": ["christian faith", "gb news", "youtube", "told", "said", "faith goes to your very being"],
                "triggers": ["christian faith", "gb news", "youtube", "told", "said", "faith goes to your very being"],
            },
        )
        if not matches:
            continue
        best = matches[0]
        passage = passages[passage_texts.index(best.choice)]
        role, review_lanes, source_chain_gap = role_candidate_for_match(claim, passage)
        quote = attribute_quotes(claim.text) or attribute_quotes(passage.text)
        triggers = detect_source_trigger_phrases(f"{claim.text}\n{passage.text}")
        output.append(SourceRoleMatch(
            claim.claim_id,
            passage.passage_id,
            claim.text,
            passage.text,
            role,
            best.score,
            best.backend_name,
            f"{best.explanation}; match_type={best.match_type}; no final role decision",
            quote,
            triggers,
            source_chain_gap,
            False,
            review_lanes,
        ))
    return tuple(output)


def build_source_role_matching_preview(article_text: object, source_text: object) -> dict[str, Any]:
    claims = split_article_claims(article_text)
    passages = extract_transcript_claim_spans(source_text)
    matches = match_article_claims_to_transcript(claims, passages)
    return {
        "schema_version": "profile-media-source-role-matching-v1",
        "article_claim_count": len(claims),
        "transcript_passage_count": len(passages),
        "match_count": len(matches),
        "final_source_role_decision": False,
        "claims": [claim.__dict__ for claim in claims],
        "transcript_passages": [passage.__dict__ for passage in passages],
        "matches": [match.to_dict() for match in matches],
    }
