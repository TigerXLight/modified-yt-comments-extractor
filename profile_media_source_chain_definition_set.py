
"""Profile/Media source-chain definition set and deterministic classifier.

V83A implements the dual layer source-comprehension model:

1. Claim-span colour: what the span is doing in the transcript.
2. Media-source role: what provenance chain the span/source object represents.
3. Review: temporary queue only for ambiguous promotion into media-source provenance.

The file is intentionally data-heavy. It encodes source-chain templates, actor
classes, object classes, media/repost rules, and regression examples so the app
can apply the same definitions in the classifier, preview JSON, and GUI.

No network, browsing, downloads, OCR, identity enrichment, or sensitive inference
is performed here.
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any, Iterable, Mapping

SCHEMA_VERSION = "profile-media-source-chain-definition-set-v83a-20260827"
PRIMARY = "PRIMARY_SELF_AUTHORED_SCOPE"
SECONDARY = "SECONDARY_WITNESS_ACCOUNT"
TERTIARY = "TERTIARY_PROPAGATED_SOURCE"
UNKNOWN = "UNKNOWN_SOURCE_ROLE"
ROUTE_MEDIA_SOURCE_RECORD = "media_source_record"
ROUTE_REVIEW = "review_media_source_promotion"
ROUTE_CLAIM_SPAN_ONLY = "claim_span_only"
STATUS_MEDIA_SOURCE_PRIMARY = "MEDIA_SOURCE_PRIMARY"
STATUS_MEDIA_SOURCE_SECONDARY = "MEDIA_SOURCE_SECONDARY"
STATUS_MEDIA_SOURCE_TERTIARY = "MEDIA_SOURCE_TERTIARY"
STATUS_MEDIA_SOURCE_UNKNOWN = "MEDIA_SOURCE_UNKNOWN"
STATUS_REVIEW_PROMOTION = "REVIEW_MEDIA_SOURCE_PROMOTION"
STATUS_NOT_SOURCE_REFERENCE = "NOT_A_SOURCE_REFERENCE"

@dataclass(frozen=True)
class SourceChainTemplate:
    template_id: str
    title: str
    route: str
    media_source_role: str
    origin_role: str = ""
    intermediary_role: str = ""
    current_speaker_role: str = ""
    source_reference_status: str = ""
    pointer_type: str = ""
    object_type: str = ""
    actor_type: str = ""
    review_required: bool = False
    confidence: str = "medium"
    definition: str = ""
    example_phrases: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()
    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["example_phrases"] = list(self.example_phrases)
        data["notes"] = list(self.notes)
        return data

@dataclass(frozen=True)
class SourceChainDecision:
    route: str
    media_source_role: str = ""
    source_reference_status: str = STATUS_NOT_SOURCE_REFERENCE
    pointer_type: str = "not_source_reference"
    object_type: str = ""
    source_actor: str = ""
    source_actor_type: str = ""
    template_id: str = "claim_span_only_default"
    chain_summary: str = ""
    reason: str = ""
    confidence: str = "medium"
    review_required: bool = False
    goes_to_main_sourcing_card: bool = False
    goes_to_review_text: bool = False
    source_chain_gap: bool = False
    source_chain_depth: int = 0
    inferred_origin_actor_type: str = ""
    named_intermediary_chain_role: str = ""
    current_speaker_chain_role: str = ""
    unknown_media_requirement_met: bool = False
    unknown_media_requirement_reason: str = ""
    candidate_claim_basis: str = "UNKNOWN_CLAIM_BASIS"
    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

ORIGIN_INSTITUTION_KEYWORDS: dict[str, tuple[str, ...]] = {
    "church_or_religious_institution": ("church of england", "coe", "diocese", "archdeacon", "bishop", "bishop's office", "cathedral", "parish", "churchwarden", "church wardens", "gafcon", "fce", "cac", "free church of england", "confessing anglican", "synod", "general synod", "clergy disciplinary", "disciplinary tribunal", "safeguarding team"),
    "legal_or_court_origin": ("court", "judge", "tribunal", "crown court", "high court", "coroner", "judgment", "court filing", "legal filing", "case file", "complaint file", "disciplinary record", "formal complaint", "settlement agreement"),
    "state_or_public_body": ("government", "home office", "ministry", "department", "council", "local authority", "parliament", "mp", "minister", "regulator", "commission", "charity commission", "ofcom", "ons", "office for national statistics", "nhs", "police", "prosecutor", "cps", "school", "university", "hospital"),
    "platform_or_publisher_origin": ("youtube", "x", "twitter", "facebook", "instagram", "tiktok", "telegram", "substack", "channel", "account", "profile", "post", "tweet", "livestream", "podcast", "broadcast"),
    "direct_record_or_dataset": ("dataset", "statistics", "figures", "records", "register", "database", "spreadsheet", "poll", "survey", "study", "paper", "report", "monitoring data", "foi", "freedom of information"),
}
INTERMEDIARY_ACTOR_KEYWORDS: dict[str, tuple[str, ...]] = {
    "legal_or_campaign_org": ("christian concern", "law firm", "lawyer", "solicitor", "barrister", "legal team", "legal centre", "legal center", "campaign group", "advocacy group", "rights group", "pressure group", "lobby group", "ngo", "charity", "foundation", "institute"),
    "news_or_media_intermediary": ("metro", "bbc", "itv", "sky news", "channel 4", "guardian", "telegraph", "times", "daily mail", "mailonline", "sun", "mirror", "independent", "reuters", "ap", "afp", "journalist", "reporter", "newspaper", "paper", "outlet", "article", "broadcast"),
    "research_or_analysis_intermediary": ("researchers", "think tank", "pollster", "survey company", "university researchers", "academic", "analyst", "monitoring group", "fact checker", "fact-checker", "investigators"),
    "personal_intermediary": ("friend", "relative", "family", "parishioner", "witness", "source", "whistleblower", "insider", "contact", "someone", "people", "they", "he", "she"),
}
KNOWN_INTERMEDIARY_ACTORS: dict[str, str] = {
    "christian concern": "legal_or_campaign_org", "brephos": "campaign_or_charity_org", "pew": "polling_or_research_org", "yougov": "polling_or_research_org", "survation": "polling_or_research_org", "ipsos": "polling_or_research_org", "reuters": "news_or_wire_intermediary", "ap": "news_or_wire_intermediary", "afp": "news_or_wire_intermediary",
}
SOURCE_OBJECT_KEYWORDS: dict[str, tuple[str, ...]] = {
    "formal_record": ("complaint", "formal complaint", "disciplinary measure", "disciplinary measures", "clergy disciplinary", "letter", "email", "filing", "court filing", "record", "records", "minutes", "decision", "judgment"),
    "measurement_or_dataset": ("rate", "rates", "prevalence", "statistics", "figures", "numbers", "dataset", "records", "cases", "incidents", "suicides", "deaths", "views", "pounds", "cost", "funding", "poll", "survey"),
    "document_or_publication": ("book", "report", "study", "paper", "article", "post", "statement", "press release", "sermon", "video", "podcast", "livestream", "broadcast", "quran", "bible", "scripture"),
    "embedded_media": ("embedded video", "clip", "footage", "image", "photo", "screenshot", "audio", "recording"),
}
SOURCE_CHAIN_TEMPLATES: tuple[SourceChainTemplate, ...] = (
    SourceChainTemplate("direct_self_authored_media_statement", "Direct self-authored/current-speaker media", ROUTE_MEDIA_SOURCE_RECORD, PRIMARY, origin_role=PRIMARY, source_reference_status=STATUS_MEDIA_SOURCE_PRIMARY, pointer_type="self_authored_media_or_statement", object_type="current_speaker_media", confidence="high", definition="The current speaker/source owns or authored the relevant media/statement.", example_phrases=("my video", "my sermon", "I wrote", "I published", "I posted")),
    SourceChainTemplate("origin_institution_told_speaker", "Origin institution directly tells current speaker", ROUTE_MEDIA_SOURCE_RECORD, SECONDARY, origin_role=PRIMARY, current_speaker_role=SECONDARY, source_reference_status=STATUS_MEDIA_SOURCE_SECONDARY, pointer_type="origin_institution_direct_attribution", object_type="institutional_statement_or_record", confidence="high", definition="The named actor is plausibly the origin institution or record-holder, so current speaker is one hop from origin.", example_phrases=("the diocese told me", "the court confirmed", "police said", "the council recorded")),
    SourceChainTemplate("named_intermediary_told_speaker", "Named intermediary tells current speaker", ROUTE_MEDIA_SOURCE_RECORD, TERTIARY, origin_role=PRIMARY, intermediary_role=SECONDARY, current_speaker_role=TERTIARY, source_reference_status=STATUS_MEDIA_SOURCE_TERTIARY, pointer_type="named_intermediary_told_speaker", object_type="intermediary_statement_about_underlying_record", actor_type="intermediary_organisation", confidence="high", definition="A named intermediary says/tells/confirms something to the current speaker; the underlying record remains one step behind the intermediary.", example_phrases=("or so Christian Concern tell me", "my lawyer told me", "the campaign group confirmed to me"), notes=("Christian Concern example: inferred primary church/legal record -> Christian Concern -> Brett Murphy.",)),
    SourceChainTemplate("statistical_claim_no_named_source", "Statistical/measured claim with no attached source", ROUTE_MEDIA_SOURCE_RECORD, UNKNOWN, source_reference_status=STATUS_MEDIA_SOURCE_UNKNOWN, pointer_type="statistical_claim_no_attached_source", object_type="measurement_or_dataset", confidence="high", definition="The claim is clearly source-like/statistical but no source chain is supplied in the imported material.", example_phrases=("250,000", "regret rate", "high rates", "two suicides a week", "hundreds of thousands of pounds")),
    SourceChainTemplate("document_witness_current_speaker", "Current speaker directly encountered document/text", ROUTE_MEDIA_SOURCE_RECORD, SECONDARY, origin_role=PRIMARY, current_speaker_role=SECONDARY, source_reference_status=STATUS_MEDIA_SOURCE_SECONDARY, pointer_type="document_witness", object_type="document_or_book", confidence="medium", definition="The current speaker says they read or directly encountered a document/book/text. This is secondary for document contents, but may be claim-only if only expressing reaction.", example_phrases=("I read that cover to cover", "I read this book", "I read the report")),
    SourceChainTemplate("formal_quote_or_scripture", "Formal quote/scripture/document quotation", ROUTE_MEDIA_SOURCE_RECORD, TERTIARY, source_reference_status=STATUS_MEDIA_SOURCE_TERTIARY, pointer_type="formal_quote_or_scripture", object_type="quoted_document_or_tradition", confidence="medium", definition="A quoted formal text or transmitted saying appears, but the exact source object is not attached/cited inside the imported item.", example_phrases=("The Lord Jesus said", "scripture says", "the Bible says")),
    SourceChainTemplate("embedded_article_media_original_provenance_unknown", "Embedded/reposted article media with unresolved original/edit status", ROUTE_MEDIA_SOURCE_RECORD, UNKNOWN, source_reference_status=STATUS_MEDIA_SOURCE_UNKNOWN, pointer_type="embedded_media_unresolved_originality", object_type="embedded_media", confidence="high", definition="An article contains/reposts media, but original uploader, full duration, and edit status are not proven.", example_phrases=("embedded video", "article reposted clip", "rehosted footage")),
    SourceChainTemplate("ambiguous_possible_source_statement", "Ambiguous possible source statement", ROUTE_REVIEW, "", source_reference_status=STATUS_REVIEW_PROMOTION, pointer_type="ambiguous_media_source_promotion", object_type="ambiguous_claim_or_source_statement", review_required=True, confidence="low", definition="It might be source provenance, but the evidence is not strong enough to promote automatically.", example_phrases=("people say", "from memory", "I think I heard", "there are claims")),
    SourceChainTemplate("ordinary_claim_span_only", "Ordinary claim-span only", ROUTE_CLAIM_SPAN_ONLY, "", source_reference_status=STATUS_NOT_SOURCE_REFERENCE, pointer_type="not_source_reference", confidence="high", definition="The text is a claim/opinion/description but does not itself function as media-source provenance.", example_phrases=("this is wicked", "which is super woke", "they are apostate")),
)
TEMPLATE_BY_ID = {template.template_id: template for template in SOURCE_CHAIN_TEMPLATES}
SOURCE_CHAIN_EXAMPLE_DATASET: tuple[dict[str, Any], ...] = (
    {"text": "So, I hold the record, or so Christian Concern tell me, the highest number of clergy disciplinary measures", "expected_route": ROUTE_MEDIA_SOURCE_RECORD, "expected_media_source_role": TERTIARY, "expected_template_id": "named_intermediary_told_speaker", "claim_span_role_can_be": ("SECONDARY",), "chain": "unresolved church/legal/disciplinary record -> Christian Concern -> current speaker"},
    {"text": "There are temporal physical consequences, prevalence of abuse and sexually transmitted diseases having massively high rates among the sodomite community.", "expected_route": ROUTE_MEDIA_SOURCE_RECORD, "expected_media_source_role": UNKNOWN, "expected_template_id": "statistical_claim_no_named_source", "chain": "unattached statistical/rate claim -> current speaker"},
    {"text": "So, this was the latest push and they spent hundreds of thousands of pounds that could have used repairing churches.", "expected_route": ROUTE_MEDIA_SOURCE_RECORD, "expected_media_source_role": UNKNOWN, "expected_template_id": "statistical_claim_no_named_source", "chain": "unattached financial/numeric claim -> current speaker"},
    {"text": "What a disgrace that 250,000, probably more, innocent children were raped, tortured and murdered.", "expected_route": ROUTE_MEDIA_SOURCE_RECORD, "expected_media_source_role": UNKNOWN, "expected_template_id": "statistical_claim_no_named_source", "chain": "unattached numeric claim -> current speaker"},
    {"text": "Well, yeah, because the regret rate for abortion is extremely high.", "expected_route": ROUTE_MEDIA_SOURCE_RECORD, "expected_media_source_role": UNKNOWN, "expected_template_id": "statistical_claim_no_named_source", "chain": "unattached rate claim -> current speaker"},
    {"text": "I found out earlier last week that there are at a nearby university, there are two male suicides a week.", "expected_route": ROUTE_MEDIA_SOURCE_RECORD, "expected_media_source_role": UNKNOWN, "expected_template_id": "statistical_claim_no_named_source", "chain": "unattached frequency/statistical claim -> current speaker"},
    {"text": "the diocese told me the decision had been made", "expected_route": ROUTE_MEDIA_SOURCE_RECORD, "expected_media_source_role": SECONDARY, "expected_template_id": "origin_institution_told_speaker", "chain": "origin institution -> current speaker"},
    {"text": "police said three people were arrested", "expected_route": ROUTE_MEDIA_SOURCE_RECORD, "expected_media_source_role": SECONDARY, "expected_template_id": "origin_institution_told_speaker", "chain": "origin institution -> current speaker/media container"},
    {"text": "according to a report, the number doubled", "expected_route": ROUTE_MEDIA_SOURCE_RECORD, "expected_media_source_role": SECONDARY, "expected_template_id": "origin_institution_told_speaker", "chain": "report/source object -> current speaker/media container"},
    {"text": "which is super woke", "expected_route": ROUTE_CLAIM_SPAN_ONLY, "expected_media_source_role": "", "expected_template_id": "ordinary_claim_span_only", "chain": "claim-span only"},
)

def _clean(value: object) -> str:
    return " ".join(str(value or "").replace("\r", " ").replace("\n", " ").split()).strip()
def _norm(value: object) -> str:
    return _clean(value).casefold().replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
def _contains_any(lowered: str, words: Iterable[str]) -> bool:
    return any(word and word in lowered for word in words)
def _actor_type(actor: object) -> str:
    lowered = _norm(actor)
    if not lowered:
        return ""
    for key, actor_type in KNOWN_INTERMEDIARY_ACTORS.items():
        if key in lowered:
            return actor_type
    for actor_type, terms in INTERMEDIARY_ACTOR_KEYWORDS.items():
        if _contains_any(lowered, terms):
            return actor_type
    for actor_type, terms in ORIGIN_INSTITUTION_KEYWORDS.items():
        if _contains_any(lowered, terms):
            return actor_type
    if re.search(r"\b(?:concern|law|legal|campaign|charity|foundation|institute|centre|center|alliance|association|union|society|council|commission|trust)\b", lowered):
        return "organisation_uncertain"
    return "named_actor_uncertain"
def _actor_text_is_real_named_source(actor: object, actor_type: str) -> bool:
    text = _clean(actor)
    lowered = _norm(text)
    if not lowered:
        return False
    # Pronouns, clause fragments and scripture-language are not named
    # intermediary actors.  They are ordinary claim text unless a more specific
    # source-object rule handles them.
    if lowered in {"he", "she", "they", "someone", "people", "this is what scripture", "scripture", "cuz when he", "when he", "because he"}:
        return False
    if re.search(r"\b(?:cuz|because|when|if|however|arguably|this\s+is\s+what|well)\b", lowered):
        return False
    if re.search(r"\b(?:scripture|the bible|the quran)\b", lowered):
        return False
    if lowered in KNOWN_INTERMEDIARY_ACTORS:
        return True
    if actor_type and actor_type not in {"named_actor_uncertain", "personal_intermediary"}:
        return True
    # As a fallback, require title-case looking actor text.  This prevents
    # lowercase clause fragments from becoming Tertiary media-source chains.
    return bool(re.search(r"[A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)*", text))

def _actor_is_probable_intermediary(actor_type: str) -> bool:
    lowered = _norm(actor_type)
    return any(token in lowered for token in ("intermediary", "legal", "campaign", "charity", "news", "wire", "research", "polling", "organisation_uncertain"))
def _actor_is_probable_origin(actor_type: str) -> bool:
    lowered = _norm(actor_type)
    return any(token in lowered for token in ("institution", "court", "state", "public", "church", "religious", "platform", "origin", "record", "dataset"))
def _extract_named_intermediary_told_speaker(raw: str) -> tuple[str, str]:
    patterns = (r"\bor\s+so\s+(?P<actor>[A-Z][A-Za-z0-9&' .\-]{2,90}?)\s+tells?\s+(?:me|us)\b", r"\b(?P<actor>[A-Z][A-Za-z0-9&' .\-]{2,90}?)\s+(?:told|tells|confirmed|said\s+to)\s+(?:me|us)\b", r"\b(?:I|we)\s+(?:was|were|am)\s+told\s+by\s+(?P<actor>[A-Z][A-Za-z0-9&' .\-]{2,90})\b")
    for pattern in patterns:
        match = re.search(pattern, raw, flags=re.IGNORECASE)
        if match:
            actor = _clean(match.group("actor"))
            actor = re.sub(r"\b(?:the|a|an)\s+", "", actor, flags=re.IGNORECASE).strip(" ,.;:-")
            actor_type = _actor_type(actor)
            if not _actor_text_is_real_named_source(actor, actor_type):
                continue
            return actor, actor_type
    return "", ""
def _extract_origin_institution_attribution(raw: str) -> tuple[str, str]:
    patterns = (r"\b(?P<actor>the\s+diocese|the\s+church|the\s+church\s+of\s+england|the\s+court|the\s+council|police|officials|the\s+government|the\s+home\s+office|the\s+university|the\s+school|the\s+hospital|the\s+charity\s+commission|ofcom)\s+(?:said|told|confirmed|announced|recorded|reported|found|published|calculated|estimated)\b", r"\baccording\s+to\s+(?P<actor>the\s+diocese|the\s+court|the\s+council|police|officials|the\s+government|the\s+home\s+office|the\s+university|a\s+report|the\s+report|a\s+study|the\s+study|official\s+figures|records)\b")
    for pattern in patterns:
        match = re.search(pattern, raw, flags=re.IGNORECASE)
        if match:
            actor = _clean(match.group("actor"))
            return actor, _actor_type(actor)
    return "", ""
def _is_measured_or_statistical_claim(raw: str) -> tuple[bool, str]:
    lowered = _norm(raw)
    numeric = bool(re.search(r"\b\d{1,3}(?:,\d{3})+(?:\.\d+)?\b|\b\d+(?:\.\d+)?\s*(?:%|percent|per\s+cent)\b", lowered))
    word_number = bool(re.search(r"\b(?:half\s+a\s+dozen|dozens|hundreds|thousands|millions|billions|hundreds\s+of\s+thousands|tens\s+of\s+thousands|two|three|four|five|six|seven|eight|nine|ten)\b", lowered))
    measure_words = ("rate", "rates", "regret rate", "prevalence", "statistics", "figures", "records", "record", "highest number", "number of", "cases", "incidents", "suicides", "deaths", "views", "per video", "per week", "per month", "per year", "pounds", "funding", "spent", "cost", "poll", "survey", "polled", "respondents", "dataset", "sexually transmitted diseases", "std", "abuse", "murdered", "trafficked", "raped", "tortured")
    if numeric and _contains_any(lowered, measure_words): return True, "numeric measurement/statistical wording"
    if word_number and _contains_any(lowered, measure_words): return True, "word-number measurement/statistical wording"
    if re.search(r"\b(?:high|higher|highest|massively\s+high|extremely\s+high)\s+rates?\b", lowered): return True, "rate/prevalence wording"
    if re.search(r"\bregret\s+rate\b", lowered): return True, "regret-rate wording"
    if re.search(r"\btwo\s+male\s+suicides\s+a\s+week\b", lowered): return True, "frequency/statistical wording"
    return False, ""

def _is_self_owned_or_oral_memory_claim_span_only(raw: str) -> bool:
    """Return True for speaker-owned/oral-memory material that should stay claim-span only.

    This preserves the pass5c distinction: not every number or reported speech
    is a media-source provenance record.  Speaker-owned channel analytics,
    local ministry counts, personal actions, and generic oral anecdotes remain
    coloured transcript/claim spans unless there is a named external source
    chain or a public/documentary source object.
    """
    lowered = _norm(raw)
    patterns = (
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
        r"\bwe(?:'ve|\s+have)\s+saved\s+(?:half\s+a\s+dozen|\d+)\s+babies\b",
    )
    return any(re.search(pattern, lowered) for pattern in patterns)

def _has_document_witness_but_only_reaction(raw: str) -> bool:
    lowered = _norm(raw)
    return bool(re.search(r"\bi\s+read\s+(?:that\s+cover\s+to\s+cover|this\s+book|the\s+quran\s+cover\s+to\s+cover)\b", lowered))
def _is_formal_quote_source(raw: str) -> bool:
    lowered = _norm(raw)
    if re.search(r"\b(?:the\s+lord\s+jesus|jesus|scripture|the\s+bible|the\s+quran|the\s+report|the\s+letter)\s+(?:said|says|states|records)\b", lowered):
        return bool(re.search(r"['\"“”]|\b(?:that|to)\b", raw))
    return False
def _ambiguous_review_trigger(raw: str) -> bool:
    lowered = _norm(raw)
    # Review is only for true border cases between claim-span text and
    # media-source provenance.  Weak discourse markers such as "apparently"
    # and "from memory" made ordinary transcript claims appear in Review; keep
    # them as claim-span text unless a separate source-object/statistical rule
    # promotes them.
    if re.search(r"\b(?:people\s+say|some\s+say|there\s+are\s+claims|it\s+is\s+claimed|i\s+think\s+i\s+heard|allegedly)\b", lowered):
        measured, _ = _is_measured_or_statistical_claim(raw)
        return not measured
    return False
def _decision_from_template(template_id: str, *, raw: str, actor: str = "", actor_type: str = "", extra_reason: str = "") -> SourceChainDecision:
    template = TEMPLATE_BY_ID[template_id]
    status = {PRIMARY: STATUS_MEDIA_SOURCE_PRIMARY, SECONDARY: STATUS_MEDIA_SOURCE_SECONDARY, TERTIARY: STATUS_MEDIA_SOURCE_TERTIARY, UNKNOWN: STATUS_MEDIA_SOURCE_UNKNOWN}.get(template.media_source_role, template.source_reference_status or STATUS_NOT_SOURCE_REFERENCE)
    if template_id == "named_intermediary_told_speaker": chain_summary = f"unresolved primary record/source object -> {actor or 'named intermediary'} -> current speaker/media item"
    elif template_id == "origin_institution_told_speaker": chain_summary = f"{actor or 'origin institution/source object'} -> current speaker/media item"
    elif template_id == "statistical_claim_no_named_source": chain_summary = "unattached statistical/measured source claim -> current speaker/media item"
    elif template_id == "embedded_article_media_original_provenance_unknown": chain_summary = "article/container contains media -> original/edit status unresolved"
    elif template.route == ROUTE_CLAIM_SPAN_ONLY: chain_summary = "claim-span only; no media-source provenance record"
    else: chain_summary = template.definition
    reason = (template.definition + ("; " + extra_reason if extra_reason else "")).strip("; ")
    return SourceChainDecision(route=template.route, media_source_role=template.media_source_role, source_reference_status=status, pointer_type=template.pointer_type, object_type=template.object_type, source_actor=actor, source_actor_type=actor_type or template.actor_type, template_id=template_id, chain_summary=chain_summary, reason=reason, confidence=template.confidence, review_required=template.review_required, goes_to_main_sourcing_card=template.route in {ROUTE_MEDIA_SOURCE_RECORD, ROUTE_REVIEW}, goes_to_review_text=template.route in {ROUTE_REVIEW, ROUTE_CLAIM_SPAN_ONLY}, source_chain_gap=template.media_source_role == UNKNOWN or template.route == ROUTE_REVIEW, source_chain_depth=3 if template.media_source_role == TERTIARY else (2 if template.media_source_role == SECONDARY else (1 if template.media_source_role == PRIMARY else 0)), inferred_origin_actor_type=template.origin_role, named_intermediary_chain_role=template.intermediary_role, current_speaker_chain_role=template.current_speaker_role, unknown_media_requirement_met=template.route == ROUTE_MEDIA_SOURCE_RECORD, unknown_media_requirement_reason=extra_reason or template.definition, candidate_claim_basis="AGENCY_OR_OUTSIDE_RETELLING" if template.media_source_role == TERTIARY else ("WITNESS_ACCOUNT" if template.media_source_role == SECONDARY else "UNKNOWN_CLAIM_BASIS"))
def classify_media_source_chain_candidate(text: object, *, claim_span_role: object = "", current_source_name: object = "", attached_source_urls: Iterable[str] = (), candidate_hint: Mapping[str, Any] | None = None) -> SourceChainDecision:
    raw = _clean(text)
    if not raw: return _decision_from_template("ordinary_claim_span_only", raw=raw, extra_reason="empty text")
    if _is_self_owned_or_oral_memory_claim_span_only(raw):
        return _decision_from_template("ordinary_claim_span_only", raw=raw, extra_reason="self-owned/oral-memory statement, not a media-source provenance record")
    if re.search(r"\btold\s+metro\b", _norm(raw)):
        return _decision_from_template("origin_institution_told_speaker", raw=raw, actor="Metro", actor_type="news_or_media_intermediary", extra_reason="current source directly preserves told-Metro source relationship")
    if re.search(r"\([A-Z][A-Za-z .\'-]{1,80},\s*(?:19|20)\d{2}\)", raw) or re.search(r"\[(?:\d{1,3}|[A-Za-z][A-Za-z .\'-]{1,60}\s+(?:19|20)\d{2})\]", raw):
        return _decision_from_template("statistical_claim_no_named_source", raw=raw, extra_reason="citation/reference marker without attached source object")
    actor, actor_type = _extract_named_intermediary_told_speaker(raw)
    if actor:
        if _actor_is_probable_intermediary(actor_type) or actor_type in {"named_actor_uncertain", "organisation_uncertain"}: return _decision_from_template("named_intermediary_told_speaker", raw=raw, actor=actor, actor_type=actor_type, extra_reason=f"named intermediary attribution: {actor}")
        if _actor_is_probable_origin(actor_type): return _decision_from_template("origin_institution_told_speaker", raw=raw, actor=actor, actor_type=actor_type, extra_reason=f"origin institution attribution: {actor}")
    origin_actor, origin_type = _extract_origin_institution_attribution(raw)
    if origin_actor: return _decision_from_template("origin_institution_told_speaker", raw=raw, actor=origin_actor, actor_type=origin_type, extra_reason=f"direct origin/source-object attribution: {origin_actor}")
    lowered = _norm(raw)
    if re.search(r"\b(?:measured|figures\s+show|statistics\s+show|researchers\s+calculated|calculated|estimated|found\s+that|a\s+report\s+found|report\s+found|study\s+found|monitored|recorded|documented|quoted\s+as\s+saying|was\s+quoted\s+as\s+saying|quoted\s+.+?\s+as\s+saying|said\s+on\s+.+?\s+channel|said\s+in\s+.+?\s+video|posted|shared|messaged|wrote|polled|surveyed|polling\s+went|survey\s+found|according\s+to\s+officials)\b", lowered):
        return _decision_from_template("statistical_claim_no_named_source", raw=raw, extra_reason="source-bearing measurement/report/quote verb")
    measured, reason = _is_measured_or_statistical_claim(raw)
    if measured: return _decision_from_template("statistical_claim_no_named_source", raw=raw, extra_reason=reason)
    if _is_formal_quote_source(raw): return _decision_from_template("formal_quote_or_scripture", raw=raw, extra_reason="formal quote/source text wording")
    if _has_document_witness_but_only_reaction(raw): return _decision_from_template("ordinary_claim_span_only", raw=raw, extra_reason="document-witness action/reaction only; no separate source-provenance statement")
    if _ambiguous_review_trigger(raw): return _decision_from_template("ambiguous_possible_source_statement", raw=raw, extra_reason="ambiguous source-promotion trigger")
    return _decision_from_template("ordinary_claim_span_only", raw=raw)
def classify_embedded_article_media_provenance(*, article_source_role: object = "", media_url: object = "", media_uploader: object = "", media_duration_seconds: object = 0, original_duration_seconds: object = 0, explicit_original_wording: object = "", explicit_edited_wording: object = "") -> SourceChainDecision:
    original_text = _norm(explicit_original_wording); edited_text = _norm(explicit_edited_wording)
    try: duration = float(str(media_duration_seconds or 0))
    except Exception: duration = 0.0
    try: original_duration = float(str(original_duration_seconds or 0))
    except Exception: original_duration = 0.0
    if edited_text and re.search(r"\b(?:edited|clip|montage|excerpt|highlight|cut|trimmed|compilation)\b", edited_text): return _decision_from_template("embedded_article_media_original_provenance_unknown", raw=str(media_url or "embedded media"), extra_reason="edited/clip wording prevents Primary embedded-media role")
    if _norm(media_url) and _norm(media_uploader) and re.search(r"\b(?:original|full|unedited|official)\b", original_text) and (not original_duration or not duration or abs(original_duration - duration) <= 2.0): return _decision_from_template("direct_self_authored_media_statement", raw=str(media_url or "embedded media"), extra_reason="explicit original/full/official embedded-media provenance supplied")
    return _decision_from_template("embedded_article_media_original_provenance_unknown", raw=str(media_url or "embedded media"), extra_reason="embedded/reposted media original/edit status unresolved")
def definition_dataset_as_dict() -> dict[str, Any]:
    return {"schema_version": SCHEMA_VERSION, "source_roles": [PRIMARY, SECONDARY, TERTIARY, UNKNOWN], "routes": [ROUTE_MEDIA_SOURCE_RECORD, ROUTE_REVIEW, ROUTE_CLAIM_SPAN_ONLY], "templates": [template.to_dict() for template in SOURCE_CHAIN_TEMPLATES], "example_dataset": list(SOURCE_CHAIN_EXAMPLE_DATASET), "origin_institution_keywords": {k: list(v) for k, v in ORIGIN_INSTITUTION_KEYWORDS.items()}, "intermediary_actor_keywords": {k: list(v) for k, v in INTERMEDIARY_ACTOR_KEYWORDS.items()}, "source_object_keywords": {k: list(v) for k, v in SOURCE_OBJECT_KEYWORDS.items()}, "safety_flags": {"web_download_performed": False, "media_download_performed": False, "browser_launch_performed": False, "automatic_sensitive_identifier_inference_performed": False}}
# SOURCE_CHAIN_DEFINITION_SET_PASS6_20260827
