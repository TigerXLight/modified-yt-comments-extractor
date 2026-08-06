from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from online_asr_keys_accounts_review_closeout import build_online_asr_keys_accounts_review_closeout_report
from online_asr_keys_accounts_review_closeout_store import (
    ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_CLOSEOUT_FILENAME,
    build_online_asr_keys_accounts_review_closeout_store_payloads,
    online_asr_keys_accounts_review_closeout_store_result_to_json,
    write_online_asr_keys_accounts_review_closeout_report,
)
from online_asr_keys_accounts_review_smoke_fixture import build_online_asr_keys_accounts_review_smoke_fixture


def test_closeout_store_writes_safe_metadata_only_report_without_paths_or_provider_calls() -> None:
    with TemporaryDirectory() as tmp:
        root = Path(tmp) / "closeout-smoke"
        smoke_result = build_online_asr_keys_accounts_review_smoke_fixture(
            root,
            package_id="online_asr_keys_accounts_closeout_store_fixture",
            created_at_utc="2026-08-07T00:45:00Z",
            app_version="test-app",
            selected_provider_id="elevenlabs_scribe_v2",
        )
        report = build_online_asr_keys_accounts_review_closeout_report(smoke_result)
        payloads = build_online_asr_keys_accounts_review_closeout_store_payloads(report)

        assert tuple(payloads) == (ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_CLOSEOUT_FILENAME,)
        assert "REVIEW_READY_METADATA_ONLY" in payloads[ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_CLOSEOUT_FILENAME]

        out = Path(tmp) / "closeout-store"
        result = write_online_asr_keys_accounts_review_closeout_report(report, out)
        encoded = online_asr_keys_accounts_review_closeout_store_result_to_json(result)
        data = json.loads(encoded)

        assert data["schema_version"] == "online_asr_keys_accounts_review_closeout_store_v1"
        assert data["review_status"] == "USER_REVIEW_REQUIRED"
        assert data["execution_state"] == "EXECUTION_GATED"
        assert data["closeout_status"] == "REVIEW_READY_METADATA_ONLY"
        assert data["keys_accounts_sidebar_label"] == "KEYS/ACCOUNTS"
        assert data["package_id"] == "online_asr_keys_accounts_closeout_store_fixture"
        assert data["selected_provider_id"] == "elevenlabs_scribe_v2"
        assert data["output_directory_role"] == "user_selected_online_asr_keys_accounts_review_closeout_directory"
        assert data["file_count"] == 1
        assert data["files"][0]["filename"] == ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_CLOSEOUT_FILENAME
        assert data["files"][0]["file_role"] == "online_asr_keys_accounts_review_closeout"
        assert len(data["files"][0]["sha256"]) == 64
        assert data["files"][0]["byte_count"] > 0
        assert data["provider_call_allowed_without_user_approval"] is False
        assert data["runtime_provider_call_performed"] is False
        assert data["credential_value_read"] is False
        assert data["plaintext_secret_storage_allowed"] is False
        assert data["secret_value_recorded"] is False
        assert data["raw_media_payload_included"] is False
        assert data["full_local_path_included"] is False
        assert data["completed_transcription_claimed"] is False
        assert data["verified_transcription_claimed"] is False
        assert (out / ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_CLOSEOUT_FILENAME).exists()
        assert str(root) not in encoded
        assert str(out) not in encoded
        assert "sk-live" not in encoded
        assert "abc123SECRET" not in encoded
        assert "provider response" not in encoded.lower()
        assert "completed transcription" not in encoded.lower()

        try:
            write_online_asr_keys_accounts_review_closeout_report(report, out, allow_overwrite=False)
        except FileExistsError as exc:
            assert ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_CLOSEOUT_FILENAME in str(exc)
        else:
            raise AssertionError("Expected overwrite protection to reject existing closeout file")


def run_self_test() -> None:
    test_closeout_store_writes_safe_metadata_only_report_without_paths_or_provider_calls()
    print("Online ASR KEYS/ACCOUNTS review closeout store self-test passed.")


if __name__ == "__main__":
    run_self_test()
