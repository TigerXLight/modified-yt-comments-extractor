from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, is_dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from online_asr_keys_accounts_review_handoff import (
    OnlineASRKeysAccountsReviewHandoffReport,
    online_asr_keys_accounts_review_handoff_report_to_json,
)


ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_HANDOFF_STORE_SCHEMA_VERSION = "online_asr_keys_accounts_review_handoff_store_v1"
ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_HANDOFF_FILENAME = "online_asr_keys_accounts_review_handoff.json"


def _value_for_dict(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return {key: _value_for_dict(item) for key, item in asdict(value).items()}
    if isinstance(value, tuple):
        return [_value_for_dict(item) for item in value]
    if isinstance(value, list):
        return [_value_for_dict(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _value_for_dict(value[key]) for key in sorted(value)}
    if hasattr(value, "to_dict") and callable(value.to_dict):
        return value.to_dict()
    return value


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class OnlineASRKeysAccountsReviewHandoffStoredFile:
    filename: str
    file_role: str
    sha256: str
    byte_count: int
    schema_version: str = ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_HANDOFF_STORE_SCHEMA_VERSION
    metadata_only: bool = True
    local_only: bool = True
    user_selected_directory_required: bool = True
    credential_value_read: bool = False
    plaintext_secret_storage_allowed: bool = False
    secret_value_recorded: bool = False
    provider_call_allowed_without_user_approval: bool = False
    runtime_provider_call_performed: bool = False
    raw_media_payload_included: bool = False
    raw_media_serialized: bool = False
    full_local_path_included: bool = False
    full_local_path_serialized: bool = False
    completed_transcription_claimed: bool = False
    verified_transcription_claimed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class OnlineASRKeysAccountsReviewHandoffStoreResult:
    package_id: str
    selected_provider_id: str
    source_schema_version: str
    review_verdict: str
    handoff_status: str
    issue_count: int
    completed_workflow_component_count: int
    next_session_context_file_count: int
    next_review_action_count: int
    output_directory_role: str
    file_count: int
    files: tuple[OnlineASRKeysAccountsReviewHandoffStoredFile, ...]
    schema_version: str = ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_HANDOFF_STORE_SCHEMA_VERSION
    review_status: str = "USER_REVIEW_REQUIRED"
    execution_state: str = "EXECUTION_GATED"
    metadata_only: bool = True
    local_only: bool = True
    user_selected_directory_required: bool = True
    keys_accounts_sidebar_label: str = "KEYS/ACCOUNTS"
    keys_accounts_shows_added_providers_only: bool = True
    add_provider_searches_full_catalog: bool = True
    online_asr_requires_explicit_provider_call_approval: bool = True
    provider_call_allowed_without_user_approval: bool = False
    runtime_provider_call_performed: bool = False
    credential_value_read: bool = False
    plaintext_secret_storage_allowed: bool = False
    secret_value_recorded: bool = False
    raw_media_payload_included: bool = False
    raw_media_serialized: bool = False
    full_local_path_included: bool = False
    full_local_path_serialized: bool = False
    completed_transcription_claimed: bool = False
    verified_transcription_claimed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)

    def to_summary_text(self) -> str:
        return "\n".join(
            (
                "Online ASR KEYS/ACCOUNTS review handoff stored",
                f"Package ID: {self.package_id}",
                f"Selected provider: {self.selected_provider_id or 'none'}",
                f"Source schema: {self.source_schema_version}",
                f"Review verdict: {self.review_verdict}",
                f"Handoff status: {self.handoff_status}",
                f"Issue count: {self.issue_count}",
                f"Completed workflow components: {self.completed_workflow_component_count}",
                f"Next-session context files: {self.next_session_context_file_count}",
                f"Next review actions: {self.next_review_action_count}",
                f"Metadata files: {self.file_count}",
                "Review status: USER_REVIEW_REQUIRED",
                "Execution state: EXECUTION_GATED",
                "Provider call allowed without user approval: false",
                "Credential value read: false",
                "Completed transcription claimed: false",
            )
        )


def build_online_asr_keys_accounts_review_handoff_store_payloads(
    report: OnlineASRKeysAccountsReviewHandoffReport,
) -> dict[str, str]:
    """Build stable handoff JSON payload text without writing files."""
    return {
        ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_HANDOFF_FILENAME: online_asr_keys_accounts_review_handoff_report_to_json(report),
    }


def write_online_asr_keys_accounts_review_handoff_report(
    report: OnlineASRKeysAccountsReviewHandoffReport,
    output_directory: str | Path,
    *,
    allow_overwrite: bool = True,
) -> OnlineASRKeysAccountsReviewHandoffStoreResult:
    """Write the metadata-only Online ASR KEYS/ACCOUNTS handoff report.

    The returned result records safe filenames and hashes only. It never exposes
    the caller's full local output path, reads credential values, executes
    provider calls, includes raw media, or claims completed/verified
    transcription.
    """
    output_path = Path(output_directory)
    output_path.mkdir(parents=True, exist_ok=True)
    payload_texts = build_online_asr_keys_accounts_review_handoff_store_payloads(report)
    stored_files: list[OnlineASRKeysAccountsReviewHandoffStoredFile] = []
    for filename, payload_text in payload_texts.items():
        file_path = output_path / filename
        if file_path.exists() and not allow_overwrite:
            raise FileExistsError(f"Refusing to overwrite existing review handoff file: {filename}")
        file_path.write_text(payload_text, encoding="utf-8")
        stored_files.append(
            OnlineASRKeysAccountsReviewHandoffStoredFile(
                filename=filename,
                file_role=filename.removesuffix(".json"),
                sha256=_sha256_text(payload_text),
                byte_count=len(payload_text.encode("utf-8")),
            )
        )
    return OnlineASRKeysAccountsReviewHandoffStoreResult(
        package_id=report.package_id,
        selected_provider_id=report.selected_provider_id,
        source_schema_version=report.source_schema_version,
        review_verdict=report.review_verdict,
        handoff_status=report.handoff_status,
        issue_count=report.issue_count,
        completed_workflow_component_count=report.completed_workflow_component_count,
        next_session_context_file_count=report.next_session_context_file_count,
        next_review_action_count=report.next_review_action_count,
        output_directory_role="user_selected_online_asr_keys_accounts_review_handoff_directory",
        file_count=len(stored_files),
        files=tuple(stored_files),
    )


def online_asr_keys_accounts_review_handoff_store_result_to_json(
    result: OnlineASRKeysAccountsReviewHandoffStoreResult,
) -> str:
    return json.dumps(result.to_dict(), indent=2, sort_keys=True) + "\n"
