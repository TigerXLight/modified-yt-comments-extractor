from __future__ import annotations

import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from online_asr_keys_accounts_review_workflow_cli import (
    run_online_asr_keys_accounts_review_workflow_cli,
)


def _write_json(path: Path, data: object) -> None:
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def test_cli_builds_safe_workflow_result_and_writes_metadata_files() -> None:
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        provider_json = root / "providers.json"
        status_json = root / "statuses.json"
        output_dir = root / "workflow-output"
        _write_json(
            provider_json,
            [
                {
                    "provider_id": "elevenlabs_scribe_v2",
                    "display_name": "ElevenLabs Scribe v2",
                    "provider_family": "elevenlabs",
                    "model_id": "scribe_v2",
                    "credential_entry_id": "elevenlabs_api_key",
                    "supports_keyterms": True,
                    "tags": ["cloud", "online-asr"],
                    "recommended_for": ["keyterms"],
                },
                {
                    "provider_id": "cohere_asr",
                    "display_name": "Cohere ASR",
                    "provider_family": "cohere",
                    "model_id": "asr",
                    "credential_entry_id": "cohere_api_key",
                },
            ],
        )
        _write_json(
            status_json,
            {
                "elevenlabs_api_key": {"state": "CONFIGURED"},
                "cohere_api_key": "MISSING",
            },
        )
        stdout = io.StringIO()
        stderr = io.StringIO()
        code = run_online_asr_keys_accounts_review_workflow_cli(
            [
                "--provider-catalog-json", str(provider_json),
                "--credential-status-json", str(status_json),
                "--output-directory", str(output_dir),
                "--package-id", "online_asr_keys_accounts_review_cli_fixture",
                "--created-at-utc", "2026-08-06T23:59:00Z",
                "--app-version", "test-app",
                "--added-provider-id", "elevenlabs_scribe_v2",
                "--selected-provider-id", "elevenlabs_scribe_v2",
                "--keys-accounts-query", "scribe",
                "--add-provider-query", "asr",
            ],
            stdout=stdout,
            stderr=stderr,
        )
        assert code == 0, stderr.getvalue()
        encoded = stdout.getvalue()
        data = json.loads(encoded)
        assert data["schema_version"] == "online_asr_keys_accounts_review_workflow_v1"
        assert data["selected_provider_id"] == "elevenlabs_scribe_v2"
        assert data["selected_provider_ready_for_gate_review"] is True
        assert data["stored_file_count"] >= 5
        assert data["provider_call_allowed_without_user_approval"] is False
        assert data["credential_value_read"] is False
        assert data["runtime_provider_call_performed"] is False
        assert data["completed_transcription_claimed"] is False
        assert data["verified_transcription_claimed"] is False
        assert str(output_dir) not in encoded
        assert "full_local_path" in encoded
        assert "SHOULD_NOT_BE_ACCEPTED" not in encoded
        assert (output_dir / "online_asr_keys_accounts_review_package").is_dir()
        assert (output_dir / "online_asr_keys_accounts_review_activity").is_dir()


def test_cli_rejects_secret_like_input_fields() -> None:
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        provider_json = root / "providers.json"
        _write_json(
            provider_json,
            [
                {
                    "provider_id": "unsafe_provider",
                    "display_name": "Unsafe Provider",
                    "provider_family": "unsafe",
                    "model_id": "unsafe",
                    "credential_entry_id": "unsafe_credential",
                    "api_key": "SHOULD_NOT_BE_ACCEPTED",
                }
            ],
        )
        stdout = io.StringIO()
        stderr = io.StringIO()
        code = run_online_asr_keys_accounts_review_workflow_cli(
            [
                "--provider-catalog-json", str(provider_json),
                "--output-directory", str(root / "out"),
                "--package-id", "unsafe_fixture",
                "--created-at-utc", "2026-08-06T23:59:00Z",
            ],
            stdout=stdout,
            stderr=stderr,
        )
        assert code == 2
        assert "secret-like field" in stderr.getvalue()
        assert stdout.getvalue() == ""


def test_cli_summary_output_is_safe_and_human_readable() -> None:
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        provider_json = root / "providers.json"
        _write_json(
            provider_json,
            [
                {
                    "provider_id": "elevenlabs_scribe_v2",
                    "display_name": "ElevenLabs Scribe v2",
                    "provider_family": "elevenlabs",
                    "model_id": "scribe_v2",
                    "credential_entry_id": "elevenlabs_api_key",
                }
            ],
        )
        stdout = io.StringIO()
        stderr = io.StringIO()
        code = run_online_asr_keys_accounts_review_workflow_cli(
            [
                "--provider-catalog-json", str(provider_json),
                "--output-directory", str(root / "out"),
                "--package-id", "summary_fixture",
                "--created-at-utc", "2026-08-06T23:59:00Z",
                "--selected-provider-id", "elevenlabs_scribe_v2",
                "--summary",
            ],
            stdout=stdout,
            stderr=stderr,
        )
        assert code == 0, stderr.getvalue()
        summary = stdout.getvalue()
        assert "Online ASR KEYS/ACCOUNTS review workflow" in summary
        assert "needs key/account" in summary
        assert "Provider call allowed without user approval: false" in summary
        assert "Credential value read: false" in summary
        assert "Completed transcription claimed: false" in summary
        assert str(root / "out") not in summary


def run_self_test() -> None:
    test_cli_builds_safe_workflow_result_and_writes_metadata_files()
    test_cli_rejects_secret_like_input_fields()
    test_cli_summary_output_is_safe_and_human_readable()
    print("Online ASR KEYS/ACCOUNTS review workflow CLI self-test passed.")


if __name__ == "__main__":
    run_self_test()
