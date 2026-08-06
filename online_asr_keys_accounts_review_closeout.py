from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, is_dataclass
from enum import Enum
from typing import Any, Mapping


ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_CLOSEOUT_SCHEMA_VERSION = (
    "online_asr_keys_accounts_review_closeout_v1"
)
ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_CLOSEOUT_STATUS = "REVIEW_READY_METADATA_ONLY"

_ONLINE_ASR_KEYS_ACCOUNTS_CLOSEOUT_COMPONENTS = (
    "keys_accounts_sidebar_label",
    "added_provider_panel",
    "add_provider_catalog_search",
    "selected_provider_readiness",
    "online_asr_execution_gate",
    "state_store_bundle",
    "total_export_review_manifest",
    "review_package_index",
    "review_package_store",
    "review_activity_chain",
    "review_activity_store",
    "one_call_review_workflow",
    "review_workflow_cli",
    "smoke_fixture_generator",
    "smoke_fixture_cli",
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


def _json_hash(value: Mapping[str, Any]) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _get_value(source: Any, name: str, default: Any = None) -> Any:
    if isinstance(source, Mapping):
        return source.get(name, default)
    return getattr(source, name, default)


@dataclass(frozen=True)
class OnlineASRKeysAccountsReviewCloseoutReport:
    package_id: str
    created_at_utc: str
    selected_provider_id: str
    selected_provider_ready_for_gate_review: bool
    workflow_result_schema_version: str
    reviewed_components: tuple[str, ...]
    reviewed_component_count: int
    fixture_file_names: tuple[str, ...]
    workflow_directory_names: tuple[str, ...]
    fixture_file_count: int
    workflow_directory_count: int
    stored_file_count: int
    closeout_hash: str
    schema_version: str = ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_CLOSEOUT_SCHEMA_VERSION
    closeout_status: str = ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_CLOSEOUT_STATUS
    review_status: str = "USER_REVIEW_REQUIRED"
    execution_state: str = "EXECUTION_GATED"
    metadata_only: bool = True
    local_only: bool = True
    keys_accounts_sidebar_label: str = "KEYS/ACCOUNTS"
    keys_accounts_shows_added_providers_only: bool = True
    add_provider_searches_full_catalog: bool = True
    user_selected_directory_required: bool = True
    provider_call_allowed_without_user_approval: bool = False
    runtime_provider_call_performed: bool = False
    credential_value_read: bool = False
    credential_plaintext_stored: bool = False
    raw_media_serialized: bool = False
    full_local_path_serialized: bool = False
    completed_transcription_claimed: bool = False
    verified_transcription_claimed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)

    def to_summary_text(self) -> str:
        readiness = (
            "ready for explicit provider-call review"
            if self.selected_provider_ready_for_gate_review
            else "needs KEYS/ACCOUNTS review before provider-call approval"
        )
        return "\n".join(
            (
                "Online ASR KEYS/ACCOUNTS review closeout",
                f"Package: {self.package_id}",
                f"Selected provider: {self.selected_provider_id or 'none'} ({readiness})",
                f"Reviewed components: {self.reviewed_component_count}",
                f"Fixture files: {self.fixture_file_count}",
                f"Workflow directories: {self.workflow_directory_count}",
                f"Stored metadata files: {self.stored_file_count}",
                "Closeout status: REVIEW_READY_METADATA_ONLY",
                "Execution state: EXECUTION_GATED",
                "Provider call allowed without user approval: false",
                "Credential value read: false",
                "Completed transcription claimed: false",
            )
        )


def build_online_asr_keys_accounts_review_closeout_report(
    smoke_fixture_result: Any,
    *,
    created_at_utc: str | None = None,
) -> OnlineASRKeysAccountsReviewCloseoutReport:
    """Build a deterministic closeout report for the safe Online ASR KEYS/ACCOUNTS workflow.

    The report summarizes the metadata-only workflow after a local smoke fixture has
    run. It intentionally keeps only filenames, directory roles/names, counts, hashes,
    and explicit safety flags. It does not expose full local paths, credential values,
    raw media, provider responses, or completed/verified transcription claims.
    """
    fixture_names = tuple(str(item) for item in _get_value(smoke_fixture_result, "written_fixture_file_names", ()))
    workflow_names = tuple(str(item) for item in _get_value(smoke_fixture_result, "written_workflow_directory_names", ()))
    report_seed = {
        "package_id": str(_get_value(smoke_fixture_result, "package_id", "")),
        "created_at_utc": str(created_at_utc or _get_value(smoke_fixture_result, "created_at_utc", "")),
        "selected_provider_id": str(_get_value(smoke_fixture_result, "selected_provider_id", "")),
        "selected_provider_ready_for_gate_review": bool(
            _get_value(smoke_fixture_result, "selected_provider_ready_for_gate_review", False)
        ),
        "workflow_result_schema_version": str(
            _get_value(smoke_fixture_result, "workflow_result_schema_version", "")
        ),
        "reviewed_components": list(_ONLINE_ASR_KEYS_ACCOUNTS_CLOSEOUT_COMPONENTS),
        "fixture_file_names": list(sorted(fixture_names)),
        "workflow_directory_names": list(sorted(workflow_names)),
        "stored_file_count": int(_get_value(smoke_fixture_result, "stored_file_count", 0) or 0),
        "closeout_status": ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_CLOSEOUT_STATUS,
    }
    return OnlineASRKeysAccountsReviewCloseoutReport(
        package_id=report_seed["package_id"],
        created_at_utc=report_seed["created_at_utc"],
        selected_provider_id=report_seed["selected_provider_id"],
        selected_provider_ready_for_gate_review=report_seed["selected_provider_ready_for_gate_review"],
        workflow_result_schema_version=report_seed["workflow_result_schema_version"],
        reviewed_components=_ONLINE_ASR_KEYS_ACCOUNTS_CLOSEOUT_COMPONENTS,
        reviewed_component_count=len(_ONLINE_ASR_KEYS_ACCOUNTS_CLOSEOUT_COMPONENTS),
        fixture_file_names=tuple(report_seed["fixture_file_names"]),
        workflow_directory_names=tuple(report_seed["workflow_directory_names"]),
        fixture_file_count=len(fixture_names),
        workflow_directory_count=len(workflow_names),
        stored_file_count=report_seed["stored_file_count"],
        closeout_hash=_json_hash(report_seed),
    )


def online_asr_keys_accounts_review_closeout_report_to_json(
    report: OnlineASRKeysAccountsReviewCloseoutReport,
) -> str:
    return json.dumps(report.to_dict(), indent=2, sort_keys=True) + "\n"
