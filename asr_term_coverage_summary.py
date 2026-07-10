from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from asr_comparison_report import (
    ASR_RESULT_SOURCE_EXTERNAL_LEADERBOARD,
    ASR_RESULT_SOURCE_USER_OBSERVATION,
    ASR_STATUS_BLOCKED,
    ASRComparisonRecord,
)


EXTERNAL_LEAD_SOURCES = (
    ASR_RESULT_SOURCE_EXTERNAL_LEADERBOARD,
    ASR_RESULT_SOURCE_USER_OBSERVATION,
)


@dataclass(frozen=True)
class ASRTermCoverageItem:
    term: str
    project_scored_attempt_count: int = 0
    hit_count: int = 0
    miss_count: int = 0
    hit_rate_percent: float | None = None
    hit_labels: tuple[str, ...] = ()
    missed_labels: tuple[str, ...] = ()


@dataclass(frozen=True)
class ASRTermCoverageSummaryResult:
    record_count: int = 0
    project_scored_count: int = 0
    external_lead_count: int = 0
    blocked_count: int = 0
    tracked_term_count: int = 0
    consistently_hit_terms: tuple[str, ...] = ()
    consistently_missed_terms: tuple[str, ...] = ()
    mixed_terms: tuple[str, ...] = ()
    provider_gap_labels: tuple[str, ...] = ()
    known_phrase_attempt_count: int = 0
    known_phrase_hit_count: int = 0
    known_phrase_miss_count: int = 0
    items: tuple[ASRTermCoverageItem, ...] = ()
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()


def _label(record: ASRComparisonRecord) -> str:
    provider = record.provider or "(unknown provider)"
    return f"{provider} / {record.model}" if record.model else provider


def _percent(hit_count: int, total_count: int) -> float | None:
    if total_count <= 0:
        return None
    return round((hit_count / total_count) * 100.0, 2)


def _term_order(records: Sequence[ASRComparisonRecord]) -> tuple[str, ...]:
    terms: list[str] = []
    for record in records:
        for term in (*record.key_terms_expected, *record.key_terms_hit, *record.key_terms_missed):
            cleaned = str(term or "").strip()
            if cleaned and cleaned not in terms:
                terms.append(cleaned)
    return tuple(terms)


def _append_unique(values: list[str], value: str) -> None:
    cleaned = str(value or "").strip()
    if cleaned and cleaned not in values:
        values.append(cleaned)


def build_asr_term_coverage_summary(
    records: Sequence[ASRComparisonRecord],
) -> ASRTermCoverageSummaryResult:
    record_tuple = tuple(records)
    project_scored = tuple(
        record
        for record in record_tuple
        if record.has_local_reference_evidence and record.status != ASR_STATUS_BLOCKED
    )
    blocked = tuple(record for record in record_tuple if record.status == ASR_STATUS_BLOCKED)
    external_leads = tuple(record for record in record_tuple if record.source in EXTERNAL_LEAD_SOURCES)

    terms = _term_order(project_scored)
    items: list[ASRTermCoverageItem] = []
    consistently_hit_terms: list[str] = []
    consistently_missed_terms: list[str] = []
    mixed_terms: list[str] = []
    provider_gap_labels: list[str] = []
    errors: list[str] = []

    for term in terms:
        hit_labels: list[str] = []
        missed_labels: list[str] = []
        for record in project_scored:
            in_hit = term in record.key_terms_hit
            in_missed = term in record.key_terms_missed
            label = _label(record)
            if in_hit:
                _append_unique(hit_labels, label)
            if in_missed:
                _append_unique(missed_labels, label)
                _append_unique(provider_gap_labels, f"{label}: missed {term}")
            if in_hit and in_missed:
                errors.append(f"{label} lists {term!r} as both hit and missed.")
        attempt_count = len(hit_labels) + len(missed_labels)
        hit_count = len(hit_labels)
        miss_count = len(missed_labels)
        item = ASRTermCoverageItem(
            term=term,
            project_scored_attempt_count=attempt_count,
            hit_count=hit_count,
            miss_count=miss_count,
            hit_rate_percent=_percent(hit_count, attempt_count),
            hit_labels=tuple(hit_labels),
            missed_labels=tuple(missed_labels),
        )
        items.append(item)
        if attempt_count == 0:
            continue
        if hit_count and not miss_count:
            consistently_hit_terms.append(term)
        elif miss_count and not hit_count:
            consistently_missed_terms.append(term)
        else:
            mixed_terms.append(term)

    known_phrase_attempts = tuple(
        record for record in project_scored if record.known_phrase_hit is not None
    )
    known_phrase_hit_count = sum(record.known_phrase_hit is True for record in known_phrase_attempts)
    known_phrase_miss_count = sum(record.known_phrase_hit is False for record in known_phrase_attempts)

    aggregate_only = tuple(
        record
        for record in project_scored
        if not record.key_terms_hit and not record.key_terms_missed
        and (record.keyterm_hit_count or record.keyterm_miss_count)
    )

    warnings: list[str] = [
        "Term coverage is based only on manually entered comparison records.",
        "Blocked providers are excluded from project-scored term coverage rates.",
        "External leaderboard and user-observation leads do not override project-specific Term QA.",
        "ASR output remains draft until strict scoring, glossary checks, and user review pass.",
    ]
    if aggregate_only:
        warnings.append(
            "Some project-scored records expose aggregate keyterm counts without term names and are not used for per-term hit/miss tables."
        )
    if not items:
        warnings.append("No explicit project-scored key-term hit/miss records were supplied.")

    return ASRTermCoverageSummaryResult(
        record_count=len(record_tuple),
        project_scored_count=len(project_scored),
        external_lead_count=len(external_leads),
        blocked_count=len(blocked),
        tracked_term_count=len(items),
        consistently_hit_terms=tuple(consistently_hit_terms),
        consistently_missed_terms=tuple(consistently_missed_terms),
        mixed_terms=tuple(mixed_terms),
        provider_gap_labels=tuple(provider_gap_labels),
        known_phrase_attempt_count=len(known_phrase_attempts),
        known_phrase_hit_count=known_phrase_hit_count,
        known_phrase_miss_count=known_phrase_miss_count,
        items=tuple(items),
        warnings=tuple(warnings),
        errors=tuple(errors),
    )


def asr_term_coverage_item_to_dict(item: ASRTermCoverageItem) -> dict[str, object]:
    return {
        "hit_count": item.hit_count,
        "hit_labels": list(item.hit_labels),
        "hit_rate_percent": item.hit_rate_percent,
        "miss_count": item.miss_count,
        "missed_labels": list(item.missed_labels),
        "project_scored_attempt_count": item.project_scored_attempt_count,
        "term": item.term,
    }


def asr_term_coverage_summary_to_dict(
    result: ASRTermCoverageSummaryResult,
) -> dict[str, object]:
    return {
        "blocked_count": result.blocked_count,
        "consistently_hit_terms": list(result.consistently_hit_terms),
        "consistently_missed_terms": list(result.consistently_missed_terms),
        "errors": list(result.errors),
        "external_lead_count": result.external_lead_count,
        "items": [asr_term_coverage_item_to_dict(item) for item in result.items],
        "known_phrase_attempt_count": result.known_phrase_attempt_count,
        "known_phrase_hit_count": result.known_phrase_hit_count,
        "known_phrase_miss_count": result.known_phrase_miss_count,
        "mixed_terms": list(result.mixed_terms),
        "project_scored_count": result.project_scored_count,
        "provider_gap_labels": list(result.provider_gap_labels),
        "record_count": result.record_count,
        "tracked_term_count": result.tracked_term_count,
        "warnings": list(result.warnings),
    }


def _format_percent(value: float | None) -> str:
    return "(none)" if value is None else f"{value:.2f}%"


def _list_text(values: Sequence[str]) -> str:
    return ", ".join(values) if values else "(none)"


def _list_lines(values: Sequence[str]) -> list[str]:
    return [f"- {value}" for value in values] if values else ["- (none)"]


def build_asr_term_coverage_summary_text(result: ASRTermCoverageSummaryResult) -> str:
    lines = [
        "ASR term coverage / gap summary",
        "Scope: local/manual comparison records only; no provider calls or transcription are performed.",
        f"Record count: {result.record_count}",
        f"Project-scored count: {result.project_scored_count}",
        f"Tracked term count: {result.tracked_term_count}",
        f"Blocked rows excluded from term rates: {result.blocked_count}",
        f"External/user-observation leads excluded from project term rates: {result.external_lead_count}",
        f"Known phrase attempts: {result.known_phrase_attempt_count}",
        f"Known phrase hits: {result.known_phrase_hit_count}",
        f"Known phrase misses: {result.known_phrase_miss_count}",
        f"Consistently hit terms: {_list_text(result.consistently_hit_terms)}",
        f"Consistently missed terms: {_list_text(result.consistently_missed_terms)}",
        f"Mixed terms: {_list_text(result.mixed_terms)}",
        "Per-term coverage:",
    ]
    if not result.items:
        lines.append("- (none)")
    for item in result.items:
        lines.append(
            f"- {item.term}: hits={item.hit_count}; misses={item.miss_count}; "
            f"attempts={item.project_scored_attempt_count}; hit_rate={_format_percent(item.hit_rate_percent)}"
        )
        if item.missed_labels:
            lines.append(f"  Missed by: {_list_text(item.missed_labels)}")
    lines.extend(
        [
            "Provider/model gaps:",
            *_list_lines(result.provider_gap_labels),
            "Warnings:",
            *_list_lines(result.warnings),
            "Errors:",
            *_list_lines(result.errors),
        ]
    )
    return "\n".join(lines)


def _markdown_cell(values: Sequence[str]) -> str:
    return (_list_text(values)).replace("|", "\\|").replace("\n", " ")


def build_asr_term_coverage_summary_markdown(
    result: ASRTermCoverageSummaryResult,
) -> str:
    lines = [
        "# ASR Term Coverage / Gap Summary",
        "",
        "Local/manual comparison records only. This report does not call providers, run transcription, download/fetch media, use network APIs, store credentials, inspect ZIPs, or wire into the GUI.",
        "",
        "## Counts",
        "",
        f"- Record count: {result.record_count}",
        f"- Project-scored count: {result.project_scored_count}",
        f"- Tracked term count: {result.tracked_term_count}",
        f"- Blocked rows excluded from term rates: {result.blocked_count}",
        f"- External/user-observation leads excluded from project term rates: {result.external_lead_count}",
        f"- Known phrase attempts: {result.known_phrase_attempt_count}",
        f"- Known phrase hits: {result.known_phrase_hit_count}",
        f"- Known phrase misses: {result.known_phrase_miss_count}",
        "",
        "## Term Groups",
        "",
        f"- Consistently hit terms: {_markdown_cell(result.consistently_hit_terms)}",
        f"- Consistently missed terms: {_markdown_cell(result.consistently_missed_terms)}",
        f"- Mixed terms: {_markdown_cell(result.mixed_terms)}",
        "",
        "## Per-Term Coverage",
        "",
        "| Term | Attempts | Hits | Misses | Hit rate | Missed by |",
        "| --- | ---: | ---: | ---: | ---: | --- |",
    ]
    for item in result.items:
        lines.append(
            "| "
            + " | ".join(
                [
                    item.term.replace("|", "\\|"),
                    str(item.project_scored_attempt_count),
                    str(item.hit_count),
                    str(item.miss_count),
                    _format_percent(item.hit_rate_percent),
                    _markdown_cell(item.missed_labels),
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Provider / Model Gaps",
            "",
            *_list_lines(result.provider_gap_labels),
            "",
            "## Safety Notes",
            "",
            *_list_lines(result.warnings),
        ]
    )
    if result.errors:
        lines.extend(["", "## Errors", "", *_list_lines(result.errors)])
    return "\n".join(lines)
