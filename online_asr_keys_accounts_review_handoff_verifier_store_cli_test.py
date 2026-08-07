from __future__ import annotations

import io
import json
import tempfile
from pathlib import Path

from online_asr_keys_accounts_review_handoff_verifier import (
    ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_HANDOFF_VERDICT_READY,
)
from online_asr_keys_accounts_review_handoff_verifier_store import (
    ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_HANDOFF_VERIFIER_FILENAME,
)
from online_asr_keys_accounts_review_handoff_verifier_store_cli import (
    ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_HANDOFF_VERIFIER_STORE_CLI_SCHEMA_VERSION,
    build_online_asr_keys_accounts_review_handoff_verifier_store_cli_result,
    online_asr_keys_accounts_review_handoff_verifier_store_cli_result_to_json,
    run_online_asr_keys_accounts_review_handoff_verifier_store_cli,
)


def _safe_handoff_store_cli_result() -> dict[str, object]:
    return {
        "schema_version": "online_asr_keys_accounts_review_handoff_store_cli_v1",
        "package_id": "online_asr_keys_accounts_handoff_verifier_store_cli_fixture",
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
        "stored_file_hashes": ["b" * 64],
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


def test_handoff_verifier_store_cli_builds_and_persists_safe_json() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        handoff_store_cli_json = tmp_path / "handoff_store_cli_result.json"
        output_dir = tmp_path / "handoff_verifier"
        handoff_store_cli_json.write_text(json.dumps(_safe_handoff_store_cli_result()), encoding="utf-8")

        stdout = io.StringIO()
        stderr = io.StringIO()
        exit_code = run_online_asr_keys_accounts_review_handoff_verifier_store_cli(
            [
                "--handoff-store-cli-result-json",
                str(handoff_store_cli_json),
                "--output-directory",
                str(output_dir),
                "--created-at-utc",
                "2026-08-07T02:12:00Z",
            ],
            stdout=stdout,
            stderr=stderr,
        )
        assert exit_code == 0, stderr.getvalue()
        result = json.loads(stdout.getvalue())
        encoded = json.dumps(result, sort_keys=True)

        assert result["schema_version"] == ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_HANDOFF_VERIFIER_STORE_CLI_SCHEMA_VERSION
        assert result["package_id"] == "online_asr_keys_accounts_handoff_verifier_store_cli_fixture"
        assert result["selected_provider_id"] == "elevenlabs_scribe_v2"
        assert result["review_verdict"] == ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_HANDOFF_VERDICT_READY
        assert result["source_review_verdict"] == "REVIEW_READY_METADATA_ONLY"
        assert result["handoff_status"] == "HANDOFF_READY_METADATA_ONLY"
        assert result["issue_count"] == 0
        assert result["required_context_file_count"] == 4
        assert result["stored_handoff_file_count"] == 1
        assert result["stored_file_count"] == 1
        assert result["stored_file_names"] == [ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_HANDOFF_VERIFIER_FILENAME]
        assert len(result["stored_file_hashes"][0]) == 64
        assert result["store_output_directory_role"] == (
            "user_selected_online_asr_keys_accounts_review_handoff_verifier_directory"
        )
        assert (output_dir / ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_HANDOFF_VERIFIER_FILENAME).exists()
        assert str(tmp_path) not in encoded
        assert "C:\\" not in encoded
        assert "T:\\" not in encoded
        assert "api_key" not in encoded
        assert "password" not in encoded
        assert result["review_status"] == "USER_REVIEW_REQUIRED"
        assert result["execution_state"] == "EXECUTION_GATED"
        assert result["metadata_only"] is True
        assert result["local_only"] is True
        assert result["user_selected_directory_required"] is True
        assert result["provider_call_allowed_without_user_approval"] is False
        assert result["runtime_provider_call_performed"] is False
        assert result["credential_value_read"] is False
        assert result["plaintext_secret_storage_allowed"] is False
        assert result["secret_value_recorded"] is False
        assert result["raw_media_payload_included"] is False
        assert result["raw_media_serialized"] is False
        assert result["full_local_path_included"] is False
        assert result["full_local_path_serialized"] is False
        assert result["completed_transcription_claimed"] is False
        assert result["verified_transcription_claimed"] is False


def test_handoff_verifier_store_cli_summary_is_safe() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        handoff_store_cli_json = tmp_path / "handoff_store_cli_result.json"
        output_dir = tmp_path / "handoff_verifier"
        handoff_store_cli_json.write_text(json.dumps(_safe_handoff_store_cli_result()), encoding="utf-8")

        stdout = io.StringIO()
        stderr = io.StringIO()
        exit_code = run_online_asr_keys_accounts_review_handoff_verifier_store_cli(
            [
                "--handoff-store-cli-result-json",
                str(handoff_store_cli_json),
                "--output-directory",
                str(output_dir),
                "--created-at-utc",
                "2026-08-07T02:13:00Z",
                "--summary",
            ],
            stdout=stdout,
            stderr=stderr,
        )
        assert exit_code == 0, stderr.getvalue()
        summary = stdout.getvalue()
        assert "Online ASR KEYS/ACCOUNTS review handoff verifier store CLI" in summary
        assert "Review verdict: HANDOFF_REVIEW_READY_METADATA_ONLY" in summary
        assert "Required context files: 4" in summary
        assert "Stored verifier files: 1" in summary
        assert "Provider call allowed without user approval: false" in summary
        assert "Credential value read: false" in summary
        assert "Completed transcription claimed: false" in summary
        assert str(tmp_path) not in summary


def test_handoff_verifier_store_cli_rejects_secret_like_inputs() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        bad_payload = _safe_handoff_store_cli_result()
        bad_payload["api_key"] = "should-not-be-here"
        source = tmp_path / "bad_handoff_store_cli_result.json"
        source.write_text(json.dumps(bad_payload), encoding="utf-8")
        stdout = io.StringIO()
        stderr = io.StringIO()
        exit_code = run_online_asr_keys_accounts_review_handoff_verifier_store_cli(
            [
                "--handoff-store-cli-result-json",
                str(source),
                "--output-directory",
                str(tmp_path / "out"),
            ],
            stdout=stdout,
            stderr=stderr,
        )
        assert exit_code == 2
        assert "secret-like field 'api_key'" in stderr.getvalue()
        assert stdout.getvalue() == ""


def test_handoff_verifier_store_cli_refuses_overwrite_when_requested() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        source = tmp_path / "handoff_store_cli_result.json"
        output_dir = tmp_path / "handoff_verifier"
        source.write_text(json.dumps(_safe_handoff_store_cli_result()), encoding="utf-8")
        assert run_online_asr_keys_accounts_review_handoff_verifier_store_cli(
            ["--handoff-store-cli-result-json", str(source), "--output-directory", str(output_dir)],
            stdout=io.StringIO(),
            stderr=io.StringIO(),
        ) == 0
        stdout = io.StringIO()
        stderr = io.StringIO()
        exit_code = run_online_asr_keys_accounts_review_handoff_verifier_store_cli(
            [
                "--handoff-store-cli-result-json",
                str(source),
                "--output-directory",
                str(output_dir),
                "--no-overwrite",
            ],
            stdout=stdout,
            stderr=stderr,
        )
        assert exit_code == 3
        assert ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_HANDOFF_VERIFIER_FILENAME in stderr.getvalue()


def test_handoff_verifier_store_cli_serialization_is_safe() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        result = build_online_asr_keys_accounts_review_handoff_verifier_store_cli_result(
            _safe_handoff_store_cli_result(),
            Path(tmp),
            created_at_utc="2026-08-07T02:14:00Z",
        )
        encoded = online_asr_keys_accounts_review_handoff_verifier_store_cli_result_to_json(result)
        data = json.loads(encoded)
        assert data["schema_version"] == ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_HANDOFF_VERIFIER_STORE_CLI_SCHEMA_VERSION
        assert data["review_verdict"] == ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_HANDOFF_VERDICT_READY
        assert data["issue_count"] == 0
        assert str(tmp) not in encoded
        assert "C:\\" not in encoded
        assert "T:\\" not in encoded
        assert "api_key" not in encoded
        assert "password" not in encoded


if __name__ == "__main__":
    test_handoff_verifier_store_cli_builds_and_persists_safe_json()
    test_handoff_verifier_store_cli_summary_is_safe()
    test_handoff_verifier_store_cli_rejects_secret_like_inputs()
    test_handoff_verifier_store_cli_refuses_overwrite_when_requested()
    test_handoff_verifier_store_cli_serialization_is_safe()
    print("Online ASR KEYS/ACCOUNTS review handoff verifier store CLI self-test passed.")
