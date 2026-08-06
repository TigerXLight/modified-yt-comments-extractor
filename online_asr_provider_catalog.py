from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field, is_dataclass
from enum import Enum
from typing import Any, Iterable, Mapping


ONLINE_ASR_PROVIDER_CATALOG_SCHEMA_VERSION = "online_asr_provider_catalog_v1"
ONLINE_ASR_PROVIDER_CATALOGUE_SCHEMA_VERSION = ONLINE_ASR_PROVIDER_CATALOG_SCHEMA_VERSION
ONLINE_ASR_CREDENTIAL_STATE_CONFIGURED = "CONFIGURED"
ONLINE_ASR_CREDENTIAL_STATE_MISSING = "MISSING"
ONLINE_ASR_CREDENTIAL_STATE_UNAVAILABLE = "UNAVAILABLE"


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


def _safe_tuple(values: Iterable[Any] | None) -> tuple[str, ...]:
    return tuple(_safe_text(value) for value in (values or ()) if _safe_text(value))


def _option_attr(option: Any, name: str, default: str = "") -> str:
    return _safe_text(getattr(option, name, default))


def _option_bool(option: Any, name: str, default: bool = False) -> bool:
    return bool(getattr(option, name, default))


def _safe_credential_state(status: Any) -> str:
    if status is None:
        return ONLINE_ASR_CREDENTIAL_STATE_UNAVAILABLE
    state = getattr(status, "state", status)
    value = getattr(state, "value", state)
    text = _safe_text(value).upper()
    if text == ONLINE_ASR_CREDENTIAL_STATE_CONFIGURED:
        return ONLINE_ASR_CREDENTIAL_STATE_CONFIGURED
    if text == ONLINE_ASR_CREDENTIAL_STATE_MISSING:
        return ONLINE_ASR_CREDENTIAL_STATE_MISSING
    if "UNAVAILABLE" in text:
        return ONLINE_ASR_CREDENTIAL_STATE_UNAVAILABLE
    return text or ONLINE_ASR_CREDENTIAL_STATE_UNAVAILABLE


def _normalise_ids(values: Iterable[str] | None) -> frozenset[str]:
    return frozenset(_safe_text(value) for value in (values or ()) if _safe_text(value))


def _matches_query(entry: "OnlineASRProviderCatalogEntry", query: str) -> bool:
    needle = _safe_text(query).casefold()
    if not needle:
        return True
    haystack = " ".join(
        (
            entry.provider_id,
            entry.display_name,
            entry.provider_family,
            entry.model_id,
            entry.credential_entry_id,
            " ".join(entry.tags),
            " ".join(entry.recommended_for),
        )
    ).casefold()
    return needle in haystack


@dataclass(frozen=True)
class OnlineASRProviderCatalogEntry:
    provider_id: str
    display_name: str
    provider_family: str
    model_id: str
    credential_entry_id: str
    credential_state: str
    added_to_keys_accounts: bool
    configured: bool
    visible_in_keys_accounts: bool
    visible_in_add_provider_catalog: bool
    key_or_account_required: bool = True
    provider_call_allowed_without_user_approval: bool = False
    plaintext_secret_storage_allowed: bool = False
    secret_value_recorded: bool = False
    raw_media_payload_included: bool = False
    full_local_path_included: bool = False
    transcript_payload_included: bool = False
    completed_transcription_claimed: bool = False
    supports_keyterms: bool = False
    tags: tuple[str, ...] = field(default_factory=tuple)
    recommended_for: tuple[str, ...] = field(default_factory=tuple)
    schema_version: str = ONLINE_ASR_PROVIDER_CATALOG_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class OnlineASRProviderCatalogState:
    catalog_state_id: str
    selected_provider_id: str
    selected_provider_configured: bool
    selected_provider_added_to_keys_accounts: bool
    keys_accounts_query: str
    add_provider_query: str
    full_provider_count: int
    added_provider_count: int
    configured_provider_count: int
    missing_key_provider_count: int
    keys_accounts_visible_count: int
    add_provider_match_count: int
    full_catalog_entries: tuple[OnlineASRProviderCatalogEntry, ...]
    keys_accounts_entries: tuple[OnlineASRProviderCatalogEntry, ...]
    add_provider_entries: tuple[OnlineASRProviderCatalogEntry, ...]
    added_provider_ids: tuple[str, ...]
    configured_provider_ids: tuple[str, ...]
    missing_key_provider_ids: tuple[str, ...]
    selected_provider_ready_for_review_gate: bool
    schema_version: str = ONLINE_ASR_PROVIDER_CATALOG_SCHEMA_VERSION
    catalogue_window_label: str = "KEYS/ACCOUNTS"
    keys_accounts_window_shows_added_providers_only: bool = True
    add_provider_window_searches_full_catalog: bool = True
    provider_call_allowed_without_user_approval: bool = False
    plaintext_secret_storage_allowed: bool = False
    secret_value_recorded: bool = False
    raw_media_payload_included: bool = False
    full_local_path_included: bool = False
    completed_transcription_claimed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)

    def to_summary_text(self) -> str:
        selected_state = "configured" if self.selected_provider_configured else "missing/unavailable"
        return "\n".join(
            (
                "Online ASR KEYS/ACCOUNTS provider catalogue",
                f"Catalogue state ID: {self.catalog_state_id}",
                f"Selected provider: {self.selected_provider_id or 'none'} ({selected_state})",
                f"Added providers shown in KEYS/ACCOUNTS: {self.keys_accounts_visible_count}",
                f"Full provider catalogue matches: {self.add_provider_match_count}",
                "Provider call allowed without user approval: false",
                "Plaintext secret storage allowed: false",
                "Completed transcription claimed: false",
            )
        )


def build_online_asr_provider_catalog_state(
    *,
    provider_options: Iterable[Any],
    credential_statuses: Mapping[str, Any] | None = None,
    added_provider_ids: Iterable[str] | None = None,
    selected_provider_id: str = "",
    keys_accounts_query: str = "",
    add_provider_query: str = "",
) -> OnlineASRProviderCatalogState:
    """Build a metadata-only provider catalogue projection for KEYS/ACCOUNTS.

    The KEYS/ACCOUNTS view is intentionally limited to providers the user has
    already added. The Add Provider view searches the full catalogue. Credential
    status is reduced to safe states only; no secret values or payloads are
    accepted or serialized here.
    """
    statuses = credential_statuses or {}
    added_ids = _normalise_ids(added_provider_ids)
    selected_id = _safe_text(selected_provider_id)
    entries: list[OnlineASRProviderCatalogEntry] = []
    for option in provider_options:
        provider_id = _option_attr(option, "provider_id")
        credential_entry_id = _option_attr(option, "credential_entry_id")
        credential_state = _safe_credential_state(statuses.get(credential_entry_id))
        added = provider_id in added_ids
        entries.append(
            OnlineASRProviderCatalogEntry(
                provider_id=provider_id,
                display_name=_option_attr(option, "display_name", provider_id),
                provider_family=_option_attr(option, "provider_family", provider_id),
                model_id=_option_attr(option, "model_id"),
                credential_entry_id=credential_entry_id,
                credential_state=credential_state,
                added_to_keys_accounts=added,
                configured=credential_state == ONLINE_ASR_CREDENTIAL_STATE_CONFIGURED,
                visible_in_keys_accounts=added,
                visible_in_add_provider_catalog=True,
                supports_keyterms=_option_bool(option, "supports_keyterms", False),
                tags=_safe_tuple(getattr(option, "tags", ())),
                recommended_for=_safe_tuple(getattr(option, "recommended_for", ())),
            )
        )
    full_entries = tuple(sorted(entries, key=lambda entry: entry.provider_id))
    keys_query = _safe_text(keys_accounts_query)
    add_query = _safe_text(add_provider_query)
    keys_entries = tuple(
        entry for entry in full_entries
        if entry.visible_in_keys_accounts and _matches_query(entry, keys_query)
    )
    add_entries = tuple(entry for entry in full_entries if _matches_query(entry, add_query))
    configured_ids = tuple(entry.provider_id for entry in full_entries if entry.configured)
    missing_ids = tuple(
        entry.provider_id for entry in full_entries
        if entry.key_or_account_required and not entry.configured
    )
    selected_entry = next((entry for entry in full_entries if entry.provider_id == selected_id), None)
    payload = {
        "added_provider_ids": [entry.provider_id for entry in keys_entries],
        "add_provider_query": add_query,
        "configured_provider_ids": configured_ids,
        "keys_accounts_query": keys_query,
        "provider_ids": [entry.provider_id for entry in full_entries],
        "schema_version": ONLINE_ASR_PROVIDER_CATALOG_SCHEMA_VERSION,
        "selected_provider_id": selected_id,
    }
    return OnlineASRProviderCatalogState(
        catalog_state_id="online_asr_provider_catalog_" + _sha16(payload),
        selected_provider_id=selected_id,
        selected_provider_configured=bool(selected_entry and selected_entry.configured),
        selected_provider_added_to_keys_accounts=bool(
            selected_entry and selected_entry.added_to_keys_accounts
        ),
        keys_accounts_query=keys_query,
        add_provider_query=add_query,
        full_provider_count=len(full_entries),
        added_provider_count=sum(1 for entry in full_entries if entry.added_to_keys_accounts),
        configured_provider_count=len(configured_ids),
        missing_key_provider_count=len(missing_ids),
        keys_accounts_visible_count=len(keys_entries),
        add_provider_match_count=len(add_entries),
        full_catalog_entries=full_entries,
        keys_accounts_entries=keys_entries,
        add_provider_entries=add_entries,
        added_provider_ids=tuple(entry.provider_id for entry in full_entries if entry.added_to_keys_accounts),
        configured_provider_ids=configured_ids,
        missing_key_provider_ids=missing_ids,
        selected_provider_ready_for_review_gate=bool(selected_entry and selected_entry.configured),
    )


def online_asr_provider_catalog_state_to_json(state: OnlineASRProviderCatalogState) -> str:
    return json.dumps(state.to_dict(), indent=2, sort_keys=True) + "\n"
