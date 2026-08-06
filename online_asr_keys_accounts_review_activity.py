from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, is_dataclass
from enum import Enum
from typing import Any, Mapping

from online_asr_keys_accounts_review_package import OnlineASRKeysAccountsReviewPackage
from online_asr_keys_accounts_review_package_store import OnlineASRKeysAccountsReviewPackageStoreResult


ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_ACTIVITY_SCHEMA_VERSION = "online_asr_keys_accounts_review_activity_v1"


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
    return json.dumps(_value_for_dict(data), separators=(",", ":"), sort_keys=True)


def _sha256(data: Any) -> str:
    return hashlib.sha256(_stable_json(data).encode("utf-8")).hexdigest()


def _sha16(data: Any) -> str:
    return _sha256(data)[:16]


@dataclass(frozen=True)
class OnlineASRKeysAccountsReviewActivityEntry:
    sequence_number: int
    activity_id: str
    activity_type: str
    subject_id: str
    subject_role: str
    detail: str
    source_sha256: str
    previous_activity_sha256: str
    activity_sha256: str
    created_at_utc: str
    schema_version: str = ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_ACTIVITY_SCHEMA_VERSION
    review_status: str = "USER_REVIEW_REQUIRED"
    execution_state: str = "EXECUTION_GATED"
    metadata_only: bool = True
    local_only: bool = True
    keys_accounts_sidebar_label: str = "KEYS/ACCOUNTS"
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
class OnlineASRKeysAccountsReviewActivityDocument:
    activity_document_id: str
    package_id: str
    package_index_id: str
    selected_provider_id: str
    entry_count: int
    entries: tuple[OnlineASRKeysAccountsReviewActivityEntry, ...]
    created_at_utc: str
    actor_role: str = "local_operator_review"
    schema_version: str = ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_ACTIVITY_SCHEMA_VERSION
    review_status: str = "USER_REVIEW_REQUIRED"
    execution_state: str = "EXECUTION_GATED"
    metadata_only: bool = True
    local_only: bool = True
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
                "Online ASR KEYS/ACCOUNTS review activity",
                f"Activity document ID: {self.activity_document_id}",
                f"Package ID: {self.package_id}",
                f"Package index ID: {self.package_index_id}",
                f"Selected provider: {self.selected_provider_id or 'none'}",
                f"Activity entries: {self.entry_count}",
                "Review status: USER_REVIEW_REQUIRED",
                "Execution state: EXECUTION_GATED",
                "Provider call allowed without user approval: false",
                "Credential value read: false",
                "Completed transcription claimed: false",
            )
        )


def _entry(
    *,
    sequence_number: int,
    activity_type: str,
    subject_id: str,
    subject_role: str,
    detail: str,
    source_payload: Mapping[str, Any],
    previous_activity_sha256: str,
    created_at_utc: str,
) -> OnlineASRKeysAccountsReviewActivityEntry:
    source_sha256 = _sha256(source_payload)
    seed = {
        "activity_type": activity_type,
        "created_at_utc": created_at_utc,
        "detail": detail,
        "previous_activity_sha256": previous_activity_sha256,
        "schema_version": ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_ACTIVITY_SCHEMA_VERSION,
        "sequence_number": sequence_number,
        "source_sha256": source_sha256,
        "subject_id": subject_id,
        "subject_role": subject_role,
    }
    activity_sha256 = _sha256(seed)
    activity_id = "online_asr_keys_accounts_activity_" + _sha16(seed)
    return OnlineASRKeysAccountsReviewActivityEntry(
        sequence_number=sequence_number,
        activity_id=activity_id,
        activity_type=activity_type,
        subject_id=subject_id,
        subject_role=subject_role,
        detail=detail,
        source_sha256=source_sha256,
        previous_activity_sha256=previous_activity_sha256,
        activity_sha256=activity_sha256,
        created_at_utc=created_at_utc,
    )


def build_online_asr_keys_accounts_review_activity_document(
    *,
    package: OnlineASRKeysAccountsReviewPackage,
    store_result: OnlineASRKeysAccountsReviewPackageStoreResult,
    created_at_utc: str,
    actor_role: str = "local_operator_review",
) -> OnlineASRKeysAccountsReviewActivityDocument:
    """Build a metadata-only activity document for Online ASR KEYS/ACCOUNTS review.

    The document records safe activity receipts around review-package creation and
    persistence. It links to package/store hashes and IDs, but it does not read
    credential values, execute provider calls, serialize raw media, expose full
    local paths, or claim a completed transcription.
    """
    previous = ""
    entries: list[OnlineASRKeysAccountsReviewActivityEntry] = []
    entry_inputs = (
        (
            "online_asr_keys_accounts_app_state_reviewed",
            package.index.app_state_id,
            "app_state",
            "App-facing KEYS/ACCOUNTS provider state prepared for review.",
            package.state_payloads.get("online_asr_keys_accounts_app_state.json", {}),
        ),
        (
            "online_asr_keys_accounts_review_manifest_indexed",
            package.index.review_manifest_package_id,
            "total_export_review_manifest",
            "Total Export review manifest indexed as metadata-only sidecar.",
            package.review_manifest.to_dict(),
        ),
        (
            "online_asr_keys_accounts_review_package_indexed",
            package.index.package_index_id,
            "review_package_index",
            "Deterministic review package index created with file roles and hashes.",
            package.index.to_dict(),
        ),
        (
            "online_asr_keys_accounts_review_package_stored",
            store_result.package_index_id,
            "review_package_store_result",
            "Metadata-only review package persisted to user-selected directory.",
            store_result.to_dict(),
        ),
    )
    for position, (activity_type, subject_id, subject_role, detail, source_payload) in enumerate(entry_inputs, start=1):
        current = _entry(
            sequence_number=position,
            activity_type=activity_type,
            subject_id=subject_id,
            subject_role=subject_role,
            detail=detail,
            source_payload=_value_for_dict(source_payload),
            previous_activity_sha256=previous,
            created_at_utc=created_at_utc,
        )
        entries.append(current)
        previous = current.activity_sha256
    document_seed = {
        "actor_role": actor_role,
        "created_at_utc": created_at_utc,
        "entries": [entry.to_dict() for entry in entries],
        "package_id": package.index.package_id,
        "package_index_id": package.index.package_index_id,
        "schema_version": ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_ACTIVITY_SCHEMA_VERSION,
        "selected_provider_id": package.index.selected_provider_id,
    }
    return OnlineASRKeysAccountsReviewActivityDocument(
        activity_document_id="online_asr_keys_accounts_review_activity_" + _sha16(document_seed),
        package_id=package.index.package_id,
        package_index_id=package.index.package_index_id,
        selected_provider_id=package.index.selected_provider_id,
        entry_count=len(entries),
        entries=tuple(entries),
        created_at_utc=created_at_utc,
        actor_role=actor_role,
    )


def online_asr_keys_accounts_review_activity_document_to_json(
    document: OnlineASRKeysAccountsReviewActivityDocument,
) -> str:
    return json.dumps(document.to_dict(), indent=2, sort_keys=True) + "\n"
