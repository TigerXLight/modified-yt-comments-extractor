from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional, Sequence


ASR_ENGINE_LOCAL = "local"
ASR_ENGINE_CLOUD = "cloud"
ASR_ENGINE_OFFLINE = "offline"
ASR_ENGINE_BROWSER = "browser"
ASR_ENGINE_UNKNOWN = "unknown"

ASR_RESULT_SOURCE_LOCAL_TEST = "local_test"
ASR_RESULT_SOURCE_EXTERNAL_LEADERBOARD = "external_leaderboard"
ASR_RESULT_SOURCE_USER_OBSERVATION = "user_observation"
ASR_RESULT_SOURCE_MANUAL = "manual"
ASR_RESULT_SOURCE_UNKNOWN = "unknown"

ASR_STATUS_ACCEPTED = "accepted"
ASR_STATUS_REJECTED = "rejected"
ASR_STATUS_BLOCKED = "blocked"
ASR_STATUS_CANDIDATE = "candidate"
ASR_STATUS_NEEDS_REVIEW = "needs_review"
ASR_STATUS_UNKNOWN = "unknown"

PROJECT_REFERENCE_PHRASE = "Oh, I've completed the Nicolas Cage event."


@dataclass(frozen=True)
class ASRComparisonRecord:
    provider: str
    model: str = ""
    engine_type: str = ASR_ENGINE_UNKNOWN
    source: str = ASR_RESULT_SOURCE_UNKNOWN
    clip_name: str = ""
    duration_seconds: Optional[float] = None
    raw_wer_percent: Optional[float] = None
    formatted_wer_percent: Optional[float] = None
    reference_accuracy_percent: Optional[float] = None
    cost_per_hour_usd: Optional[float] = None
    latency_seconds: Optional[float] = None
    key_terms_expected: tuple[str, ...] = ()
    key_terms_hit: tuple[str, ...] = ()
    key_terms_missed: tuple[str, ...] = ()
    known_phrase_expected: str = PROJECT_REFERENCE_PHRASE
    known_phrase_hit: Optional[bool] = None
    status: str = ASR_STATUS_NEEDS_REVIEW
    notes: str = ""

    @property
    def keyterm_hit_count(self) -> int:
        return len(self.key_terms_hit)

    @property
    def keyterm_miss_count(self) -> int:
        return len(self.key_terms_missed)

    @property
    def keyterm_hit_rate_percent(self) -> Optional[float]:
        expected_count = len(self.key_terms_expected)
        if expected_count == 0:
            return None
        return round((self.keyterm_hit_count / expected_count) * 100.0, 2)

    @property
    def has_local_reference_evidence(self) -> bool:
        return (
            self.reference_accuracy_percent is not None
            and self.source in {ASR_RESULT_SOURCE_LOCAL_TEST, ASR_RESULT_SOURCE_MANUAL}
        )


def default_asr_key_terms() -> tuple[str, ...]:
    return (
        "Kingman",
        "ZoneX",
        "Shadowsmith",
        "Nicolas Cage",
        "Freckelston",
        "Caltheris",
        "Nyxara",
    )


def _clean_string(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _optional_float(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _optional_bool(value: Any) -> Optional[bool]:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return value
    normalized = str(value).strip().casefold()
    if normalized in {"1", "true", "yes", "y", "hit", "found"}:
        return True
    if normalized in {"0", "false", "no", "n", "miss", "missing"}:
        return False
    return None


def _string_tuple(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        values = value.split(",")
    else:
        try:
            values = list(value)
        except TypeError:
            values = [value]
    return tuple(item for item in (_clean_string(raw) for raw in values) if item)


def _record_from_dict(row: dict[str, Any]) -> ASRComparisonRecord:
    return ASRComparisonRecord(
        provider=_clean_string(row.get("provider")),
        model=_clean_string(row.get("model")),
        engine_type=_clean_string(row.get("engine_type")) or ASR_ENGINE_UNKNOWN,
        source=_clean_string(row.get("source")) or ASR_RESULT_SOURCE_UNKNOWN,
        clip_name=_clean_string(row.get("clip_name")),
        duration_seconds=_optional_float(row.get("duration_seconds")),
        raw_wer_percent=_optional_float(row.get("raw_wer_percent")),
        formatted_wer_percent=_optional_float(row.get("formatted_wer_percent")),
        reference_accuracy_percent=_optional_float(row.get("reference_accuracy_percent")),
        cost_per_hour_usd=_optional_float(row.get("cost_per_hour_usd")),
        latency_seconds=_optional_float(row.get("latency_seconds")),
        key_terms_expected=_string_tuple(
            row.get("key_terms_expected") or default_asr_key_terms()
        ),
        key_terms_hit=_string_tuple(row.get("key_terms_hit")),
        key_terms_missed=_string_tuple(row.get("key_terms_missed")),
        known_phrase_expected=(
            _clean_string(row.get("known_phrase_expected")) or PROJECT_REFERENCE_PHRASE
        ),
        known_phrase_hit=_optional_bool(row.get("known_phrase_hit")),
        status=_clean_string(row.get("status")) or ASR_STATUS_NEEDS_REVIEW,
        notes=_clean_string(row.get("notes")),
    )


def build_asr_comparison_records_from_dicts(
    rows: Sequence[dict[str, Any]],
) -> tuple[ASRComparisonRecord, ...]:
    return tuple(_record_from_dict(row) for row in rows)


def asr_comparison_record_to_dict(record: ASRComparisonRecord) -> dict[str, object]:
    return {
        "clip_name": record.clip_name,
        "cost_per_hour_usd": record.cost_per_hour_usd,
        "duration_seconds": record.duration_seconds,
        "engine_type": record.engine_type,
        "formatted_wer_percent": record.formatted_wer_percent,
        "has_local_reference_evidence": record.has_local_reference_evidence,
        "key_terms_expected": list(record.key_terms_expected),
        "key_terms_hit": list(record.key_terms_hit),
        "key_terms_missed": list(record.key_terms_missed),
        "keyterm_hit_count": record.keyterm_hit_count,
        "keyterm_hit_rate_percent": record.keyterm_hit_rate_percent,
        "keyterm_miss_count": record.keyterm_miss_count,
        "known_phrase_expected": record.known_phrase_expected,
        "known_phrase_hit": record.known_phrase_hit,
        "latency_seconds": record.latency_seconds,
        "model": record.model,
        "notes": record.notes,
        "provider": record.provider,
        "raw_wer_percent": record.raw_wer_percent,
        "reference_accuracy_percent": record.reference_accuracy_percent,
        "source": record.source,
        "status": record.status,
    }


def asr_comparison_records_to_dict(
    records: Sequence[ASRComparisonRecord],
) -> dict[str, object]:
    return {
        "known_reference_phrase": PROJECT_REFERENCE_PHRASE,
        "project_key_terms": list(default_asr_key_terms()),
        "records": [
            asr_comparison_record_to_dict(record)
            for record in records
        ],
        "record_count": len(records),
    }


def _metric_value(record: ASRComparisonRecord, metric: str) -> Optional[float]:
    value = getattr(record, metric, None)
    if isinstance(value, (int, float)):
        return float(value)
    return None


def rank_asr_records(
    records: Sequence[ASRComparisonRecord],
    metric: str = "reference_accuracy_percent",
) -> tuple[ASRComparisonRecord, ...]:
    lower_is_better = metric in {"raw_wer_percent", "formatted_wer_percent"}

    def sort_key(record: ASRComparisonRecord) -> tuple[object, ...]:
        value = _metric_value(record, metric)
        missing = value is None
        comparable = 0.0 if value is None else value
        if not lower_is_better:
            comparable = -comparable
        return (
            missing,
            comparable,
            record.provider.casefold(),
            record.model.casefold(),
            record.source.casefold(),
        )

    return tuple(sorted(records, key=sort_key))


def _format_percent(value: Optional[float]) -> str:
    return "(unknown)" if value is None else f"{value:.2f}%"


def _format_optional_number(value: Optional[float], suffix: str = "") -> str:
    return "(unknown)" if value is None else f"{value:g}{suffix}"


def _yes_no_unknown(value: Optional[bool]) -> str:
    if value is True:
        return "yes"
    if value is False:
        return "no"
    return "unknown"


def build_asr_comparison_text(records: Sequence[ASRComparisonRecord]) -> str:
    ranked = rank_asr_records(records)
    lines = [
        "ASR comparison report",
        "Scope: local/manual reporting only; no provider calls or transcription are performed.",
        f"Record count: {len(records)}",
        "Ranked by project reference accuracy:",
    ]
    if not ranked:
        lines.append("- (none)")
    for record in ranked:
        lines.append(
            f"- {record.provider} / {record.model or '(model unknown)'} "
            f"[status={record.status}; source={record.source}; "
            f"reference_accuracy={_format_percent(record.reference_accuracy_percent)}; "
            f"raw_wer={_format_percent(record.raw_wer_percent)}; "
            f"formatted_wer={_format_percent(record.formatted_wer_percent)}; "
            f"keyterms={record.keyterm_hit_count}/{len(record.key_terms_expected)}; "
            f"known_phrase={_yes_no_unknown(record.known_phrase_hit)}]"
        )
        if record.key_terms_missed:
            lines.append(f"  Missed terms: {', '.join(record.key_terms_missed)}")
        if record.notes:
            lines.append(f"  Notes: {record.notes}")
    lines.extend(
        [
            "Caution:",
            "- External leaderboard records may lack local reference accuracy and should not override project-specific strict scoring.",
            "- ASR output remains draft unless quality gates and Term QA/glossary review pass.",
        ]
    )
    return "\n".join(lines)


def build_asr_comparison_markdown(records: Sequence[ASRComparisonRecord]) -> str:
    ranked = rank_asr_records(records)
    lines = [
        "# ASR Comparison Report",
        "",
        "Local/manual reporting only. This report format does not call providers or run transcription.",
        "",
        "| Provider | Model | Status | Source | Reference accuracy | Raw WER | Formatted WER | Keyterms | Known phrase | Cost/hr | Latency |",
        "| --- | --- | --- | --- | ---: | ---: | ---: | ---: | --- | ---: | ---: |",
    ]
    for record in ranked:
        keyterm_total = len(record.key_terms_expected)
        lines.append(
            "| "
            + " | ".join(
                [
                    record.provider or "(unknown)",
                    record.model or "(unknown)",
                    record.status,
                    record.source,
                    _format_percent(record.reference_accuracy_percent),
                    _format_percent(record.raw_wer_percent),
                    _format_percent(record.formatted_wer_percent),
                    f"{record.keyterm_hit_count}/{keyterm_total}",
                    _yes_no_unknown(record.known_phrase_hit),
                    _format_optional_number(record.cost_per_hour_usd, ""),
                    _format_optional_number(record.latency_seconds, "s"),
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Notes",
            "",
            "- External leaderboard records are research leads unless separately scored on project reference clips.",
            "- Track missed terms explicitly because plain WER can hide proper-noun failures.",
            "- ASR output remains draft unless strict quality gates and Term QA/glossary review pass.",
        ]
    )
    return "\n".join(lines)
