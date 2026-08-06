from __future__ import annotations

import io
import json
import tempfile
from pathlib import Path

from online_asr_keys_accounts_review_closeout_cli import (
    build_online_asr_keys_accounts_review_closeout_cli_result,
    online_asr_keys_accounts_review_closeout_cli_result_to_json,
    run_online_asr_keys_accounts_review_closeout_cli,
)


def _safe_smoke_fixture_result() -> dict[str, object]:
    return {
        "package_id": "online_asr_keys_accounts_review_package_test",
        "created_at_utc": "2026-08-07T00:00:00Z",
        "selected_provider_id": "elevenlabs_scribe_v2",
        "selected_provider_ready_for_gate_review": True,
        "workflow_result_schema_version": "online_asr_keys_accounts_review_workflow_v1",
        "written_fixture_file_names": [
            "safe_provider_catalog_fixture.json",
            "safe_credential_status_fixture.json",
            "safe_online_asr_execution_gate_summary_fixture.json",
        ],
        "written_workflow_directory_names": [
            "online_asr_keys_accounts_review_activity",
            "online_asr_keys_accounts_review_package",
        ],
        "stored_file_count": 9,
    }


def test_closeout_cli_builds_and_persists_safe_json() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        smoke_json = tmp_path / "smoke_fixture_result.json"
        output_dir = tmp_path / "closeout"
        smoke_json.write_text(json.dumps(_safe_smoke_fixture_result()), encoding="utf-8")

        stdout = io.StringIO()
        stderr = io.StringIO()
        exit_code = run_online_asr_keys_accounts_review_closeout_cli(
            [
                "--smoke-fixture-result-json",
                str(smoke_json),
                "--output-directory",
                str(output_dir),
                "--created-at-utc",
                "2026-08-07T00:00:00Z",
            ],
            stdout=stdout,
            stderr=stderr,
        )
        assert exit_code == 0, stderr.getvalue()
        result = json.loads(stdout.getvalue())
        encoded = json.dumps(result, sort_keys=True)
        assert result["schema_version"] == "online_asr_keys_accounts_review_closeout_cli_v1"
        assert result["stored_file_count"] == 1
        assert result["stored_file_names"] == ["online_asr_keys_accounts_review_closeout.json"]
        assert result["provider_call_allowed_without_user_approval"] is False
        assert result["runtime_provider_call_performed"] is False
        assert result["credential_value_read"] is False
        assert result["secret_value_recorded"] is False
        assert result["raw_media_payload_included"] is False
        assert result["full_local_path_included"] is False
        assert result["completed_transcription_claimed"] is False
        assert result["verified_transcription_claimed"] is False
        assert (output_dir / "online_asr_keys_accounts_review_closeout.json").exists()
        assert str(tmp_path) not in encoded
        assert "api_key" not in encoded
        assert "completed transcription" not in encoded.casefold()


def test_closeout_cli_rejects_secret_like_input_fields() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        smoke_json = tmp_path / "unsafe_smoke_fixture_result.json"
        payload = _safe_smoke_fixture_result()
        payload["api_key"] = "do-not-store"
        smoke_json.write_text(json.dumps(payload), encoding="utf-8")
        stdout = io.StringIO()
        stderr = io.StringIO()
        exit_code = run_online_asr_keys_accounts_review_closeout_cli(
            [
                "--smoke-fixture-result-json",
                str(smoke_json),
                "--output-directory",
                str(tmp_path / "closeout"),
            ],
            stdout=stdout,
            stderr=stderr,
        )
        assert exit_code == 2
        assert "secret-like field" in stderr.getvalue()
        assert not (tmp_path / "closeout" / "online_asr_keys_accounts_review_closeout.json").exists()


def test_closeout_cli_summary_is_safe() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        smoke_json = tmp_path / "smoke_fixture_result.json"
        smoke_json.write_text(json.dumps(_safe_smoke_fixture_result()), encoding="utf-8")
        stdout = io.StringIO()
        stderr = io.StringIO()
        exit_code = run_online_asr_keys_accounts_review_closeout_cli(
            [
                "--smoke-fixture-result-json",
                str(smoke_json),
                "--output-directory",
                str(tmp_path / "closeout"),
                "--summary",
            ],
            stdout=stdout,
            stderr=stderr,
        )
        assert exit_code == 0, stderr.getvalue()
        summary = stdout.getvalue()
        assert "Online ASR KEYS/ACCOUNTS review closeout CLI" in summary
        assert "Provider call allowed without user approval: false" in summary
        assert "Credential value read: false" in summary
        assert "Completed transcription claimed: false" in summary
        assert str(tmp_path) not in summary
        assert "api_key" not in summary


def test_closeout_cli_result_json_is_deterministic_and_safe() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        result = build_online_asr_keys_accounts_review_closeout_cli_result(
            _safe_smoke_fixture_result(),
            Path(tmp) / "closeout",
        )
        encoded_one = online_asr_keys_accounts_review_closeout_cli_result_to_json(result)
        encoded_two = online_asr_keys_accounts_review_closeout_cli_result_to_json(result)
        assert encoded_one == encoded_two
        assert "online_asr_keys_accounts_review_closeout_cli_v1" in encoded_one
        assert str(tmp) not in encoded_one
        assert "provider_call_allowed_without_user_approval" in encoded_one
        assert "credential_value_read" in encoded_one
        assert "full_local_path_included" in encoded_one


def run_self_test() -> None:
    test_closeout_cli_builds_and_persists_safe_json()
    test_closeout_cli_rejects_secret_like_input_fields()
    test_closeout_cli_summary_is_safe()
    test_closeout_cli_result_json_is_deterministic_and_safe()
    print("Online ASR KEYS/ACCOUNTS review closeout CLI self-test passed.")


if __name__ == "__main__":
    run_self_test()
