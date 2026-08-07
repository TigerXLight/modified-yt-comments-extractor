from __future__ import annotations

import json

from online_asr_keys_accounts_review_release_gate import (
    ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_RELEASE_GATE_SCHEMA_VERSION,
    ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_RELEASE_GATE_VERDICT_NEEDS_REVIEW,
    ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_RELEASE_GATE_VERDICT_READY,
    REQUIRED_ONLINE_ASR_KEYS_ACCOUNTS_RELEASE_COMPONENT_SCHEMAS,
    build_online_asr_keys_accounts_review_release_gate_report,
    online_asr_keys_accounts_review_release_gate_report_to_json,
)


def _safe_artifact(schema_version: str, package_id: str = "release_gate_fixture") -> dict[str, object]:
    return {
        "schema_version": schema_version,
        "package_id": package_id,
        "selected_provider_id": "elevenlabs_scribe_v2",
        "stored_file_names": [f"{schema_version}.json"],
        "stored_file_hashes": ["a" * 64],
        "issue_count": 0,
        "review_verdict": "READY_METADATA_ONLY",
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


def _safe_chain() -> tuple[dict[str, object], ...]:
    return tuple(
        _safe_artifact(schema_version, f"package_{index}")
        for index, schema_version in enumerate(REQUIRED_ONLINE_ASR_KEYS_ACCOUNTS_RELEASE_COMPONENT_SCHEMAS, start=1)
    )


def test_release_gate_accepts_full_safe_component_chain() -> None:
    report = build_online_asr_keys_accounts_review_release_gate_report(_safe_chain())
    data = report.to_dict()
    encoded = online_asr_keys_accounts_review_release_gate_report_to_json(report)

    assert data["schema_version"] == ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_RELEASE_GATE_SCHEMA_VERSION
    assert data["review_verdict"] == ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_RELEASE_GATE_VERDICT_READY
    assert data["release_gate_ready"] is True
    assert data["source_artifact_count"] == len(REQUIRED_ONLINE_ASR_KEYS_ACCOUNTS_RELEASE_COMPONENT_SCHEMAS)
    assert data["coverage_component_count"] == len(REQUIRED_ONLINE_ASR_KEYS_ACCOUNTS_RELEASE_COMPONENT_SCHEMAS)
    assert data["missing_schema_versions"] == []
    assert data["issue_count"] == 0
    assert data["observed_schema_versions"] == sorted(REQUIRED_ONLINE_ASR_KEYS_ACCOUNTS_RELEASE_COMPONENT_SCHEMAS)
    assert data["selected_provider_ids"] == ["elevenlabs_scribe_v2"]
    assert len(data["stored_file_names"]) == len(REQUIRED_ONLINE_ASR_KEYS_ACCOUNTS_RELEASE_COMPONENT_SCHEMAS)
    assert len(data["stored_file_hashes"]) == 1
    assert data["review_status"] == "USER_REVIEW_REQUIRED"
    assert data["execution_state"] == "EXECUTION_GATED"
    assert data["metadata_only"] is True
    assert data["local_only"] is True
    assert data["user_selected_directory_required"] is True
    assert data["keys_accounts_sidebar_label"] == "KEYS/ACCOUNTS"
    assert data["provider_call_allowed_without_user_approval"] is False
    assert data["runtime_provider_call_performed"] is False
    assert data["credential_value_read"] is False
    assert data["plaintext_secret_storage_allowed"] is False
    assert data["secret_value_recorded"] is False
    assert data["raw_media_payload_included"] is False
    assert data["raw_media_serialized"] is False
    assert data["full_local_path_included"] is False
    assert data["full_local_path_serialized"] is False
    assert data["completed_transcription_claimed"] is False
    assert data["verified_transcription_claimed"] is False
    assert "C:\\" not in encoded
    assert "T:\\" not in encoded
    assert "/mnt/" not in encoded
    assert "api_key" not in encoded
    assert "password" not in encoded


def test_release_gate_reports_missing_required_component() -> None:
    artifacts = _safe_chain()[:-1]
    report = build_online_asr_keys_accounts_review_release_gate_report(artifacts)
    data = report.to_dict()

    assert data["review_verdict"] == ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_RELEASE_GATE_VERDICT_NEEDS_REVIEW
    assert data["release_gate_ready"] is False
    assert data["coverage_component_count"] == len(REQUIRED_ONLINE_ASR_KEYS_ACCOUNTS_RELEASE_COMPONENT_SCHEMAS) - 1
    assert data["missing_schema_versions"] == [REQUIRED_ONLINE_ASR_KEYS_ACCOUNTS_RELEASE_COMPONENT_SCHEMAS[-1]]
    assert any(issue["issue_code"] == "required_component_schema_missing" for issue in data["issues"])


def test_release_gate_reports_unsafe_flags_and_secret_like_fields() -> None:
    artifacts = list(_safe_chain())
    bad = dict(artifacts[0])
    bad["provider_call_allowed_without_user_approval"] = True
    bad["api_key"] = "redacted-but-invalid-field"
    artifacts[0] = bad

    report = build_online_asr_keys_accounts_review_release_gate_report(tuple(artifacts))
    data = report.to_dict()
    issue_codes = {issue["issue_code"] for issue in data["issues"]}

    assert data["release_gate_ready"] is False
    assert "false_safety_flag_not_false" in issue_codes
    assert "secret_like_field_present" in issue_codes
    assert data["review_verdict"] == ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_RELEASE_GATE_VERDICT_NEEDS_REVIEW


def test_release_gate_reports_full_paths_and_transcription_claims() -> None:
    artifacts = list(_safe_chain())
    bad = dict(artifacts[1])
    bad["diagnostic_path"] = r"T:\References\to go\secret.wav"
    bad["completed_transcription_claimed"] = True
    artifacts[1] = bad

    report = build_online_asr_keys_accounts_review_release_gate_report(tuple(artifacts))
    data = report.to_dict()
    issue_codes = {issue["issue_code"] for issue in data["issues"]}

    assert data["release_gate_ready"] is False
    assert "full_local_path_present" in issue_codes
    assert "false_safety_flag_not_false" in issue_codes


def test_release_gate_reports_source_issues_and_needs_review_verdicts() -> None:
    artifacts = list(_safe_chain())
    bad = dict(artifacts[2])
    bad["issue_count"] = 2
    bad["review_verdict"] = "SAFETY_NEEDS_USER_REVIEW"
    artifacts[2] = bad

    report = build_online_asr_keys_accounts_review_release_gate_report(tuple(artifacts))
    data = report.to_dict()
    issue_codes = {issue["issue_code"] for issue in data["issues"]}

    assert data["release_gate_ready"] is False
    assert "source_issue_count_not_zero" in issue_codes
    assert "source_verdict_not_ready" in issue_codes


def test_release_gate_summary_is_safe() -> None:
    report = build_online_asr_keys_accounts_review_release_gate_report(_safe_chain())
    summary = report.to_summary_text()

    assert "Online ASR KEYS/ACCOUNTS review release gate" in summary
    assert "Review verdict: READY_FOR_USER_REVIEW_METADATA_ONLY" in summary
    assert "Release gate ready: true" in summary
    assert "Component coverage: 5/5" in summary
    assert "Issue count: 0" in summary
    assert "Provider call allowed without user approval: false" in summary
    assert "Credential value read: false" in summary
    assert "Completed transcription claimed: false" in summary
    assert "C:\\" not in summary
    assert "T:\\" not in summary


def test_release_gate_json_round_trip_is_safe() -> None:
    report = build_online_asr_keys_accounts_review_release_gate_report(_safe_chain())
    encoded = online_asr_keys_accounts_review_release_gate_report_to_json(report)
    data = json.loads(encoded)

    assert data["schema_version"] == ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_RELEASE_GATE_SCHEMA_VERSION
    assert data["review_verdict"] == ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_RELEASE_GATE_VERDICT_READY
    assert data["release_gate_ready"] is True
    assert data["issue_count"] == 0
    assert "api_key" not in encoded
    assert "password" not in encoded
    assert "C:\\" not in encoded
    assert "T:\\" not in encoded


if __name__ == "__main__":
    test_release_gate_accepts_full_safe_component_chain()
    test_release_gate_reports_missing_required_component()
    test_release_gate_reports_unsafe_flags_and_secret_like_fields()
    test_release_gate_reports_full_paths_and_transcription_claims()
    test_release_gate_reports_source_issues_and_needs_review_verdicts()
    test_release_gate_summary_is_safe()
    test_release_gate_json_round_trip_is_safe()
    print("Online ASR KEYS/ACCOUNTS review release gate self-test passed.")
