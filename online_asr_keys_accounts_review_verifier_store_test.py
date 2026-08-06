from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from online_asr_keys_accounts_review_verifier import build_online_asr_keys_accounts_review_verification_report
from online_asr_keys_accounts_review_verifier_store import (
    ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_VERIFIER_FILENAME,
    build_online_asr_keys_accounts_review_verifier_store_payloads,
    online_asr_keys_accounts_review_verifier_store_result_to_json,
    write_online_asr_keys_accounts_review_verification_report,
)


def _safe_closeout_cli_result() -> dict[str, object]:
    return {
        "schema_version": "online_asr_keys_accounts_review_closeout_cli_v1",
        "package_id": "online_asr_keys_accounts_verifier_store_fixture",
        "selected_provider_id": "elevenlabs_scribe_v2",
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
        "full_local_path_included": False,
        "completed_transcription_claimed": False,
        "verified_transcription_claimed": False,
        "stored_file_names": ["online_asr_keys_accounts_review_closeout.json"],
        "stored_file_hashes": ["a" * 64],
        "stored_file_count": 1,
    }


def test_verifier_store_writes_safe_report_without_paths_or_provider_calls() -> None:
    with TemporaryDirectory() as tmp:
        report = build_online_asr_keys_accounts_review_verification_report(
            _safe_closeout_cli_result(),
            created_at_utc="2026-08-07T00:56:00Z",
        )
        assert report.issue_count == 0
        payloads = build_online_asr_keys_accounts_review_verifier_store_payloads(report)

        assert tuple(payloads) == (ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_VERIFIER_FILENAME,)
        assert "REVIEW_READY_METADATA_ONLY" in payloads[ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_VERIFIER_FILENAME]

        out = Path(tmp) / "verifier-store"
        result = write_online_asr_keys_accounts_review_verification_report(report, out)
        encoded = online_asr_keys_accounts_review_verifier_store_result_to_json(result)
        data = json.loads(encoded)

        assert data["schema_version"] == "online_asr_keys_accounts_review_verifier_store_v1"
        assert data["review_status"] == "USER_REVIEW_REQUIRED"
        assert data["execution_state"] == "EXECUTION_GATED"
        assert data["keys_accounts_sidebar_label"] == "KEYS/ACCOUNTS"
        assert data["package_id"] == "online_asr_keys_accounts_verifier_store_fixture"
        assert data["selected_provider_id"] == "elevenlabs_scribe_v2"
        assert data["review_verdict"] == "REVIEW_READY_METADATA_ONLY"
        assert data["issue_count"] == 0
        assert data["output_directory_role"] == "user_selected_online_asr_keys_accounts_review_verifier_directory"
        assert data["file_count"] == 1
        assert data["files"][0]["filename"] == ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_VERIFIER_FILENAME
        assert data["files"][0]["file_role"] == "online_asr_keys_accounts_review_verification_report"
        assert len(data["files"][0]["sha256"]) == 64
        assert (out / ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_VERIFIER_FILENAME).exists()

        forbidden = (
            "api_key",
            "password",
            "provider_call_performed: true",
            "completed transcription",
            "verified transcription",
            str(out),
            str(Path(tmp)),
        )
        lowered = encoded.casefold()
        for item in forbidden:
            assert item.casefold() not in lowered
        assert data["provider_call_allowed_without_user_approval"] is False
        assert data["runtime_provider_call_performed"] is False
        assert data["credential_value_read"] is False
        assert data["full_local_path_included"] is False
        assert data["completed_transcription_claimed"] is False
        assert data["verified_transcription_claimed"] is False


def test_verifier_store_refuses_overwrite_when_requested() -> None:
    with TemporaryDirectory() as tmp:
        report = build_online_asr_keys_accounts_review_verification_report(_safe_closeout_cli_result())
        out = Path(tmp) / "verifier-store"
        write_online_asr_keys_accounts_review_verification_report(report, out)
        try:
            write_online_asr_keys_accounts_review_verification_report(report, out, allow_overwrite=False)
        except FileExistsError as exc:
            assert ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_VERIFIER_FILENAME in str(exc)
        else:  # pragma: no cover - defensive assertion style for script execution.
            raise AssertionError("expected FileExistsError")


def run_self_test() -> None:
    test_verifier_store_writes_safe_report_without_paths_or_provider_calls()
    test_verifier_store_refuses_overwrite_when_requested()
    print("Online ASR KEYS/ACCOUNTS review verifier store self-test passed.")


if __name__ == "__main__":
    run_self_test()
