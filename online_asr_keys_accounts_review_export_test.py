from __future__ import annotations

import json
from dataclasses import dataclass

from online_asr_keys_accounts_app_state import build_online_asr_keys_accounts_app_state
from online_asr_keys_accounts_review_export import (
    build_online_asr_keys_accounts_review_export_summary,
    build_online_asr_keys_accounts_review_manifest,
    online_asr_keys_accounts_review_export_summary_to_json,
    online_asr_keys_accounts_review_manifest_to_json,
)
from online_asr_keys_accounts_state_store import build_online_asr_keys_accounts_state_store_payloads
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
    manifest = build_online_asr_keys_accounts_review_manifest(
        app_state=state,
        package_id="online_asr_keys_accounts_review_fixture",
        created_at_utc="2026-08-06T22:30:00Z",
        state_payloads=payloads,
        online_asr_gate_summary={
            "schema_version": "online_asr_gate_summary_fixture_v1",
            "selected_provider_id": "elevenlabs_scribe_v2",
            "provider_call_allowed_without_user_approval": False,
            "runtime_provider_call_performed": False,
            "credential_value_read": False,
        },
        app_version="test",
    )

    assert manifest.package_id == "online_asr_keys_accounts_review_fixture"
    assert manifest.source_urls == []
    assert manifest.app_version == "test"
    assert manifest.archive_results == []
    assert len(manifest.assets) == 5
    assert [asset.asset_type for asset in manifest.assets].count(ASSET_MANIFEST) == 1
    assert [asset.asset_type for asset in manifest.assets].count(ASSET_RAW_SIDECAR) == 4
    assert all(asset.path == "" for asset in manifest.assets)
    assert all(asset.sha256 for asset in manifest.assets)
    assert all(asset.mime_type == "application/json" for asset in manifest.assets)
    assert "Online ASR KEYS/ACCOUNTS app state metadata" in manifest.capture_options
    assert "Online ASR execution-gate metadata" in manifest.capture_options
    assert "USER_REVIEW_REQUIRED" in manifest.notes
    assert "EXECUTION_GATED" in manifest.notes
    assert "No credential values" in manifest.notes

    summary = build_online_asr_keys_accounts_review_export_summary(
        app_state=state,
        manifest=manifest,
        state_payload_filenames=payloads.keys(),
    )
    assert summary.selected_provider_id == "elevenlabs_scribe_v2"
    assert summary.selected_provider_ready_for_gate_review is True
    assert summary.manifest_asset_count == 5
    assert summary.review_status == "USER_REVIEW_REQUIRED"
    assert summary.execution_state == "EXECUTION_GATED"

    encoded = (
        online_asr_keys_accounts_review_manifest_to_json(manifest)
        + online_asr_keys_accounts_review_export_summary_to_json(summary)
        + json.dumps(payloads, sort_keys=True)
    )
    assert "online_asr_keys_accounts_review_export_v1" in encoded
    assert "provider_call_allowed_without_user_approval" in encoded
    assert "runtime_provider_call_performed" in encoded
    assert "credential_value_read" in encoded
    assert "plaintext_secret_storage_allowed" in encoded
    assert "completed_transcription_claimed" in encoded
    assert "Online ASR KEYS/ACCOUNTS review export" in summary.to_summary_text()
    assert "Provider call allowed without user approval: false" in summary.to_summary_text()

    unsafe = encoded.casefold()
    assert "actual-secret" not in unsafe
    assert "api_key_value" not in unsafe
    assert "c:/users/fahad" not in unsafe
    assert "raw_media_payload_value" not in unsafe
    assert "provider_call_executed" not in unsafe
    assert "completed transcription: true" not in unsafe
    assert "verified transcription" not in unsafe


if __name__ == "__main__":
    run_self_test()
    print("Online ASR KEYS/ACCOUNTS review export self-test passed.")
