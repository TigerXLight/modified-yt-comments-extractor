"""Extract source-reference candidates from Profile/Media claim spans.

No network, crawling, downloads, browser automation, or dependency-heavy NLP is
performed here.  The extractor is deliberately conservative and explainable.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any, Iterable, Mapping

from profile_media_source_reference_policy import POLICY_VERSION


@dataclass(frozen=True)
class SourceReferenceCandidate:
    text: str
    kind: str
    source_reference_status: str
    source_pointer_type: str
    source_object_type: str = ""
    source_actor: str = ""
    reason: str = ""
    goes_to_main_sourcing_card: bool = False
    goes_to_review_text: bool = True
    linked_claim_span_edit_key: str = ""
    resolved_source_url: str = ""
    section_label: str = ""
    review_required: bool = True
    unknown_media_requirement_met: bool = False
    unknown_media_requirement_reason: str = ""
    media_source_role: str = ""
    candidate_source_role: str = ""
    source_chain_template_id: str = ""
    source_chain_summary: str = ""
    source_chain_depth: int = 0
    source_actor_type: str = ""
    named_intermediary_chain_role: str = ""
    current_speaker_chain_role: str = ""
    inferred_origin_actor_type: str = ""
    source_chain_definition_schema_version: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _clean(value: object) -> str:
    return " ".join(str(value or "").replace("\r", " ").replace("\n", " ").split()).strip()


def _norm(value: object) -> str:
    text = _clean(value).casefold()
    return text.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')


def _status_for_resolved_context(text: str, *, current_source_name: object = "", attached_source_urls: Iterable[str] = ()) -> tuple[str, str]:
    lowered = _norm(text)
    current = _norm(current_source_name)
    attached = tuple(_clean(item) for item in attached_source_urls if _clean(item))
    if re.search(r"\btold\s+metro\b", lowered) and ("metro" in current or not current):
        return "RESOLVED_SECONDARY_SOURCE", "current source directly preserves the quoted/told-Metro source relationship"
    if re.search(r"\bcomments?\s+(?:below|section)\b", lowered) and attached:
        return "RESOLVED_SECONDARY_SOURCE", "comment corpus is preserved/attached"
    if re.search(r"\b(?:youtube|video|channel|post|tweet|x post)\b", lowered) and attached:
        return "RESOLVED_PRIMARY_SOURCE", "original media/post URL is attached"
    if re.search(r"\[\d+\]|\([A-Za-z][A-Za-z .'-]+,\s*\d{4}\)", text) and attached:
        return "RESOLVED_SECONDARY_SOURCE", "citation/reference link is attached for review"
    return "UNRESOLVED_SOURCE_REFERENCE", "text points to a source object but no linked source body/URL was supplied"


def classify_source_reference_candidate(
    text: object,
    *,
    current_source_name: object = "",
    attached_source_urls: Iterable[str] = (),
    claim_span: Mapping[str, Any] | None = None,
) -> SourceReferenceCandidate:
    raw = _clean(text)
    lowered = _norm(raw)
    edit_key = _clean((claim_span or {}).get("edit_key") if isinstance(claim_span, Mapping) else "")
    section_label = _clean((claim_span or {}).get("section_label") if isinstance(claim_span, Mapping) else "")

    pointer_type = ""
    object_type = ""
    if re.search(r"\b(?:measured|figures\s+show|statistics\s+show|researchers\s+calculated|calculated|estimated)\b", lowered):
        pointer_type, object_type = "measurement_or_dataset", "dataset"
    elif re.search(r"\b(?:found\s+that|a\s+report\s+found|report\s+found|study\s+found|pew\s+survey\s+found)\b", lowered):
        pointer_type, object_type = ("poll_or_survey", "survey") if "survey" in lowered else ("study_or_analysis", "report")
    elif re.search(r"\b(?:monitored|recorded|documented|council\s+recorded)\b", lowered):
        pointer_type, object_type = "monitoring_or_records", "records"
    elif re.search(r"\b(?:quoted\s+as\s+saying|was\s+quoted\s+as\s+saying|quoted\s+.+\s+as\s+saying|told\s+metro|told\s+the\s+paper|told\s+the\s+court)\b", lowered):
        pointer_type, object_type = "quote_or_interview", "quote"
    elif re.search(r"\b(?:saw\s+firsthand|witnessed|was\s+a\s+witness)\b", lowered):
        pointer_type, object_type = "witness", "witness"
    elif re.search(r"\b(?:said\s+on\s+.+\s+channel|said\s+in\s+.+\s+video|said\s+in\s+.+\s+post|posted|shared|messaged|wrote)\b", lowered):
        pointer_type, object_type = "media_channel_or_post", "post"
    elif re.search(r"\b(?:the\s+\d+\s+of\s+.+\s+were\s+polled|were\s+polled|polling\s+went\s+on|polled|surveyed)\b", lowered):
        pointer_type, object_type = "poll_or_survey", "poll"
    elif re.search(r"\bpeople\s+say\b.*\bcomments?\s+(?:below|section)\b", lowered):
        pointer_type, object_type = "comment_corpus", "comments"
    elif re.search(r"\b(?:according\s+to\s+officials|police\s+said|officials\s+said|spokesperson\s+said|confirmed|announced|stated|claimed|alleged|reported)\b", lowered):
        pointer_type, object_type = "report_or_statement", "statement"
    elif re.search(r"\[\d+\]|\([A-Za-z][A-Za-z .'-]+,\s*\d{4}\)", raw):
        pointer_type, object_type = "citation_or_reference", "paper"

    if not pointer_type:
        return SourceReferenceCandidate(
            text=raw,
            kind="claim_span",
            source_reference_status="NOT_A_SOURCE_REFERENCE",
            source_pointer_type="not_source_reference",
            source_object_type="",
            reason="ordinary claim-span without a source-bearing object trigger",
            goes_to_main_sourcing_card=False,
            goes_to_review_text=True,
            linked_claim_span_edit_key=edit_key,
            section_label=section_label,
            review_required=False,
        )

    status, reason = _status_for_resolved_context(raw, current_source_name=current_source_name, attached_source_urls=attached_source_urls)
    return SourceReferenceCandidate(
        text=raw,
        kind="source_reference_candidate",
        source_reference_status=status,
        source_pointer_type=pointer_type,
        source_object_type=object_type,
        reason=reason,
        goes_to_main_sourcing_card=True,
        goes_to_review_text=True,
        linked_claim_span_edit_key=edit_key,
        section_label=section_label,
        review_required=status.startswith("UNRESOLVED"),
    )


def extract_source_reference_candidates(
    spans_or_texts: Iterable[Mapping[str, Any] | str],
    *,
    current_source_name: object = "",
    attached_source_urls: Iterable[str] = (),
) -> dict[str, Any]:
    candidates = []
    for item in spans_or_texts:
        if isinstance(item, Mapping):
            text = item.get("text", "")
            candidate = classify_source_reference_candidate(
                text,
                current_source_name=current_source_name,
                attached_source_urls=attached_source_urls,
                claim_span=item,
            )
        else:
            candidate = classify_source_reference_candidate(
                item,
                current_source_name=current_source_name,
                attached_source_urls=attached_source_urls,
            )
        candidates.append(candidate.to_dict())
    main = [item for item in candidates if item.get("goes_to_main_sourcing_card")]
    return {
        "schema_version": POLICY_VERSION,
        "candidate_count": len(candidates),
        "main_sourcing_card_candidate_count": len(main),
        "candidates": candidates,
        "main_sourcing_card_candidates": main,
        "safety_flags": {
            "web_download_performed": False,
            "media_download_performed": False,
            "browser_launch_performed": False,
            "automatic_classification_performed": False,
            "sensitive_identifier_inference_performed": False,
        },
    }

# SOURCE_REFERENCE_PASS4_CANDIDATE_LAYER_20260827
# Strengthen the separate source-reference layer.  This does not change
# coloured claim-span roles; it only decides whether an ordinary-looking span
# points to a missing/linked evidentiary object that belongs on the main
# Sourcing card.  Ordinary Unknown claim-spans still stay out of the main card.
_BASE_CLASSIFY_SOURCE_REFERENCE_CANDIDATE_PASS4_20260827 = classify_source_reference_candidate


def _pass4_large_or_measurement_claim(lowered: str) -> bool:
    large_number = re.search(r"\b\d{1,3}(?:,\d{3})+\b|\b\d+(?:\.\d+)?\s*(?:%|percent)\b", lowered)
    word_number = re.search(r"\b(?:hundreds\s+of\s+thousands|tens\s+of\s+thousands|thousands|millions|half\s+a\s+dozen|dozens)\b", lowered)
    measure_context = re.search(
        r"\b(?:rate|rates|number\s+of|highest\s+number|recorded\s+cases|reported\s+incidents|incidents|cases|views\s+per\s+video|views|pounds|suicides|per\s+(?:week|month|year|video)|children|respondents|polled|surveyed|statistics|figures|dataset|records)\b",
        lowered,
    )
    if re.search(r"\b(?:regret\s+rate|rate\s+for|rates\s+among|two\s+male\s+suicides\s+a\s+week|highest\s+number\s+of)\b", lowered):
        return True
    return bool((large_number or word_number) and measure_context)


def _pass4_source_actor(raw: str) -> str:
    clean = _clean(raw)
    patterns = [
        r"\bor\s+so\s+([A-Z][A-Za-z0-9&' .-]{2,80}?)\s+tells?\s+me\b",
        r"\b([A-Z][A-Za-z0-9&' .-]{2,80}?)\s+tells?\s+me\b",
        r"\baccording\s+to\s+([A-Za-z][A-Za-z0-9&' .-]{2,80})\b",
        r"\b([A-Z][A-Za-z0-9&' .-]{2,80}?)\s+(?:said|reported|claimed|alleged|announced|confirmed|wrote|posted|shared|messaged)\b",
        r"\b(police|officials|researchers|the\s+council|the\s+court|the\s+government|the\s+home\s+office|a\s+spokesperson)\s+(?:said|reported|confirmed|announced|recorded)\b",
    ]
    for pattern in patterns:
        found = re.search(pattern, clean, flags=re.IGNORECASE)
        if found:
            actor = _clean(found.group(1))
            actor = re.sub(r"^(?:the|a|an)\s+", "", actor, flags=re.IGNORECASE)
            return actor[:120]
    return ""


def _pass4_infer_pointer(raw: str) -> tuple[str, str, str]:
    lowered = _norm(raw)

    # Directly received source/attribution, including phrases from the user's
    # policy such as "or so X tells me", "X said to me", and repeated reported
    # statements from parishioners or other actors.
    if re.search(r"\bor\s+so\s+[A-Z][A-Za-z0-9&' .-]{2,80}?\s+tells?\s+me\b", raw, flags=re.IGNORECASE):
        return "quote_or_interview", "quote", "directly named source actor tells the speaker"
    if re.search(r"\b(?:said|told)\s+to\s+me\b|\btells?\s+me\b|\bwill\s+say\s+to\s+me\b", lowered):
        return "quote_or_interview", "quote", "span points to a direct told/said-to-me source relationship"
    if re.search(r"\bi\s+(?:heard|read)\s+(?:from\s+)?[A-Z]?[A-Za-z0-9&' .-]{2,80}\s+that\b", raw, flags=re.IGNORECASE):
        return "quote_or_interview", "quote", "speaker reports a named heard/read source chain"

    # Generic source-bearing named actor statements. Keep this after direct-
    # attribution checks so ordinary claim-spans without a source verb are not
    # promoted to the main card.
    if re.search(r"\b(?:police|officials|researchers|spokesperson|council|court|government|home\s+office|charity|commission|think\s+tank|regulator)\s+(?:said|reported|confirmed|announced|recorded|found|calculated|estimated|documented)\b", lowered):
        return "report_or_statement", "statement", "institutional/source-like actor with source-bearing verb"
    if re.search(r"\b[A-Z][A-Za-z0-9&' .-]{2,80}?\s+(?:said|reported|claimed|alleged|announced|confirmed|wrote|posted|shared|messaged)\b", raw):
        return "report_or_statement", "statement", "named actor with source-bearing verb"

    # Source-acquisition and measurable/numeric claims from the policy. These
    # are not normal Unknown claims because they imply a missing count, dataset,
    # record, poll, report, analytics page, or other source object.
    if re.search(r"\bi\s+found\s+out\b", lowered):
        return "report_or_statement", "statement", "speaker says he found out a claim but the source object is not linked"
    if _pass4_large_or_measurement_claim(lowered):
        return "measurement_or_dataset", "dataset", "measurable/numeric claim implies a dataset, record, analytics source, poll, or report"

    # Document-witness: direct encounter with a document/book/text. This is a
    # source object even when the semantic claim role is Secondary.
    if re.search(r"\bi\s+read\s+(?:that\s+cover\s+to\s+cover|the\s+quran\s+cover\s+to\s+cover|this\s+book|that\s+book|this\s+document|that\s+document|the\s+report|the\s+paper)\b", lowered):
        return "document_witness", "document", "speaker directly encountered a document/book/text source object"

    return "", "", ""


def classify_source_reference_candidate(  # type: ignore[no-redef]
    text: object,
    *,
    current_source_name: object = "",
    attached_source_urls: Iterable[str] = (),
    claim_span: Mapping[str, Any] | None = None,
) -> SourceReferenceCandidate:
    base = _BASE_CLASSIFY_SOURCE_REFERENCE_CANDIDATE_PASS4_20260827(
        text,
        current_source_name=current_source_name,
        attached_source_urls=attached_source_urls,
        claim_span=claim_span,
    )
    if base.kind == "source_reference_candidate":
        actor = base.source_actor or _pass4_source_actor(str(text or ""))
        if actor:
            return SourceReferenceCandidate(**{**base.to_dict(), "source_actor": actor})
        return base

    raw = _clean(text)
    edit_key = _clean((claim_span or {}).get("edit_key") if isinstance(claim_span, Mapping) else "")
    section_label = _clean((claim_span or {}).get("section_label") if isinstance(claim_span, Mapping) else "")
    pointer_type, object_type, pointer_reason = _pass4_infer_pointer(raw)
    if not pointer_type:
        return base

    status, status_reason = _status_for_resolved_context(
        raw,
        current_source_name=current_source_name,
        attached_source_urls=attached_source_urls,
    )
    return SourceReferenceCandidate(
        text=raw,
        kind="source_reference_candidate",
        source_reference_status=status,
        source_pointer_type=pointer_type,
        source_object_type=object_type,
        source_actor=_pass4_source_actor(raw),
        reason=f"{pointer_reason}; {status_reason}",
        goes_to_main_sourcing_card=True,
        goes_to_review_text=True,
        linked_claim_span_edit_key=edit_key,
        section_label=section_label,
        review_required=status.startswith("UNRESOLVED"),
    )



# SOURCE_REFERENCE_PASS4C_UNKNOWN_MEDIA_REQUIREMENT_20260827
# A source-reference candidate may enter the main Sourcing/Review card only if
# it fulfils the user's Unknown-media-source requirement: it must point to a
# source object or source-bearing process, such as quoted/told/witnessed/reported,
# found/measured/monitored/recorded/polled/surveyed/calculated figures, a named
# report/study/poll/dataset/record/citation, or a directly encountered document.
# Ordinary Unknown claims stay in the coloured Review text only.
_BASE_CLASSIFY_SOURCE_REFERENCE_CANDIDATE_PASS4C_20260827 = classify_source_reference_candidate


def _pass4c_named_or_source_like_actor_statement(raw: str, lowered: str) -> bool:
    source_actor = r"(?:police|officials|researchers|spokesperson|council|court|judge|government|home\s+office|charity|commission|think\s+tank|regulator|pollster|survey|study|paper|journal|newspaper|article|video|channel|witness|victim|family|lawyer|ngo|official)"
    source_verb = r"(?:said|reported|claimed|alleged|announced|confirmed|recorded|found|calculated|estimated|documented|published|posted|shared|wrote|messaged|measured|monitored|polled|surveyed)"
    if re.search(rf"\b{source_actor}\s+{source_verb}\b", lowered):
        return True
    if re.search(r"\baccording\s+to\s+(?:officials|police|researchers|a\s+report|the\s+report|a\s+study|the\s+study|the\s+council|the\s+court|the\s+government|the\s+home\s+office|a\s+spokesperson)\b", lowered):
        return True
    if re.search(r"\bor\s+so\s+[A-Z][A-Za-z0-9&' .-]{2,80}?\s+tells?\s+me\b", raw, flags=re.IGNORECASE):
        return True
    if re.search(r"\b[A-Z][A-Za-z0-9&' .-]{2,80}?\s+(?:said|reported|claimed|alleged|announced|confirmed|wrote|posted|shared|messaged)\b", raw):
        return True
    return False


def _pass4c_unknown_media_requirement(raw: str, candidate: SourceReferenceCandidate) -> tuple[bool, str]:
    lowered = _norm(raw)
    pointer = _clean(candidate.source_pointer_type)

    if pointer in {"measurement_or_dataset", "study_or_analysis", "monitoring_or_records", "poll_or_survey", "citation_or_reference"}:
        return True, "measurement/study/records/poll/citation source-object requirement met"

    if pointer == "comment_corpus":
        if re.search(r"\bcomments?\s+(?:below|section)\b", lowered):
            return True, "comment-corpus source-object requirement met"
        return False, "comment-corpus pointer lacked comment-section wording"

    if pointer == "document_witness":
        if re.search(r"\bi\s+read\s+(?:that\s+cover\s+to\s+cover|the\s+quran\s+cover\s+to\s+cover|this\s+book|that\s+book|this\s+document|that\s+document|the\s+report|the\s+paper)\b", lowered):
            return True, "directly encountered document/book/text source-object requirement met"
        return False, "document pointer lacked a direct document-witness phrase"

    if pointer in {"quote_or_interview", "direct_attribution"}:
        if re.search(r"\b(?:quoted\s+as\s+saying|was\s+quoted\s+as\s+saying|quoted\s+.+\s+as\s+saying|told\s+metro|told\s+the\s+paper|told\s+the\s+court|said\s+to\s+me|told\s+me|tells?\s+me|will\s+say\s+to\s+me|or\s+so\s+.+?\s+tells?\s+me)\b", lowered):
            return True, "quote/interview/told-me source-bearing requirement met"
        if _pass4c_named_or_source_like_actor_statement(raw, lowered):
            return True, "named/source-like actor statement requirement met"
        return False, "quote/interview pointer lacked source-bearing attribution wording"

    if pointer == "witness":
        if re.search(r"\b(?:saw\s+firsthand|witnessed|was\s+a\s+witness)\b", lowered):
            return True, "witness-source requirement met"
        return False, "witness pointer lacked firsthand/witness wording"

    if pointer in {"media_channel_or_post", "report_or_statement"}:
        if re.search(r"\b(?:said\s+on\s+.+\s+channel|said\s+in\s+.+\s+video|said\s+in\s+.+\s+post|posted|shared|messaged|wrote)\b", lowered):
            return True, "media/post source-bearing requirement met"
        if _pass4c_named_or_source_like_actor_statement(raw, lowered):
            return True, "named/source-like actor report-statement requirement met"
        if re.search(r"\bi\s+found\s+out\b", lowered) and _pass4_large_or_measurement_claim(lowered):
            return True, "found-out numeric/source-bearing requirement met"
        return False, "ordinary reported-looking claim did not satisfy Unknown-media source requirement"

    if _pass4_large_or_measurement_claim(lowered):
        return True, "numeric/measurable source-object requirement met"

    return False, "ordinary Unknown claim-span without required media/source object"


def classify_source_reference_candidate(  # type: ignore[no-redef]
    text: object,
    *,
    current_source_name: object = "",
    attached_source_urls: Iterable[str] = (),
    claim_span: Mapping[str, Any] | None = None,
) -> SourceReferenceCandidate:
    candidate = _BASE_CLASSIFY_SOURCE_REFERENCE_CANDIDATE_PASS4C_20260827(
        text,
        current_source_name=current_source_name,
        attached_source_urls=attached_source_urls,
        claim_span=claim_span,
    )
    raw = _clean(text)
    if candidate.kind != "source_reference_candidate":
        data = candidate.to_dict()
        data["unknown_media_requirement_met"] = False
        data["unknown_media_requirement_reason"] = "not a source-reference candidate"
        return SourceReferenceCandidate(**data)

    met, requirement_reason = _pass4c_unknown_media_requirement(raw, candidate)
    data = candidate.to_dict()
    data["unknown_media_requirement_met"] = met
    data["unknown_media_requirement_reason"] = requirement_reason
    if not met:
        data.update(
            kind="claim_span",
            source_reference_status="NOT_A_SOURCE_REFERENCE",
            source_pointer_type="not_source_reference",
            source_object_type="",
            source_actor="",
            reason="ordinary Unknown claim-span; failed Unknown-media source requirement: " + requirement_reason,
            goes_to_main_sourcing_card=False,
            review_required=False,
        )
        return SourceReferenceCandidate(**data)

    reason = _clean(data.get("reason"))
    if requirement_reason and requirement_reason not in reason:
        data["reason"] = (reason + "; " + requirement_reason).strip("; ")
    data["goes_to_main_sourcing_card"] = True
    data["review_required"] = str(data.get("source_reference_status") or "").startswith("UNRESOLVED")
    return SourceReferenceCandidate(**data)


# SOURCE_REFERENCE_PASS5C_TIGHT_REVIEW_GATE_20260827
# Tighten the Review/source-reference lane so it is not a dumping ground for
# every Secondary/Tertiary or self-owned remembered event.  Keep the main
# Sourcing/Review card for missing media/source objects: named source actors,
# institutional/documented reports, polls/studies/datasets/records/citations,
# and numeric/measured claims that are not merely the speaker's own experience.
_BASE_CLASSIFY_SOURCE_REFERENCE_CANDIDATE_PASS5C_20260827 = classify_source_reference_candidate


def _pass5c_demote_candidate(data: dict[str, Any], reason: str) -> SourceReferenceCandidate:
    data = dict(data)
    data.update(
        kind="claim_span",
        source_reference_status="NOT_A_SOURCE_REFERENCE",
        source_pointer_type="not_source_reference",
        source_object_type="",
        source_actor="",
        reason="not promoted to Review: " + reason,
        goes_to_main_sourcing_card=False,
        review_required=False,
        unknown_media_requirement_met=False,
        unknown_media_requirement_reason=reason,
    )
    return SourceReferenceCandidate(**data)


def _pass5c_is_self_owned_or_oral_memory(raw: str, lowered: str) -> bool:
    # These are claim-role decisions or oral anecdotes, not missing media/source
    # objects.  They remain visible in the coloured transcript but do not enter
    # the main Sourcing/Review queue.
    personal_patterns = (
        r"\bi\s+read\s+(?:that\s+cover\s+to\s+cover|the\s+quran\s+cover\s+to\s+cover|this\s+book|that\s+book)\b",
        r"\bi\s+blew\s+a\s+puff\b",
        r"\bi(?:'ve|\s+have)?\s+long\s+said\b",
        r"\bthe\s+lord\s+jesus\s+said\b",
        r"\bparishioners\s+will\s+say\s+to\s+me\b",
        r"\bparishioners\s+say\s+to\s+me\b",
        r"\bi(?:'ve|\s+have)\s+spoken\s+to\s+kai\b",
        r"\bkai\s+.*\bhas\s+said\b",
        r"\b(?:he|she|they)\s+said\s+to\s+me\b",
        r"\bi\s+was\s+invited\s+to\s+rallies\b",
        r"\bi\s+started\s+with\s+like\s+five\s+views\b",
        r"\bi\s+was\s+getting\s+[\d,]+\s+views\s+per\s+video\b",
    )
    return any(re.search(pattern, lowered) for pattern in personal_patterns)


def _pass5c_numeric_is_self_analytics_or_ministry_count(raw: str, lowered: str) -> bool:
    # Not every number is an unknown-media gap.  Speaker-owned channel analytics
    # and local ministry self-counts can be manually reviewed as claim spans, but
    # should not automatically become Sourcing-card candidates.
    if re.search(r"\bi\s+was\s+getting\s+[\d,]+\s+views\s+per\s+video\b|\bstarted\s+with\s+like\s+five\s+views\b", lowered):
        return True
    if re.search(r"\bwe(?:'ve|\s+have)\s+saved\s+(?:half\s+a\s+dozen|\d+)\s+babies\b", lowered):
        return True
    return False


def classify_source_reference_candidate(  # type: ignore[no-redef]
    text: object,
    *,
    current_source_name: object = "",
    attached_source_urls: Iterable[str] = (),
    claim_span: Mapping[str, Any] | None = None,
) -> SourceReferenceCandidate:
    candidate = _BASE_CLASSIFY_SOURCE_REFERENCE_CANDIDATE_PASS5C_20260827(
        text,
        current_source_name=current_source_name,
        attached_source_urls=attached_source_urls,
        claim_span=claim_span,
    )
    raw = _clean(text)
    lowered = _norm(raw)
    data = candidate.to_dict()
    if candidate.kind != "source_reference_candidate" or not bool(data.get("goes_to_main_sourcing_card")):
        return candidate

    if _pass5c_is_self_owned_or_oral_memory(raw, lowered):
        return _pass5c_demote_candidate(data, "self-owned/oral-memory statement, not an unknown media/source-reference object")
    if _pass5c_numeric_is_self_analytics_or_ministry_count(raw, lowered):
        return _pass5c_demote_candidate(data, "speaker-owned analytics/ministry count, not a source-reference gap")

    pointer = _clean(data.get("source_pointer_type"))
    source_actor = _clean(data.get("source_actor"))
    # Direct document witness only stays if it is a report/paper/study/citation;
    # plain book/Quran reading is a claim-role span, not a sourcing gap.
    if pointer == "document_witness":
        if re.search(r"\b(?:report|paper|study|dataset|records?|filing|article)\b", lowered):
            return candidate
        return _pass5c_demote_candidate(data, "plain document/book reading does not need a separate source-reference Review item")

    # Quote/interview direct speech is promoted only when it points to a named
    # source actor or published/media context.  Generic conversations stay out.
    if pointer in {"quote_or_interview", "direct_attribution"}:
        if source_actor and source_actor.casefold() not in {"parishioners", "kai"}:
            return candidate
        if re.search(r"\b(?:told\s+metro|told\s+the\s+paper|told\s+the\s+court|quoted\s+as\s+saying|was\s+quoted\s+as\s+saying|quoted\s+.+\s+as\s+saying)\b", lowered):
            return candidate
        return _pass5c_demote_candidate(data, "generic oral/direct-speech attribution is not an unknown media/source requirement")

    # Generic named actor statements must look like public/published/source-like
    # statements, not just conversational 'X said to me'.
    if pointer == "report_or_statement":
        if re.search(r"\b(?:police|officials|researchers|spokesperson|council|court|government|home\s+office|commission|regulator|report|study|survey|poll|figures|statistics)\b", lowered):
            return candidate
        if re.search(r"\b(?:reported|documented|recorded|published|calculated|estimated|measured|monitored|surveyed|polled)\b", lowered):
            return candidate
        if re.search(r"\bi\s+found\s+out\b", lowered) and _pass4_large_or_measurement_claim(lowered):
            return candidate
        return _pass5c_demote_candidate(data, "ordinary stated/said claim without public source-object trigger")

    return candidate


# SOURCE_CHAIN_DEFINITION_SET_PASS6_20260827
from profile_media_source_chain_definition_set import SCHEMA_VERSION as SOURCE_CHAIN_DEFINITION_SCHEMA_VERSION, ROUTE_CLAIM_SPAN_ONLY, classify_media_source_chain_candidate
_BASE_CLASSIFY_SOURCE_REFERENCE_CANDIDATE_PASS6_20260827 = classify_source_reference_candidate

def _source_chain_candidate_from_decision(raw: str, decision: object, *, edit_key: str = "", section_label: str = "") -> SourceReferenceCandidate:
    data = {
        "text": raw,
        "kind": "source_reference_candidate" if getattr(decision, "route", "") != ROUTE_CLAIM_SPAN_ONLY else "claim_span",
        "source_reference_status": getattr(decision, "source_reference_status", "NOT_A_SOURCE_REFERENCE"),
        "source_pointer_type": getattr(decision, "pointer_type", "not_source_reference"),
        "source_object_type": getattr(decision, "object_type", ""),
        "source_actor": getattr(decision, "source_actor", ""),
        "reason": getattr(decision, "reason", ""),
        "goes_to_main_sourcing_card": bool(getattr(decision, "goes_to_main_sourcing_card", False)),
        "goes_to_review_text": bool(getattr(decision, "goes_to_review_text", False)),
        "linked_claim_span_edit_key": edit_key,
        "resolved_source_url": "",
        "section_label": section_label,
        "review_required": bool(getattr(decision, "review_required", False)),
        "unknown_media_requirement_met": bool(getattr(decision, "unknown_media_requirement_met", False)),
        "unknown_media_requirement_reason": getattr(decision, "unknown_media_requirement_reason", ""),
        "media_source_role": getattr(decision, "media_source_role", ""),
        "candidate_source_role": getattr(decision, "media_source_role", ""),
        "source_chain_template_id": getattr(decision, "template_id", ""),
        "source_chain_summary": getattr(decision, "chain_summary", ""),
        "source_chain_depth": int(getattr(decision, "source_chain_depth", 0) or 0),
        "source_actor_type": getattr(decision, "source_actor_type", ""),
        "named_intermediary_chain_role": getattr(decision, "named_intermediary_chain_role", ""),
        "current_speaker_chain_role": getattr(decision, "current_speaker_chain_role", ""),
        "inferred_origin_actor_type": getattr(decision, "inferred_origin_actor_type", ""),
        "source_chain_definition_schema_version": SOURCE_CHAIN_DEFINITION_SCHEMA_VERSION,
    }
    return SourceReferenceCandidate(**data)

def classify_source_reference_candidate(  # type: ignore[no-redef]
    text: object,
    *,
    current_source_name: object = "",
    attached_source_urls: Iterable[str] = (),
    claim_span: Mapping[str, Any] | None = None,
) -> SourceReferenceCandidate:
    raw = _clean(text)
    edit_key = _clean((claim_span or {}).get("edit_key") if isinstance(claim_span, Mapping) else "")
    section_label = _clean((claim_span or {}).get("section_label") if isinstance(claim_span, Mapping) else "")
    claim_span_role = _clean((claim_span or {}).get("role") if isinstance(claim_span, Mapping) else "")
    decision = classify_media_source_chain_candidate(raw, claim_span_role=claim_span_role, current_source_name=current_source_name, attached_source_urls=attached_source_urls)
    return _source_chain_candidate_from_decision(raw, decision, edit_key=edit_key, section_label=section_label)
