from __future__ import annotations

import io
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from online_asr_keys_accounts_review_workflow_cli import (
    run_online_asr_keys_accounts_review_workflow_cli,
)


ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_SMOKE_FIXTURE_SCHEMA_VERSION = (
    "online_asr_keys_accounts_review_smoke_fixture_v1"
)


@dataclass(frozen=True)
class OnlineASRKeysAccountsReviewSmokeFixtureResult:
    schema_version: str
    package_id: str
    created_at_utc: str
    selected_provider_id: str
    selected_provider_ready_for_gate_review: bool
    provider_count: int
    credential_status_count: int
    workflow_exit_code: int
    workflow_result_schema_version: str
    stored_file_count: int
    written_fixture_file_names: tuple[str, ...]
    written_workflow_directory_names: tuple[str, ...]
    output_directory_name: str
    provider_call_allowed_without_user_approval: bool = False
    credential_value_read: bool = False
    runtime_provider_call_performed: bool = False
    raw_media_serialized: bool = False
    full_local_path_serialized: bool = False
    completed_transcription_claimed: bool = False
    verified_transcription_claimed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "package_id": self.package_id,
            "created_at_utc": self.created_at_utc,
            "selected_provider_id": self.selected_provider_id,
            "selected_provider_ready_for_gate_review": self.selected_provider_ready_for_gate_review,
            "provider_count": self.provider_count,
            "credential_status_count": self.credential_status_count,
            "workflow_exit_code": self.workflow_exit_code,
            "workflow_result_schema_version": self.workflow_result_schema_version,
            "stored_file_count": self.stored_file_count,
            "written_fixture_file_names": list(self.written_fixture_file_names),
            "written_workflow_directory_names": list(self.written_workflow_directory_names),
            "output_directory_name": self.output_directory_name,
            "provider_call_allowed_without_user_approval": self.provider_call_allowed_without_user_approval,
            "credential_value_read": self.credential_value_read,
            "runtime_provider_call_performed": self.runtime_provider_call_performed,
            "raw_media_serialized": self.raw_media_serialized,
            "full_local_path_serialized": self.full_local_path_serialized,
            "completed_transcription_claimed": self.completed_transcription_claimed,
            "verified_transcription_claimed": self.verified_transcription_claimed,
        }

    def to_summary_text(self) -> str:
        readiness = "ready for gate review" if self.selected_provider_ready_for_gate_review else "needs key/account review"
        return (
            "Online ASR KEYS/ACCOUNTS smoke fixture: "
            f"{self.provider_count} provider(s), selected provider {self.selected_provider_id} {readiness}. "
            f"Workflow files: {self.stored_file_count}. "
            "Provider call allowed without user approval: false. "
            "Credential value read: false. "
            "Completed transcription claimed: false."
        )


def _write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _default_provider_catalog() -> list[dict[str, Any]]:
    return [
        {
            "provider_id": "elevenlabs_scribe_v2",
            "display_name": "ElevenLabs Scribe v2",
            "provider_family": "elevenlabs",
            "model_id": "scribe_v2",
            "credential_entry_id": "elevenlabs_account_status",
            "supports_keyterms": True,
            "tags": ["cloud", "online-asr", "keyterms"],
            "recommended_for": ["keyterms", "cloud-candidate"],
        },
        {
            "provider_id": "cohere_asr",
            "display_name": "Cohere ASR",
            "provider_family": "cohere",
            "model_id": "asr",
            "credential_entry_id": "cohere_account_status",
            "supports_keyterms": False,
            "tags": ["cloud", "online-asr"],
            "recommended_for": ["comparison-only"],
        },
        {
            "provider_id": "azure_speech",
            "display_name": "Azure Speech",
            "provider_family": "azure",
            "model_id": "speech-to-text",
            "credential_entry_id": "azure_account_status",
            "supports_keyterms": False,
            "tags": ["cloud", "online-asr"],
            "recommended_for": ["comparison-only"],
        },
    ]


def _default_credential_statuses() -> dict[str, dict[str, str]]:
    return {
        "elevenlabs_account_status": {"state": "CONFIGURED"},
        "cohere_account_status": {"state": "MISSING"},
        "azure_account_status": {"state": "UNAVAILABLE"},
    }


def _default_gate_summary(selected_provider_id: str) -> dict[str, Any]:
    return {
        "schema_version": "online_asr_execution_gate_summary_fixture_v1",
        "selected_provider_id": selected_provider_id,
        "gate_status": "APPROVAL_REQUIRED",
        "provider_call_allowed_without_user_approval": False,
        "credential_value_read": False,
        "runtime_provider_call_performed": False,
        "raw_media_serialized": False,
        "full_local_path_serialized": False,
        "completed_transcription_claimed": False,
        "verified_transcription_claimed": False,
        "review_note": "Fixture-only Online ASR gate summary; no provider API call was made.",
    }


def build_online_asr_keys_accounts_review_smoke_fixture(
    output_directory: str | Path,
    *,
    package_id: str,
    created_at_utc: str,
    app_version: str = "",
    selected_provider_id: str = "elevenlabs_scribe_v2",
    provider_catalog: list[dict[str, Any]] | None = None,
    credential_statuses: Mapping[str, Any] | None = None,
    allow_overwrite: bool = True,
) -> OnlineASRKeysAccountsReviewSmokeFixtureResult:
    """Create a safe local smoke fixture for the Online ASR KEYS/ACCOUNTS review workflow."""

    root = Path(output_directory)
    root.mkdir(parents=True, exist_ok=True)
    fixtures_dir = root / "online_asr_keys_accounts_review_fixture_inputs"
    workflow_dir = root / "online_asr_keys_accounts_review_workflow_output"

    providers = provider_catalog if provider_catalog is not None else _default_provider_catalog()
    statuses = dict(credential_statuses) if credential_statuses is not None else _default_credential_statuses()
    gate_summary = _default_gate_summary(selected_provider_id)

    provider_json = fixtures_dir / "online_asr_provider_catalog.safe.fixture.json"
    status_json = fixtures_dir / "online_asr_credential_status.safe.fixture.json"
    gate_json = fixtures_dir / "online_asr_execution_gate_summary.safe.fixture.json"
    _write_json(provider_json, providers)
    _write_json(status_json, statuses)
    _write_json(gate_json, gate_summary)

    stdout = io.StringIO()
    stderr = io.StringIO()
    args = [
        "--provider-catalog-json",
        str(provider_json),
        "--credential-status-json",
        str(status_json),
        "--online-asr-gate-summary-json",
        str(gate_json),
        "--output-directory",
        str(workflow_dir),
        "--package-id",
        package_id,
        "--created-at-utc",
        created_at_utc,
        "--app-version",
        app_version,
        "--added-provider-id",
        selected_provider_id,
        "--selected-provider-id",
        selected_provider_id,
        "--keys-accounts-query",
        "scribe",
        "--add-provider-query",
        "asr",
    ]
    if not allow_overwrite:
        args.append("--no-overwrite")

    exit_code = run_online_asr_keys_accounts_review_workflow_cli(
        args,
        stdout=stdout,
        stderr=stderr,
    )
    if exit_code != 0:
        raise RuntimeError(stderr.getvalue().strip() or f"Workflow CLI failed with exit code {exit_code}")

    workflow_data = json.loads(stdout.getvalue())
    fixture_names = tuple(sorted(item.name for item in fixtures_dir.iterdir() if item.is_file()))
    workflow_dir_names = tuple(sorted(item.name for item in workflow_dir.iterdir() if item.is_dir()))
    return OnlineASRKeysAccountsReviewSmokeFixtureResult(
        schema_version=ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_SMOKE_FIXTURE_SCHEMA_VERSION,
        package_id=package_id,
        created_at_utc=created_at_utc,
        selected_provider_id=str(workflow_data.get("selected_provider_id") or selected_provider_id),
        selected_provider_ready_for_gate_review=bool(
            workflow_data.get("selected_provider_ready_for_gate_review", False)
        ),
        provider_count=len(providers),
        credential_status_count=len(statuses),
        workflow_exit_code=exit_code,
        workflow_result_schema_version=str(workflow_data.get("schema_version") or ""),
        stored_file_count=int(workflow_data.get("stored_file_count") or 0),
        written_fixture_file_names=fixture_names,
        written_workflow_directory_names=workflow_dir_names,
        output_directory_name=root.name,
        provider_call_allowed_without_user_approval=bool(
            workflow_data.get("provider_call_allowed_without_user_approval", False)
        ),
        credential_value_read=bool(workflow_data.get("credential_value_read", False)),
        runtime_provider_call_performed=bool(workflow_data.get("runtime_provider_call_performed", False)),
        raw_media_serialized=bool(workflow_data.get("raw_media_serialized", False)),
        full_local_path_serialized=bool(workflow_data.get("full_local_path_serialized", False)),
        completed_transcription_claimed=bool(workflow_data.get("completed_transcription_claimed", False)),
        verified_transcription_claimed=bool(workflow_data.get("verified_transcription_claimed", False)),
    )


def online_asr_keys_accounts_review_smoke_fixture_result_to_json(
    result: OnlineASRKeysAccountsReviewSmokeFixtureResult,
) -> str:
    return json.dumps(result.to_dict(), indent=2, sort_keys=True) + "\n"
