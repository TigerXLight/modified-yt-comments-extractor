from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum

from online_asr_keys_accounts_app_state import (
    build_online_asr_keys_accounts_app_state,
    online_asr_keys_accounts_app_state_to_json,
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


def _statuses() -> dict[str, FakeCredentialStatus]:
    return {
        "asr:elevenlabs_scribe": FakeCredentialStatus(FakeCredentialState.CONFIGURED),
        "asr:azure_speech": FakeCredentialStatus(FakeCredentialState.MISSING),
    }


def run_self_test() -> None:
    state = build_online_asr_keys_accounts_app_state(
        provider_options=_providers(),
        credential_statuses=_statuses(),
        added_provider_ids=("elevenlabs_scribe", "azure_speech"),
        selected_provider_id="azure_speech",
        keys_accounts_query="scribe",
        add_provider_query="cohere",
    )
    assert state.keys_accounts_sidebar_label == "KEYS/ACCOUNTS"
    assert state.keys_accounts_window_shows_added_providers_only is True
    assert state.add_provider_window_searches_full_catalog is True
    assert state.online_asr_button_label == "Online ASR"
    assert state.local_asr_button_label == "Local ASR"
    assert state.online_asr_next_to_local_asr is True
    assert state.online_asr_reuses_local_asr_control_style is True
    assert state.keys_accounts_panel.search_scope == "added_providers_only"
    assert state.add_provider_panel.search_scope == "full_provider_catalog"
    assert state.keys_accounts_panel.provider_ids == ("elevenlabs_scribe",)
    assert state.add_provider_panel.provider_ids == ("cohere_transcribe",)
    assert state.added_provider_count == 2
    assert state.configured_provider_count == 1
    assert state.missing_key_provider_count == 2
    assert state.selected_provider.provider_id == "azure_speech"
    assert state.selected_provider.configured is False
    assert state.selected_provider.added_to_keys_accounts is True
    assert state.selected_provider.ready_for_review_gate is False
    assert state.selected_provider.action_required == "configure_provider_key_or_account"
    assert "KEYS/ACCOUNTS" in state.selected_provider.action_label

    ready_state = build_online_asr_keys_accounts_app_state(
        provider_options=_providers(),
        credential_statuses=_statuses(),
        added_provider_ids=("elevenlabs_scribe",),
        selected_provider_id="elevenlabs_scribe",
    )
    assert ready_state.selected_provider_ready_for_gate_review is True
    assert ready_state.selected_provider.action_required == "review_and_explicitly_approve_provider_call"
    assert ready_state.catalog_state.selected_provider_ready_for_review_gate is True

    not_added_state = build_online_asr_keys_accounts_app_state(
        provider_options=_providers(),
        credential_statuses=_statuses(),
        added_provider_ids=("elevenlabs_scribe",),
        selected_provider_id="cohere_transcribe",
    )
    assert not_added_state.selected_provider.added_to_keys_accounts is False
    assert not_added_state.selected_provider.ready_for_review_gate is False
    assert not_added_state.selected_provider.action_required == "add_provider_to_keys_accounts"

    encoded = online_asr_keys_accounts_app_state_to_json(state)
    decoded = json.loads(encoded)
    assert decoded["schema_version"] == "online_asr_keys_accounts_app_state_v1"
    assert decoded["catalog_state"]["schema_version"] == "online_asr_provider_catalog_v1"
    assert "KEYS/ACCOUNTS" in encoded
    assert "Online ASR" in encoded
    assert "Local ASR" in encoded
    assert "added_providers_only" in encoded
    assert "full_provider_catalog" in encoded
    assert "provider_call_allowed_without_user_approval" in encoded
    assert "runtime_provider_call_performed" in encoded
    assert "credential_value_read" in encoded

    unsafe = encoded.casefold()
    assert "api_key" not in unsafe
    assert "secret_value\":" not in unsafe
    assert "c:/users/fahad" not in unsafe
    assert "provider_call_executed" not in unsafe
    assert "runtime_provider_call_performed: true" not in unsafe
    assert "completed transcription: true" not in unsafe

    summary = state.to_summary_text()
    assert "Online ASR KEYS/ACCOUNTS app state" in summary
    assert "Online ASR sits beside Local ASR: true" in summary
    assert "Online ASR reuses Local ASR control style: true" in summary
    assert "Provider call allowed without user approval: false" in summary
    assert "Runtime provider call performed: false" in summary


if __name__ == "__main__":
    run_self_test()
    print("Online ASR KEYS/ACCOUNTS app state self-test passed.")
