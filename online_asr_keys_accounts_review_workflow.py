from __future__ import annotations

import json
from dataclasses import asdict, dataclass, is_dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Iterable, Mapping

from online_asr_keys_accounts_app_state import (
    OnlineASRKeysAccountsAppState,
    build_online_asr_keys_accounts_app_state,
)
from online_asr_keys_accounts_review_activity import (
    OnlineASRKeysAccountsReviewActivityDocument,
    build_online_asr_keys_accounts_review_activity_document,
)
from online_asr_keys_accounts_review_activity_store import (
    OnlineASRKeysAccountsReviewActivityStoreResult,
    write_online_asr_keys_accounts_review_activity_document,
)
from online_asr_keys_accounts_review_package import (
    OnlineASRKeysAccountsReviewPackage,
    build_online_asr_keys_accounts_review_package,
)
from online_asr_keys_accounts_review_package_store import (
    OnlineASRKeysAccountsReviewPackageStoreResult,
    write_online_asr_keys_accounts_review_package,
)


ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_WORKFLOW_SCHEMA_VERSION = "online_asr_keys_accounts_review_workflow_v1"
ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_PACKAGE_DIRECTORY_NAME = "online_asr_keys_accounts_review_package"
ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_ACTIVITY_DIRECTORY_NAME = "online_asr_keys_accounts_review_activity"


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


@dataclass(frozen=True)
class OnlineASRKeysAccountsReviewWorkflowResult:
    app_state: OnlineASRKeysAccountsAppState
    review_package: OnlineASRKeysAccountsReviewPackage
    package_store_result: OnlineASRKeysAccountsReviewPackageStoreResult
    activity_document: OnlineASRKeysAccountsReviewActivityDocument
    activity_store_result: OnlineASRKeysAccountsReviewActivityStoreResult
    output_root_role: str
    package_output_directory_role: str
    activity_output_directory_role: str
    selected_provider_id: str
    selected_provider_ready_for_gate_review: bool
    review_manifest_asset_count: int
    package_file_count: int
    activity_entry_count: int
    stored_file_count: int
    schema_version: str = ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_WORKFLOW_SCHEMA_VERSION
    review_status: str = "USER_REVIEW_REQUIRED"
    execution_state: str = "EXECUTION_GATED"
    metadata_only: bool = True
    local_only: bool = True
    user_selected_directory_required: bool = True
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
    verified_transcription_claimed: bool = False

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
                "Online ASR KEYS/ACCOUNTS review workflow",
                f"Selected provider: {self.selected_provider_id or 'none'} ({readiness})",
                f"Review manifest assets: {self.review_manifest_asset_count}",
                f"Package files: {self.package_file_count}",
                f"Activity entries: {self.activity_entry_count}",
                f"Stored metadata files: {self.stored_file_count}",
                "Review status: USER_REVIEW_REQUIRED",
                "Execution state: EXECUTION_GATED",
                "Provider call allowed without user approval: false",
                "Credential value read: false",
                "Completed transcription claimed: false",
            )
        )


def build_online_asr_keys_accounts_review_workflow_result(
    *,
    app_state: OnlineASRKeysAccountsAppState,
    review_package: OnlineASRKeysAccountsReviewPackage,
    package_store_result: OnlineASRKeysAccountsReviewPackageStoreResult,
    activity_store_result: OnlineASRKeysAccountsReviewActivityStoreResult,
    activity_document: OnlineASRKeysAccountsReviewActivityDocument,
    output_root_role: str = "user_selected_online_asr_keys_accounts_review_workflow_directory",
) -> OnlineASRKeysAccountsReviewWorkflowResult:
    """Compose app state, package, and activity-store results into one safe workflow result."""
    stored_file_count = package_store_result.file_count + activity_store_result.file_count
    return OnlineASRKeysAccountsReviewWorkflowResult(
        app_state=app_state,
        review_package=review_package,
        package_store_result=package_store_result,
        activity_document=activity_document,
        activity_store_result=activity_store_result,
        output_root_role=output_root_role,
        package_output_directory_role=package_store_result.output_directory_role,
        activity_output_directory_role=activity_store_result.output_directory_role,
        selected_provider_id=app_state.selected_provider.provider_id,
        selected_provider_ready_for_gate_review=app_state.selected_provider_ready_for_gate_review,
        review_manifest_asset_count=len(review_package.review_manifest.assets),
        package_file_count=review_package.index.package_file_count,
        activity_entry_count=activity_document.entry_count,
        stored_file_count=stored_file_count,
    )


def build_online_asr_keys_accounts_review_workflow(
    *,
    provider_options: Iterable[Any],
    credential_statuses: Mapping[str, Any] | None,
    output_directory: str | Path,
    package_id: str,
    created_at_utc: str,
    added_provider_ids: Iterable[str] | None = None,
    selected_provider_id: str = "",
    keys_accounts_query: str = "",
    add_provider_query: str = "",
    app_version: str = "",
    online_asr_gate_summary: Mapping[str, Any] | Any | None = None,
    allow_overwrite: bool = True,
) -> OnlineASRKeysAccountsReviewWorkflowResult:
    """Build and persist a complete metadata-only Online ASR KEYS/ACCOUNTS review workflow.

    This is a one-call local workflow around the previously separate safe layers:
    app-facing KEYS/ACCOUNTS state, review package index, review package store,
    activity document, and activity document store. It writes only metadata JSON
    files into a caller-selected output root and returns safe roles, counts,
    hashes, and filenames rather than full local paths.

    The workflow does not read credential values, execute provider calls,
    serialize raw media, expose full local paths, or claim completed/verified
    transcription.
    """
    app_state = build_online_asr_keys_accounts_app_state(
        provider_options=provider_options,
        credential_statuses=credential_statuses,
        added_provider_ids=added_provider_ids,
        selected_provider_id=selected_provider_id,
        keys_accounts_query=keys_accounts_query,
        add_provider_query=add_provider_query,
    )
    review_package = build_online_asr_keys_accounts_review_package(
        app_state=app_state,
        package_id=package_id,
        created_at_utc=created_at_utc,
        app_version=app_version,
        online_asr_gate_summary=online_asr_gate_summary,
    )
    output_root = Path(output_directory)
    package_store_result = write_online_asr_keys_accounts_review_package(
        review_package,
        output_root / ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_PACKAGE_DIRECTORY_NAME,
        allow_overwrite=allow_overwrite,
    )
    activity_document = build_online_asr_keys_accounts_review_activity_document(
        package=review_package,
        store_result=package_store_result,
        created_at_utc=created_at_utc,
    )
    activity_store_result = write_online_asr_keys_accounts_review_activity_document(
        activity_document,
        output_root / ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_ACTIVITY_DIRECTORY_NAME,
        allow_overwrite=allow_overwrite,
    )
    return build_online_asr_keys_accounts_review_workflow_result(
        app_state=app_state,
        review_package=review_package,
        package_store_result=package_store_result,
        activity_store_result=activity_store_result,
        activity_document=activity_document,
    )


def online_asr_keys_accounts_review_workflow_result_to_json(
    result: OnlineASRKeysAccountsReviewWorkflowResult,
) -> str:
    return json.dumps(result.to_dict(), indent=2, sort_keys=True) + "\n"
