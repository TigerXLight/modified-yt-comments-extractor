from asr_comparison_report import (
    ASR_ENGINE_CLOUD,
    ASR_ENGINE_LOCAL,
    ASR_RESULT_SOURCE_EXTERNAL_LEADERBOARD,
    ASR_RESULT_SOURCE_LOCAL_TEST,
    ASR_STATUS_BLOCKED,
    ASR_STATUS_CANDIDATE,
    ASR_STATUS_NEEDS_REVIEW,
    default_asr_key_terms,
    build_asr_comparison_markdown,
    build_asr_comparison_records_from_dicts,
    build_asr_comparison_text,
    asr_comparison_record_to_dict,
    asr_comparison_records_to_dict,
    rank_asr_records,
)


def _sample_records():
    return build_asr_comparison_records_from_dicts(
        [
            {
                "provider": "ElevenLabs",
                "model": "Scribe v2 keyterms",
                "engine_type": ASR_ENGINE_CLOUD,
                "source": ASR_RESULT_SOURCE_LOCAL_TEST,
                "clip_name": "directml_probe_30s.wav",
                "duration_seconds": 30,
                "reference_accuracy_percent": 84.95,
                "key_terms_hit": ["Shadowsmith", "Nicolas Cage", "Caltheris"],
                "key_terms_missed": ["Kingman", "ZoneX", "Freckelston", "Nyxara"],
                "known_phrase_hit": True,
                "status": ASR_STATUS_CANDIDATE,
                "notes": "Best tested cloud result so far; still draft text.",
            },
            {
                "provider": "whisper.cpp",
                "model": "Vulkan large-v3-turbo phrase prompt",
                "engine_type": ASR_ENGINE_LOCAL,
                "source": ASR_RESULT_SOURCE_LOCAL_TEST,
                "clip_name": "directml_probe_30s.wav",
                "duration_seconds": 30,
                "reference_accuracy_percent": 74.19,
                "key_terms_hit": ["Nicolas Cage"],
                "key_terms_missed": ["Kingman", "ZoneX", "Freckelston", "Nyxara"],
                "known_phrase_hit": False,
                "status": "local_fallback",
                "notes": "Best tested no-cloud/free baseline.",
            },
            {
                "provider": "AWS Transcribe",
                "model": "custom vocabulary",
                "engine_type": ASR_ENGINE_CLOUD,
                "source": ASR_RESULT_SOURCE_LOCAL_TEST,
                "status": ASR_STATUS_BLOCKED,
                "notes": "Blocked by SubscriptionRequiredException before score.",
            },
            {
                "provider": "GPT-4o Transcribe",
                "model": "Voicewriter raw WER overall",
                "engine_type": ASR_ENGINE_CLOUD,
                "source": ASR_RESULT_SOURCE_EXTERNAL_LEADERBOARD,
                "raw_wer_percent": 5.4,
                "formatted_wer_percent": 12.2,
                "cost_per_hour_usd": 0.36,
                "status": ASR_STATUS_NEEDS_REVIEW,
                "notes": "User-supplied external leaderboard note; not locally scored.",
            },
        ]
    )


def run_self_test() -> None:
    terms = default_asr_key_terms()
    assert terms == (
        "Kingman",
        "ZoneX",
        "Shadowsmith",
        "Nicolas Cage",
        "Freckelston",
        "Caltheris",
        "Nyxara",
    )

    partial = build_asr_comparison_records_from_dicts([
        {"provider": "Partial Provider"}
    ])[0]
    assert partial.provider == "Partial Provider"
    assert partial.model == ""
    assert partial.reference_accuracy_percent is None
    assert partial.key_terms_expected == terms

    records = _sample_records()
    assert len(records) == 4

    elevenlabs = records[0]
    assert elevenlabs.reference_accuracy_percent == 84.95
    assert elevenlabs.keyterm_hit_count == 3
    assert elevenlabs.keyterm_miss_count == 4
    assert elevenlabs.keyterm_hit_rate_percent == 42.86
    assert elevenlabs.known_phrase_hit is True
    assert elevenlabs.has_local_reference_evidence is True

    whisper = records[1]
    assert whisper.reference_accuracy_percent == 74.19
    assert whisper.engine_type == ASR_ENGINE_LOCAL
    assert whisper.has_local_reference_evidence is True

    aws = records[2]
    assert aws.status == ASR_STATUS_BLOCKED
    assert aws.reference_accuracy_percent is None
    assert aws.has_local_reference_evidence is False

    external = records[3]
    assert external.raw_wer_percent == 5.4
    assert external.formatted_wer_percent == 12.2
    assert external.reference_accuracy_percent is None
    assert external.has_local_reference_evidence is False

    ranked_by_accuracy = rank_asr_records(records)
    assert ranked_by_accuracy[0].provider == "ElevenLabs"
    assert ranked_by_accuracy[1].provider == "whisper.cpp"
    assert ranked_by_accuracy[-1].provider in {"AWS Transcribe", "GPT-4o Transcribe"}

    ranked_by_raw_wer = rank_asr_records(records, metric="raw_wer_percent")
    assert ranked_by_raw_wer[0].provider == "GPT-4o Transcribe"
    assert ranked_by_raw_wer[-1].raw_wer_percent is None

    elevenlabs_dict = asr_comparison_record_to_dict(elevenlabs)
    assert set(elevenlabs_dict) == {
        "clip_name",
        "cost_per_hour_usd",
        "duration_seconds",
        "engine_type",
        "formatted_wer_percent",
        "has_local_reference_evidence",
        "key_terms_expected",
        "key_terms_hit",
        "key_terms_missed",
        "keyterm_hit_count",
        "keyterm_hit_rate_percent",
        "keyterm_miss_count",
        "known_phrase_expected",
        "known_phrase_hit",
        "latency_seconds",
        "model",
        "notes",
        "provider",
        "raw_wer_percent",
        "reference_accuracy_percent",
        "source",
        "status",
    }
    assert elevenlabs_dict["key_terms_missed"] == ["Kingman", "ZoneX", "Freckelston", "Nyxara"]

    all_records_dict = asr_comparison_records_to_dict(records)
    assert all_records_dict["record_count"] == 4
    assert all_records_dict["project_key_terms"] == list(terms)

    text = build_asr_comparison_text(records)
    assert "ASR comparison report" in text
    assert "ElevenLabs / Scribe v2 keyterms" in text
    assert "whisper.cpp" in text
    assert "Missed terms: Kingman, ZoneX, Freckelston, Nyxara" in text
    assert "External leaderboard records" in text

    markdown = build_asr_comparison_markdown(records)
    assert "# ASR Comparison Report" in markdown
    assert "| ElevenLabs | Scribe v2 keyterms |" in markdown
    assert "| GPT-4o Transcribe | Voicewriter raw WER overall |" in markdown
    assert "ASR output remains draft" in markdown


if __name__ == "__main__":
    run_self_test()
    print("ASR comparison report self-test passed.")
