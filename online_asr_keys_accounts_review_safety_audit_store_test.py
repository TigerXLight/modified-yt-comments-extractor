from __future__ import annotations

import hashlib
import json
import tempfile
from pathlib import Path

from online_asr_keys_accounts_review_safety_audit import (
    ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_SAFETY_AUDIT_VERDICT_NEEDS_REVIEW,
    ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_SAFETY_AUDIT_VERDICT_READY,
    build_online_asr_keys_accounts_review_safety_audit_report,
)
from online_asr_keys_accounts_review_safety_audit_store import (
    ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_SAFETY_AUDIT_FILENAME,
    ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_SAFETY_AUDIT_STORE_SCHEMA_VERSION,
    build_online_asr_keys_accounts_review_safety_audit_store_payloads,
    online_asr_keys_accounts_review_safety_audit_store_result_to_json,
    write_online_asr_keys_accounts_review_safety_audit_report,
)


def _safe_artifact() -> dict[str, object]:
    return {
        "schema_version": "online_asr_keys_accounts_review_handoff_verifier_store_cli_v1",
        "package_id": "online_asr_keys_accounts_safety_audit_store_fixture",
        "selected_provider_id": "elevenlabs_scribe_v2",
        "review_verdict": "HANDOFF_REVIEW_READY_METADATA_ONLY",
        "issue_count": 0,
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


def _unsafe_artifact() -> dict[str, object]:
    artifact = _safe_artifact()
    artifact["credential_value_read"] = True
    artifact["completed_transcription_claimed"] = True
    artifact["api_key"] = "super-secret-value-that-must-not-leak"
    artifact["output"] = "T:\\References\\private\\audit.json"
    return artifact


def test_safety_audit_store_writes_safe_result_without_full_paths() -> None:
    report = build_online_asr_keys_accounts_review_safety_audit_report(_safe_artifact())
    payloads = build_online_asr_keys_accounts_review_safety_audit_store_payloads(report)

    with tempfile.TemporaryDirectory() as tmpdir:
        result = write_online_asr_keys_accounts_review_safety_audit_report(report, tmpdir)
        data = result.to_dict()
        encoded = online_asr_keys_accounts_review_safety_audit_store_result_to_json(result)
        written = Path(tmpdir) / ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_SAFETY_AUDIT_FILENAME
        written_bytes = written.read_bytes()

        assert set(payloads) == {ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_SAFETY_AUDIT_FILENAME}
        assert json.loads(written.read_text(encoding="utf-8"))["review_verdict"] == (
            ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_SAFETY_AUDIT_VERDICT_READY
        )
        assert data["schema_version"] == ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_SAFETY_AUDIT_STORE_SCHEMA_VERSION
        assert data["source_schema_version"] == "online_asr_keys_accounts_review_safety_audit_v1"
        assert data["review_verdict"] == ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_SAFETY_AUDIT_VERDICT_READY
        assert data["source_artifact_count"] == 1
        assert data["issue_count"] == 0
        assert data["file_count"] == 1
        assert data["output_directory_role"] == (
            "user_selected_online_asr_keys_accounts_review_safety_audit_directory"
        )
        assert data["files"][0]["filename"] == ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_SAFETY_AUDIT_FILENAME
        assert data["files"][0]["byte_count"] == len(written_bytes)
        assert data["files"][0]["sha256"] == hashlib.sha256(written_bytes).hexdigest()
        assert data["package_ids"] == ["online_asr_keys_accounts_safety_audit_store_fixture"]
        assert data["selected_provider_ids"] == ["elevenlabs_scribe_v2"]
        assert data["metadata_only"] is True
        assert data["local_only"] is True
        assert data["user_selected_directory_required"] is True
        assert data["keys_accounts_sidebar_label"] == "KEYS/ACCOUNTS"
        assert data["provider_call_allowed_without_user_approval"] is False
        assert data["runtime_provider_call_performed"] is False
        assert data["credential_value_read"] is False
        assert data["raw_media_payload_included"] is False
        assert data["full_local_path_included"] is False
        assert data["completed_transcription_claimed"] is False
        assert str(tmpdir) not in encoded
        assert "C:\\" not in encoded
        assert "T:\\" not in encoded
        assert "api_key" not in encoded
        assert "password" not in encoded


def test_safety_audit_store_preserves_needs_review_without_secret_values() -> None:
    report = build_online_asr_keys_accounts_review_safety_audit_report(_unsafe_artifact())

    with tempfile.TemporaryDirectory() as tmpdir:
        result = write_online_asr_keys_accounts_review_safety_audit_report(report, tmpdir)
        data = result.to_dict()
        stored = json.loads(
            (Path(tmpdir) / ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_SAFETY_AUDIT_FILENAME).read_text(
                encoding="utf-8"
            )
        )
        encoded_result = online_asr_keys_accounts_review_safety_audit_store_result_to_json(result)
        encoded_stored = json.dumps(stored, sort_keys=True)

        assert data["review_verdict"] == ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_SAFETY_AUDIT_VERDICT_NEEDS_REVIEW
        assert data["issue_count"] == 4
        assert stored["review_verdict"] == ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_SAFETY_AUDIT_VERDICT_NEEDS_REVIEW
        assert stored["issue_count"] == 4
        assert "super-secret-value-that-must-not-leak" not in encoded_result
        assert "super-secret-value-that-must-not-leak" not in encoded_stored
        assert "T:\\References\\private" not in encoded_result
        assert "T:\\References\\private" not in encoded_stored
        assert data["credential_value_read"] is False
        assert data["completed_transcription_claimed"] is False


def test_safety_audit_store_summary_and_overwrite_gate() -> None:
    report = build_online_asr_keys_accounts_review_safety_audit_report(_safe_artifact())

    with tempfile.TemporaryDirectory() as tmpdir:
        first = write_online_asr_keys_accounts_review_safety_audit_report(report, tmpdir)
        summary = first.to_summary_text()
        assert "Online ASR KEYS/ACCOUNTS review safety audit stored" in summary
        assert "Review verdict: SAFETY_REVIEW_READY_METADATA_ONLY" in summary
        assert "Source artifacts checked: 1" in summary
        assert "Provider call allowed without user approval: false" in summary
        assert "Credential value read: false" in summary
        assert "Completed transcription claimed: false" in summary

        try:
            write_online_asr_keys_accounts_review_safety_audit_report(
                report,
                tmpdir,
                allow_overwrite=False,
            )
        except FileExistsError as exc:
            assert ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_SAFETY_AUDIT_FILENAME in str(exc)
        else:  # pragma: no cover
            raise AssertionError("overwrite refusal should fail")


if __name__ == "__main__":
    test_safety_audit_store_writes_safe_result_without_full_paths()
    test_safety_audit_store_preserves_needs_review_without_secret_values()
    test_safety_audit_store_summary_and_overwrite_gate()
    print("Online ASR KEYS/ACCOUNTS review safety audit store self-test passed.")
