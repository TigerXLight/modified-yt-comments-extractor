from __future__ import annotations

import json
import tempfile
from dataclasses import dataclass
from pathlib import Path

from online_asr_keys_accounts_app_state import build_online_asr_keys_accounts_app_state
from online_asr_keys_accounts_review_activity import (
    build_online_asr_keys_accounts_review_activity_document,
    online_asr_keys_accounts_review_activity_document_to_json,
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


def _build_package_and_store_result():
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
        created_at_utc="2026-08-06T22:45:00Z",
        app_version="test",
    )
    with tempfile.TemporaryDirectory() as directory:
        store_result = write_online_asr_keys_accounts_review_package(package, Path(directory))
    return package, store_result


def run_self_test() -> None:
    package, store_result = _build_package_and_store_result()
    document = build_online_asr_keys_accounts_review_activity_document(
        package=package,
        store_result=store_result,
        created_at_utc="2026-08-06T22:46:00Z",
    )
    assert document.package_id == package.index.package_id
    assert document.package_index_id == package.index.package_index_id
    assert document.selected_provider_id == "elevenlabs_scribe_v2"
    assert document.entry_count == 4
    assert document.review_status == "USER_REVIEW_REQUIRED"
    assert document.execution_state == "EXECUTION_GATED"
    assert document.provider_call_allowed_without_user_approval is False
    assert document.runtime_provider_call_performed is False
    assert document.credential_value_read is False
    assert document.full_local_path_included is False
    assert document.completed_transcription_claimed is False

    previous = ""
    for expected_sequence, entry in enumerate(document.entries, start=1):
        assert entry.sequence_number == expected_sequence
        assert entry.previous_activity_sha256 == previous
        assert len(entry.source_sha256) == 64
        assert len(entry.activity_sha256) == 64
        assert entry.activity_id.startswith("online_asr_keys_accounts_activity_")
        assert entry.metadata_only is True
        assert entry.provider_call_allowed_without_user_approval is False
        assert entry.credential_value_read is False
        previous = entry.activity_sha256

    encoded = online_asr_keys_accounts_review_activity_document_to_json(document)
    decoded = json.loads(encoded)
    assert decoded["activity_document_id"] == document.activity_document_id
    assert decoded["entry_count"] == 4
    assert "KEYS/ACCOUNTS" in encoded
    assert "provider_call_allowed_without_user_approval" in encoded
    assert "credential_value_read" in encoded
    assert "completed_transcription_claimed" in encoded
    assert "runtime_provider_call_performed" in encoded
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

    duplicate = build_online_asr_keys_accounts_review_activity_document(
        package=package,
        store_result=store_result,
        created_at_utc="2026-08-06T22:46:00Z",
    )
    assert duplicate.to_dict() == document.to_dict()
    summary = document.to_summary_text()
    assert "Online ASR KEYS/ACCOUNTS review activity" in summary
    assert "Provider call allowed without user approval: false" in summary
    print("Online ASR KEYS/ACCOUNTS review activity self-test passed.")


if __name__ == "__main__":
    run_self_test()
