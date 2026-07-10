import json
from pathlib import Path

from asr_comparison_report import (
    ASR_STATUS_BLOCKED,
    build_asr_comparison_records_from_dicts,
)
from asr_term_coverage_summary import (
    asr_term_coverage_item_to_dict,
    asr_term_coverage_summary_to_dict,
    build_asr_term_coverage_summary,
    build_asr_term_coverage_summary_markdown,
    build_asr_term_coverage_summary_text,
)


ROOT = Path(__file__).resolve().parent
SEED_JSON = ROOT / "ASR_MANUAL_RESULTS_SEED.json"


def _load_records():
    with SEED_JSON.open("r", encoding="utf-8") as handle:
        seed = json.load(handle)
    return build_asr_comparison_records_from_dicts(seed["records"])


def _item_by_term(result):
    return {item.term: item for item in result.items}


def run_self_test() -> None:
    records = _load_records()
    result = build_asr_term_coverage_summary(records)
    by_term = _item_by_term(result)

    assert result.record_count == len(records)
    assert result.project_scored_count == 11
    assert result.blocked_count == 1
    assert result.external_lead_count == 13
    assert result.tracked_term_count == 7
    assert result.known_phrase_attempt_count == 11
    assert result.known_phrase_hit_count == 1
    assert result.known_phrase_miss_count == 10

    assert "Kingman" in result.consistently_missed_terms
    assert "ZoneX" in result.consistently_missed_terms
    assert "Freckelston" in result.consistently_missed_terms
    assert "Nyxara" in result.consistently_missed_terms
    assert "Nicolas Cage" in result.mixed_terms
    assert "Shadowsmith" in result.mixed_terms
    assert "Caltheris" in result.mixed_terms
    assert result.consistently_hit_terms == ()

    kingman = by_term["Kingman"]
    assert kingman.project_scored_attempt_count == 10
    assert kingman.hit_count == 0
    assert kingman.miss_count == 10
    assert kingman.hit_rate_percent == 0.0
    assert any("ElevenLabs" in label for label in kingman.missed_labels)

    nicolas = by_term["Nicolas Cage"]
    assert nicolas.project_scored_attempt_count == 11
    assert nicolas.hit_count == 9
    assert nicolas.miss_count == 2
    assert nicolas.hit_rate_percent == 81.82
    assert any("Google Speech-to-Text / v1 video" in label for label in nicolas.missed_labels)
    assert any("ElevenLabs / Scribe v2" in label for label in nicolas.hit_labels)

    caltheris = by_term["Caltheris"]
    assert caltheris.project_scored_attempt_count == 10
    assert caltheris.hit_count == 4
    assert caltheris.miss_count == 6
    assert caltheris.hit_rate_percent == 40.0
    assert any("AssemblyAI / Universal-3.5 Pro default" in label for label in caltheris.missed_labels)

    assert any("ElevenLabs / Scribe v2 with keyterms: missed Kingman" == label for label in result.provider_gap_labels)
    assert any("whisper.cpp" in label and "missed ZoneX" in label for label in result.provider_gap_labels)
    assert all("AWS Transcribe" not in label for label in result.provider_gap_labels)

    blocked_records = [record for record in records if record.status == ASR_STATUS_BLOCKED]
    assert blocked_records
    assert blocked_records[0].provider == "AWS Transcribe"

    item_dict = asr_term_coverage_item_to_dict(nicolas)
    assert list(item_dict) == [
        "hit_count",
        "hit_labels",
        "hit_rate_percent",
        "miss_count",
        "missed_labels",
        "project_scored_attempt_count",
        "term",
    ]

    result_dict = asr_term_coverage_summary_to_dict(result)
    assert list(result_dict) == [
        "blocked_count",
        "consistently_hit_terms",
        "consistently_missed_terms",
        "errors",
        "external_lead_count",
        "items",
        "known_phrase_attempt_count",
        "known_phrase_hit_count",
        "known_phrase_miss_count",
        "mixed_terms",
        "project_scored_count",
        "provider_gap_labels",
        "record_count",
        "tracked_term_count",
        "warnings",
    ]
    assert result_dict == asr_term_coverage_summary_to_dict(
        build_asr_term_coverage_summary(records)
    )

    text = build_asr_term_coverage_summary_text(result)
    assert "ASR term coverage / gap summary" in text
    assert "Tracked term count: 7" in text
    assert "Blocked rows excluded from term rates: 1" in text
    assert "Known phrase hits: 1" in text
    assert "Kingman: hits=0; misses=10" in text
    assert "ElevenLabs / Scribe v2 with keyterms: missed Kingman" in text
    assert "ASR output remains draft" in text

    markdown = build_asr_term_coverage_summary_markdown(result)
    assert "# ASR Term Coverage / Gap Summary" in markdown
    assert "| Term | Attempts | Hits | Misses | Hit rate | Missed by |" in markdown
    assert "No provider calls" not in markdown
    assert "does not call providers" in markdown
    assert "Blocked rows excluded from term rates: 1" in markdown
    assert "External/user-observation leads excluded" in markdown
    assert "Term QA" in markdown


if __name__ == "__main__":
    run_self_test()
    print("ASR term coverage summary self-test passed.")
