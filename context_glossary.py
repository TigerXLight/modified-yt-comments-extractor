from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Sequence


TERM_CATEGORY_PERSON = "person"
TERM_CATEGORY_PLACE = "place"
TERM_CATEGORY_ORGANIZATION = "organization"
TERM_CATEGORY_PRODUCT = "product"
TERM_CATEGORY_EVENT = "event"
TERM_CATEGORY_MEDIA_TITLE = "media_title"
TERM_CATEGORY_TECHNICAL = "technical"
TERM_CATEGORY_SOURCE_SPECIFIC = "source_specific"
TERM_CATEGORY_UNKNOWN = "unknown"

HINT_SOURCE_USER = "user"
HINT_SOURCE_SOURCE_URL = "source_url"
HINT_SOURCE_TITLE = "title"
HINT_SOURCE_TRANSCRIPT = "transcript"
HINT_SOURCE_COMMENTS = "comments"
HINT_SOURCE_MANUAL = "manual"
HINT_SOURCE_RESOLVER = "resolver"
HINT_SOURCE_UNKNOWN = "unknown"


@dataclass(frozen=True)
class ContextHint:
    value: str
    source: str = HINT_SOURCE_UNKNOWN
    label: str = ""
    confidence: float = 0.0
    notes: str = ""


@dataclass(frozen=True)
class GlossaryTerm:
    text: str
    aliases: tuple[str, ...] = ()
    category: str = TERM_CATEGORY_UNKNOWN
    source: str = HINT_SOURCE_UNKNOWN
    notes: str = ""
    case_sensitive: bool = False


@dataclass(frozen=True)
class TopicResolutionResult:
    source_label: str = ""
    source_url: str = ""
    context_hints: tuple[ContextHint, ...] = ()
    glossary_terms: tuple[GlossaryTerm, ...] = ()
    warnings: tuple[str, ...] = ()


def normalize_glossary_text(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").strip())


def glossary_key(value: str, case_sensitive: bool = False) -> str:
    normalized = normalize_glossary_text(value)
    if case_sensitive:
        return normalized
    return normalized.casefold()


def _normalized_aliases(aliases: Sequence[str]) -> tuple[str, ...]:
    normalized_aliases = []
    seen_aliases = set()
    for alias in aliases:
        normalized = normalize_glossary_text(alias)
        if not normalized:
            continue
        key = normalized.casefold()
        if key in seen_aliases:
            continue
        seen_aliases.add(key)
        normalized_aliases.append(normalized)
    return tuple(normalized_aliases)


def dedupe_glossary_terms(terms: Sequence[GlossaryTerm]) -> tuple[GlossaryTerm, ...]:
    deduped = []
    seen = set()
    for term in terms:
        text = normalize_glossary_text(term.text)
        if not text:
            continue
        key = glossary_key(text, term.case_sensitive)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(
            GlossaryTerm(
                text=text,
                aliases=_normalized_aliases(term.aliases),
                category=term.category,
                source=term.source,
                notes=term.notes,
                case_sensitive=term.case_sensitive,
            )
        )
    return tuple(deduped)


def glossary_terms_from_strings(
    values: Sequence[str],
    *,
    category: str = TERM_CATEGORY_UNKNOWN,
    source: str = HINT_SOURCE_USER,
) -> tuple[GlossaryTerm, ...]:
    terms = [
        GlossaryTerm(
            text=normalize_glossary_text(value),
            category=category,
            source=source,
        )
        for value in values
    ]
    return dedupe_glossary_terms(terms)


def phrase_prompt_terms(
    terms: Sequence[GlossaryTerm],
    *,
    include_aliases: bool = True,
    max_terms: int = 80,
) -> tuple[str, ...]:
    if max_terms <= 0:
        return ()

    prompt_terms = []
    seen = set()
    for term in dedupe_glossary_terms(terms):
        values = [term.text]
        if include_aliases:
            values.extend(term.aliases)

        for value in values:
            normalized = normalize_glossary_text(value)
            if not normalized:
                continue
            key = glossary_key(normalized, term.case_sensitive)
            if key in seen:
                continue
            seen.add(key)
            prompt_terms.append(normalized)
            if len(prompt_terms) >= max_terms:
                return tuple(prompt_terms)
    return tuple(prompt_terms)


def resolve_context_hints(
    *,
    source_label: str = "",
    source_url: str = "",
    title: str = "",
    user_terms: Sequence[str] = (),
) -> TopicResolutionResult:
    normalized_source_label = normalize_glossary_text(source_label)
    normalized_source_url = normalize_glossary_text(source_url)
    normalized_title = normalize_glossary_text(title)

    hints = []
    if normalized_source_label:
        hints.append(
            ContextHint(
                value=normalized_source_label,
                source=HINT_SOURCE_MANUAL,
                label="source_label",
            )
        )
    if normalized_source_url:
        hints.append(
            ContextHint(
                value=normalized_source_url,
                source=HINT_SOURCE_SOURCE_URL,
                label="source_url",
            )
        )
    if normalized_title:
        hints.append(
            ContextHint(
                value=normalized_title,
                source=HINT_SOURCE_TITLE,
                label="title",
            )
        )

    return TopicResolutionResult(
        source_label=normalized_source_label,
        source_url=normalized_source_url,
        context_hints=tuple(hints),
        glossary_terms=glossary_terms_from_strings(user_terms),
    )
