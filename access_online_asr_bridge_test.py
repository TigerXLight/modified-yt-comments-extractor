from dataclasses import dataclass
from enum import Enum

from access_online_asr_bridge import (
    PREFERRED_LOCAL_ASR_DEVICE,
    PREFERRED_LOCAL_ASR_ENGINE,
    PREFERRED_LOCAL_ASR_MODEL,
    access_online_asr_bridge_summary_to_json,
    build_access_online_asr_bridge_preservation_report,
    build_access_online_asr_bridge_summary,
    validate_access_online_asr_bridge_preservation_report,
    validate_access_online_asr_bridge_summary,
)
from core.settings import AppSettings


class FakeCredentialState(Enum):
    CONFIGURED = "CONFIGURED"
    MISSING = "MISSING"


@dataclass(frozen=True)
class FakeCredentialStatus:
    state: FakeCredentialState


@dataclass(frozen=True)
class FakeOnlineASRProvider:
    provider_id: str
    display_name: str
    model_id: str
    credential_entry_id: str


def test_access_online_asr_bridge_summarizes_non_secret_provider_state() -> None:
    provider = FakeOnlineASRProvider(
        provider_id="elevenlabs_scribe",
        display_name="ElevenLabs Scribe",
        model_id="scribe_v2",
        credential_entry_id="asr:elevenlabs_scribe",
    )
    settings = AppSettings(access_keys_added_provider_ids=("asr:elevenlabs_scribe",))

    summary = build_access_online_asr_bridge_summary(
        settings=settings,
        online_asr_provider_options=(provider,),
        credential_statuses={
            provider.credential_entry_id: FakeCredentialStatus(FakeCredentialState.CONFIGURED)
        },
    )
    data = summary.to_dict()

    assert summary.summary_id.startswith("access_online_asr_bridge_")
    assert summary.added_provider_count == 1
    assert summary.catalogue_provider_count > 0
    assert summary.search_added_supported is True
    assert summary.search_catalogue_supported is True
    assert summary.online_asr_command_state == "approval_required_before_provider_call"
    assert summary.online_asr_provider_readiness_count == 1
    assert summary.online_asr_configured_provider_count == 1
    assert summary.credential_values_read is False
    assert summary.provider_call_performed is False
    assert summary.asr_run_performed is False
    assert summary.plaintext_secret_included is False
    assert data["online_asr_provider_records"][0]["credential_configured"] is True
    validate_access_online_asr_bridge_summary(data)


def test_access_online_asr_bridge_preserves_local_asr_benchmark_guard() -> None:
    summary = build_access_online_asr_bridge_summary()
    rendered = access_online_asr_bridge_summary_to_json(summary)

    assert summary.local_asr_preferred_engine == PREFERRED_LOCAL_ASR_ENGINE
    assert summary.local_asr_preferred_device == PREFERRED_LOCAL_ASR_DEVICE
    assert summary.local_asr_preferred_model == PREFERRED_LOCAL_ASR_MODEL
    assert summary.local_asr_benchmark_profile_guard == "preserve_whispercpp_vulkan_large_v3"
    assert "large-v3" in rendered
    assert "Vulkan" in rendered
    assert "credential_values_read" in rendered
    assert "ONLINE-ASR-SECRET" not in rendered
    assert "sk-" not in rendered
    assert "Authorization:" not in rendered


def test_access_online_asr_bridge_preservation_report_is_non_secret() -> None:
    summary = build_access_online_asr_bridge_summary()
    report = build_access_online_asr_bridge_preservation_report(summary)
    data = report.to_dict()
    assert report.search_added_vs_catalogue_split_preserved is True
    assert report.online_asr_provider_calls_blocked is True
    assert report.local_asr_benchmark_profile_preserved is True
    assert report.local_asr_preferred_model == "large-v3"
    assert report.local_asr_preferred_device == "Vulkan"
    assert report.credential_values_read is False
    assert report.provider_call_performed is False
    assert report.asr_run_performed is False
    assert report.plaintext_secret_included is False
    validate_access_online_asr_bridge_preservation_report(data)


def run_self_test() -> None:
    test_access_online_asr_bridge_summarizes_non_secret_provider_state()
    test_access_online_asr_bridge_preserves_local_asr_benchmark_guard()
    test_access_online_asr_bridge_preservation_report_is_non_secret()


if __name__ == "__main__":
    run_self_test()
    print("Access/Online ASR bridge self-test passed.")
