from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from online_asr_keys_accounts_review_handoff import build_online_asr_keys_accounts_review_handoff_report
from online_asr_keys_accounts_review_handoff_store import (
    ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_HANDOFF_FILENAME,
    build_online_asr_keys_accounts_review_handoff_store_payloads,
    online_asr_keys_accounts_review_handoff_store_result_to_json,
    write_online_asr_keys_accounts_review_handoff_report,
)


def _safe_verifier_store_cli_result() -> dict[str, object]:
    return {
        "schema_version": "online_asr_keys_accounts_review_verifier_store_cli_v1",
        "package_id": "online_asr_keys_accounts_handoff_store_fixture",
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
        "raw_media_serialized": False,
        "full_local_path_included": False,
        "full_local_path_serialized": False,
        "completed_transcription_claimed": False,
        "verified_transcription_claimed": False,
    }


def test_handoff_store_writes_safe_report_without_paths_or_provider_calls() -> None:
    with TemporaryDirectory() as tmp:
        report = build_online_asr_keys_accounts_review_handoff_report(
            _safe_verifier_store_cli_result(),
            created_at_utc="2026-08-07T01:12:00Z",
        )
        assert report.issue_count == 0
        payloads = build_online_asr_keys_accounts_review_handoff_store_payloads(report)

        assert tuple(payloads) == (ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_HANDOFF_FILENAME,)
        assert "HANDOFF_READY_METADATA_ONLY" in payloads[ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_HANDOFF_FILENAME]
        assert "SOURCE_EVIDENCE_ROADMAP_COVERAGE_AUDIT.md" in payloads[ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_HANDOFF_FILENAME]

        out = Path(tmp) / "handoff-store"
        result = write_online_asr_keys_accounts_review_handoff_report(report, out)
        encoded = online_asr_keys_accounts_review_handoff_store_result_to_json(result)
        data = json.loads(encoded)

        assert data["schema_version"] == "online_asr_keys_accounts_review_handoff_store_v1"
        assert data["review_status"] == "USER_REVIEW_REQUIRED"
        assert data["execution_state"] == "EXECUTION_GATED"
        assert data["keys_accounts_sidebar_label"] == "KEYS/ACCOUNTS"
        assert data["keys_accounts_shows_added_providers_only"] is True
        assert data["add_provider_searches_full_catalog"] is True
        assert data["online_asr_requires_explicit_provider_call_approval"] is True
        assert data["package_id"] == "online_asr_keys_accounts_handoff_store_fixture"
        assert data["selected_provider_id"] == "elevenlabs_scribe_v2"
        assert data["source_schema_version"] == "online_asr_keys_accounts_review_verifier_store_cli_v1"
        assert data["review_verdict"] == "REVIEW_READY_METADATA_ONLY"
        assert data["handoff_status"] == "HANDOFF_READY_METADATA_ONLY"
        assert data["issue_count"] == 0
        assert data["completed_workflow_component_count"] >= 19
        assert data["next_session_context_file_count"] == 4
        assert data["next_review_action_count"] == 4
        assert data["output_directory_role"] == "user_selected_online_asr_keys_accounts_review_handoff_directory"
        assert data["file_count"] == 1
        assert data["files"][0]["filename"] == ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_HANDOFF_FILENAME
        assert data["files"][0]["file_role"] == "online_asr_keys_accounts_review_handoff"
        assert len(data["files"][0]["sha256"]) == 64
        assert (out / ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_HANDOFF_FILENAME).exists()

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
        assert data["raw_media_payload_included"] is False
        assert data["raw_media_serialized"] is False
        assert data["full_local_path_included"] is False
        assert data["full_local_path_serialized"] is False
        assert data["completed_transcription_claimed"] is False
        assert data["verified_transcription_claimed"] is False


def test_handoff_store_refuses_overwrite_when_requested() -> None:
    with TemporaryDirectory() as tmp:
        report = build_online_asr_keys_accounts_review_handoff_report(_safe_verifier_store_cli_result())
        out = Path(tmp) / "handoff-store"
        write_online_asr_keys_accounts_review_handoff_report(report, out)
        try:
            write_online_asr_keys_accounts_review_handoff_report(report, out, allow_overwrite=False)
        except FileExistsError as exc:
            assert ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_HANDOFF_FILENAME in str(exc)
        else:  # pragma: no cover - defensive assertion style for script execution.
            raise AssertionError("expected FileExistsError")


def test_handoff_store_summary_text_is_copyable_and_safe() -> None:
    report = build_online_asr_keys_accounts_review_handoff_report(_safe_verifier_store_cli_result())
    with TemporaryDirectory() as tmp:
        result = write_online_asr_keys_accounts_review_handoff_report(report, Path(tmp) / "handoff-store")
        summary = result.to_summary_text()
    assert "Online ASR KEYS/ACCOUNTS review handoff stored" in summary
    assert "Handoff status: HANDOFF_READY_METADATA_ONLY" in summary
    assert "Provider call allowed without user approval: false" in summary
    assert "Credential value read: false" in summary
    assert "Completed transcription claimed: false" in summary
    assert "C:\\" not in summary
    assert "T:\\" not in summary
    assert "/home/" not in summary


def run_self_test() -> None:
    test_handoff_store_writes_safe_report_without_paths_or_provider_calls()
    test_handoff_store_refuses_overwrite_when_requested()
    test_handoff_store_summary_text_is_copyable_and_safe()
    print("Online ASR KEYS/ACCOUNTS review handoff store self-test passed.")


if __name__ == "__main__":
    run_self_test()
