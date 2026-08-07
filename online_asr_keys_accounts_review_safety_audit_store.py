from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, is_dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from online_asr_keys_accounts_review_safety_audit import (
    OnlineASRKeysAccountsReviewSafetyAuditReport,
    online_asr_keys_accounts_review_safety_audit_report_to_json,
)


ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_SAFETY_AUDIT_STORE_SCHEMA_VERSION = (
    "online_asr_keys_accounts_review_safety_audit_store_v1"
)
ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_SAFETY_AUDIT_FILENAME = (
    "online_asr_keys_accounts_review_safety_audit_report.json"
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


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


@dataclass(frozen=True)
class OnlineASRKeysAccountsReviewSafetyAuditStoredFile:
    filename: str
    file_role: str
    sha256: str
    byte_count: int
    schema_version: str = ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_SAFETY_AUDIT_STORE_SCHEMA_VERSION
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
class OnlineASRKeysAccountsReviewSafetyAuditStoreResult:
    source_artifact_count: int
    review_verdict: str
    issue_count: int
    source_schema_version: str
    schema_versions: tuple[str, ...]
    package_ids: tuple[str, ...]
    selected_provider_ids: tuple[str, ...]
    output_directory_role: str
    file_count: int
    files: tuple[OnlineASRKeysAccountsReviewSafetyAuditStoredFile, ...]
    schema_version: str = ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_SAFETY_AUDIT_STORE_SCHEMA_VERSION
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
                "Online ASR KEYS/ACCOUNTS review safety audit stored",
                f"Review verdict: {self.review_verdict}",
                f"Source artifacts checked: {self.source_artifact_count}",
                f"Issue count: {self.issue_count}",
                f"Schema versions: {', '.join(self.schema_versions) or 'none'}",
                f"Packages: {', '.join(self.package_ids) or 'none'}",
                f"Selected providers: {', '.join(self.selected_provider_ids) or 'none'}",
                f"Metadata files: {self.file_count}",
                "Review status: USER_REVIEW_REQUIRED",
                "Execution state: EXECUTION_GATED",
                "Provider call allowed without user approval: false",
                "Credential value read: false",
                "Completed transcription claimed: false",
            )
        )


def build_online_asr_keys_accounts_review_safety_audit_store_payloads(
    report: OnlineASRKeysAccountsReviewSafetyAuditReport,
) -> dict[str, str]:
    """Build stable safety-audit JSON payload text without writing files."""
    return {
        ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_SAFETY_AUDIT_FILENAME: (
            online_asr_keys_accounts_review_safety_audit_report_to_json(report)
        ),
    }


def write_online_asr_keys_accounts_review_safety_audit_report(
    report: OnlineASRKeysAccountsReviewSafetyAuditReport,
    output_directory: str | Path,
    *,
    allow_overwrite: bool = True,
) -> OnlineASRKeysAccountsReviewSafetyAuditStoreResult:
    """Write the metadata-only Online ASR KEYS/ACCOUNTS safety-audit report.

    The returned result records safe filenames and hashes only. It never exposes
    the caller's full local output path, reads credential values, executes
    provider calls, includes raw media, or claims completed/verified
    transcription. Payloads are written as UTF-8 bytes so stored byte counts are
    stable on Windows and POSIX.
    """
    output_path = Path(output_directory)
    output_path.mkdir(parents=True, exist_ok=True)
    payload_texts = build_online_asr_keys_accounts_review_safety_audit_store_payloads(report)
    stored_files: list[OnlineASRKeysAccountsReviewSafetyAuditStoredFile] = []
    for filename, payload_text in payload_texts.items():
        file_path = output_path / filename
        if file_path.exists() and not allow_overwrite:
            raise FileExistsError(
                f"Refusing to overwrite existing review safety audit file: {filename}"
            )
        payload_bytes = payload_text.encode("utf-8")
        file_path.write_bytes(payload_bytes)
        stored_files.append(
            OnlineASRKeysAccountsReviewSafetyAuditStoredFile(
                filename=filename,
                file_role=filename.removesuffix(".json"),
                sha256=_sha256_bytes(payload_bytes),
                byte_count=len(payload_bytes),
            )
        )
    return OnlineASRKeysAccountsReviewSafetyAuditStoreResult(
        source_artifact_count=report.source_artifact_count,
        review_verdict=report.review_verdict,
        issue_count=report.issue_count,
        source_schema_version=report.schema_version,
        schema_versions=report.schema_versions,
        package_ids=report.package_ids,
        selected_provider_ids=report.selected_provider_ids,
        output_directory_role="user_selected_online_asr_keys_accounts_review_safety_audit_directory",
        file_count=len(stored_files),
        files=tuple(stored_files),
    )


def online_asr_keys_accounts_review_safety_audit_store_result_to_json(
    result: OnlineASRKeysAccountsReviewSafetyAuditStoreResult,
) -> str:
    return json.dumps(result.to_dict(), indent=2, sort_keys=True) + "\n"
