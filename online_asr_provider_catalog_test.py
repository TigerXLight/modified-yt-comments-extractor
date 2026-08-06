from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum

from online_asr_provider_catalog import (
    ONLINE_ASR_CREDENTIAL_STATE_CONFIGURED,
    ONLINE_ASR_CREDENTIAL_STATE_MISSING,
    build_online_asr_provider_catalog_state,
    online_asr_provider_catalog_state_to_json,
)


class FakeCredentialState(Enum):
    CONFIGURED = "CONFIGURED"
    MISSING = "MISSING"


@dataclass(frozen=True)
class FakeCredentialStatus:
    state: FakeCredentialState


@dataclass(frozen=True)
class FakeProviderOption:
    provider_id: str
    display_name: str
    provider_family: str
    model_id: str
    credential_entry_id: str
    supports_keyterms: bool = False
    tags: tuple[str, ...] = ()
    recommended_for: tuple[str, ...] = ()


def _providers() -> tuple[FakeProviderOption, ...]:
    return (
        FakeProviderOption(
            provider_id="elevenlabs_scribe",
            display_name="ElevenLabs Scribe v2",
            provider_family="ElevenLabs",
            model_id="scribe_v2",
            credential_entry_id="asr:elevenlabs_scribe",
            supports_keyterms=True,
            tags=("cloud", "keyterms"),
            recommended_for=("best-cloud-candidate",),
        ),
        FakeProviderOption(
            provider_id="cohere_transcribe",
            display_name="Cohere Transcribe",
            provider_family="Cohere",
            model_id="latest",
            credential_entry_id="asr:cohere_transcribe",
            tags=("cloud",),
        ),
        FakeProviderOption(
            provider_id="azure_speech",
            display_name="Azure Speech",
            provider_family="Azure",
            model_id="speech_to_text",
            credential_entry_id="asr:azure_speech",
            tags=("cloud",),
        ),
    )


def run_self_test() -> None:
    statuses = {
        "asr:elevenlabs_scribe": FakeCredentialStatus(FakeCredentialState.CONFIGURED),
        "asr:azure_speech": FakeCredentialStatus(FakeCredentialState.MISSING),
    }
    state = build_online_asr_provider_catalog_state(
        provider_options=_providers(),
        credential_statuses=statuses,
        added_provider_ids=("elevenlabs_scribe", "azure_speech"),
        selected_provider_id="elevenlabs_scribe",
        keys_accounts_query="speech",
        add_provider_query="cohere",
    )
    assert state.catalogue_window_label == "KEYS/ACCOUNTS"
    assert state.keys_accounts_window_shows_added_providers_only is True
    assert state.add_provider_window_searches_full_catalog is True
    assert state.full_provider_count == 3
    assert state.added_provider_count == 2
    assert state.configured_provider_count == 1
    assert state.missing_key_provider_count == 2
    assert state.selected_provider_configured is True
    assert state.selected_provider_added_to_keys_accounts is True
    assert state.selected_provider_ready_for_review_gate is True
    assert [entry.provider_id for entry in state.keys_accounts_entries] == ["azure_speech"]
    assert [entry.provider_id for entry in state.add_provider_entries] == ["cohere_transcribe"]
    assert state.full_catalog_entries[0].plaintext_secret_storage_allowed is False
    assert state.full_catalog_entries[0].secret_value_recorded is False
    assert state.full_catalog_entries[0].provider_call_allowed_without_user_approval is False
    assert state.full_catalog_entries[0].credential_state == ONLINE_ASR_CREDENTIAL_STATE_MISSING
    elevenlabs = next(entry for entry in state.full_catalog_entries if entry.provider_id == "elevenlabs_scribe")
    assert elevenlabs.credential_state == ONLINE_ASR_CREDENTIAL_STATE_CONFIGURED
    assert elevenlabs.supports_keyterms is True

    missing_selected = build_online_asr_provider_catalog_state(
        provider_options=_providers(),
        credential_statuses=statuses,
        added_provider_ids=("azure_speech",),
        selected_provider_id="azure_speech",
    )
    assert missing_selected.selected_provider_configured is False
    assert missing_selected.selected_provider_ready_for_review_gate is False
    assert [entry.provider_id for entry in missing_selected.keys_accounts_entries] == ["azure_speech"]

    encoded = online_asr_provider_catalog_state_to_json(state)
    decoded = json.loads(encoded)
    assert decoded["schema_version"] == "online_asr_provider_catalog_v1"
    assert "KEYS/ACCOUNTS" in encoded
    assert "provider_call_allowed_without_user_approval" in encoded
    assert "plaintext_secret_storage_allowed" in encoded
    assert "completed_transcription_claimed" in encoded
    unsafe = encoded.casefold()
    assert "api_key" not in unsafe
    assert "secret_value\":" not in unsafe
    assert "c:/users/fahad" not in unsafe
    assert "provider_call_executed" not in unsafe
    assert "completed transcription: true" not in unsafe

    summary = state.to_summary_text()
    assert "Online ASR KEYS/ACCOUNTS provider catalogue" in summary
    assert "Provider call allowed without user approval: false" in summary
    assert "Plaintext secret storage allowed: false" in summary


if __name__ == "__main__":
    run_self_test()
    print("Online ASR provider catalog self-test passed.")
