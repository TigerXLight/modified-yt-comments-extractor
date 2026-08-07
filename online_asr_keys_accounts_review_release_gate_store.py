from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, is_dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from online_asr_keys_accounts_review_release_gate import (
    OnlineASRKeysAccountsReviewReleaseGateReport,
    online_asr_keys_accounts_review_release_gate_report_to_json,
)


ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_RELEASE_GATE_STORE_SCHEMA_VERSION = (
    "online_asr_keys_accounts_review_release_gate_store_v1"
)
ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_RELEASE_GATE_FILENAME = (
    "online_asr_keys_accounts_review_release_gate_report.json"
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
class OnlineASRKeysAccountsReviewReleaseGateStoredFile:
    filename: str
    file_role: str
    sha256: str
    byte_count: int
    schema_version: str = ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_RELEASE_GATE_STORE_SCHEMA_VERSION
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
class OnlineASRKeysAccountsReviewReleaseGateStoreResult:
    source_artifact_count: int
    review_verdict: str
    release_gate_ready: bool
    issue_count: int
    coverage_component_count: int
    required_component_count: int
    source_schema_version: str
    observed_schema_versions: tuple[str, ...]
    missing_schema_versions: tuple[str, ...]
    package_ids: tuple[str, ...]
    selected_provider_ids: tuple[str, ...]
    output_directory_role: str
    file_count: int
    files: tuple[OnlineASRKeysAccountsReviewReleaseGateStoredFile, ...]
    schema_version: str = ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_RELEASE_GATE_STORE_SCHEMA_VERSION
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
                "Online ASR KEYS/ACCOUNTS review release gate stored",
                f"Review verdict: {self.review_verdict}",
                f"Release gate ready: {str(self.release_gate_ready).lower()}",
                f"Source artifacts checked: {self.source_artifact_count}",
                f"Component coverage: {self.coverage_component_count}/{self.required_component_count}",
                f"Issue count: {self.issue_count}",
                f"Missing schema versions: {', '.join(self.missing_schema_versions) or 'none'}",
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


def build_online_asr_keys_accounts_review_release_gate_store_payloads(
    report: OnlineASRKeysAccountsReviewReleaseGateReport,
) -> dict[str, str]:
    """Build stable release-gate JSON payload text without writing files."""
    return {
        ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_RELEASE_GATE_FILENAME: (
            online_asr_keys_accounts_review_release_gate_report_to_json(report)
        ),
    }


def write_online_asr_keys_accounts_review_release_gate_report(
    report: OnlineASRKeysAccountsReviewReleaseGateReport,
    output_directory: str | Path,
    *,
    allow_overwrite: bool = True,
) -> OnlineASRKeysAccountsReviewReleaseGateStoreResult:
    """Write the metadata-only Online ASR KEYS/ACCOUNTS release-gate report.

    The returned result records safe filenames and hashes only. It never exposes
    the caller's full local output path, reads credential values, executes
    provider calls, includes raw media, or claims completed/verified
    transcription. Payloads are written as UTF-8 bytes so stored byte counts are
    stable on Windows and POSIX.
    """
    output_path = Path(output_directory)
    output_path.mkdir(parents=True, exist_ok=True)
    payload_texts = build_online_asr_keys_accounts_review_release_gate_store_payloads(report)
    stored_files: list[OnlineASRKeysAccountsReviewReleaseGateStoredFile] = []
    for filename, payload_text in payload_texts.items():
        file_path = output_path / filename
        if file_path.exists() and not allow_overwrite:
            raise FileExistsError(
                f"Refusing to overwrite existing review release-gate file: {filename}"
            )
        payload_bytes = payload_text.encode("utf-8")
        file_path.write_bytes(payload_bytes)
        stored_files.append(
            OnlineASRKeysAccountsReviewReleaseGateStoredFile(
                filename=filename,
                file_role=filename.removesuffix(".json"),
                sha256=_sha256_bytes(payload_bytes),
                byte_count=len(payload_bytes),
            )
        )
    return OnlineASRKeysAccountsReviewReleaseGateStoreResult(
        source_artifact_count=report.source_artifact_count,
        review_verdict=report.review_verdict,
        release_gate_ready=report.release_gate_ready,
        issue_count=report.issue_count,
        coverage_component_count=report.coverage_component_count,
        required_component_count=len(report.required_schema_versions),
        source_schema_version=report.schema_version,
        observed_schema_versions=report.observed_schema_versions,
        missing_schema_versions=report.missing_schema_versions,
        package_ids=report.package_ids,
        selected_provider_ids=report.selected_provider_ids,
        output_directory_role="user_selected_online_asr_keys_accounts_review_release_gate_directory",
        file_count=len(stored_files),
        files=tuple(stored_files),
    )


def online_asr_keys_accounts_review_release_gate_store_result_to_json(
    result: OnlineASRKeysAccountsReviewReleaseGateStoreResult,
) -> str:
    return json.dumps(result.to_dict(), indent=2, sort_keys=True) + "\n"
