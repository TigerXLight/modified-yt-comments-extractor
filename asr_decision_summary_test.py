from asr_comparison_report import (
    ASR_ENGINE_CLOUD,
    ASR_RESULT_SOURCE_LOCAL_TEST,
    ASR_STATUS_ACCEPTED,
    build_asr_comparison_records_from_dicts,
)
from asr_comparison_report_cli import load_asr_records_from_json
from asr_decision_summary import (
    DEFAULT_PROJECT_THRESHOLD_PERCENT,
    asr_decision_summary_to_dict,
    build_asr_decision_summary,
    build_asr_decision_summary_markdown,
    build_asr_decision_summary_text,
)


def run_self_test() -> None:
    metadata, records = load_asr_records_from_json("ASR_MANUAL_RESULTS_SEED.json")
    assert metadata["schema"] == "asr_comparison_report.manual_seed.v1"
    assert len(records) == 25

    result = build_asr_decision_summary(records)
    assert result.threshold_percent == DEFAULT_PROJECT_THRESHOLD_PERCENT
    assert result.record_count == 25
    assert result.project_scored_count == 11
    assert result.accepted_count == 0
    assert result.candidate_count == 7
    assert result.rejected_count == 9
    assert result.blocked_count == 1
    assert result.needs_review_count == 8
    assert result.unknown_count == 0
    assert result.external_lead_count == 13
    assert result.below_threshold_count == 11
    assert result.best_scored_label == "ElevenLabs / Scribe v2 with keyterms"
    assert result.best_scored_accuracy_percent == 84.95
    assert result.best_local_label == "whisper.cpp / Vulkan large-v3-turbo phrase prompt"
    assert result.best_local_accuracy_percent == 74.19
    assert result.blocked_labels == (
        "AWS Transcribe / Batch transcription with custom vocabulary",
    )
    assert "SubscriptionRequiredException" in result.blocked_details[0]
    assert "ElevenLabs / Scribe v2 with keyterms" in result.below_threshold_candidate_labels
    assert "whisper.cpp / Vulkan large-v3-turbo phrase prompt" in result.below_threshold_candidate_labels
    assert any("must not be ranked" in warning for warning in result.warnings)
    assert any("External leaderboard" in warning for warning in result.warnings)
    assert result.errors == ()

    as_dict = asr_decision_summary_to_dict(result)
    assert list(as_dict) == [
        "accepted_count",
        "below_threshold_candidate_labels",
        "below_threshold_count",
        "best_local_accuracy_percent",
        "best_local_label",
        "best_scored_accuracy_percent",
        "best_scored_label",
        "blocked_count",
        "blocked_details",
        "blocked_labels",
        "candidate_count",
        "errors",
        "external_lead_count",
        "needs_review_count",
        "project_scored_count",
        "recommendation",
        "record_count",
        "rejected_count",
        "threshold_percent",
        "unknown_count",
        "warnings",
    ]
    assert as_dict == asr_decision_summary_to_dict(build_asr_decision_summary(records))

    text = build_asr_decision_summary_text(result)
    assert "ASR decision summary" in text
    assert "Strict project threshold: 95.00%" in text
    assert "Best project-scored result: ElevenLabs" in text
    assert "AWS Transcribe" in text
    assert "Blocked providers have no comparable quality result" in text
    assert "External leaderboard and user-observation leads" in text
    assert "Safe next action:" in text

    markdown = build_asr_decision_summary_markdown(result)
    assert "# ASR Decision Summary" in markdown
    assert "Strict project threshold: 95.00%" in markdown
    assert "## Blocked Providers" in markdown
    assert "Blocked means no comparable quality score" in markdown
    assert "Candidate means worth considering or retesting, not accepted" in markdown
    assert "External leaderboard/research leads do not override" in markdown

    accepted_records = build_asr_comparison_records_from_dicts(
        [
            {
                "provider": "Synthetic accepted provider",
                "model": "local fixture",
                "engine_type": ASR_ENGINE_CLOUD,
                "source": ASR_RESULT_SOURCE_LOCAL_TEST,
                "reference_accuracy_percent": 96.0,
                "status": ASR_STATUS_ACCEPTED,
            }
        ]
    )
    accepted = build_asr_decision_summary(accepted_records)
    assert accepted.accepted_count == 1
    assert accepted.below_threshold_count == 0
    assert accepted.errors == ()

    invalid_accepted_records = build_asr_comparison_records_from_dicts(
        [
            {
                "provider": "Synthetic invalid accepted provider",
                "source": ASR_RESULT_SOURCE_LOCAL_TEST,
                "reference_accuracy_percent": 80.0,
                "status": ASR_STATUS_ACCEPTED,
            }
        ]
    )
    invalid_accepted = build_asr_decision_summary(invalid_accepted_records)
    assert invalid_accepted.errors
    assert "below the 95.00% gate" in invalid_accepted.errors[0]


if __name__ == "__main__":
    run_self_test()
    print("ASR decision summary self-test passed.")
