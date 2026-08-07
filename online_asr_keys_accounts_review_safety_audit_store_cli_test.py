from __future__ import annotations

import io
import json
import tempfile
from pathlib import Path

from online_asr_keys_accounts_review_safety_audit import (
    ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_SAFETY_AUDIT_VERDICT_READY,
)
from online_asr_keys_accounts_review_safety_audit_store import (
    ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_SAFETY_AUDIT_FILENAME,
)
from online_asr_keys_accounts_review_safety_audit_store_cli import (
    ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_SAFETY_AUDIT_STORE_CLI_SCHEMA_VERSION,
    build_online_asr_keys_accounts_review_safety_audit_store_cli_result,
    online_asr_keys_accounts_review_safety_audit_store_cli_result_to_json,
    run_online_asr_keys_accounts_review_safety_audit_store_cli,
)


def _safe_artifact(package_id: str = "online_asr_keys_accounts_safety_audit_store_cli_fixture") -> dict[str, object]:
    return {
        "schema_version": "online_asr_keys_accounts_review_handoff_verifier_store_cli_v1",
        "package_id": package_id,
        "selected_provider_id": "elevenlabs_scribe_v2",
        "review_verdict": "HANDOFF_REVIEW_READY_METADATA_ONLY",
        "issue_count": 0,
        "review_status": "USER_REVIEW_REQUIRED",
        "execution_state": "EXECUTION_GATED",
        "metadata_only": True,
        "local_only": True,
        "user_selected_directory_required": True,
        "keys_accounts_sidebar_label": "KEYS/ACCOUNTS",
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


def test_safety_audit_store_cli_builds_and_persists_safe_json() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        artifact_json = tmp_path / "safe_artifact.json"
        output_dir = tmp_path / "safety_audit"
        artifact_json.write_text(json.dumps(_safe_artifact()), encoding="utf-8")

        stdout = io.StringIO()
        stderr = io.StringIO()
        exit_code = run_online_asr_keys_accounts_review_safety_audit_store_cli(
            [
                "--artifact-json",
                str(artifact_json),
                "--output-directory",
                str(output_dir),
            ],
            stdout=stdout,
            stderr=stderr,
        )
        assert exit_code == 0, stderr.getvalue()
        result = json.loads(stdout.getvalue())
        encoded = json.dumps(result, sort_keys=True)

        assert result["schema_version"] == ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_SAFETY_AUDIT_STORE_CLI_SCHEMA_VERSION
        assert result["review_verdict"] == ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_SAFETY_AUDIT_VERDICT_READY
        assert result["source_artifact_count"] == 1
        assert result["issue_count"] == 0
        assert result["audit_schema_version"] == "online_asr_keys_accounts_review_safety_audit_v1"
        assert result["store_schema_version"] == "online_asr_keys_accounts_review_safety_audit_store_v1"
        assert result["store_output_directory_role"] == (
            "user_selected_online_asr_keys_accounts_review_safety_audit_directory"
        )
        assert result["schema_versions"] == ["online_asr_keys_accounts_review_handoff_verifier_store_cli_v1"]
        assert result["package_ids"] == ["online_asr_keys_accounts_safety_audit_store_cli_fixture"]
        assert result["selected_provider_ids"] == ["elevenlabs_scribe_v2"]
        assert result["stored_file_count"] == 1
        assert result["stored_file_names"] == [ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_SAFETY_AUDIT_FILENAME]
        assert len(result["stored_file_hashes"][0]) == 64
        assert (output_dir / ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_SAFETY_AUDIT_FILENAME).exists()
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
        assert result["keys_accounts_sidebar_label"] == "KEYS/ACCOUNTS"
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


def test_safety_audit_store_cli_accepts_multiple_safe_artifacts() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        artifact_one = tmp_path / "artifact_one.json"
        artifact_two = tmp_path / "artifact_two.json"
        output_dir = tmp_path / "safety_audit"
        artifact_one.write_text(json.dumps(_safe_artifact("package_a")), encoding="utf-8")
        artifact_two.write_text(json.dumps(_safe_artifact("package_b")), encoding="utf-8")

        stdout = io.StringIO()
        stderr = io.StringIO()
        exit_code = run_online_asr_keys_accounts_review_safety_audit_store_cli(
            [
                "--artifact-json",
                str(artifact_one),
                "--artifact-json",
                str(artifact_two),
                "--output-directory",
                str(output_dir),
            ],
            stdout=stdout,
            stderr=stderr,
        )
        assert exit_code == 0, stderr.getvalue()
        result = json.loads(stdout.getvalue())
        assert result["source_artifact_count"] == 2
        assert result["package_ids"] == ["package_a", "package_b"]
        assert result["selected_provider_ids"] == ["elevenlabs_scribe_v2"]


def test_safety_audit_store_cli_summary_is_safe() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        artifact_json = tmp_path / "safe_artifact.json"
        output_dir = tmp_path / "safety_audit"
        artifact_json.write_text(json.dumps(_safe_artifact()), encoding="utf-8")

        stdout = io.StringIO()
        stderr = io.StringIO()
        exit_code = run_online_asr_keys_accounts_review_safety_audit_store_cli(
            [
                "--artifact-json",
                str(artifact_json),
                "--output-directory",
                str(output_dir),
                "--summary",
            ],
            stdout=stdout,
            stderr=stderr,
        )
        assert exit_code == 0, stderr.getvalue()
        summary = stdout.getvalue()
        assert "Online ASR KEYS/ACCOUNTS review safety audit store CLI" in summary
        assert "Review verdict: SAFETY_REVIEW_READY_METADATA_ONLY" in summary
        assert "Source artifacts checked: 1" in summary
        assert "Stored audit files: 1" in summary
        assert "Provider call allowed without user approval: false" in summary
        assert "Credential value read: false" in summary
        assert "Completed transcription claimed: false" in summary
        assert str(tmp_path) not in summary


def test_safety_audit_store_cli_rejects_secret_like_inputs() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        bad_payload = _safe_artifact()
        bad_payload["api_key"] = "should-not-be-here"
        source = tmp_path / "bad_artifact.json"
        source.write_text(json.dumps(bad_payload), encoding="utf-8")
        stdout = io.StringIO()
        stderr = io.StringIO()
        exit_code = run_online_asr_keys_accounts_review_safety_audit_store_cli(
            [
                "--artifact-json",
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


def test_safety_audit_store_cli_refuses_overwrite_when_requested() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        source = tmp_path / "safe_artifact.json"
        output_dir = tmp_path / "safety_audit"
        source.write_text(json.dumps(_safe_artifact()), encoding="utf-8")
        assert run_online_asr_keys_accounts_review_safety_audit_store_cli(
            ["--artifact-json", str(source), "--output-directory", str(output_dir)],
            stdout=io.StringIO(),
            stderr=io.StringIO(),
        ) == 0
        stdout = io.StringIO()
        stderr = io.StringIO()
        exit_code = run_online_asr_keys_accounts_review_safety_audit_store_cli(
            [
                "--artifact-json",
                str(source),
                "--output-directory",
                str(output_dir),
                "--no-overwrite",
            ],
            stdout=stdout,
            stderr=stderr,
        )
        assert exit_code == 3
        assert ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_SAFETY_AUDIT_FILENAME in stderr.getvalue()


def test_safety_audit_store_cli_serialization_is_safe() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        result = build_online_asr_keys_accounts_review_safety_audit_store_cli_result(
            (_safe_artifact(),),
            Path(tmp),
        )
        encoded = online_asr_keys_accounts_review_safety_audit_store_cli_result_to_json(result)
        data = json.loads(encoded)
        assert data["schema_version"] == ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_SAFETY_AUDIT_STORE_CLI_SCHEMA_VERSION
        assert data["review_verdict"] == ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_SAFETY_AUDIT_VERDICT_READY
        assert data["issue_count"] == 0
        assert str(tmp) not in encoded
        assert "C:\\" not in encoded
        assert "T:\\" not in encoded
        assert "api_key" not in encoded
        assert "password" not in encoded


if __name__ == "__main__":
    test_safety_audit_store_cli_builds_and_persists_safe_json()
    test_safety_audit_store_cli_accepts_multiple_safe_artifacts()
    test_safety_audit_store_cli_summary_is_safe()
    test_safety_audit_store_cli_rejects_secret_like_inputs()
    test_safety_audit_store_cli_refuses_overwrite_when_requested()
    test_safety_audit_store_cli_serialization_is_safe()
    print("Online ASR KEYS/ACCOUNTS review safety audit store CLI self-test passed.")
