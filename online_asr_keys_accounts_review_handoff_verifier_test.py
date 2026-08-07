from __future__ import annotations

import io
import json
import tempfile
from pathlib import Path

from online_asr_keys_accounts_review_handoff_verifier import (
    ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_HANDOFF_VERDICT_NEEDS_REVIEW,
    ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_HANDOFF_VERDICT_READY,
    ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_HANDOFF_VERIFIER_SCHEMA_VERSION,
    OnlineASRHandoffVerifierError,
    build_online_asr_keys_accounts_review_handoff_verification_report,
    online_asr_keys_accounts_review_handoff_verification_report_to_json,
    run_online_asr_keys_accounts_review_handoff_verifier_cli,
)


def _safe_handoff_store_cli_result() -> dict[str, object]:
    return {
        "schema_version": "online_asr_keys_accounts_review_handoff_store_cli_v1",
        "package_id": "online_asr_keys_accounts_handoff_verifier_fixture",
        "selected_provider_id": "elevenlabs_scribe_v2",
        "review_verdict": "REVIEW_READY_METADATA_ONLY",
        "handoff_status": "HANDOFF_READY_METADATA_ONLY",
        "handoff_schema_version": "online_asr_keys_accounts_review_handoff_v1",
        "store_schema_version": "online_asr_keys_accounts_review_handoff_store_v1",
        "store_output_directory_role": "user_selected_online_asr_keys_accounts_review_handoff_directory",
        "issue_count": 0,
        "completed_workflow_component_count": 21,
        "next_session_context_file_count": 4,
        "next_review_action_count": 4,
        "reviewed_artifact_count": 1,
        "stored_file_count": 1,
        "stored_file_names": ["online_asr_keys_accounts_review_handoff.json"],
        "stored_file_hashes": ["a" * 64],
        "review_status": "USER_REVIEW_REQUIRED",
        "execution_state": "EXECUTION_GATED",
        "metadata_only": True,
        "local_only": True,
        "user_selected_directory_required": True,
        "keys_accounts_sidebar_label": "KEYS/ACCOUNTS",
        "keys_accounts_shows_added_providers_only": True,
        "add_provider_searches_full_catalog": True,
        "online_asr_requires_explicit_provider_call_approval": True,
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


def test_handoff_verifier_builds_safe_metadata_report() -> None:
    report = build_online_asr_keys_accounts_review_handoff_verification_report(
        _safe_handoff_store_cli_result(),
        created_at_utc="2026-08-07T01:30:00Z",
    )
    data = report.to_dict()
    assert data["schema_version"] == ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_HANDOFF_VERIFIER_SCHEMA_VERSION
    assert data["package_id"] == "online_asr_keys_accounts_handoff_verifier_fixture"
    assert data["selected_provider_id"] == "elevenlabs_scribe_v2"
    assert data["handoff_status"] == "HANDOFF_READY_METADATA_ONLY"
    assert data["stored_file_count"] == 1
    assert data["stored_file_names"] == ["online_asr_keys_accounts_review_handoff.json"]
    assert data["required_context_files"][0] == "SOURCE_EVIDENCE_ROADMAP_COVERAGE_AUDIT.md"
    assert data["required_context_file_count"] == 4
    assert data["issue_count"] == 0
    assert data["review_verdict"] == ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_HANDOFF_VERDICT_READY
    assert data["keys_accounts_sidebar_label"] == "KEYS/ACCOUNTS"
    assert data["keys_accounts_shows_added_providers_only"] is True
    assert data["add_provider_searches_full_catalog"] is True
    assert data["online_asr_requires_explicit_provider_call_approval"] is True
    assert data["review_status"] == "USER_REVIEW_REQUIRED"
    assert data["execution_state"] == "EXECUTION_GATED"
    assert data["metadata_only"] is True
    assert data["local_only"] is True
    assert data["provider_call_allowed_without_user_approval"] is False
    assert data["runtime_provider_call_performed"] is False
    assert data["credential_value_read"] is False
    assert data["secret_value_recorded"] is False
    assert data["raw_media_payload_included"] is False
    assert data["raw_media_serialized"] is False
    assert data["full_local_path_included"] is False
    assert data["full_local_path_serialized"] is False
    assert data["completed_transcription_claimed"] is False
    assert data["verified_transcription_claimed"] is False


def test_handoff_verifier_json_is_deterministic_and_safe() -> None:
    report_one = build_online_asr_keys_accounts_review_handoff_verification_report(
        _safe_handoff_store_cli_result(),
        created_at_utc="2026-08-07T01:30:00Z",
    )
    report_two = build_online_asr_keys_accounts_review_handoff_verification_report(
        _safe_handoff_store_cli_result(),
        created_at_utc="2026-08-07T01:30:00Z",
    )
    encoded_one = online_asr_keys_accounts_review_handoff_verification_report_to_json(report_one)
    encoded_two = online_asr_keys_accounts_review_handoff_verification_report_to_json(report_two)
    assert encoded_one == encoded_two
    data = json.loads(encoded_one)
    assert data["review_verdict"] == ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_HANDOFF_VERDICT_READY
    assert "C:\\" not in encoded_one
    assert "T:\\" not in encoded_one
    assert "api_key" not in encoded_one
    assert "password" not in encoded_one


def test_handoff_verifier_reports_safety_issues_without_raising_for_bad_flags() -> None:
    payload = _safe_handoff_store_cli_result()
    payload["runtime_provider_call_performed"] = True
    payload["completed_transcription_claimed"] = True
    payload["stored_file_hashes"] = ["not-a-sha256"]
    report = build_online_asr_keys_accounts_review_handoff_verification_report(payload)
    assert report.issue_count >= 3
    assert report.review_verdict == ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_HANDOFF_VERDICT_NEEDS_REVIEW
    joined_issues = "\n".join(report.issues)
    assert "runtime_provider_call_performed must be false" in joined_issues
    assert "completed_transcription_claimed must be false" in joined_issues
    assert "sha256 hex digest" in joined_issues


def test_handoff_verifier_rejects_secret_like_input_fields() -> None:
    payload = _safe_handoff_store_cli_result()
    payload["client_secret"] = "do-not-store"
    try:
        build_online_asr_keys_accounts_review_handoff_verification_report(payload)
    except OnlineASRHandoffVerifierError as exc:
        assert "secret-like field" in str(exc)
    else:  # pragma: no cover - defensive assertion for simple self-test execution.
        raise AssertionError("expected secret-like field rejection")


def test_handoff_verifier_cli_json_and_summary_are_safe() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        handoff_store_cli_json = tmp_path / "handoff_store_cli_result.json"
        handoff_store_cli_json.write_text(json.dumps(_safe_handoff_store_cli_result()), encoding="utf-8")

        stdout = io.StringIO()
        stderr = io.StringIO()
        exit_code = run_online_asr_keys_accounts_review_handoff_verifier_cli(
            [
                "--handoff-store-cli-result-json",
                str(handoff_store_cli_json),
                "--created-at-utc",
                "2026-08-07T01:30:00Z",
            ],
            stdout=stdout,
            stderr=stderr,
        )
        assert exit_code == 0, stderr.getvalue()
        result = json.loads(stdout.getvalue())
        assert result["review_verdict"] == ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_HANDOFF_VERDICT_READY
        assert result["issue_count"] == 0
        assert str(tmp_path) not in stdout.getvalue()

        summary_stdout = io.StringIO()
        summary_stderr = io.StringIO()
        summary_exit = run_online_asr_keys_accounts_review_handoff_verifier_cli(
            [
                "--handoff-store-cli-result-json",
                str(handoff_store_cli_json),
                "--summary",
            ],
            stdout=summary_stdout,
            stderr=summary_stderr,
        )
        assert summary_exit == 0, summary_stderr.getvalue()
        summary = summary_stdout.getvalue()
        assert "Online ASR KEYS/ACCOUNTS review handoff verifier" in summary
        assert "Handoff status: HANDOFF_READY_METADATA_ONLY" in summary
        assert "Provider call allowed without user approval: false" in summary
        assert "Credential value read: false" in summary
        assert "Completed transcription claimed: false" in summary
        assert str(tmp_path) not in summary


def test_handoff_verifier_cli_returns_review_code_for_metadata_issues() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        handoff_store_cli_json = tmp_path / "bad_handoff_store_cli_result.json"
        payload = _safe_handoff_store_cli_result()
        payload["full_local_path_serialized"] = True
        payload["stored_file_count"] = 2
        handoff_store_cli_json.write_text(json.dumps(payload), encoding="utf-8")

        stdout = io.StringIO()
        stderr = io.StringIO()
        exit_code = run_online_asr_keys_accounts_review_handoff_verifier_cli(
            ["--handoff-store-cli-result-json", str(handoff_store_cli_json)],
            stdout=stdout,
            stderr=stderr,
        )
        assert exit_code == 4, stderr.getvalue()
        result = json.loads(stdout.getvalue())
        assert result["review_verdict"] == ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_HANDOFF_VERDICT_NEEDS_REVIEW
        assert result["issue_count"] >= 2


if __name__ == "__main__":
    test_handoff_verifier_builds_safe_metadata_report()
    test_handoff_verifier_json_is_deterministic_and_safe()
    test_handoff_verifier_reports_safety_issues_without_raising_for_bad_flags()
    test_handoff_verifier_rejects_secret_like_input_fields()
    test_handoff_verifier_cli_json_and_summary_are_safe()
    test_handoff_verifier_cli_returns_review_code_for_metadata_issues()
    print("Online ASR KEYS/ACCOUNTS review handoff verifier self-test passed.")
