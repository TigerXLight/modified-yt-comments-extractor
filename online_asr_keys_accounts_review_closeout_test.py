from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from online_asr_keys_accounts_review_closeout import (
    ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_CLOSEOUT_SCHEMA_VERSION,
    build_online_asr_keys_accounts_review_closeout_report,
    online_asr_keys_accounts_review_closeout_report_to_json,
)
from online_asr_keys_accounts_review_smoke_fixture import (
    build_online_asr_keys_accounts_review_smoke_fixture,
)


def test_closeout_report_summarizes_safe_smoke_fixture_without_paths_or_provider_calls() -> None:
    with TemporaryDirectory() as tmp:
        root = Path(tmp) / "closeout-smoke"
        smoke_result = build_online_asr_keys_accounts_review_smoke_fixture(
            root,
            package_id="online_asr_keys_accounts_closeout_fixture",
            created_at_utc="2026-08-07T00:20:00Z",
            app_version="test-app",
            selected_provider_id="elevenlabs_scribe_v2",
        )
        report = build_online_asr_keys_accounts_review_closeout_report(smoke_result)
        encoded = online_asr_keys_accounts_review_closeout_report_to_json(report)
        data = json.loads(encoded)

        assert data["schema_version"] == ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_CLOSEOUT_SCHEMA_VERSION
        assert data["closeout_status"] == "REVIEW_READY_METADATA_ONLY"
        assert data["review_status"] == "USER_REVIEW_REQUIRED"
        assert data["execution_state"] == "EXECUTION_GATED"
        assert data["keys_accounts_sidebar_label"] == "KEYS/ACCOUNTS"
        assert data["selected_provider_id"] == "elevenlabs_scribe_v2"
        assert data["selected_provider_ready_for_gate_review"] is True
        assert data["reviewed_component_count"] >= 10
        assert data["fixture_file_count"] == 3
        assert data["workflow_directory_count"] == 2
        assert data["stored_file_count"] > 0
        assert len(data["closeout_hash"]) == 64
        assert "online_asr_execution_gate" in data["reviewed_components"]
        assert "review_workflow_cli" in data["reviewed_components"]
        assert "smoke_fixture_cli" in data["reviewed_components"]
        assert data["provider_call_allowed_without_user_approval"] is False
        assert data["runtime_provider_call_performed"] is False
        assert data["credential_value_read"] is False
        assert data["credential_plaintext_stored"] is False
        assert data["raw_media_serialized"] is False
        assert data["full_local_path_serialized"] is False
        assert data["completed_transcription_claimed"] is False
        assert data["verified_transcription_claimed"] is False
        assert str(root) not in encoded
        assert "sk-live" not in encoded
        assert "abc123SECRET" not in encoded
        assert "completed transcription: true" not in encoded.lower()

        summary = report.to_summary_text()
        assert "REVIEW_READY_METADATA_ONLY" in summary
        assert "Provider call allowed without user approval: false" in summary
        assert "Credential value read: false" in summary


def test_closeout_report_hash_is_deterministic_for_same_smoke_result() -> None:
    with TemporaryDirectory() as tmp:
        root = Path(tmp) / "deterministic-closeout"
        smoke_result = build_online_asr_keys_accounts_review_smoke_fixture(
            root,
            package_id="online_asr_keys_accounts_closeout_deterministic",
            created_at_utc="2026-08-07T00:21:00Z",
            app_version="test-app",
        )
        first = build_online_asr_keys_accounts_review_closeout_report(smoke_result)
        second = build_online_asr_keys_accounts_review_closeout_report(smoke_result)
        assert first.closeout_hash == second.closeout_hash
        assert first.to_dict() == second.to_dict()


def run_self_test() -> None:
    test_closeout_report_summarizes_safe_smoke_fixture_without_paths_or_provider_calls()
    test_closeout_report_hash_is_deterministic_for_same_smoke_result()
    print("Online ASR KEYS/ACCOUNTS review closeout self-test passed.")


if __name__ == "__main__":
    run_self_test()
