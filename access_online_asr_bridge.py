from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, is_dataclass
from enum import Enum
from typing import Any, Iterable, Mapping

from access_keys_catalog import AccessKeysCatalogBundle, build_default_access_keys_catalog_bundle
from access_keys_metadata import AccessEntryKind
from access_keys_view_model import build_access_keys_manager_view
from online_asr_execution_gate import (
    OnlineASRExecutionGateSummary,
    build_online_asr_provider_gate_records,
)


ACCESS_ONLINE_ASR_BRIDGE_SCHEMA_VERSION = "access_online_asr_bridge_v1"
PREFERRED_LOCAL_ASR_ENGINE = "whisper.cpp"
PREFERRED_LOCAL_ASR_DEVICE = "Vulkan"
PREFERRED_LOCAL_ASR_MODEL = "large-v3"


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


def _stable_json(data: Any, *, pretty: bool = False) -> str:
    if pretty:
        return json.dumps(_value_for_dict(data), indent=2, sort_keys=True)
    return json.dumps(_value_for_dict(data), sort_keys=True, separators=(",", ":"))


def _sha16(data: Any) -> str:
    return hashlib.sha256(_stable_json(data).encode("utf-8")).hexdigest()[:16]


def _stable_tuple(values: Iterable[str]) -> tuple[str, ...]:
    return tuple(sorted(str(value or "").strip() for value in values if str(value or "").strip()))


@dataclass(frozen=True)
class AccessOnlineASRBridgeSummary:
    summary_id: str
    added_provider_ids: tuple[str, ...]
    added_provider_count: int
    catalogue_provider_count: int
    access_catalogue_entry_count: int
    add_provider_catalogue_visible: bool = True
    search_added_supported: bool = True
    search_catalogue_supported: bool = True
    online_asr_command_state: str = "approval_required_before_provider_call"
    online_asr_provider_readiness_count: int = 0
    online_asr_configured_provider_count: int = 0
    online_asr_provider_records: tuple[Mapping[str, Any], ...] = ()
    local_asr_preferred_engine: str = PREFERRED_LOCAL_ASR_ENGINE
    local_asr_preferred_device: str = PREFERRED_LOCAL_ASR_DEVICE
    local_asr_preferred_model: str = PREFERRED_LOCAL_ASR_MODEL
    local_asr_benchmark_profile_guard: str = "preserve_whispercpp_vulkan_large_v3"
    credential_values_read: bool = False
    provider_call_performed: bool = False
    asr_run_performed: bool = False
    plaintext_secret_included: bool = False
    metadata_only: bool = True
    user_review_required: bool = True
    schema_version: str = ACCESS_ONLINE_ASR_BRIDGE_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


def build_access_online_asr_bridge_summary(
    *,
    settings: Any | None = None,
    catalog_bundle: AccessKeysCatalogBundle | None = None,
    online_asr_provider_options: Iterable[Any] = (),
    credential_statuses: Mapping[str, Any] | None = None,
) -> AccessOnlineASRBridgeSummary:
    bundle = catalog_bundle or build_default_access_keys_catalog_bundle()
    added_provider_ids = _stable_tuple(getattr(settings, "access_keys_added_provider_ids", ()) or ())
    added_view = build_access_keys_manager_view(
        bundle.catalog,
        entry_kind=AccessEntryKind.ASR_PROVIDER,
        selected_entry_id=added_provider_ids[0] if added_provider_ids else "",
        layouts=bundle.layouts,
    )
    catalogue_view = build_access_keys_manager_view(
        bundle.catalog,
        search_query="",
        layouts=bundle.layouts,
    )
    provider_records = build_online_asr_provider_gate_records(
        online_asr_provider_options,
        credential_statuses or {},
    )
    provider_record_dicts = tuple(record.to_dict() for record in provider_records)
    payload = {
        "added_provider_ids": added_provider_ids,
        "catalogue_provider_count": added_view.visible_entry_count,
        "online_asr_provider_ids": [record.provider_id for record in provider_records],
        "schema_version": ACCESS_ONLINE_ASR_BRIDGE_SCHEMA_VERSION,
    }
    return AccessOnlineASRBridgeSummary(
        summary_id="access_online_asr_bridge_" + _sha16(payload),
        added_provider_ids=added_provider_ids,
        added_provider_count=len(added_provider_ids),
        catalogue_provider_count=added_view.visible_entry_count,
        access_catalogue_entry_count=catalogue_view.visible_entry_count,
        online_asr_provider_readiness_count=len(provider_records),
        online_asr_configured_provider_count=sum(
            1 for record in provider_records if record.credential_configured
        ),
        online_asr_provider_records=provider_record_dicts,
    )


def validate_access_online_asr_bridge_summary(data: Mapping[str, Any]) -> None:
    if data.get("schema_version") != ACCESS_ONLINE_ASR_BRIDGE_SCHEMA_VERSION:
        raise ValueError("Unsupported Access/Online ASR bridge schema version")
    for required_false in (
        "credential_values_read",
        "provider_call_performed",
        "asr_run_performed",
        "plaintext_secret_included",
    ):
        if data.get(required_false) is not False:
            raise ValueError(f"Unsafe Access/Online ASR bridge flag: {required_false}")
    if data.get("local_asr_preferred_model") != PREFERRED_LOCAL_ASR_MODEL:
        raise ValueError("Local ASR preferred benchmark model changed")
    if data.get("local_asr_preferred_device") != PREFERRED_LOCAL_ASR_DEVICE:
        raise ValueError("Local ASR preferred benchmark device changed")


def access_online_asr_bridge_summary_to_json(summary: AccessOnlineASRBridgeSummary) -> str:
    return _stable_json(summary.to_dict(), pretty=True)
