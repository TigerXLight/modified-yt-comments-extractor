from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, is_dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Mapping

from online_asr_keys_accounts_app_state import OnlineASRKeysAccountsAppState


ONLINE_ASR_KEYS_ACCOUNTS_STATE_STORE_SCHEMA_VERSION = "online_asr_keys_accounts_state_store_v1"


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
    if isinstance(value, Path):
        return value.name
    return value


def _canonical_json(data: Mapping[str, Any]) -> str:
    return json.dumps(data, separators=(",", ":"), sort_keys=True)


def _sha16(data: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canonical_json(data).encode("utf-8")).hexdigest()[:16]


def _write_json(path: Path, payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(_value_for_dict(payload), indent=2, sort_keys=True) + "\n"
    path.write_text(encoded, encoding="utf-8")
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class OnlineASRKeysAccountsStateStoreFile:
    file_role: str
    filename: str
    sha256: str
    schema_version: str = ONLINE_ASR_KEYS_ACCOUNTS_STATE_STORE_SCHEMA_VERSION
    metadata_only: bool = True
    plaintext_secret_storage_allowed: bool = False
    secret_value_recorded: bool = False
    credential_value_read: bool = False
    provider_call_allowed_without_user_approval: bool = False
    runtime_provider_call_performed: bool = False
    raw_media_payload_included: bool = False
    full_local_path_included: bool = False
    completed_transcription_claimed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class OnlineASRKeysAccountsStateStoreResult:
    bundle_id: str
    output_directory_name: str
    app_state_id: str
    selected_provider_id: str
    selected_provider_ready_for_gate_review: bool
    file_count: int
    files: tuple[OnlineASRKeysAccountsStateStoreFile, ...]
    summary_text: str
    schema_version: str = ONLINE_ASR_KEYS_ACCOUNTS_STATE_STORE_SCHEMA_VERSION
    review_status: str = "USER_REVIEW_REQUIRED"
    execution_state: str = "EXECUTION_GATED"
    metadata_only: bool = True
    local_only: bool = True
    plaintext_secret_storage_allowed: bool = False
    secret_value_recorded: bool = False
    credential_value_read: bool = False
    provider_call_allowed_without_user_approval: bool = False
    runtime_provider_call_performed: bool = False
    raw_media_payload_included: bool = False
    full_local_path_included: bool = False
    completed_transcription_claimed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)

    def to_summary_text(self) -> str:
        return self.summary_text


def build_online_asr_keys_accounts_state_store_payloads(
    app_state: OnlineASRKeysAccountsAppState,
) -> dict[str, Mapping[str, Any]]:
    """Build metadata-only JSON payloads for saving KEYS/ACCOUNTS app state.

    The payloads intentionally mirror only safe UI/review state. They do not read
    credential values, dispatch provider calls, serialize raw media, expose full
    local paths, or claim that any Online ASR transcription completed.
    """
    app_state_payload = app_state.to_dict()
    catalog_payload = app_state.catalog_state.to_dict()
    selected_payload = app_state.selected_provider.to_dict()
    bundle_payload = {
        "schema_version": ONLINE_ASR_KEYS_ACCOUNTS_STATE_STORE_SCHEMA_VERSION,
        "review_status": "USER_REVIEW_REQUIRED",
        "execution_state": "EXECUTION_GATED",
        "app_state_id": app_state.app_state_id,
        "selected_provider_id": app_state.selected_provider.provider_id,
        "selected_provider_ready_for_gate_review": app_state.selected_provider_ready_for_gate_review,
        "keys_accounts_sidebar_label": app_state.keys_accounts_sidebar_label,
        "keys_accounts_window_shows_added_providers_only": True,
        "add_provider_window_searches_full_catalog": True,
        "online_asr_next_to_local_asr": True,
        "online_asr_reuses_local_asr_control_style": True,
        "added_provider_count": app_state.added_provider_count,
        "configured_provider_count": app_state.configured_provider_count,
        "missing_key_provider_count": app_state.missing_key_provider_count,
        "provider_call_allowed_without_user_approval": False,
        "runtime_provider_call_performed": False,
        "credential_value_read": False,
        "plaintext_secret_storage_allowed": False,
        "secret_value_recorded": False,
        "raw_media_payload_included": False,
        "full_local_path_included": False,
        "completed_transcription_claimed": False,
    }
    return {
        "online_asr_keys_accounts_app_state.json": app_state_payload,
        "online_asr_provider_catalog_state.json": catalog_payload,
        "online_asr_selected_provider_readiness.json": selected_payload,
        "online_asr_keys_accounts_state_bundle.json": bundle_payload,
    }


def write_online_asr_keys_accounts_state_bundle(
    app_state: OnlineASRKeysAccountsAppState,
    output_directory: str | Path,
) -> OnlineASRKeysAccountsStateStoreResult:
    """Write safe Online ASR KEYS/ACCOUNTS metadata state into a user-chosen folder."""
    output = Path(output_directory)
    output.mkdir(parents=True, exist_ok=True)
    payloads = build_online_asr_keys_accounts_state_store_payloads(app_state)
    files: list[OnlineASRKeysAccountsStateStoreFile] = []
    for filename, payload in payloads.items():
        sha256 = _write_json(output / filename, payload)
        files.append(
            OnlineASRKeysAccountsStateStoreFile(
                file_role=filename.removesuffix(".json"),
                filename=filename,
                sha256=sha256,
            )
        )
    result_seed = {
        "app_state_id": app_state.app_state_id,
        "files": [file.to_dict() for file in files],
        "schema_version": ONLINE_ASR_KEYS_ACCOUNTS_STATE_STORE_SCHEMA_VERSION,
        "selected_provider_id": app_state.selected_provider.provider_id,
    }
    ready = app_state.selected_provider_ready_for_gate_review
    readiness = "ready for explicit provider-call review" if ready else "needs key/account before provider-call review"
    summary = "\n".join(
        (
            "Online ASR KEYS/ACCOUNTS state bundle",
            f"Bundle ID: online_asr_keys_accounts_state_{_sha16(result_seed)}",
            f"Output folder: {output.name}",
            f"Selected provider: {app_state.selected_provider.provider_id or 'none'} ({readiness})",
            f"Metadata files written: {len(files)}",
            "Review status: USER_REVIEW_REQUIRED",
            "Execution state: EXECUTION_GATED",
            "Provider call allowed without user approval: false",
            "Credential value read: false",
            "Plaintext secret storage allowed: false",
            "Runtime provider call performed: false",
        )
    )
    return OnlineASRKeysAccountsStateStoreResult(
        bundle_id="online_asr_keys_accounts_state_" + _sha16(result_seed),
        output_directory_name=output.name,
        app_state_id=app_state.app_state_id,
        selected_provider_id=app_state.selected_provider.provider_id,
        selected_provider_ready_for_gate_review=ready,
        file_count=len(files),
        files=tuple(files),
        summary_text=summary,
    )


def online_asr_keys_accounts_state_store_result_to_json(
    result: OnlineASRKeysAccountsStateStoreResult,
) -> str:
    return json.dumps(result.to_dict(), indent=2, sort_keys=True) + "\n"
