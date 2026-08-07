from __future__ import annotations

import hashlib
import json
import tempfile
from pathlib import Path

from online_asr_keys_accounts_review_release_gate import ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_RELEASE_GATE_VERDICT_READY
from online_asr_keys_accounts_review_release_section_closeout import (
    REQUIRED_ONLINE_ASR_KEYS_ACCOUNTS_RELEASE_SECTION_SCHEMAS,
    build_online_asr_keys_accounts_review_release_section_closeout_report,
)
from online_asr_keys_accounts_review_release_section_closeout_store import (
    ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_RELEASE_SECTION_CLOSEOUT_FILENAME,
    ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_RELEASE_SECTION_CLOSEOUT_STORE_SCHEMA_VERSION,
    online_asr_keys_accounts_review_release_section_closeout_store_result_to_json,
    write_online_asr_keys_accounts_review_release_section_closeout_report,
)


def _safe_artifact(schema_version: str, package_id: str = "release_section_store_fixture") -> dict[str, object]:
    return {
        "schema_version": schema_version,
        "package_id": package_id,
        "selected_provider_id": "elevenlabs_scribe_v2",
        "stored_file_names": [f"{schema_version}.json"],
        "stored_file_hashes": ["c" * 64],
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
        _safe_artifact(schema_version, f"section_store_package_{index}")
        for index, schema_version in enumerate(REQUIRED_ONLINE_ASR_KEYS_ACCOUNTS_RELEASE_SECTION_SCHEMAS, start=1)
    )


def test_release_section_store_writes_safe_result_without_full_paths() -> None:
    report = build_online_asr_keys_accounts_review_release_section_closeout_report(_safe_chain())
    with tempfile.TemporaryDirectory() as tmpdir:
        result = write_online_asr_keys_accounts_review_release_section_closeout_report(report, tmpdir)
        data = result.to_dict()
        encoded = online_asr_keys_accounts_review_release_section_closeout_store_result_to_json(result)
        written = Path(tmpdir) / ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_RELEASE_SECTION_CLOSEOUT_FILENAME
        written_bytes = written.read_bytes()
        stored = json.loads(written.read_text(encoding="utf-8"))

        assert data["schema_version"] == ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_RELEASE_SECTION_CLOSEOUT_STORE_SCHEMA_VERSION
        assert data["source_schema_version"] == "online_asr_keys_accounts_review_release_section_closeout_v1"
        assert data["review_verdict"] == ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_RELEASE_GATE_VERDICT_READY
        assert data["section_ready"] is True
        assert data["issue_count"] == 0
        assert data["file_count"] == 1
        assert data["files"][0]["filename"] == ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_RELEASE_SECTION_CLOSEOUT_FILENAME
        assert data["files"][0]["byte_count"] == len(written_bytes)
        assert data["files"][0]["sha256"] == hashlib.sha256(written_bytes).hexdigest()
        assert stored["section_ready"] is True
        assert str(tmpdir) not in encoded
        assert "api_key" not in encoded
        assert "password" not in encoded
        assert data["credential_value_read"] is False
        assert data["completed_transcription_claimed"] is False


def test_release_section_store_summary_and_overwrite_gate() -> None:
    report = build_online_asr_keys_accounts_review_release_section_closeout_report(_safe_chain())
    with tempfile.TemporaryDirectory() as tmpdir:
        first = write_online_asr_keys_accounts_review_release_section_closeout_report(report, tmpdir)
        summary = first.to_summary_text()
        assert "Online ASR KEYS/ACCOUNTS release section closeout stored" in summary
        assert "Section ready: true" in summary
        assert "Issue count: 0" in summary
        assert "Provider call allowed without user approval: false" in summary
        try:
            write_online_asr_keys_accounts_review_release_section_closeout_report(
                report,
                tmpdir,
                allow_overwrite=False,
            )
        except FileExistsError as exc:
            assert ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_RELEASE_SECTION_CLOSEOUT_FILENAME in str(exc)
        else:  # pragma: no cover
            raise AssertionError("overwrite refusal should fail")


if __name__ == "__main__":
    test_release_section_store_writes_safe_result_without_full_paths()
    test_release_section_store_summary_and_overwrite_gate()
    print("Online ASR KEYS/ACCOUNTS review release section closeout store self-test passed.")
