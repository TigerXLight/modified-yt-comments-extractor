from __future__ import annotations

import io
import json
import tempfile
from pathlib import Path

from online_asr_keys_accounts_review_verifier import (
    build_online_asr_keys_accounts_review_verification_report,
    online_asr_keys_accounts_review_verification_report_to_json,
    run_online_asr_keys_accounts_review_verifier_cli,
)


def _safe_closeout_cli_result() -> dict[str, object]:
    return {
        "schema_version": "online_asr_keys_accounts_review_closeout_cli_v1",
        "package_id": "online_asr_keys_accounts_review_package_test",
        "selected_provider_id": "elevenlabs_scribe_v2",
        "closeout_status": "REVIEW_READY_METADATA_ONLY",
        "report_schema_version": "online_asr_keys_accounts_review_closeout_v1",
        "store_schema_version": "online_asr_keys_accounts_review_closeout_store_v1",
        "stored_file_count": 1,
        "stored_file_names": ["online_asr_keys_accounts_review_closeout.json"],
        "stored_file_hashes": ["a" * 64],
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
    }


def _safe_closeout_report() -> dict[str, object]:
    return {
        "schema_version": "online_asr_keys_accounts_review_closeout_v1",
        "package_id": "online_asr_keys_accounts_review_package_test",
        "selected_provider_id": "elevenlabs_scribe_v2",
        "closeout_status": "REVIEW_READY_METADATA_ONLY",
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
    }


def test_verifier_accepts_safe_closeout_payloads() -> None:
    report = build_online_asr_keys_accounts_review_verification_report(
        _safe_closeout_cli_result(),
        _safe_closeout_report(),
        created_at_utc="2026-08-07T00:00:00Z",
    )
    data = report.to_dict()
    encoded = json.dumps(data, sort_keys=True)
    assert data["schema_version"] == "online_asr_keys_accounts_review_verifier_v1"
    assert data["review_verdict"] == "REVIEW_READY_METADATA_ONLY"
    assert data["issue_count"] == 0
    assert data["reviewed_artifact_names"] == ["closeout_cli_result", "closeout_report"]
    assert data["stored_file_names"] == ["online_asr_keys_accounts_review_closeout.json"]
    assert data["provider_call_allowed_without_user_approval"] is False
    assert data["runtime_provider_call_performed"] is False
    assert data["credential_value_read"] is False
    assert data["secret_value_recorded"] is False
    assert data["raw_media_payload_included"] is False
    assert data["full_local_path_included"] is False
    assert data["completed_transcription_claimed"] is False
    assert data["verified_transcription_claimed"] is False
    assert "api_key" not in encoded
    assert "completed transcription" not in encoded.casefold()


def test_verifier_reports_unsafe_flags_without_running_provider_calls() -> None:
    payload = _safe_closeout_cli_result()
    payload["runtime_provider_call_performed"] = True
    payload["stored_file_count"] = 2
    report = build_online_asr_keys_accounts_review_verification_report(payload)
    assert report.review_verdict == "NEEDS_USER_REVIEW"
    assert report.issue_count >= 2
    joined = "\n".join(report.issues)
    assert "runtime_provider_call_performed must be false" in joined
    assert "stored_file_count must match" in joined
    assert report.provider_call_allowed_without_user_approval is False
    assert report.credential_value_read is False


def test_verifier_rejects_secret_like_input_fields() -> None:
    payload = _safe_closeout_cli_result()
    payload["api_key"] = "do-not-read"
    try:
        build_online_asr_keys_accounts_review_verification_report(payload)
    except ValueError as exc:
        assert "secret-like field" in str(exc)
    else:  # pragma: no cover - defensive assertion for self-test clarity.
        raise AssertionError("secret-like field was not rejected")


def test_verifier_cli_prints_safe_json_and_summary() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        closeout_cli_json = tmp_path / "closeout_cli_result.json"
        closeout_report_json = tmp_path / "closeout_report.json"
        closeout_cli_json.write_text(json.dumps(_safe_closeout_cli_result()), encoding="utf-8")
        closeout_report_json.write_text(json.dumps(_safe_closeout_report()), encoding="utf-8")

        stdout = io.StringIO()
        stderr = io.StringIO()
        exit_code = run_online_asr_keys_accounts_review_verifier_cli(
            [
                "--closeout-cli-result-json",
                str(closeout_cli_json),
                "--closeout-report-json",
                str(closeout_report_json),
            ],
            stdout=stdout,
            stderr=stderr,
        )
        assert exit_code == 0, stderr.getvalue()
        data = json.loads(stdout.getvalue())
        assert data["review_verdict"] == "REVIEW_READY_METADATA_ONLY"
        assert str(tmp_path) not in stdout.getvalue()

        summary_stdout = io.StringIO()
        exit_code = run_online_asr_keys_accounts_review_verifier_cli(
            [
                "--closeout-cli-result-json",
                str(closeout_cli_json),
                "--summary",
            ],
            stdout=summary_stdout,
            stderr=io.StringIO(),
        )
        assert exit_code == 0
        summary = summary_stdout.getvalue()
        assert "Online ASR KEYS/ACCOUNTS review verifier" in summary
        assert "Provider call allowed without user approval: false" in summary
        assert "Credential value read: false" in summary
        assert "Completed transcription claimed: false" in summary
        assert str(tmp_path) not in summary


def test_verifier_json_is_deterministic() -> None:
    report = build_online_asr_keys_accounts_review_verification_report(_safe_closeout_cli_result())
    first = online_asr_keys_accounts_review_verification_report_to_json(report)
    second = online_asr_keys_accounts_review_verification_report_to_json(report)
    assert first == second
    assert "online_asr_keys_accounts_review_verifier_v1" in first
    assert "provider_call_allowed_without_user_approval" in first
    assert "credential_value_read" in first
    assert "full_local_path_included" in first


def run_self_test() -> None:
    test_verifier_accepts_safe_closeout_payloads()
    test_verifier_reports_unsafe_flags_without_running_provider_calls()
    test_verifier_rejects_secret_like_input_fields()
    test_verifier_cli_prints_safe_json_and_summary()
    test_verifier_json_is_deterministic()
    print("Online ASR KEYS/ACCOUNTS review verifier self-test passed.")


if __name__ == "__main__":
    run_self_test()
