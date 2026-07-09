import json
from pathlib import Path

from asr_comparison_report import (
    ASR_RESULT_SOURCE_EXTERNAL_LEADERBOARD,
    ASR_RESULT_SOURCE_LOCAL_TEST,
    ASR_RESULT_SOURCE_USER_OBSERVATION,
    ASR_STATUS_BLOCKED,
    ASR_STATUS_CANDIDATE,
    ASR_STATUS_REJECTED,
    build_asr_comparison_records_from_dicts,
    build_asr_comparison_text,
    default_asr_key_terms,
    rank_asr_records,
)


ROOT = Path(__file__).resolve().parent
SEED_JSON = ROOT / "ASR_MANUAL_RESULTS_SEED.json"
SEED_MD = ROOT / "ASR_MANUAL_RESULTS_SEED.md"


def _load_seed():
    with SEED_JSON.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _records_by_id(rows):
    return {row["record_id"]: row for row in rows}


def _records_by_provider(records):
    by_provider = {}
    for record in records:
        by_provider.setdefault(record.provider, []).append(record)
    return by_provider


def _assert_record_exists_for_provider(records, provider, *, model_contains=""):
    for record in records:
        if record.provider == provider and model_contains.casefold() in record.model.casefold():
            return record
    raise AssertionError(f"Missing record for {provider!r} containing {model_contains!r}")


def run_self_test() -> None:
    seed = _load_seed()
    assert set(seed) == {"metadata", "records"}

    metadata = seed["metadata"]
    assert metadata["schema"] == "asr_comparison_report.manual_seed.v1"
    assert metadata["name"] == "ASR manual results seed"
    assert "No provider calls" in metadata["warning"]
    assert tuple(metadata["project_key_terms"]) == default_asr_key_terms()

    rows = seed["records"]
    assert isinstance(rows, list)
    assert len(rows) >= 20
    assert len({row["record_id"] for row in rows}) == len(rows)

    by_id = _records_by_id(rows)
    records = build_asr_comparison_records_from_dicts(rows)
    by_provider = _records_by_provider(records)
    assert len(records) == len(rows)

    elevenlabs = by_id["project_elevenlabs_scribe_v2_keyterms"]
    assert elevenlabs["provider"] == "ElevenLabs"
    assert elevenlabs["reference_accuracy_percent"] == 84.95
    assert elevenlabs["status"] == ASR_STATUS_CANDIDATE
    assert elevenlabs["key_terms_missed"] == [
        "Kingman",
        "ZoneX",
        "Freckelston",
        "Nyxara",
    ]
    elevenlabs_record = _assert_record_exists_for_provider(records, "ElevenLabs", model_contains="Scribe v2")
    assert elevenlabs_record.known_phrase_hit is True
    assert elevenlabs_record.has_local_reference_evidence is True

    whisper = by_id["project_whispercpp_vulkan_large_v3_turbo_phrase_prompt"]
    assert whisper["provider"] == "whisper.cpp"
    assert whisper["reference_accuracy_percent"] == 74.19
    assert "no-cloud/free local fallback" in whisper["notes"]
    whisper_record = _assert_record_exists_for_provider(records, "whisper.cpp", model_contains="Vulkan")
    assert whisper_record.source == ASR_RESULT_SOURCE_LOCAL_TEST
    assert whisper_record.has_local_reference_evidence is True

    aws = by_id["project_aws_transcribe_custom_vocabulary_blocked"]
    assert aws["provider"] == "AWS Transcribe"
    assert aws["status"] == ASR_STATUS_BLOCKED
    assert "SubscriptionRequiredException" in aws["notes"]
    assert _assert_record_exists_for_provider(records, "AWS Transcribe").reference_accuracy_percent is None

    for provider, model_text in (
        ("AssemblyAI", "default"),
        ("Deepgram", "Nova-3"),
        ("Speechmatics", "custom dictionary"),
        ("Azure Speech SDK", "en-US"),
        ("Google Speech-to-Text", "video"),
        ("Cohere", "cohere-transcribe"),
        ("Google Speech-to-Text", "latest_long"),
    ):
        record = _assert_record_exists_for_provider(records, provider, model_contains=model_text)
        assert record.status == ASR_STATUS_REJECTED
        assert record.reference_accuracy_percent is not None
        assert record.reference_accuracy_percent < 84.95

    assert len(by_provider["AssemblyAI"]) == 2
    assert len(by_provider["Azure Speech SDK"]) == 2

    external_records = [
        record for record in records
        if record.source == ASR_RESULT_SOURCE_EXTERNAL_LEADERBOARD
    ]
    assert external_records
    for record in external_records:
        assert record.reference_accuracy_percent is None
        assert record.status != "accepted"
        assert record.has_local_reference_evidence is False

    gpt4o_overall = by_id["external_voicewriter_gpt4o_overall"]
    assert gpt4o_overall["provider"] == "GPT-4o Transcribe"
    assert gpt4o_overall["raw_wer_percent"] == 5.4
    assert gpt4o_overall["formatted_wer_percent"] == 12.2
    assert gpt4o_overall["source"] == ASR_RESULT_SOURCE_EXTERNAL_LEADERBOARD

    gemini_accented = by_id["external_voicewriter_gemini_2_5_pro_accented"]
    assert gemini_accented["provider"] == "Gemini 2.5 Pro"
    assert gemini_accented["raw_wer_percent"] == 4.0
    assert gemini_accented["formatted_wer_percent"] == 12.4

    meta_lead = by_id["lead_meta_seamless_instagram_adjacent"]
    assert meta_lead["source"] == ASR_RESULT_SOURCE_USER_OBSERVATION
    assert meta_lead["status"] == ASR_STATUS_CANDIDATE
    assert "Instagram" in meta_lead["notes"]
    assert "seamless.metademolab.com" in meta_lead["notes"]

    villflow = by_id["lead_groq_villflowstt"]
    assert villflow["source"] == ASR_RESULT_SOURCE_USER_OBSERVATION
    assert villflow["status"] == ASR_STATUS_CANDIDATE
    assert "Groq" in villflow["provider"]
    assert "VillFlowSTT" in villflow["notes"]

    md_text = SEED_MD.read_text(encoding="utf-8")
    assert "does not call ASR providers" in md_text
    assert "ASR output remains draft text" in md_text

    ranked = rank_asr_records(records)
    assert ranked[0].provider == "ElevenLabs"
    assert ranked[1].provider == "whisper.cpp"

    report_text = build_asr_comparison_text(records)
    assert "ASR comparison report" in report_text
    assert "ElevenLabs / Scribe v2 with keyterms" in report_text
    assert "GPT-4o Transcribe" in report_text
    assert "External leaderboard records" in report_text


if __name__ == "__main__":
    run_self_test()
    print("ASR manual results seed self-test passed.")
