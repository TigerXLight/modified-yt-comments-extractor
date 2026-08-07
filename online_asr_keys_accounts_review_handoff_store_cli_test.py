from __future__ import annotations

import io
import json
import tempfile
from pathlib import Path

from online_asr_keys_accounts_review_handoff_store_cli import (
    build_online_asr_keys_accounts_review_handoff_store_cli_result,
    online_asr_keys_accounts_review_handoff_store_cli_result_to_json,
    run_online_asr_keys_accounts_review_handoff_store_cli,
)


def _safe_verifier_store_cli_result() -> dict[str, object]:
    return {
        "schema_version": "online_asr_keys_accounts_review_verifier_store_cli_v1",
        "package_id": "online_asr_keys_accounts_handoff_store_cli_fixture",
        "selected_provider_id": "elevenlabs_scribe_v2",
        "review_verdict": "REVIEW_READY_METADATA_ONLY",
        "stored_file_count": 1,
        "stored_file_names": ["online_asr_keys_accounts_review_verification_report.json"],
        "stored_file_hashes": ["f" * 64],
        "review_status": "USER_REVIEW_REQUIRED",
        "execution_state": "EXECUTION_GATED",
        "metadata_only": True,
        "local_only": True,
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


def test_handoff_store_cli_builds_and_persists_safe_json() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        verifier_store_cli_json = tmp_path / "verifier_store_cli_result.json"
        output_dir = tmp_path / "handoff"
        verifier_store_cli_json.write_text(json.dumps(_safe_verifier_store_cli_result()), encoding="utf-8")

        stdout = io.StringIO()
        stderr = io.StringIO()
        exit_code = run_online_asr_keys_accounts_review_handoff_store_cli(
            [
                "--verifier-store-cli-result-json",
                str(verifier_store_cli_json),
                "--output-directory",
                str(output_dir),
                "--created-at-utc",
                "2026-08-07T01:18:00Z",
            ],
            stdout=stdout,
            stderr=stderr,
        )
        assert exit_code == 0, stderr.getvalue()
        result = json.loads(stdout.getvalue())
        encoded = json.dumps(result, sort_keys=True)

        assert result["schema_version"] == "online_asr_keys_accounts_review_handoff_store_cli_v1"
        assert result["package_id"] == "online_asr_keys_accounts_handoff_store_cli_fixture"
        assert result["selected_provider_id"] == "elevenlabs_scribe_v2"
        assert result["review_verdict"] == "REVIEW_READY_METADATA_ONLY"
        assert result["handoff_status"] == "HANDOFF_READY_METADATA_ONLY"
        assert result["issue_count"] == 0
        assert result["completed_workflow_component_count"] >= 19
        assert result["next_session_context_file_count"] == 4
        assert result["next_review_action_count"] == 4
        assert result["reviewed_artifact_count"] == 1
        assert result["stored_file_count"] == 1
        assert result["stored_file_names"] == ["online_asr_keys_accounts_review_handoff.json"]
        assert result["store_output_directory_role"] == "user_selected_online_asr_keys_accounts_review_handoff_directory"
        assert result["provider_call_allowed_without_user_approval"] is False
        assert result["runtime_provider_call_performed"] is False
        assert result["credential_value_read"] is False
        assert result["secret_value_recorded"] is False
        assert result["raw_media_payload_included"] is False
        assert result["raw_media_serialized"] is False
        assert result["full_local_path_included"] is False
        assert result["full_local_path_serialized"] is False
        assert result["completed_transcription_claimed"] is False
        assert result["verified_transcription_claimed"] is False
        assert (output_dir / "online_asr_keys_accounts_review_handoff.json").exists()
        assert str(tmp_path) not in encoded
        assert "api_key" not in encoded
        assert "password" not in encoded


def test_handoff_store_cli_rejects_secret_like_input_fields() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        verifier_store_cli_json = tmp_path / "unsafe_verifier_store_cli_result.json"
        payload = _safe_verifier_store_cli_result()
        payload["token"] = "do-not-store"
        verifier_store_cli_json.write_text(json.dumps(payload), encoding="utf-8")
        stdout = io.StringIO()
        stderr = io.StringIO()
        exit_code = run_online_asr_keys_accounts_review_handoff_store_cli(
            [
                "--verifier-store-cli-result-json",
                str(verifier_store_cli_json),
                "--output-directory",
                str(tmp_path / "handoff"),
            ],
            stdout=stdout,
            stderr=stderr,
        )
        assert exit_code == 2
        assert "secret-like field" in stderr.getvalue()
        assert not (tmp_path / "handoff" / "online_asr_keys_accounts_review_handoff.json").exists()


def test_handoff_store_cli_summary_output_is_safe() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        verifier_store_cli_json = tmp_path / "verifier_store_cli_result.json"
        verifier_store_cli_json.write_text(json.dumps(_safe_verifier_store_cli_result()), encoding="utf-8")
        stdout = io.StringIO()
        stderr = io.StringIO()
        exit_code = run_online_asr_keys_accounts_review_handoff_store_cli(
            [
                "--verifier-store-cli-result-json",
                str(verifier_store_cli_json),
                "--output-directory",
                str(tmp_path / "handoff"),
                "--summary",
            ],
            stdout=stdout,
            stderr=stderr,
        )
        assert exit_code == 0, stderr.getvalue()
        summary = stdout.getvalue()
        assert "Online ASR KEYS/ACCOUNTS review handoff store CLI" in summary
        assert "Handoff status: HANDOFF_READY_METADATA_ONLY" in summary
        assert "Provider call allowed without user approval: false" in summary
        assert "Credential value read: false" in summary
        assert "Completed transcription claimed: false" in summary
        assert str(tmp_path) not in summary
        assert "api_key" not in summary
        assert "password" not in summary


def test_handoff_store_cli_no_overwrite_returns_safe_error_code() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        verifier_store_cli_json = tmp_path / "verifier_store_cli_result.json"
        output_dir = tmp_path / "handoff"
        verifier_store_cli_json.write_text(json.dumps(_safe_verifier_store_cli_result()), encoding="utf-8")
        first_exit = run_online_asr_keys_accounts_review_handoff_store_cli(
            [
                "--verifier-store-cli-result-json",
                str(verifier_store_cli_json),
                "--output-directory",
                str(output_dir),
            ],
            stdout=io.StringIO(),
            stderr=io.StringIO(),
        )
        assert first_exit == 0
        stdout = io.StringIO()
        stderr = io.StringIO()
        second_exit = run_online_asr_keys_accounts_review_handoff_store_cli(
            [
                "--verifier-store-cli-result-json",
                str(verifier_store_cli_json),
                "--output-directory",
                str(output_dir),
                "--no-overwrite",
            ],
            stdout=stdout,
            stderr=stderr,
        )
        assert second_exit == 3
        assert "online_asr_keys_accounts_review_handoff.json" in stderr.getvalue()
        assert str(tmp_path) not in stderr.getvalue()


def test_handoff_store_cli_result_json_is_deterministic_and_safe() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        result = build_online_asr_keys_accounts_review_handoff_store_cli_result(
            _safe_verifier_store_cli_result(),
            Path(tmp) / "handoff",
        )
        encoded_one = online_asr_keys_accounts_review_handoff_store_cli_result_to_json(result)
        encoded_two = online_asr_keys_accounts_review_handoff_store_cli_result_to_json(result)
        assert encoded_one == encoded_two
        assert "online_asr_keys_accounts_review_handoff_store_cli_v1" in encoded_one
        assert "HANDOFF_READY_METADATA_ONLY" in encoded_one
        assert str(tmp) not in encoded_one
        assert "provider_call_allowed_without_user_approval" in encoded_one
        assert "credential_value_read" in encoded_one
        assert "full_local_path_included" in encoded_one


def run_self_test() -> None:
    test_handoff_store_cli_builds_and_persists_safe_json()
    test_handoff_store_cli_rejects_secret_like_input_fields()
    test_handoff_store_cli_summary_output_is_safe()
    test_handoff_store_cli_no_overwrite_returns_safe_error_code()
    test_handoff_store_cli_result_json_is_deterministic_and_safe()
    print("Online ASR KEYS/ACCOUNTS review handoff store CLI self-test passed.")


if __name__ == "__main__":
    run_self_test()
