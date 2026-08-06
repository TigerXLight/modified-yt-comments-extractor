from __future__ import annotations

import json
import tempfile
from dataclasses import dataclass
from pathlib import Path

from online_asr_keys_accounts_app_state import build_online_asr_keys_accounts_app_state
from online_asr_keys_accounts_state_store import (
    build_online_asr_keys_accounts_state_store_payloads,
    online_asr_keys_accounts_state_store_result_to_json,
    write_online_asr_keys_accounts_state_bundle,
)
from online_asr_provider_catalog import ONLINE_ASR_CREDENTIAL_STATE_CONFIGURED


@dataclass(frozen=True)
class ProviderOption:
    provider_id: str
    display_name: str
    provider_family: str
    model_id: str
    credential_entry_id: str
    supports_keyterms: bool = False
    tags: tuple[str, ...] = ()
    recommended_for: tuple[str, ...] = ()


@dataclass(frozen=True)
class CredentialStatus:
    state: str


def _provider_options() -> tuple[ProviderOption, ...]:
    return (
        ProviderOption(
            provider_id="elevenlabs_scribe_v2",
            display_name="ElevenLabs Scribe v2",
            provider_family="elevenlabs",
            model_id="scribe_v2",
            credential_entry_id="online_asr.elevenlabs.api_key",
            supports_keyterms=True,
            tags=("cloud", "keyterms"),
            recommended_for=("cloud_candidate",),
        ),
        ProviderOption(
            provider_id="cohere_transcribe",
            display_name="Cohere Transcribe",
            provider_family="cohere",
            model_id="command-audio",
            credential_entry_id="online_asr.cohere.api_key",
            tags=("cloud",),
        ),
    )


def run_self_test() -> None:
    state = build_online_asr_keys_accounts_app_state(
        provider_options=_provider_options(),
        credential_statuses={
            "online_asr.elevenlabs.api_key": CredentialStatus(ONLINE_ASR_CREDENTIAL_STATE_CONFIGURED),
        },
        added_provider_ids=("elevenlabs_scribe_v2",),
        selected_provider_id="elevenlabs_scribe_v2",
        keys_accounts_query="scribe",
        add_provider_query="cohere",
    )

    payloads = build_online_asr_keys_accounts_state_store_payloads(state)
    assert sorted(payloads) == [
        "online_asr_keys_accounts_app_state.json",
        "online_asr_keys_accounts_state_bundle.json",
        "online_asr_provider_catalog_state.json",
        "online_asr_selected_provider_readiness.json",
    ]
    assert payloads["online_asr_keys_accounts_state_bundle.json"]["review_status"] == "USER_REVIEW_REQUIRED"
    assert payloads["online_asr_keys_accounts_state_bundle.json"]["execution_state"] == "EXECUTION_GATED"
    assert payloads["online_asr_keys_accounts_state_bundle.json"]["provider_call_allowed_without_user_approval"] is False
    assert payloads["online_asr_keys_accounts_state_bundle.json"]["credential_value_read"] is False
    assert payloads["online_asr_keys_accounts_state_bundle.json"]["online_asr_reuses_local_asr_control_style"] is True

    with tempfile.TemporaryDirectory() as tmp:
        result = write_online_asr_keys_accounts_state_bundle(state, tmp)
        output = Path(tmp)
        assert result.file_count == 4
        assert result.output_directory_name == output.name
        assert result.selected_provider_id == "elevenlabs_scribe_v2"
        assert result.selected_provider_ready_for_gate_review is True
        assert sorted(path.name for path in output.glob("*.json")) == sorted(payloads)
        for stored in output.glob("*.json"):
            json.loads(stored.read_text(encoding="utf-8"))

    encoded = online_asr_keys_accounts_state_store_result_to_json(result)
    for filename in payloads:
        assert filename in encoded
    assert "online_asr_keys_accounts_state_store_v1" in encoded
    assert "USER_REVIEW_REQUIRED" in encoded
    assert "EXECUTION_GATED" in encoded
    assert "provider_call_allowed_without_user_approval" in encoded
    assert "credential_value_read" in encoded
    assert "plaintext_secret_storage_allowed" in encoded
    assert "runtime_provider_call_performed" in encoded

    unsafe = encoded.casefold() + json.dumps(payloads, sort_keys=True).casefold()
    assert "actual-secret" not in unsafe
    assert "api_key_value" not in unsafe
    assert "c:/users/fahad" not in unsafe
    assert "raw_media_payload_value" not in unsafe
    assert "provider_call_executed" not in unsafe
    assert "completed transcription: true" not in unsafe
    assert "verified transcription" not in unsafe

    summary = result.to_summary_text()
    assert "Online ASR KEYS/ACCOUNTS state bundle" in summary
    assert "Review status: USER_REVIEW_REQUIRED" in summary
    assert "Execution state: EXECUTION_GATED" in summary
    assert "Provider call allowed without user approval: false" in summary
    assert "Runtime provider call performed: false" in summary


if __name__ == "__main__":
    run_self_test()
    print("Online ASR KEYS/ACCOUNTS state store self-test passed.")
