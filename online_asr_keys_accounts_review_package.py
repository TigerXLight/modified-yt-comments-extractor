from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, is_dataclass
from enum import Enum
from typing import Any, Mapping

from online_asr_keys_accounts_app_state import OnlineASRKeysAccountsAppState
from online_asr_keys_accounts_review_export import (
    OnlineASRKeysAccountsReviewExportSummary,
    build_online_asr_keys_accounts_review_export_summary,
    build_online_asr_keys_accounts_review_manifest,
)
from online_asr_keys_accounts_state_store import (
    build_online_asr_keys_accounts_state_store_payloads,
)
from total_export_manifest import ASSET_MANIFEST, ASSET_RAW_SIDECAR, TotalExportManifest


ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_PACKAGE_SCHEMA_VERSION = "online_asr_keys_accounts_review_package_v1"


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
class OnlineASRKeysAccountsReviewPackageFile:
    file_role: str
    filename: str
    sha256: str
    asset_type: str
    source_section: str
    schema_version: str = ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_PACKAGE_SCHEMA_VERSION
    metadata_only: bool = True
    local_only: bool = True
    credential_value_read: bool = False
    plaintext_secret_storage_allowed: bool = False
    secret_value_recorded: bool = False
    provider_call_allowed_without_user_approval: bool = False
    runtime_provider_call_performed: bool = False
    raw_media_payload_included: bool = False
    full_local_path_included: bool = False
    completed_transcription_claimed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class OnlineASRKeysAccountsReviewPackageIndex:
    package_id: str
    package_index_id: str
    created_at_utc: str
    selected_provider_id: str
    selected_provider_ready_for_gate_review: bool
    app_state_id: str
    review_manifest_package_id: str
    review_manifest_asset_count: int
    state_payload_file_count: int
    package_file_count: int
    capture_options: tuple[str, ...]
    files: tuple[OnlineASRKeysAccountsReviewPackageFile, ...]
    schema_version: str = ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_PACKAGE_SCHEMA_VERSION
    review_status: str = "USER_REVIEW_REQUIRED"
    execution_state: str = "EXECUTION_GATED"
    metadata_only: bool = True
    local_only: bool = True
    keys_accounts_sidebar_label: str = "KEYS/ACCOUNTS"
    keys_accounts_window_shows_added_providers_only: bool = True
    add_provider_window_searches_full_catalog: bool = True
    provider_call_allowed_without_user_approval: bool = False
    runtime_provider_call_performed: bool = False
    credential_value_read: bool = False
    plaintext_secret_storage_allowed: bool = False
    secret_value_recorded: bool = False
    raw_media_payload_included: bool = False
    full_local_path_included: bool = False
    completed_transcription_claimed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)

    def to_summary_text(self) -> str:
        readiness = (
            "ready for explicit provider-call review"
            if self.selected_provider_ready_for_gate_review
            else "needs key/account before provider-call review"
        )
        return "\n".join(
            (
                "Online ASR KEYS/ACCOUNTS review package index",
                f"Package ID: {self.package_id}",
                f"Package index ID: {self.package_index_id}",
                f"Selected provider: {self.selected_provider_id or 'none'} ({readiness})",
                f"Package files: {self.package_file_count}",
                f"Review manifest assets: {self.review_manifest_asset_count}",
                "Review status: USER_REVIEW_REQUIRED",
                "Execution state: EXECUTION_GATED",
                "Provider call allowed without user approval: false",
                "Credential value read: false",
                "Completed transcription claimed: false",
            )
        )


@dataclass(frozen=True)
class OnlineASRKeysAccountsReviewPackage:
    index: OnlineASRKeysAccountsReviewPackageIndex
    state_payloads: Mapping[str, Mapping[str, Any]]
    review_manifest: TotalExportManifest
    review_summary: OnlineASRKeysAccountsReviewExportSummary
    schema_version: str = ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_PACKAGE_SCHEMA_VERSION
    metadata_only: bool = True
    provider_call_allowed_without_user_approval: bool = False
    runtime_provider_call_performed: bool = False
    credential_value_read: bool = False
    plaintext_secret_storage_allowed: bool = False
    secret_value_recorded: bool = False
    raw_media_payload_included: bool = False
    full_local_path_included: bool = False
    completed_transcription_claimed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


def _state_file_entry(filename: str, payload: Mapping[str, Any]) -> OnlineASRKeysAccountsReviewPackageFile:
    asset_type = ASSET_MANIFEST if filename.endswith("state_bundle.json") else ASSET_RAW_SIDECAR
    return OnlineASRKeysAccountsReviewPackageFile(
        file_role=filename.removesuffix(".json"),
        filename=filename,
        sha256=_sha256(payload),
        asset_type=asset_type,
        source_section="state_store_payload",
    )


def _package_file_entry(
    *,
    file_role: str,
    filename: str,
    payload: Mapping[str, Any],
    asset_type: str,
    source_section: str,
) -> OnlineASRKeysAccountsReviewPackageFile:
    return OnlineASRKeysAccountsReviewPackageFile(
        file_role=file_role,
        filename=filename,
        sha256=_sha256(payload),
        asset_type=asset_type,
        source_section=source_section,
    )


def build_online_asr_keys_accounts_review_package(
    *,
    app_state: OnlineASRKeysAccountsAppState,
    package_id: str,
    created_at_utc: str,
    app_version: str = "",
    online_asr_gate_summary: Mapping[str, Any] | Any | None = None,
) -> OnlineASRKeysAccountsReviewPackage:
    """Build a metadata-only package index for Online ASR KEYS/ACCOUNTS review export.

    This is the next safe handoff layer after the app-state, state-store, and
    review-manifest builders. It creates one deterministic index tying together
    the safe state payloads, Total Export review manifest, and review summary.
    It does not write files, read credential values, execute provider calls,
    include raw media, expose full local paths, or claim completed transcription.
    """
    state_payloads = build_online_asr_keys_accounts_state_store_payloads(app_state)
    review_manifest = build_online_asr_keys_accounts_review_manifest(
        app_state=app_state,
        package_id=package_id,
        created_at_utc=created_at_utc,
        state_payloads=state_payloads,
        online_asr_gate_summary=online_asr_gate_summary,
        app_version=app_version,
    )
    review_summary = build_online_asr_keys_accounts_review_export_summary(
        app_state=app_state,
        manifest=review_manifest,
        state_payload_filenames=state_payloads.keys(),
    )
    file_entries = [_state_file_entry(filename, state_payloads[filename]) for filename in sorted(state_payloads)]
    file_entries.append(
        _package_file_entry(
            file_role="online_asr_keys_accounts_review_manifest",
            filename="online_asr_keys_accounts_review_manifest.json",
            payload=review_manifest.to_dict(),
            asset_type=ASSET_MANIFEST,
            source_section="review_manifest",
        )
    )
    file_entries.append(
        _package_file_entry(
            file_role="online_asr_keys_accounts_review_summary",
            filename="online_asr_keys_accounts_review_summary.json",
            payload=review_summary.to_dict(),
            asset_type=ASSET_RAW_SIDECAR,
            source_section="review_summary",
        )
    )
    seed = {
        "app_state_id": app_state.app_state_id,
        "created_at_utc": created_at_utc,
        "files": [entry.to_dict() for entry in file_entries],
        "package_id": package_id,
        "schema_version": ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_PACKAGE_SCHEMA_VERSION,
        "selected_provider_id": app_state.selected_provider.provider_id,
    }
    index = OnlineASRKeysAccountsReviewPackageIndex(
        package_id=package_id,
        package_index_id="online_asr_keys_accounts_review_package_" + _sha16(seed),
        created_at_utc=created_at_utc,
        selected_provider_id=app_state.selected_provider.provider_id,
        selected_provider_ready_for_gate_review=app_state.selected_provider_ready_for_gate_review,
        app_state_id=app_state.app_state_id,
        review_manifest_package_id=review_manifest.package_id,
        review_manifest_asset_count=len(review_manifest.assets),
        state_payload_file_count=len(state_payloads),
        package_file_count=len(file_entries) + 1,
        capture_options=tuple(sorted(review_manifest.capture_options)),
        files=tuple(file_entries),
    )
    return OnlineASRKeysAccountsReviewPackage(
        index=index,
        state_payloads=state_payloads,
        review_manifest=review_manifest,
        review_summary=review_summary,
    )


def build_online_asr_keys_accounts_review_package_payloads(
    package: OnlineASRKeysAccountsReviewPackage,
) -> dict[str, Mapping[str, Any]]:
    """Return the safe JSON payload map represented by a review package."""
    payloads: dict[str, Mapping[str, Any]] = {
        "online_asr_keys_accounts_review_package_index.json": package.index.to_dict(),
        "online_asr_keys_accounts_review_manifest.json": package.review_manifest.to_dict(),
        "online_asr_keys_accounts_review_summary.json": package.review_summary.to_dict(),
    }
    payloads.update(dict(package.state_payloads))
    return payloads


def online_asr_keys_accounts_review_package_to_json(
    package: OnlineASRKeysAccountsReviewPackage,
) -> str:
    return json.dumps(package.to_dict(), indent=2, sort_keys=True) + "\n"


def online_asr_keys_accounts_review_package_index_to_json(
    index: OnlineASRKeysAccountsReviewPackageIndex,
) -> str:
    return json.dumps(index.to_dict(), indent=2, sort_keys=True) + "\n"
