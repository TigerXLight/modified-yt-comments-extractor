from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from online_asr_keys_accounts_review_smoke_fixture import (
    build_online_asr_keys_accounts_review_smoke_fixture,
    online_asr_keys_accounts_review_smoke_fixture_result_to_json,
)


def test_smoke_fixture_writes_safe_inputs_and_workflow_outputs() -> None:
    with TemporaryDirectory() as tmp:
        root = Path(tmp) / "online-asr-smoke"
        result = build_online_asr_keys_accounts_review_smoke_fixture(
            root,
            package_id="online_asr_keys_accounts_smoke_fixture",
            created_at_utc="2026-08-07T00:04:00Z",
            app_version="test-app",
        )
        encoded = online_asr_keys_accounts_review_smoke_fixture_result_to_json(result)
        data = json.loads(encoded)
        assert data["schema_version"] == "online_asr_keys_accounts_review_smoke_fixture_v1"
        assert data["workflow_result_schema_version"] == "online_asr_keys_accounts_review_workflow_v1"
        assert data["selected_provider_id"] == "elevenlabs_scribe_v2"
        assert data["selected_provider_ready_for_gate_review"] is True
        assert data["provider_count"] == 3
        assert data["credential_status_count"] == 3
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
        assert "online_asr_credential_status.safe.fixture.json" in data["written_fixture_file_names"]
        assert "online_asr_execution_gate_summary.safe.fixture.json" in data["written_fixture_file_names"]
        assert "online_asr_keys_accounts_review_package" in data["written_workflow_directory_names"]
        assert "online_asr_keys_accounts_review_activity" in data["written_workflow_directory_names"]
        assert str(root) not in encoded
        assert "SHOULD_NOT_BE_ACCEPTED" not in encoded
        assert "secret_value" not in encoded
        assert (root / "online_asr_keys_accounts_review_fixture_inputs").is_dir()
        assert (root / "online_asr_keys_accounts_review_workflow_output").is_dir()


def test_smoke_fixture_summary_is_safe_and_review_focused() -> None:
    with TemporaryDirectory() as tmp:
        root = Path(tmp) / "summary-fixture"
        result = build_online_asr_keys_accounts_review_smoke_fixture(
            root,
            package_id="online_asr_keys_accounts_summary_fixture",
            created_at_utc="2026-08-07T00:04:00Z",
        )
        summary = result.to_summary_text()
        assert "Online ASR KEYS/ACCOUNTS smoke fixture" in summary
        assert "ready for gate review" in summary
        assert "Provider call allowed without user approval: false" in summary
        assert "Credential value read: false" in summary
        assert "Completed transcription claimed: false" in summary
        assert str(root) not in summary


def run_self_test() -> None:
    test_smoke_fixture_writes_safe_inputs_and_workflow_outputs()
    test_smoke_fixture_summary_is_safe_and_review_focused()
    print("Online ASR KEYS/ACCOUNTS smoke fixture self-test passed.")


if __name__ == "__main__":
    run_self_test()
