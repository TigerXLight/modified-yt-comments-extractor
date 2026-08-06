from __future__ import annotations

import json
import tempfile
from dataclasses import dataclass
from pathlib import Path

from online_asr_keys_accounts_review_workflow import (
    ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_ACTIVITY_DIRECTORY_NAME,
    ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_PACKAGE_DIRECTORY_NAME,
    build_online_asr_keys_accounts_review_workflow,
    online_asr_keys_accounts_review_workflow_result_to_json,
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
    with tempfile.TemporaryDirectory() as tmp:
        result = build_online_asr_keys_accounts_review_workflow(
            provider_options=_provider_options(),
            credential_statuses={
                "online_asr.elevenlabs.api_key": CredentialStatus(ONLINE_ASR_CREDENTIAL_STATE_CONFIGURED),
            },
            added_provider_ids=("elevenlabs_scribe_v2",),
            selected_provider_id="elevenlabs_scribe_v2",
            keys_accounts_query="scribe",
            add_provider_query="cohere",
            output_directory=tmp,
            package_id="online_asr_keys_accounts_review_pkg_test",
            created_at_utc="2026-08-06T23:59:00Z",
            app_version="test-app",
            online_asr_gate_summary={
                "provider_id": "elevenlabs_scribe_v2",
                "provider_call_allowed_without_user_approval": False,
            },
        )
        root = Path(tmp)
        assert (root / ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_PACKAGE_DIRECTORY_NAME).is_dir()
        assert (root / ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_ACTIVITY_DIRECTORY_NAME).is_dir()
        assert result.keys_accounts_sidebar_label == "KEYS/ACCOUNTS"
        assert result.keys_accounts_window_shows_added_providers_only is True
        assert result.add_provider_window_searches_full_catalog is True
        assert result.selected_provider_id == "elevenlabs_scribe_v2"
        assert result.selected_provider_ready_for_gate_review is True
        assert result.review_manifest_asset_count > 0
        assert result.package_file_count >= result.package_store_result.file_count
        assert result.activity_entry_count == 4
        assert result.stored_file_count == result.package_store_result.file_count + result.activity_store_result.file_count
        assert result.package_output_directory_role.endswith("review_package_directory")
        assert result.activity_output_directory_role.endswith("review_activity_directory")
        assert all(stored.filename.endswith(".json") for stored in result.package_store_result.files)
        assert all(stored.filename.endswith(".json") for stored in result.activity_store_result.files)

        encoded = online_asr_keys_accounts_review_workflow_result_to_json(result)
        decoded = json.loads(encoded)
        assert decoded["schema_version"] == "online_asr_keys_accounts_review_workflow_v1"
        assert decoded["metadata_only"] is True
        assert decoded["provider_call_allowed_without_user_approval"] is False
        assert decoded["runtime_provider_call_performed"] is False
        assert decoded["credential_value_read"] is False
        assert decoded["plaintext_secret_storage_allowed"] is False
        assert decoded["secret_value_recorded"] is False
        assert decoded["raw_media_payload_included"] is False
        assert decoded["full_local_path_included"] is False
        assert decoded["completed_transcription_claimed"] is False
        assert decoded["verified_transcription_claimed"] is False
        assert "online_asr.elevenlabs.api_key" in encoded
        assert "api_key_value" not in encoded.lower()
        assert "sk-" not in encoded.lower()
        assert "provider_call_performed\": true" not in encoded.lower()
        assert str(root) not in encoded
        summary = result.to_summary_text()
        assert "Provider call allowed without user approval: false" in summary
        assert "Credential value read: false" in summary
        assert "Completed transcription claimed: false" in summary
    print("Online ASR KEYS/ACCOUNTS review workflow self-test passed.")


if __name__ == "__main__":
    run_self_test()
