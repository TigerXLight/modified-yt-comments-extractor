from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, is_dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Mapping

from online_asr_keys_accounts_review_package import (
    OnlineASRKeysAccountsReviewPackage,
    build_online_asr_keys_accounts_review_package_payloads,
)


ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_PACKAGE_STORE_SCHEMA_VERSION = "online_asr_keys_accounts_review_package_store_v1"


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


def _stable_json(data: Any) -> str:
    return json.dumps(_value_for_dict(data), indent=2, sort_keys=True) + "\n"


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class OnlineASRKeysAccountsReviewPackageStoredFile:
    filename: str
    file_role: str
    sha256: str
    byte_count: int
    schema_version: str = ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_PACKAGE_STORE_SCHEMA_VERSION
    metadata_only: bool = True
    local_only: bool = True
    user_selected_directory_required: bool = True
    credential_value_read: bool = False
    plaintext_secret_storage_allowed: bool = False
    secret_value_recorded: bool = False
    provider_call_allowed_without_user_approval: bool = False
    runtime_provider_call_performed: bool = False
    raw_media_payload_included: bool = False
    full_local_path_included: bool = False
    completed_transcription_claimed: bool = False
    verified_transcription_claimed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class OnlineASRKeysAccountsReviewPackageStoreResult:
    package_id: str
    package_index_id: str
    output_directory_role: str
    file_count: int
    files: tuple[OnlineASRKeysAccountsReviewPackageStoredFile, ...]
    schema_version: str = ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_PACKAGE_STORE_SCHEMA_VERSION
    review_status: str = "USER_REVIEW_REQUIRED"
    execution_state: str = "EXECUTION_GATED"
    metadata_only: bool = True
    local_only: bool = True
    user_selected_directory_required: bool = True
    keys_accounts_sidebar_label: str = "KEYS/ACCOUNTS"
    provider_call_allowed_without_user_approval: bool = False
    runtime_provider_call_performed: bool = False
    credential_value_read: bool = False
    plaintext_secret_storage_allowed: bool = False
    secret_value_recorded: bool = False
    raw_media_payload_included: bool = False
    full_local_path_included: bool = False
    completed_transcription_claimed: bool = False
    verified_transcription_claimed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)

    def to_summary_text(self) -> str:
        return "\n".join(
            (
                "Online ASR KEYS/ACCOUNTS review package stored",
                f"Package ID: {self.package_id}",
                f"Package index ID: {self.package_index_id}",
                f"Metadata files: {self.file_count}",
                "Review status: USER_REVIEW_REQUIRED",
                "Execution state: EXECUTION_GATED",
                "Provider call allowed without user approval: false",
                "Credential value read: false",
                "Completed transcription claimed: false",
            )
        )


def _role_from_filename(filename: str) -> str:
    return filename.removesuffix(".json")


def build_online_asr_keys_accounts_review_package_store_payloads(
    package: OnlineASRKeysAccountsReviewPackage,
) -> dict[str, str]:
    """Build stable JSON payload text for a review package without writing files."""
    payloads = build_online_asr_keys_accounts_review_package_payloads(package)
    return {filename: _stable_json(payloads[filename]) for filename in sorted(payloads)}


def write_online_asr_keys_accounts_review_package(
    package: OnlineASRKeysAccountsReviewPackage,
    output_directory: str | Path,
    *,
    allow_overwrite: bool = True,
) -> OnlineASRKeysAccountsReviewPackageStoreResult:
    """Write the metadata-only Online ASR KEYS/ACCOUNTS review package sidecars.

    The returned result deliberately records only filenames and hashes, not the
    caller's full local output directory path. The function writes only the safe
    JSON sidecars produced by the package builder. It does not read credential
    values, execute provider calls, include raw media, or claim a completed
    transcription.
    """
    output_path = Path(output_directory)
    output_path.mkdir(parents=True, exist_ok=True)
    payload_texts = build_online_asr_keys_accounts_review_package_store_payloads(package)
    stored_files: list[OnlineASRKeysAccountsReviewPackageStoredFile] = []
    for filename, payload_text in payload_texts.items():
        file_path = output_path / filename
        if file_path.exists() and not allow_overwrite:
            raise FileExistsError(f"Refusing to overwrite existing review package file: {filename}")
        file_path.write_text(payload_text, encoding="utf-8")
        stored_files.append(
            OnlineASRKeysAccountsReviewPackageStoredFile(
                filename=filename,
                file_role=_role_from_filename(filename),
                sha256=_sha256_text(payload_text),
                byte_count=len(payload_text.encode("utf-8")),
            )
        )
    return OnlineASRKeysAccountsReviewPackageStoreResult(
        package_id=package.index.package_id,
        package_index_id=package.index.package_index_id,
        output_directory_role="user_selected_online_asr_keys_accounts_review_package_directory",
        file_count=len(stored_files),
        files=tuple(stored_files),
    )


def online_asr_keys_accounts_review_package_store_result_to_json(
    result: OnlineASRKeysAccountsReviewPackageStoreResult,
) -> str:
    return json.dumps(result.to_dict(), indent=2, sort_keys=True) + "\n"
