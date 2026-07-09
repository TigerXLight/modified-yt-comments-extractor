from asr_provider_metadata import (
    PROVIDER_STATUS_BLOCKED,
    PROVIDER_STATUS_CANDIDATE,
    PROVIDER_STATUS_LOCAL_FALLBACK,
    PROVIDER_STATUS_REJECTED,
    available_asr_provider_metadata,
    blocked_asr_provider_metadata,
    get_asr_provider_metadata,
    recommended_asr_provider_metadata,
    rejected_asr_provider_metadata,
)


def run_self_test() -> None:
    providers = available_asr_provider_metadata()
    provider_ids = [provider.provider_id for provider in providers]
    assert len(provider_ids) == len(set(provider_ids))

    elevenlabs = get_asr_provider_metadata("elevenlabs_scribe")
    assert elevenlabs is not None
    assert elevenlabs.status == PROVIDER_STATUS_CANDIDATE
    assert elevenlabs.best_known_accuracy_percent == 84.95
    assert elevenlabs.credentials_required
    assert not elevenlabs.local_runtime
    assert "Term QA" in elevenlabs.notes

    whisper_cpp = get_asr_provider_metadata("whisper_cpp_vulkan_large_v3_turbo")
    assert whisper_cpp is not None
    assert whisper_cpp.status == PROVIDER_STATUS_LOCAL_FALLBACK
    assert whisper_cpp.best_known_accuracy_percent == 74.19
    assert whisper_cpp.local_runtime
    assert not whisper_cpp.credentials_required

    aws = get_asr_provider_metadata("aws_transcribe_custom_vocabulary")
    assert aws is not None
    assert aws.status == PROVIDER_STATUS_BLOCKED
    assert aws.best_known_accuracy_percent is None
    assert "SubscriptionRequiredException" in aws.access_limitations

    rejected_ids = {provider.provider_id for provider in rejected_asr_provider_metadata()}
    assert rejected_ids == {
        "assemblyai_universal_3_5_pro",
        "deepgram_nova_3",
        "speechmatics_enhanced",
        "azure_speech",
        "google_stt_video_enhanced",
        "cohere_transcribe",
        "google_stt_latest_long",
    }
    assert all(
        provider.status == PROVIDER_STATUS_REJECTED
        for provider in rejected_asr_provider_metadata()
    )

    recommended_ids = [provider.provider_id for provider in recommended_asr_provider_metadata()]
    assert recommended_ids == [
        "elevenlabs_scribe",
        "whisper_cpp_vulkan_large_v3_turbo",
    ]

    blocked_ids = [provider.provider_id for provider in blocked_asr_provider_metadata()]
    assert blocked_ids == ["aws_transcribe_custom_vocabulary"]
    assert get_asr_provider_metadata("unknown_provider") is None

    assert all(not provider.test_connection_supported for provider in providers)


if __name__ == "__main__":
    run_self_test()
    print("ASR provider metadata self-test passed.")
