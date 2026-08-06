from __future__ import annotations

import json
from dataclasses import dataclass

from online_asr_keys_accounts_app_state import build_online_asr_keys_accounts_app_state
from online_asr_keys_accounts_review_package import (
    build_online_asr_keys_accounts_review_package,
    build_online_asr_keys_accounts_review_package_payloads,
    online_asr_keys_accounts_review_package_index_to_json,
    online_asr_keys_accounts_review_package_to_json,
)
from online_asr_provider_catalog import ONLINE_ASR_CREDENTIAL_STATE_CONFIGURED
from total_export_manifest import ASSET_MANIFEST, ASSET_RAW_SIDECAR


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
    app_state = build_online_asr_keys_accounts_app_state(
        provider_options=_provider_options(),
        credential_statuses={
            "online_asr.elevenlabs.api_key": CredentialStatus(ONLINE_ASR_CREDENTIAL_STATE_CONFIGURED),
        },
        added_provider_ids=("elevenlabs_scribe_v2",),
        selected_provider_id="elevenlabs_scribe_v2",
        keys_accounts_query="scribe",
        add_provider_query="cohere",
    )
    package = build_online_asr_keys_accounts_review_package(
        app_state=app_state,
        package_id="online_asr_keys_accounts_review_package_fixture",
        created_at_utc="2026-08-06T22:55:00Z",
        app_version="test",
        online_asr_gate_summary={
            "schema_version": "online_asr_gate_summary_fixture_v1",
            "selected_provider_id": "elevenlabs_scribe_v2",
            "provider_call_allowed_without_user_approval": False,
            "runtime_provider_call_performed": False,
            "credential_value_read": False,
        },
    )
    payloads = build_online_asr_keys_accounts_review_package_payloads(package)

    assert package.index.package_id == "online_asr_keys_accounts_review_package_fixture"
    assert package.index.review_manifest_package_id == package.review_manifest.package_id
    assert package.index.selected_provider_id == "elevenlabs_scribe_v2"
    assert package.index.selected_provider_ready_for_gate_review is True
    assert package.index.state_payload_file_count == 4
    assert package.index.review_manifest_asset_count == 5
    assert package.index.package_file_count == 7
    assert len(package.index.files) == 6
    assert len(payloads) == 7
    assert "online_asr_keys_accounts_review_package_index.json" in payloads
    assert "online_asr_keys_accounts_review_manifest.json" in payloads
    assert "online_asr_keys_accounts_review_summary.json" in payloads
    assert "online_asr_keys_accounts_app_state.json" in payloads
    assert "online_asr_provider_catalog_state.json" in payloads
    assert "online_asr_selected_provider_readiness.json" in payloads
    assert "online_asr_keys_accounts_state_bundle.json" in payloads
    assert package.review_manifest.app_version == "test"
    assert package.review_manifest.source_urls == []
    assert package.review_manifest.archive_results == []
    assert package.index.keys_accounts_sidebar_label == "KEYS/ACCOUNTS"
    assert package.index.keys_accounts_window_shows_added_providers_only is True
    assert package.index.add_provider_window_searches_full_catalog is True
    assert package.index.provider_call_allowed_without_user_approval is False
    assert package.index.runtime_provider_call_performed is False
    assert package.index.credential_value_read is False
    assert package.index.completed_transcription_claimed is False
    assert all(file.metadata_only is True for file in package.index.files)
    assert all(file.sha256 for file in package.index.files)
    assert [file.asset_type for file in package.index.files].count(ASSET_MANIFEST) == 2
    assert [file.asset_type for file in package.index.files].count(ASSET_RAW_SIDECAR) == 4
    assert "Online ASR execution-gate metadata" in package.index.capture_options
    assert "Provider call allowed without user approval: false" in package.index.to_summary_text()
    assert "Credential value read: false" in package.index.to_summary_text()

    encoded = (
        online_asr_keys_accounts_review_package_to_json(package)
        + online_asr_keys_accounts_review_package_index_to_json(package.index)
        + json.dumps(payloads, sort_keys=True)
    )
    assert "online_asr_keys_accounts_review_package_v1" in encoded
    assert "online_asr_keys_accounts_review_export_v1" in encoded
    assert "online_asr_keys_accounts_state_store_v1" in encoded
    assert "online_asr_keys_accounts_app_state_v1" in encoded
    assert "online_asr_provider_catalog_v1" in encoded
    assert "provider_call_allowed_without_user_approval" in encoded
    assert "runtime_provider_call_performed" in encoded
    assert "credential_value_read" in encoded
    assert "plaintext_secret_storage_allowed" in encoded
    assert "completed_transcription_claimed" in encoded

    unsafe = encoded.casefold()
    assert "actual-secret" not in unsafe
    assert "api_key_value" not in unsafe
    assert '"secret_value_recorded": true' not in unsafe
    assert "c:/users/fahad" not in unsafe
    assert "raw_media_payload_value" not in unsafe
    assert "provider_call_executed" not in unsafe
    assert "completed transcription: true" not in unsafe
    assert "verified transcription" not in unsafe


if __name__ == "__main__":
    run_self_test()
    print("Online ASR KEYS/ACCOUNTS review package self-test passed.")
