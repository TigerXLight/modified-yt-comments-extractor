from __future__ import annotations

import json

from online_asr_keys_accounts_review_safety_audit import (
    ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_SAFETY_AUDIT_SCHEMA_VERSION,
    ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_SAFETY_AUDIT_VERDICT_NEEDS_REVIEW,
    ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_SAFETY_AUDIT_VERDICT_READY,
    OnlineASRKeysAccountsReviewSafetyAuditError,
    build_online_asr_keys_accounts_review_safety_audit_report,
    online_asr_keys_accounts_review_safety_audit_report_to_json,
)


def _safe_handoff_verifier_store_cli_result() -> dict[str, object]:
    return {
        "schema_version": "online_asr_keys_accounts_review_handoff_verifier_store_cli_v1",
        "package_id": "online_asr_keys_accounts_safety_audit_fixture",
        "selected_provider_id": "elevenlabs_scribe_v2",
        "review_verdict": "HANDOFF_REVIEW_READY_METADATA_ONLY",
        "source_review_verdict": "REVIEW_READY_METADATA_ONLY",
        "handoff_status": "HANDOFF_READY_METADATA_ONLY",
        "handoff_store_cli_schema_version": "online_asr_keys_accounts_review_handoff_store_cli_v1",
        "verifier_schema_version": "online_asr_keys_accounts_review_handoff_verifier_v1",
        "store_schema_version": "online_asr_keys_accounts_review_handoff_verifier_store_v1",
        "store_output_directory_role": "user_selected_online_asr_keys_accounts_review_handoff_verifier_directory",
        "issue_count": 0,
        "required_context_file_count": 4,
        "stored_handoff_file_count": 1,
        "stored_file_count": 1,
        "stored_file_names": ["online_asr_keys_accounts_review_handoff_verifier.json"],
        "stored_file_hashes": ["a" * 64],
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


def test_safety_audit_accepts_safe_metadata_only_artifact() -> None:
    report = build_online_asr_keys_accounts_review_safety_audit_report(
        _safe_handoff_verifier_store_cli_result()
    )
    data = report.to_dict()
    encoded = online_asr_keys_accounts_review_safety_audit_report_to_json(report)

    assert data["schema_version"] == ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_SAFETY_AUDIT_SCHEMA_VERSION
    assert data["review_verdict"] == ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_SAFETY_AUDIT_VERDICT_READY
    assert data["source_artifact_count"] == 1
    assert data["issue_count"] == 0
    assert data["issues"] == []
    assert data["package_ids"] == ["online_asr_keys_accounts_safety_audit_fixture"]
    assert data["selected_provider_ids"] == ["elevenlabs_scribe_v2"]
    assert data["false_safety_flag_count"] == 11
    assert data["true_safety_flag_count"] == 3
    assert data["expected_text_field_count"] == 3
    assert data["review_status"] == "USER_REVIEW_REQUIRED"
    assert data["execution_state"] == "EXECUTION_GATED"
    assert data["keys_accounts_sidebar_label"] == "KEYS/ACCOUNTS"
    assert data["provider_call_allowed_without_user_approval"] is False
    assert data["credential_value_read"] is False
    assert data["completed_transcription_claimed"] is False
    assert "C:\\" not in encoded
    assert "T:\\" not in encoded
    assert "api_key" not in encoded
    assert "password" not in encoded


def test_safety_audit_combines_multiple_safe_artifacts() -> None:
    first = _safe_handoff_verifier_store_cli_result()
    second = _safe_handoff_verifier_store_cli_result()
    second["schema_version"] = "online_asr_keys_accounts_review_closeout_cli_v1"
    second["package_id"] = "online_asr_keys_accounts_second_fixture"
    second["selected_provider_id"] = "local_whispercpp_large_v3_vulkan_reference"

    report = build_online_asr_keys_accounts_review_safety_audit_report([first, second])
    data = report.to_dict()

    assert data["review_verdict"] == ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_SAFETY_AUDIT_VERDICT_READY
    assert data["source_artifact_count"] == 2
    assert data["issue_count"] == 0
    assert data["schema_versions"] == [
        "online_asr_keys_accounts_review_closeout_cli_v1",
        "online_asr_keys_accounts_review_handoff_verifier_store_cli_v1",
    ]
    assert data["package_ids"] == [
        "online_asr_keys_accounts_safety_audit_fixture",
        "online_asr_keys_accounts_second_fixture",
    ]
    assert data["selected_provider_ids"] == [
        "elevenlabs_scribe_v2",
        "local_whispercpp_large_v3_vulkan_reference",
    ]


def test_safety_audit_reports_flags_without_leaking_secret_values() -> None:
    bad = _safe_handoff_verifier_store_cli_result()
    bad["credential_value_read"] = True
    bad["provider_call_allowed_without_user_approval"] = True
    bad["api_key"] = "super-secret-value-that-must-not-leak"
    bad["nested"] = {"client_secret": "nested-super-secret"}

    report = build_online_asr_keys_accounts_review_safety_audit_report(bad)
    encoded = online_asr_keys_accounts_review_safety_audit_report_to_json(report)
    issue_codes = {issue["issue_code"] for issue in json.loads(encoded)["issues"]}

    assert report.review_verdict == ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_SAFETY_AUDIT_VERDICT_NEEDS_REVIEW
    assert report.issue_count == 4
    assert "false_safety_flag_not_false" in issue_codes
    assert "secret_like_field_present" in issue_codes
    assert "super-secret-value-that-must-not-leak" not in encoded
    assert "nested-super-secret" not in encoded


def test_safety_audit_reports_full_paths_and_transcription_claims() -> None:
    bad = _safe_handoff_verifier_store_cli_result()
    bad["full_local_path_included"] = True
    bad["completed_transcription_claimed"] = True
    bad["output"] = "T:\\References\\private\\out.json"

    report = build_online_asr_keys_accounts_review_safety_audit_report(bad)
    data = report.to_dict()
    issue_codes = [issue["issue_code"] for issue in data["issues"]]

    assert data["review_verdict"] == ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_SAFETY_AUDIT_VERDICT_NEEDS_REVIEW
    assert data["issue_count"] == 3
    assert issue_codes.count("false_safety_flag_not_false") == 2
    assert "full_local_path_value_present" in issue_codes
    assert "T:\\References" not in json.dumps(data)


def test_safety_audit_summary_is_safe_and_rejects_bad_container() -> None:
    report = build_online_asr_keys_accounts_review_safety_audit_report(
        _safe_handoff_verifier_store_cli_result()
    )
    summary = report.to_summary_text()
    assert "Online ASR KEYS/ACCOUNTS review safety audit" in summary
    assert "Review verdict: SAFETY_REVIEW_READY_METADATA_ONLY" in summary
    assert "Provider call allowed without user approval: false" in summary
    assert "Credential value read: false" in summary
    assert "Completed transcription claimed: false" in summary

    try:
        build_online_asr_keys_accounts_review_safety_audit_report([])
    except OnlineASRKeysAccountsReviewSafetyAuditError as exc:
        assert "at least one artifact" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("empty artifact list should fail")


if __name__ == "__main__":
    test_safety_audit_accepts_safe_metadata_only_artifact()
    test_safety_audit_combines_multiple_safe_artifacts()
    test_safety_audit_reports_flags_without_leaking_secret_values()
    test_safety_audit_reports_full_paths_and_transcription_claims()
    test_safety_audit_summary_is_safe_and_rejects_bad_container()
    print("Online ASR KEYS/ACCOUNTS review safety audit self-test passed.")
