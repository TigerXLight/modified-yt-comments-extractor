from __future__ import annotations

import json

from online_asr_keys_accounts_review_handoff import (
    ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_HANDOFF_SCHEMA_VERSION,
    OnlineASRReviewHandoffError,
    build_online_asr_keys_accounts_review_handoff_report,
    online_asr_keys_accounts_review_handoff_report_to_json,
)


def _safe_verifier_store_cli_result() -> dict[str, object]:
    return {
        "schema_version": "online_asr_keys_accounts_review_verifier_store_cli_v1",
        "package_id": "pkg-online-asr-review-001",
        "selected_provider_id": "elevenlabs_scribe_v2",
        "review_verdict": "REVIEW_READY_METADATA_ONLY",
        "stored_file_count": 1,
        "stored_file_names": ["online_asr_keys_accounts_review_verification_report.json"],
        "stored_file_hashes": ["f" * 64],
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


def test_handoff_report_builds_safe_metadata_summary() -> None:
    report = build_online_asr_keys_accounts_review_handoff_report(
        _safe_verifier_store_cli_result(),
        created_at_utc="2026-08-07T00:00:00Z",
    )
    data = report.to_dict()
    assert data["schema_version"] == ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_HANDOFF_SCHEMA_VERSION
    assert data["package_id"] == "pkg-online-asr-review-001"
    assert data["selected_provider_id"] == "elevenlabs_scribe_v2"
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
    assert data["raw_media_payload_included"] is False
    assert data["full_local_path_included"] is False
    assert data["completed_transcription_claimed"] is False
    assert data["verified_transcription_claimed"] is False
    assert data["completed_workflow_component_count"] >= 19
    assert "online_asr_keys_accounts_review_verifier_store_cli" in data["completed_workflow_components"]
    assert data["next_session_context_files"][0] == "SOURCE_EVIDENCE_ROADMAP_COVERAGE_AUDIT.md"
    assert data["reviewed_artifact_count"] == 1
    assert data["issue_count"] == 0
    assert len(data["handoff_hash"]) == 64


def test_handoff_report_json_is_deterministic_and_safe() -> None:
    report_one = build_online_asr_keys_accounts_review_handoff_report(
        _safe_verifier_store_cli_result(),
        created_at_utc="2026-08-07T00:00:00Z",
    )
    report_two = build_online_asr_keys_accounts_review_handoff_report(
        _safe_verifier_store_cli_result(),
        created_at_utc="2026-08-07T00:00:00Z",
    )
    encoded_one = online_asr_keys_accounts_review_handoff_report_to_json(report_one)
    encoded_two = online_asr_keys_accounts_review_handoff_report_to_json(report_two)
    assert encoded_one == encoded_two
    data = json.loads(encoded_one)
    assert data["handoff_status"] == "HANDOFF_READY_METADATA_ONLY"
    assert "C:\\" not in encoded_one
    assert "T:\\" not in encoded_one
    assert "/home/" not in encoded_one
    assert "api_key" not in encoded_one
    assert "password" not in encoded_one
    assert "completed_transcription_claimed" in encoded_one


def test_handoff_report_rejects_secret_like_input_fields() -> None:
    payload = _safe_verifier_store_cli_result()
    payload["providers"] = [{"provider_id": "bad", "api_key": "do-not-serialize"}]
    try:
        build_online_asr_keys_accounts_review_handoff_report(payload)
    except OnlineASRReviewHandoffError as exc:
        assert "secret-like field" in str(exc)
    else:
        raise AssertionError("Expected secret-like verifier-store CLI input field to be rejected")


def test_handoff_report_surfaces_safety_issues_without_marking_execution_safe() -> None:
    payload = _safe_verifier_store_cli_result()
    payload["provider_call_allowed_without_user_approval"] = True
    payload["credential_value_read"] = True
    payload["stored_file_count"] = 2
    report = build_online_asr_keys_accounts_review_handoff_report(payload)
    data = report.to_dict()
    assert data["issue_count"] >= 3
    assert data["execution_state"] == "EXECUTION_GATED"
    assert data["review_status"] == "USER_REVIEW_REQUIRED"
    assert data["provider_call_allowed_without_user_approval"] is False
    assert data["credential_value_read"] is False
    assert any("provider_call_allowed_without_user_approval" in item for item in data["issues"])
    assert any("credential_value_read" in item for item in data["issues"])
    assert any("stored_file_count" in item for item in data["issues"])


def test_handoff_summary_text_is_copyable_and_safe() -> None:
    report = build_online_asr_keys_accounts_review_handoff_report(_safe_verifier_store_cli_result())
    summary = report.to_summary_text()
    assert "Online ASR KEYS/ACCOUNTS review handoff" in summary
    assert "Provider call allowed without user approval: false" in summary
    assert "Credential value read: false" in summary
    assert "Completed transcription claimed: false" in summary
    assert "C:\\" not in summary
    assert "T:\\" not in summary


def run_self_test() -> None:
    test_handoff_report_builds_safe_metadata_summary()
    test_handoff_report_json_is_deterministic_and_safe()
    test_handoff_report_rejects_secret_like_input_fields()
    test_handoff_report_surfaces_safety_issues_without_marking_execution_safe()
    test_handoff_summary_text_is_copyable_and_safe()
    print("Online ASR KEYS/ACCOUNTS review handoff self-test passed.")


if __name__ == "__main__":
    run_self_test()
