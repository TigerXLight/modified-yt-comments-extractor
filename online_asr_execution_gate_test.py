import json
from dataclasses import dataclass
from enum import Enum

from online_asr_execution_gate import (
    ONLINE_ASR_CREDENTIAL_STATE_CONFIGURED,
    ONLINE_ASR_CREDENTIAL_STATE_MISSING,
    build_online_asr_execution_gate_plan,
    render_online_asr_execution_gate_summary_text,
)


class FakeCredentialState(Enum):
    CONFIGURED = "CONFIGURED"
    MISSING = "MISSING"


@dataclass(frozen=True)
class FakeStatus:
    state: FakeCredentialState


@dataclass(frozen=True)
class FakeProvider:
    provider_id: str
    display_name: str
    model_id: str
    credential_entry_id: str


def run_self_test() -> None:
    provider = FakeProvider(
        provider_id="elevenlabs_scribe",
        display_name="ElevenLabs Scribe v2",
        model_id="scribe_v2",
        credential_entry_id="asr:elevenlabs_scribe",
    )
    missing_plan, missing_summary = build_online_asr_execution_gate_plan(
        selected_provider=provider,
        provider_options=(provider,),
        credential_statuses={provider.credential_entry_id: FakeStatus(FakeCredentialState.MISSING)},
        media_file_selected=True,
        media_file_name="private-media.wav",
    )
    missing_dict = missing_summary.to_dict()
    assert missing_summary.credential_configured is False
    assert missing_summary.provider_records[0].credential_state == ONLINE_ASR_CREDENTIAL_STATE_MISSING
    assert missing_summary.provider_call_allowed_without_user_approval is False
    assert missing_summary.plaintext_secret_storage_allowed is False
    assert missing_summary.full_local_path_included is False
    assert missing_summary.completed_transcription_claimed is False
    assert missing_plan.provider_call_allowed is False
    rendered = json.dumps(missing_dict, sort_keys=True)
    assert "C:/Users/fahad/private-media.wav" not in rendered
    assert "api_key" not in rendered.casefold()
    assert "private-media.wav" not in rendered

    configured_plan, configured_summary = build_online_asr_execution_gate_plan(
        selected_provider=provider,
        provider_options=(provider,),
        credential_statuses={provider.credential_entry_id: FakeStatus(FakeCredentialState.CONFIGURED)},
        media_file_selected=True,
        media_file_name="clip.wav",
    )
    assert configured_summary.credential_configured is True
    assert configured_summary.provider_records[0].credential_state == ONLINE_ASR_CREDENTIAL_STATE_CONFIGURED
    assert configured_summary.configured_provider_count == 1
    assert configured_summary.execution_gate_plan_id == configured_plan.plan_id
    assert configured_plan.application_execution_allowed is False

    repeat_plan, repeat_summary = build_online_asr_execution_gate_plan(
        selected_provider=provider,
        provider_options=(provider,),
        credential_statuses={provider.credential_entry_id: FakeStatus(FakeCredentialState.CONFIGURED)},
        media_file_selected=True,
        media_file_name="clip.wav",
    )
    assert repeat_plan.plan_id == configured_plan.plan_id
    assert repeat_summary.summary_id == configured_summary.summary_id

    text = render_online_asr_execution_gate_summary_text(configured_summary, plan=configured_plan)
    assert "Online ASR execution gate" in text
    assert "Provider call allowed without user approval: false" in text
    assert "Plaintext secret storage allowed: false" in text
    assert "Completed transcription claimed: false" in text


if __name__ == "__main__":
    run_self_test()
    print("Online ASR execution gate self-test passed.")
