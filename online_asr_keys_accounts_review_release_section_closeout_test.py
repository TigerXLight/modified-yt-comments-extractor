from __future__ import annotations

import json

from online_asr_keys_accounts_review_release_gate import (
    ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_RELEASE_GATE_VERDICT_NEEDS_REVIEW,
    ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_RELEASE_GATE_VERDICT_READY,
)
from online_asr_keys_accounts_review_release_section_closeout import (
    ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_RELEASE_SECTION_CLOSEOUT_SCHEMA_VERSION,
    ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_RELEASE_SECTION_NAME,
    REQUIRED_ONLINE_ASR_KEYS_ACCOUNTS_RELEASE_SECTION_SCHEMAS,
    build_online_asr_keys_accounts_review_release_section_closeout_report,
    online_asr_keys_accounts_review_release_section_closeout_report_to_json,
)


def _safe_artifact(schema_version: str, package_id: str = "release_section_fixture") -> dict[str, object]:
    return {
        "schema_version": schema_version,
        "package_id": package_id,
        "selected_provider_id": "elevenlabs_scribe_v2",
        "stored_file_names": [f"{schema_version}.json"],
        "stored_file_hashes": ["b" * 64],
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


def _safe_section_chain() -> tuple[dict[str, object], ...]:
    return tuple(
        _safe_artifact(schema_version, f"section_package_{index}")
        for index, schema_version in enumerate(REQUIRED_ONLINE_ASR_KEYS_ACCOUNTS_RELEASE_SECTION_SCHEMAS, start=1)
    )


def test_release_section_closeout_is_ready_for_complete_safe_chain() -> None:
    report = build_online_asr_keys_accounts_review_release_section_closeout_report(_safe_section_chain())
    data = report.to_dict()
    encoded = online_asr_keys_accounts_review_release_section_closeout_report_to_json(report)

    assert data["schema_version"] == ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_RELEASE_SECTION_CLOSEOUT_SCHEMA_VERSION
    assert data["roadmap_section"] == ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_RELEASE_SECTION_NAME
    assert data["review_verdict"] == ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_RELEASE_GATE_VERDICT_READY
    assert data["section_ready"] is True
    assert data["issue_count"] == 0
    assert data["coverage_component_count"] == len(REQUIRED_ONLINE_ASR_KEYS_ACCOUNTS_RELEASE_SECTION_SCHEMAS)
    assert data["missing_schema_versions"] == []
    assert "continue_with_next_roadmap_section_as_a_single_mega_patch" in data["next_actions"]
    assert data["keys_accounts_sidebar_label"] == "KEYS/ACCOUNTS"
    assert data["provider_call_allowed_without_user_approval"] is False
    assert data["credential_value_read"] is False
    assert data["completed_transcription_claimed"] is False
    assert "api_key" not in encoded
    assert "password" not in encoded


def test_release_section_closeout_needs_review_for_missing_or_unsafe_artifact() -> None:
    artifacts = list(_safe_section_chain())[:-1]
    unsafe = dict(artifacts[0])
    unsafe["diagnostic_path"] = r"T:\References\private\release_section.json"
    unsafe["completed_transcription_claimed"] = True
    artifacts[0] = unsafe
    report = build_online_asr_keys_accounts_review_release_section_closeout_report(tuple(artifacts))
    data = report.to_dict()
    encoded = json.dumps(data, sort_keys=True)

    assert data["review_verdict"] == ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_RELEASE_GATE_VERDICT_NEEDS_REVIEW
    assert data["section_ready"] is False
    assert data["issue_count"] >= 3
    assert data["missing_schema_versions"] == [REQUIRED_ONLINE_ASR_KEYS_ACCOUNTS_RELEASE_SECTION_SCHEMAS[-1]]
    assert "review_release_section_issues_before_progressing" in data["next_actions"]
    assert "T:\\References\\private" not in encoded
    assert data["completed_transcription_claimed"] is False


def test_release_section_closeout_summary() -> None:
    report = build_online_asr_keys_accounts_review_release_section_closeout_report(_safe_section_chain())
    summary = report.to_summary_text()
    assert "Roadmap section: Online ASR KEYS/ACCOUNTS review release gate" in summary
    assert "Section ready: true" in summary
    assert "Component coverage: 5/5" in summary
    assert "Provider call allowed without user approval: false" in summary
    assert "Credential value read: false" in summary
    assert "Completed transcription claimed: false" in summary


if __name__ == "__main__":
    test_release_section_closeout_is_ready_for_complete_safe_chain()
    test_release_section_closeout_needs_review_for_missing_or_unsafe_artifact()
    test_release_section_closeout_summary()
    print("Online ASR KEYS/ACCOUNTS review release section closeout self-test passed.")
