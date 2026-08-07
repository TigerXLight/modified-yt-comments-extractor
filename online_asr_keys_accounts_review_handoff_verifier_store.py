from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, is_dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from online_asr_keys_accounts_review_handoff_verifier import (
    OnlineASRKeysAccountsReviewHandoffVerificationReport,
    online_asr_keys_accounts_review_handoff_verification_report_to_json,
)


ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_HANDOFF_VERIFIER_STORE_SCHEMA_VERSION = (
    "online_asr_keys_accounts_review_handoff_verifier_store_v1"
)
ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_HANDOFF_VERIFIER_FILENAME = (
    "online_asr_keys_accounts_review_handoff_verification_report.json"
)


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
class OnlineASRKeysAccountsReviewHandoffVerifierStoredFile:
    filename: str
    file_role: str
    sha256: str
    byte_count: int
    schema_version: str = ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_HANDOFF_VERIFIER_STORE_SCHEMA_VERSION
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
class OnlineASRKeysAccountsReviewHandoffVerifierStoreResult:
    package_id: str
    selected_provider_id: str
    source_schema_version: str
    handoff_status: str
    source_review_verdict: str
    review_verdict: str
    issue_count: int
    required_context_file_count: int
    stored_handoff_file_count: int
    output_directory_role: str
    file_count: int
    files: tuple[OnlineASRKeysAccountsReviewHandoffVerifierStoredFile, ...]
    schema_version: str = ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_HANDOFF_VERIFIER_STORE_SCHEMA_VERSION
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
                "Online ASR KEYS/ACCOUNTS review handoff verifier stored",
                f"Package ID: {self.package_id}",
                f"Selected provider: {self.selected_provider_id or 'none'}",
                f"Handoff status: {self.handoff_status}",
                f"Source review verdict: {self.source_review_verdict}",
                f"Review verdict: {self.review_verdict}",
                f"Issue count: {self.issue_count}",
                f"Required context files: {self.required_context_file_count}",
                f"Stored handoff files checked: {self.stored_handoff_file_count}",
                f"Metadata files: {self.file_count}",
                "Review status: USER_REVIEW_REQUIRED",
                "Execution state: EXECUTION_GATED",
                "Provider call allowed without user approval: false",
                "Credential value read: false",
                "Completed transcription claimed: false",
            )
        )


def build_online_asr_keys_accounts_review_handoff_verifier_store_payloads(
    report: OnlineASRKeysAccountsReviewHandoffVerificationReport,
) -> dict[str, str]:
    """Build stable handoff-verifier JSON payload text without writing files."""
    return {
        ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_HANDOFF_VERIFIER_FILENAME: (
            online_asr_keys_accounts_review_handoff_verification_report_to_json(report)
        ),
    }


def write_online_asr_keys_accounts_review_handoff_verification_report(
    report: OnlineASRKeysAccountsReviewHandoffVerificationReport,
    output_directory: str | Path,
    *,
    allow_overwrite: bool = True,
) -> OnlineASRKeysAccountsReviewHandoffVerifierStoreResult:
    """Write the metadata-only Online ASR KEYS/ACCOUNTS handoff verifier report.

    The returned result records safe filenames and hashes only. It never exposes
    the caller's full local output path, reads credential values, executes
    provider calls, includes raw media, or claims completed/verified
    transcription.
    """
    output_path = Path(output_directory)
    output_path.mkdir(parents=True, exist_ok=True)
    payload_texts = build_online_asr_keys_accounts_review_handoff_verifier_store_payloads(report)
    stored_files: list[OnlineASRKeysAccountsReviewHandoffVerifierStoredFile] = []
    for filename, payload_text in payload_texts.items():
        file_path = output_path / filename
        if file_path.exists() and not allow_overwrite:
            raise FileExistsError(
                f"Refusing to overwrite existing review handoff verifier file: {filename}"
            )
        payload_bytes = payload_text.encode("utf-8")
        file_path.write_bytes(payload_bytes)
        stored_files.append(
            OnlineASRKeysAccountsReviewHandoffVerifierStoredFile(
                filename=filename,
                file_role=filename.removesuffix(".json"),
                sha256=_sha256_text(payload_text),
                byte_count=len(payload_bytes),
            )
        )
    return OnlineASRKeysAccountsReviewHandoffVerifierStoreResult(
        package_id=report.package_id,
        selected_provider_id=report.selected_provider_id,
        source_schema_version=report.schema_version,
        handoff_status=report.handoff_status,
        source_review_verdict=report.source_review_verdict,
        review_verdict=report.review_verdict,
        issue_count=report.issue_count,
        required_context_file_count=report.required_context_file_count,
        stored_handoff_file_count=report.stored_file_count,
        output_directory_role="user_selected_online_asr_keys_accounts_review_handoff_verifier_directory",
        file_count=len(stored_files),
        files=tuple(stored_files),
    )


def online_asr_keys_accounts_review_handoff_verifier_store_result_to_json(
    result: OnlineASRKeysAccountsReviewHandoffVerifierStoreResult,
) -> str:
    return json.dumps(result.to_dict(), indent=2, sort_keys=True) + "\n"
