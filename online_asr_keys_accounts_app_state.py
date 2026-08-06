from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field, is_dataclass
from enum import Enum
from typing import Any, Iterable, Mapping

from online_asr_provider_catalog import (
    OnlineASRProviderCatalogEntry,
    OnlineASRProviderCatalogState,
    build_online_asr_provider_catalog_state,
)


ONLINE_ASR_KEYS_ACCOUNTS_APP_STATE_SCHEMA_VERSION = "online_asr_keys_accounts_app_state_v1"


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
    return value


def _canonical_json(data: Mapping[str, Any]) -> str:
    return json.dumps(data, separators=(",", ":"), sort_keys=True)


def _sha16(data: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canonical_json(data).encode("utf-8")).hexdigest()[:16]


def _safe_text(value: Any) -> str:
    return " ".join(str(value or "").replace("\x00", " ").split())


def _entry_display_name(entry: OnlineASRProviderCatalogEntry | None, fallback: str) -> str:
    if entry is None:
        return _safe_text(fallback)
    return entry.display_name or entry.provider_id


@dataclass(frozen=True)
class OnlineASRKeysAccountsSearchPanelState:
    panel_id: str
    label: str
    query: str
    search_scope: str
    result_count: int
    provider_ids: tuple[str, ...]
    empty_state_text: str
    schema_version: str = ONLINE_ASR_KEYS_ACCOUNTS_APP_STATE_SCHEMA_VERSION
    visible_provider_scope_is_safe: bool = True
    plaintext_secret_storage_allowed: bool = False
    secret_value_recorded: bool = False
    provider_call_allowed_without_user_approval: bool = False
    runtime_provider_call_performed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class OnlineASRSelectedProviderReadinessState:
    provider_id: str
    display_name: str
    configured: bool
    added_to_keys_accounts: bool
    ready_for_review_gate: bool
    action_required: str
    action_label: str
    schema_version: str = ONLINE_ASR_KEYS_ACCOUNTS_APP_STATE_SCHEMA_VERSION
    credential_value_read: bool = False
    plaintext_secret_storage_allowed: bool = False
    secret_value_recorded: bool = False
    provider_call_allowed_without_user_approval: bool = False
    runtime_provider_call_performed: bool = False
    completed_transcription_claimed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class OnlineASRKeysAccountsAppState:
    app_state_id: str
    selected_provider: OnlineASRSelectedProviderReadinessState
    keys_accounts_panel: OnlineASRKeysAccountsSearchPanelState
    add_provider_panel: OnlineASRKeysAccountsSearchPanelState
    catalog_state: OnlineASRProviderCatalogState
    schema_version: str = ONLINE_ASR_KEYS_ACCOUNTS_APP_STATE_SCHEMA_VERSION
    keys_accounts_sidebar_label: str = "KEYS/ACCOUNTS"
    keys_accounts_window_shows_added_providers_only: bool = True
    add_provider_window_searches_full_catalog: bool = True
    local_asr_button_label: str = "Local ASR"
    online_asr_button_label: str = "Online ASR"
    online_asr_next_to_local_asr: bool = True
    online_asr_reuses_local_asr_control_style: bool = True
    selected_provider_ready_for_gate_review: bool = False
    added_provider_count: int = 0
    configured_provider_count: int = 0
    missing_key_provider_count: int = 0
    provider_call_allowed_without_user_approval: bool = False
    plaintext_secret_storage_allowed: bool = False
    secret_value_recorded: bool = False
    raw_media_payload_included: bool = False
    full_local_path_included: bool = False
    credential_value_read: bool = False
    runtime_provider_call_performed: bool = False
    completed_transcription_claimed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)

    def to_summary_text(self) -> str:
        readiness = "ready for review gate" if self.selected_provider_ready_for_gate_review else "needs key/account"
        return "\n".join(
            (
                "Online ASR KEYS/ACCOUNTS app state",
                f"App state ID: {self.app_state_id}",
                f"Sidebar label: {self.keys_accounts_sidebar_label}",
                f"Selected provider: {self.selected_provider.provider_id or 'none'} ({readiness})",
                f"Added providers visible in KEYS/ACCOUNTS: {self.keys_accounts_panel.result_count}",
                f"Add Provider catalogue matches: {self.add_provider_panel.result_count}",
                "Online ASR sits beside Local ASR: true",
                "Online ASR reuses Local ASR control style: true",
                "Provider call allowed without user approval: false",
                "Plaintext secret storage allowed: false",
                "Runtime provider call performed: false",
            )
        )


def _provider_ids(entries: Iterable[OnlineASRProviderCatalogEntry]) -> tuple[str, ...]:
    return tuple(entry.provider_id for entry in entries)


def _selected_entry(
    catalog_state: OnlineASRProviderCatalogState,
) -> OnlineASRProviderCatalogEntry | None:
    return next(
        (
            entry for entry in catalog_state.full_catalog_entries
            if entry.provider_id == catalog_state.selected_provider_id
        ),
        None,
    )


def _selected_readiness(
    catalog_state: OnlineASRProviderCatalogState,
) -> OnlineASRSelectedProviderReadinessState:
    entry = _selected_entry(catalog_state)
    configured = bool(entry and entry.configured)
    added = bool(entry and entry.added_to_keys_accounts)
    ready = bool(configured and added)
    if not entry:
        action_required = "select_online_asr_provider"
        action_label = "Select an Online ASR provider"
    elif not added:
        action_required = "add_provider_to_keys_accounts"
        action_label = "Add provider in KEYS/ACCOUNTS"
    elif not configured:
        action_required = "configure_provider_key_or_account"
        action_label = "Configure provider key/account in KEYS/ACCOUNTS"
    else:
        action_required = "review_and_explicitly_approve_provider_call"
        action_label = "Review and explicitly approve Online ASR provider call"
    return OnlineASRSelectedProviderReadinessState(
        provider_id=catalog_state.selected_provider_id,
        display_name=_entry_display_name(entry, catalog_state.selected_provider_id),
        configured=configured,
        added_to_keys_accounts=added,
        ready_for_review_gate=ready,
        action_required=action_required,
        action_label=action_label,
    )


def build_online_asr_keys_accounts_app_state(
    *,
    provider_options: Iterable[Any],
    credential_statuses: Mapping[str, Any] | None = None,
    added_provider_ids: Iterable[str] | None = None,
    selected_provider_id: str = "",
    keys_accounts_query: str = "",
    add_provider_query: str = "",
) -> OnlineASRKeysAccountsAppState:
    """Build a safe app-facing state projection for KEYS/ACCOUNTS and Online ASR.

    This is metadata-only UI state. It separates the added-provider list shown by
    KEYS/ACCOUNTS from the full searchable Add Provider catalogue and exposes the
    selected Online ASR provider readiness needed before the execution-gate plan.
    It does not read credential values, dispatch provider calls, serialize raw
    media, or claim that any transcription completed.
    """
    catalog_state = build_online_asr_provider_catalog_state(
        provider_options=provider_options,
        credential_statuses=credential_statuses,
        added_provider_ids=added_provider_ids,
        selected_provider_id=selected_provider_id,
        keys_accounts_query=keys_accounts_query,
        add_provider_query=add_provider_query,
    )
    selected = _selected_readiness(catalog_state)
    keys_panel = OnlineASRKeysAccountsSearchPanelState(
        panel_id="online_asr_keys_accounts_added_providers",
        label="KEYS/ACCOUNTS added providers",
        query=catalog_state.keys_accounts_query,
        search_scope="added_providers_only",
        result_count=catalog_state.keys_accounts_visible_count,
        provider_ids=_provider_ids(catalog_state.keys_accounts_entries),
        empty_state_text="No added Online ASR providers match this KEYS/ACCOUNTS search.",
    )
    add_panel = OnlineASRKeysAccountsSearchPanelState(
        panel_id="online_asr_add_provider_full_catalog",
        label="Add Provider full catalogue",
        query=catalog_state.add_provider_query,
        search_scope="full_provider_catalog",
        result_count=catalog_state.add_provider_match_count,
        provider_ids=_provider_ids(catalog_state.add_provider_entries),
        empty_state_text="No Online ASR providers match this Add Provider catalogue search.",
    )
    payload = {
        "catalog_state_id": catalog_state.catalog_state_id,
        "keys_accounts_provider_ids": list(keys_panel.provider_ids),
        "add_provider_ids": list(add_panel.provider_ids),
        "schema_version": ONLINE_ASR_KEYS_ACCOUNTS_APP_STATE_SCHEMA_VERSION,
        "selected_provider_id": selected.provider_id,
    }
    return OnlineASRKeysAccountsAppState(
        app_state_id="online_asr_keys_accounts_app_" + _sha16(payload),
        selected_provider=selected,
        keys_accounts_panel=keys_panel,
        add_provider_panel=add_panel,
        catalog_state=catalog_state,
        selected_provider_ready_for_gate_review=selected.ready_for_review_gate,
        added_provider_count=catalog_state.added_provider_count,
        configured_provider_count=catalog_state.configured_provider_count,
        missing_key_provider_count=catalog_state.missing_key_provider_count,
    )


def online_asr_keys_accounts_app_state_to_json(state: OnlineASRKeysAccountsAppState) -> str:
    return json.dumps(state.to_dict(), indent=2, sort_keys=True) + "\n"
