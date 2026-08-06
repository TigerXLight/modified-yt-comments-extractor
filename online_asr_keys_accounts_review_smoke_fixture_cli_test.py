from __future__ import annotations

import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from online_asr_keys_accounts_review_smoke_fixture_cli import (
    run_online_asr_keys_accounts_review_smoke_fixture_cli,
)


def test_smoke_fixture_cli_writes_safe_fixture_and_workflow_outputs() -> None:
    with TemporaryDirectory() as tmp:
        root = Path(tmp) / "cli-smoke"
        stdout = io.StringIO()
        stderr = io.StringIO()
        exit_code = run_online_asr_keys_accounts_review_smoke_fixture_cli(
            [
                "--output-directory",
                str(root),
                "--package-id",
                "online_asr_keys_accounts_cli_smoke_fixture",
                "--created-at-utc",
                "2026-08-07T00:12:00Z",
                "--app-version",
                "test-app",
                "--selected-provider-id",
                "elevenlabs_scribe_v2",
            ],
            stdout=stdout,
            stderr=stderr,
        )
        assert exit_code == 0, stderr.getvalue()
        data = json.loads(stdout.getvalue())
        assert data["schema_version"] == "online_asr_keys_accounts_review_smoke_fixture_v1"
        assert data["workflow_result_schema_version"] == "online_asr_keys_accounts_review_workflow_v1"
        assert data["selected_provider_id"] == "elevenlabs_scribe_v2"
        assert data["selected_provider_ready_for_gate_review"] is True
        assert data["workflow_exit_code"] == 0
        assert data["stored_file_count"] >= 5
        assert data["provider_call_allowed_without_user_approval"] is False
        assert data["credential_value_read"] is False
        assert data["runtime_provider_call_performed"] is False
        assert data["raw_media_serialized"] is False
        assert data["full_local_path_serialized"] is False
        assert data["completed_transcription_claimed"] is False
        assert data["verified_transcription_claimed"] is False
        assert "online_asr_provider_catalog.safe.fixture.json" in data["written_fixture_file_names"]
        assert "online_asr_keys_accounts_review_package" in data["written_workflow_directory_names"]
        assert "online_asr_keys_accounts_review_activity" in data["written_workflow_directory_names"]
        encoded = stdout.getvalue()
        assert str(root) not in encoded
        assert "SHOULD_NOT_BE_ACCEPTED" not in encoded
        assert "secret_value" not in encoded
        assert stderr.getvalue() == ""


def test_smoke_fixture_cli_summary_output_is_safe() -> None:
    with TemporaryDirectory() as tmp:
        root = Path(tmp) / "summary-cli"
        stdout = io.StringIO()
        stderr = io.StringIO()
        exit_code = run_online_asr_keys_accounts_review_smoke_fixture_cli(
            [
                "--output-directory",
                str(root),
                "--package-id",
                "online_asr_keys_accounts_cli_summary_fixture",
                "--created-at-utc",
                "2026-08-07T00:12:00Z",
                "--summary",
            ],
            stdout=stdout,
            stderr=stderr,
        )
        assert exit_code == 0, stderr.getvalue()
        summary = stdout.getvalue()
        assert "Online ASR KEYS/ACCOUNTS smoke fixture" in summary
        assert "Provider call allowed without user approval: false" in summary
        assert "Credential value read: false" in summary
        assert "Completed transcription claimed: false" in summary
        assert str(root) not in summary
        assert stderr.getvalue() == ""


def test_smoke_fixture_cli_rejects_secret_like_input_fields() -> None:
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        provider_json = root / "providers.json"
        provider_json.write_text(
            json.dumps(
                [
                    {
                        "provider_id": "unsafe_provider",
                        "display_name": "Unsafe Provider",
                        "credential_entry_id": "unsafe_status",
                        "api_key": "SHOULD_NOT_BE_ACCEPTED",
                    }
                ]
            ),
            encoding="utf-8",
        )
        stdout = io.StringIO()
        stderr = io.StringIO()
        exit_code = run_online_asr_keys_accounts_review_smoke_fixture_cli(
            [
                "--output-directory",
                str(root / "out"),
                "--package-id",
                "unsafe_fixture",
                "--created-at-utc",
                "2026-08-07T00:12:00Z",
                "--provider-catalog-json",
                str(provider_json),
            ],
            stdout=stdout,
            stderr=stderr,
        )
        assert exit_code == 2
        assert "secret-like field" in stderr.getvalue()
        assert "SHOULD_NOT_BE_ACCEPTED" not in stderr.getvalue()
        assert stdout.getvalue() == ""


def run_self_test() -> None:
    test_smoke_fixture_cli_writes_safe_fixture_and_workflow_outputs()
    test_smoke_fixture_cli_summary_output_is_safe()
    test_smoke_fixture_cli_rejects_secret_like_input_fields()
    print("Online ASR KEYS/ACCOUNTS smoke fixture CLI self-test passed.")


if __name__ == "__main__":
    run_self_test()
