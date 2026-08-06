from __future__ import annotations

import json
import tempfile
from dataclasses import dataclass
from pathlib import Path

from online_asr_keys_accounts_app_state import build_online_asr_keys_accounts_app_state
from online_asr_keys_accounts_review_package import build_online_asr_keys_accounts_review_package
from online_asr_keys_accounts_review_package_store import (
    build_online_asr_keys_accounts_review_package_store_payloads,
    online_asr_keys_accounts_review_package_store_result_to_json,
    write_online_asr_keys_accounts_review_package,
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


def _build_package():
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
    return build_online_asr_keys_accounts_review_package(
        app_state=app_state,
        package_id="online_asr_keys_accounts_review_package_fixture",
        created_at_utc="2026-08-06T23:30:00Z",
        app_version="test",
        online_asr_gate_summary={
            "schema_version": "online_asr_gate_summary_fixture_v1",
            "selected_provider_id": "elevenlabs_scribe_v2",
            "provider_call_allowed_without_user_approval": False,
            "runtime_provider_call_performed": False,
            "credential_value_read": False,
        },
    )


def run_self_test() -> None:
    package = _build_package()
    payload_texts = build_online_asr_keys_accounts_review_package_store_payloads(package)
    assert len(payload_texts) == 7
    assert list(payload_texts) == sorted(payload_texts)
    assert "online_asr_keys_accounts_review_package_index.json" in payload_texts
    assert "online_asr_keys_accounts_review_manifest.json" in payload_texts
    assert "online_asr_keys_accounts_review_summary.json" in payload_texts
    assert all(text.endswith("\n") for text in payload_texts.values())
    assert all(json.loads(text) for text in payload_texts.values())

    with tempfile.TemporaryDirectory() as temp_dir:
        result = write_online_asr_keys_accounts_review_package(package, temp_dir)
        output_dir = Path(temp_dir)
        assert result.package_id == package.index.package_id
        assert result.package_index_id == package.index.package_index_id
        assert result.file_count == 7
        assert len(result.files) == 7
        assert result.output_directory_role == "user_selected_online_asr_keys_accounts_review_package_directory"
        assert all(file.metadata_only is True for file in result.files)
        assert all(file.local_only is True for file in result.files)
        assert all(file.user_selected_directory_required is True for file in result.files)
        assert all(file.sha256 for file in result.files)
        assert all(file.byte_count > 0 for file in result.files)
        for stored_file in result.files:
            written = output_dir / stored_file.filename
            assert written.exists()
            assert written.read_text(encoding="utf-8") == payload_texts[stored_file.filename]

        try:
            write_online_asr_keys_accounts_review_package(package, temp_dir, allow_overwrite=False)
        except FileExistsError as exc:
            assert "online_asr" in str(exc)
        else:
            raise AssertionError("allow_overwrite=False should refuse existing package files")

        encoded = (
            online_asr_keys_accounts_review_package_store_result_to_json(result)
            + result.to_summary_text()
            + json.dumps({name: json.loads(text) for name, text in payload_texts.items()}, sort_keys=True)
        )
        assert "online_asr_keys_accounts_review_package_store_v1" in encoded
        assert "online_asr_keys_accounts_review_package_v1" in encoded
        assert "provider_call_allowed_without_user_approval" in encoded
        assert "runtime_provider_call_performed" in encoded
        assert "credential_value_read" in encoded
        assert "plaintext_secret_storage_allowed" in encoded
        assert "completed_transcription_claimed" in encoded
        assert "verified_transcription_claimed" in encoded
        assert "Provider call allowed without user approval: false" in encoded
        assert "Credential value read: false" in encoded
        assert "Completed transcription claimed: false" in encoded

        unsafe = encoded.casefold()
        assert temp_dir.casefold() not in unsafe
        assert "actual-secret" not in unsafe
        assert "api_key_value" not in unsafe
        assert "secret_value_recorded\": true" not in unsafe
        assert "c:/users/fahad" not in unsafe
        assert "raw_media_payload_value" not in unsafe
        assert "provider_call_executed" not in unsafe
        assert "completed transcription: true" not in unsafe
        assert "verified transcription: true" not in unsafe


if __name__ == "__main__":
    run_self_test()
    print("Online ASR KEYS/ACCOUNTS review package store self-test passed.")
