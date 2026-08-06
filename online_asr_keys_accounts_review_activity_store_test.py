from __future__ import annotations

import json
import tempfile
from dataclasses import dataclass
from pathlib import Path

from online_asr_keys_accounts_app_state import build_online_asr_keys_accounts_app_state
from online_asr_keys_accounts_review_activity import build_online_asr_keys_accounts_review_activity_document
from online_asr_keys_accounts_review_activity_store import (
    ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_ACTIVITY_FILENAME,
    build_online_asr_keys_accounts_review_activity_store_payloads,
    online_asr_keys_accounts_review_activity_store_result_to_json,
    write_online_asr_keys_accounts_review_activity_document,
)
from online_asr_keys_accounts_review_package import build_online_asr_keys_accounts_review_package
from online_asr_keys_accounts_review_package_store import write_online_asr_keys_accounts_review_package
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


def _build_activity_document():
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
        package_id="online_asr_keys_accounts_review_test",
        created_at_utc="2026-08-06T22:50:00Z",
        app_version="test",
    )
    with tempfile.TemporaryDirectory() as directory:
        store_result = write_online_asr_keys_accounts_review_package(package, Path(directory))
    return build_online_asr_keys_accounts_review_activity_document(
        package=package,
        store_result=store_result,
        created_at_utc="2026-08-06T22:51:00Z",
    )


def run_self_test() -> None:
    document = _build_activity_document()
    payloads = build_online_asr_keys_accounts_review_activity_store_payloads(document)
    assert tuple(payloads) == (ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_ACTIVITY_FILENAME,)
    assert document.activity_document_id in payloads[ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_ACTIVITY_FILENAME]

    with tempfile.TemporaryDirectory() as directory:
        result = write_online_asr_keys_accounts_review_activity_document(document, directory)
        output_file = Path(directory) / ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_ACTIVITY_FILENAME
        assert output_file.exists()
        assert output_file.read_text(encoding="utf-8") == payloads[ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_ACTIVITY_FILENAME]
        assert result.activity_document_id == document.activity_document_id
        assert result.package_id == document.package_id
        assert result.package_index_id == document.package_index_id
        assert result.output_directory_role == "user_selected_online_asr_keys_accounts_review_activity_directory"
        assert result.file_count == 1
        assert result.review_status == "USER_REVIEW_REQUIRED"
        assert result.execution_state == "EXECUTION_GATED"
        assert result.provider_call_allowed_without_user_approval is False
        assert result.runtime_provider_call_performed is False
        assert result.credential_value_read is False
        assert result.full_local_path_included is False
        assert result.completed_transcription_claimed is False
        stored_file = result.files[0]
        assert stored_file.filename == ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_ACTIVITY_FILENAME
        assert stored_file.file_role == "online_asr_keys_accounts_review_activity"
        assert len(stored_file.sha256) == 64
        assert stored_file.byte_count > 0
        try:
            write_online_asr_keys_accounts_review_activity_document(document, directory, allow_overwrite=False)
        except FileExistsError as exc:
            assert ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_ACTIVITY_FILENAME in str(exc)
        else:
            raise AssertionError("allow_overwrite=False should refuse existing activity file")

    encoded = online_asr_keys_accounts_review_activity_store_result_to_json(result)
    decoded = json.loads(encoded)
    assert decoded["activity_document_id"] == document.activity_document_id
    assert decoded["file_count"] == 1
    assert "KEYS/ACCOUNTS" in encoded
    assert "provider_call_allowed_without_user_approval" in encoded
    assert "credential_value_read" in encoded
    assert "completed_transcription_claimed" in encoded
    lower = encoded.lower()
    assert "sk-" not in lower
    assert "api_key_value" not in lower
    assert "secret-value-literal" not in lower
    assert "raw media payload bytes" not in lower
    assert "completed transcript" not in lower
    assert "verified transcript" not in lower
    assert ":\\" not in encoded
    assert "/tmp/" not in encoded
    assert "\\temp\\" not in lower

    summary = result.to_summary_text()
    assert "Online ASR KEYS/ACCOUNTS review activity stored" in summary
    assert "Provider call allowed without user approval: false" in summary
    print("Online ASR KEYS/ACCOUNTS review activity store self-test passed.")


if __name__ == "__main__":
    run_self_test()
