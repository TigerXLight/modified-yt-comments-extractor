from __future__ import annotations

import json
import tempfile
from pathlib import Path

from online_asr_keys_accounts_review_handoff_verifier import (
    ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_HANDOFF_VERDICT_READY,
    build_online_asr_keys_accounts_review_handoff_verification_report,
)
from online_asr_keys_accounts_review_handoff_verifier_store import (
    ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_HANDOFF_VERIFIER_FILENAME,
    ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_HANDOFF_VERIFIER_STORE_SCHEMA_VERSION,
    build_online_asr_keys_accounts_review_handoff_verifier_store_payloads,
    online_asr_keys_accounts_review_handoff_verifier_store_result_to_json,
    write_online_asr_keys_accounts_review_handoff_verification_report,
)


def _safe_handoff_store_cli_result() -> dict[str, object]:
    return {
        "schema_version": "online_asr_keys_accounts_review_handoff_store_cli_v1",
        "package_id": "online_asr_keys_accounts_handoff_verifier_store_fixture",
        "selected_provider_id": "elevenlabs_scribe_v2",
        "review_verdict": "REVIEW_READY_METADATA_ONLY",
        "handoff_status": "HANDOFF_READY_METADATA_ONLY",
        "handoff_schema_version": "online_asr_keys_accounts_review_handoff_v1",
        "store_schema_version": "online_asr_keys_accounts_review_handoff_store_v1",
        "store_output_directory_role": "user_selected_online_asr_keys_accounts_review_handoff_directory",
        "issue_count": 0,
        "completed_workflow_component_count": 21,
        "next_session_context_file_count": 4,
        "next_review_action_count": 4,
        "reviewed_artifact_count": 1,
        "stored_file_count": 1,
        "stored_file_names": ["online_asr_keys_accounts_review_handoff.json"],
        "stored_file_hashes": ["a" * 64],
        "review_status": "USER_REVIEW_REQUIRED",
        "execution_state": "EXECUTION_GATED",
        "metadata_only": True,
        "local_only": True,
        "user_selected_directory_required": True,
        "keys_accounts_sidebar_label": "KEYS/ACCOUNTS",
        "keys_accounts_shows_added_providers_only": True,
        "add_provider_searches_full_catalog": True,
        "online_asr_requires_explicit_provider_call_approval": True,
        "provider_call_allowed_without_user_approval": False,
        "runtime_provider_call_performed": False,
        "credential_value_read": False,
        "plaintext_secret_storage_allowed": False,
        "secret_value_recorded": False,
        "raw_media_payload_included": False,
        "raw_media_serialized": False,
        "full_local_path_included": False,
        "full_local_path_serialized": False,
        "completed_transcription_claimed": False,
        "verified_transcription_claimed": False,
    }


def _safe_report():
    return build_online_asr_keys_accounts_review_handoff_verification_report(
        _safe_handoff_store_cli_result(),
        created_at_utc="2026-08-07T01:45:00Z",
    )


def test_handoff_verifier_store_payload_is_stable_and_safe() -> None:
    report = _safe_report()
    payloads = build_online_asr_keys_accounts_review_handoff_verifier_store_payloads(report)
    assert list(payloads) == [ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_HANDOFF_VERIFIER_FILENAME]
    encoded = payloads[ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_HANDOFF_VERIFIER_FILENAME]
    data = json.loads(encoded)
    assert data["schema_version"] == "online_asr_keys_accounts_review_handoff_verifier_v1"
    assert data["review_verdict"] == ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_HANDOFF_VERDICT_READY
    assert data["issue_count"] == 0
    assert "C:\\" not in encoded
    assert "T:\\" not in encoded
    assert "api_key" not in encoded
    assert "password" not in encoded


def test_handoff_verifier_store_writes_safe_result_without_full_paths() -> None:
    report = _safe_report()
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        result = write_online_asr_keys_accounts_review_handoff_verification_report(
            report,
            tmp_path,
        )
        data = result.to_dict()
        assert data["schema_version"] == ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_HANDOFF_VERIFIER_STORE_SCHEMA_VERSION
        assert data["package_id"] == "online_asr_keys_accounts_handoff_verifier_store_fixture"
        assert data["selected_provider_id"] == "elevenlabs_scribe_v2"
        assert data["review_verdict"] == ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_HANDOFF_VERDICT_READY
        assert data["source_review_verdict"] == "REVIEW_READY_METADATA_ONLY"
        assert data["handoff_status"] == "HANDOFF_READY_METADATA_ONLY"
        assert data["required_context_file_count"] == 4
        assert data["stored_handoff_file_count"] == 1
        assert data["file_count"] == 1
        assert data["output_directory_role"] == (
            "user_selected_online_asr_keys_accounts_review_handoff_verifier_directory"
        )
        assert data["files"][0]["filename"] == ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_HANDOFF_VERIFIER_FILENAME
        assert data["files"][0]["file_role"] == (
            "online_asr_keys_accounts_review_handoff_verification_report"
        )
        assert len(data["files"][0]["sha256"]) == 64
        written = tmp_path / ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_HANDOFF_VERIFIER_FILENAME
        assert written.exists()
        assert data["files"][0]["byte_count"] == len(written.read_bytes())
        encoded = online_asr_keys_accounts_review_handoff_verifier_store_result_to_json(result)
        assert str(tmp_path) not in encoded
        assert "C:\\" not in encoded
        assert "T:\\" not in encoded
        assert "api_key" not in encoded
        assert "password" not in encoded
        assert data["review_status"] == "USER_REVIEW_REQUIRED"
        assert data["execution_state"] == "EXECUTION_GATED"
        assert data["metadata_only"] is True
        assert data["local_only"] is True
        assert data["user_selected_directory_required"] is True
        assert data["provider_call_allowed_without_user_approval"] is False
        assert data["runtime_provider_call_performed"] is False
        assert data["credential_value_read"] is False
        assert data["secret_value_recorded"] is False
        assert data["raw_media_payload_included"] is False
        assert data["raw_media_serialized"] is False
        assert data["full_local_path_included"] is False
        assert data["full_local_path_serialized"] is False
        assert data["completed_transcription_claimed"] is False
        assert data["verified_transcription_claimed"] is False


def test_handoff_verifier_store_refuses_overwrite_when_requested() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        report = _safe_report()
        write_online_asr_keys_accounts_review_handoff_verification_report(report, tmp_path)
        try:
            write_online_asr_keys_accounts_review_handoff_verification_report(
                report,
                tmp_path,
                allow_overwrite=False,
            )
        except FileExistsError as exc:
            assert ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_HANDOFF_VERIFIER_FILENAME in str(exc)
        else:  # pragma: no cover - defensive assertion for simple self-test execution.
            raise AssertionError("expected overwrite refusal")


def test_handoff_verifier_store_summary_is_safe() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        result = write_online_asr_keys_accounts_review_handoff_verification_report(
            _safe_report(),
            Path(tmp),
        )
        summary = result.to_summary_text()
        assert "Online ASR KEYS/ACCOUNTS review handoff verifier stored" in summary
        assert "Review verdict: HANDOFF_REVIEW_READY_METADATA_ONLY" in summary
        assert "Required context files: 4" in summary
        assert "Provider call allowed without user approval: false" in summary
        assert "Credential value read: false" in summary
        assert "Completed transcription claimed: false" in summary
        assert str(tmp) not in summary


if __name__ == "__main__":
    test_handoff_verifier_store_payload_is_stable_and_safe()
    test_handoff_verifier_store_writes_safe_result_without_full_paths()
    test_handoff_verifier_store_refuses_overwrite_when_requested()
    test_handoff_verifier_store_summary_is_safe()
    print("Online ASR KEYS/ACCOUNTS review handoff verifier store self-test passed.")
