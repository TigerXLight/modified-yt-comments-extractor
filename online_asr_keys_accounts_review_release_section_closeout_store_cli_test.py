from __future__ import annotations

import io
import json
import tempfile
from pathlib import Path

from online_asr_keys_accounts_review_release_gate import ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_RELEASE_GATE_VERDICT_READY
from online_asr_keys_accounts_review_release_section_closeout import (
    REQUIRED_ONLINE_ASR_KEYS_ACCOUNTS_RELEASE_SECTION_SCHEMAS,
)
from online_asr_keys_accounts_review_release_section_closeout_store import (
    ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_RELEASE_SECTION_CLOSEOUT_FILENAME,
)
from online_asr_keys_accounts_review_release_section_closeout_store_cli import (
    ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_RELEASE_SECTION_CLOSEOUT_STORE_CLI_SCHEMA_VERSION,
    build_online_asr_keys_accounts_review_release_section_closeout_store_cli_result,
    online_asr_keys_accounts_review_release_section_closeout_store_cli_result_to_json,
    run_online_asr_keys_accounts_review_release_section_closeout_store_cli,
)


def _safe_artifact(schema_version: str, package_id: str = "release_section_cli_fixture") -> dict[str, object]:
    return {
        "schema_version": schema_version,
        "package_id": package_id,
        "selected_provider_id": "elevenlabs_scribe_v2",
        "stored_file_names": [f"{schema_version}.json"],
        "stored_file_hashes": ["d" * 64],
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
        _safe_artifact(schema_version, f"section_cli_package_{index}")
        for index, schema_version in enumerate(REQUIRED_ONLINE_ASR_KEYS_ACCOUNTS_RELEASE_SECTION_SCHEMAS, start=1)
    )


def test_release_section_store_cli_builds_safe_result_without_full_paths() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        result = build_online_asr_keys_accounts_review_release_section_closeout_store_cli_result(_safe_chain(), tmpdir)
        data = result.to_dict()
        encoded = online_asr_keys_accounts_review_release_section_closeout_store_cli_result_to_json(result)

        assert data["schema_version"] == ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_RELEASE_SECTION_CLOSEOUT_STORE_CLI_SCHEMA_VERSION
        assert data["review_verdict"] == ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_RELEASE_GATE_VERDICT_READY
        assert data["section_ready"] is True
        assert data["issue_count"] == 0
        assert data["coverage_component_count"] == len(REQUIRED_ONLINE_ASR_KEYS_ACCOUNTS_RELEASE_SECTION_SCHEMAS)
        assert data["missing_schema_versions"] == []
        assert data["stored_file_count"] == 1
        assert data["stored_file_names"] == [ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_RELEASE_SECTION_CLOSEOUT_FILENAME]
        assert (Path(tmpdir) / ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_RELEASE_SECTION_CLOSEOUT_FILENAME).exists()
        assert data["keys_accounts_sidebar_label"] == "KEYS/ACCOUNTS"
        assert data["provider_call_allowed_without_user_approval"] is False
        assert data["credential_value_read"] is False
        assert data["completed_transcription_claimed"] is False
        assert str(tmpdir) not in encoded
        assert "api_key" not in encoded
        assert "password" not in encoded


def test_release_section_store_cli_rejects_secret_like_input() -> None:
    unsafe = dict(_safe_chain()[0])
    unsafe["token"] = "super-secret-value-that-must-not-leak"
    with tempfile.TemporaryDirectory() as tmpdir:
        try:
            build_online_asr_keys_accounts_review_release_section_closeout_store_cli_result((unsafe,), tmpdir)
        except ValueError as exc:
            assert "secret-like field" in str(exc)
        else:  # pragma: no cover
            raise AssertionError("secret-like input must be rejected")


def test_release_section_store_cli_entrypoint_json_and_summary() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        artifact_paths: list[str] = []
        for index, artifact in enumerate(_safe_chain(), start=1):
            path = Path(tmpdir) / f"section_artifact_{index}.json"
            path.write_text(json.dumps(artifact), encoding="utf-8")
            artifact_paths.append(str(path))
        output_dir = Path(tmpdir) / "out"
        argv: list[str] = []
        for path in artifact_paths:
            argv.extend(["--artifact-json", path])
        argv.extend(["--output-directory", str(output_dir)])
        stdout = io.StringIO()
        stderr = io.StringIO()

        assert run_online_asr_keys_accounts_review_release_section_closeout_store_cli(
            argv,
            stdout=stdout,
            stderr=stderr,
        ) == 0
        data = json.loads(stdout.getvalue())
        assert data["section_ready"] is True
        assert data["stored_file_count"] == 1
        assert str(output_dir) not in stdout.getvalue()
        assert stderr.getvalue() == ""

        summary = io.StringIO()
        assert run_online_asr_keys_accounts_review_release_section_closeout_store_cli(
            [*argv, "--summary"],
            stdout=summary,
            stderr=io.StringIO(),
        ) == 0
        assert "Online ASR KEYS/ACCOUNTS release section closeout store CLI" in summary.getvalue()
        assert "Section ready: true" in summary.getvalue()
        assert "Provider call allowed without user approval: false" in summary.getvalue()


if __name__ == "__main__":
    test_release_section_store_cli_builds_safe_result_without_full_paths()
    test_release_section_store_cli_rejects_secret_like_input()
    test_release_section_store_cli_entrypoint_json_and_summary()
    print("Online ASR KEYS/ACCOUNTS review release section closeout store CLI self-test passed.")
