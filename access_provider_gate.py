from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, is_dataclass
from enum import Enum
from typing import Any, Iterable, Mapping

from access_keys_metadata import (
    AccessEntryKind,
    AccessKeysCatalog,
    AccessMode,
    CredentialStatus,
)


ACCESS_PROVIDER_GATE_SCHEMA_VERSION = "access_provider_gate_v1"


@dataclass(frozen=True)
class AccessProviderGateRecord:
    entry_id: str
    entry_kind: str
    display_name: str
    access_mode: str
    credential_status: str
    credentials_required: bool
    credentials_optional: bool
    supports_connection_test: bool
    approval_required: bool
    operator_review_required: bool = True
    metadata_only: bool = True
    credential_value_included: bool = False
    credential_lookup_performed: bool = False
    provider_call_performed: bool = False
    browser_profile_access_performed: bool = False
    archive_provider_call_performed: bool = False
    download_performed: bool = False
    automatic_classification: bool = False

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class AccessProviderGateSummary:
    gate_summary_id: str
    records: tuple[AccessProviderGateRecord, ...]
    schema_version: str = ACCESS_PROVIDER_GATE_SCHEMA_VERSION
    review_status: str = "USER_REVIEW_REQUIRED"
    approval_required: bool = True
    operator_review_required: bool = True
    metadata_only: bool = True
    local_only: bool = True
    credential_value_included: bool = False
    credential_lookup_performed: bool = False
    provider_call_performed: bool = False
    browser_profile_access_performed: bool = False
    archive_provider_call_performed: bool = False
    download_performed: bool = False
    live_fetch_or_api_call_performed: bool = False
    automatic_classification: bool = False
    sensitive_inference_prohibited: bool = True

    @property
    def record_count(self) -> int:
        return len(self.records)

    @property
    def approval_required_count(self) -> int:
        return sum(1 for record in self.records if record.approval_required)

    @property
    def asr_provider_count(self) -> int:
        return sum(1 for record in self.records if record.entry_kind == AccessEntryKind.ASR_PROVIDER.value)

    @property
    def source_adapter_count(self) -> int:
        return sum(1 for record in self.records if record.entry_kind == AccessEntryKind.SOURCE_ADAPTER.value)

    @property
    def archive_service_count(self) -> int:
        return sum(1 for record in self.records if record.entry_kind == AccessEntryKind.ARCHIVE_SERVICE.value)

    @property
    def browser_assisted_capture_count(self) -> int:
        return sum(1 for record in self.records if record.entry_kind == AccessEntryKind.BROWSER_ASSISTED_CAPTURE.value)

    def to_dict(self) -> dict[str, Any]:
        data = _value_for_dict(self)
        data["archive_service_count"] = self.archive_service_count
        data["approval_required_count"] = self.approval_required_count
        data["asr_provider_count"] = self.asr_provider_count
        data["browser_assisted_capture_count"] = self.browser_assisted_capture_count
        data["record_count"] = self.record_count
        data["source_adapter_count"] = self.source_adapter_count
        return data


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
        return json.dumps(_value_for_dict(data), ensure_ascii=False, indent=2, sort_keys=True)
    return json.dumps(_value_for_dict(data), ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha16(data: Any) -> str:
    return hashlib.sha256(_stable_json(data).encode("utf-8")).hexdigest()[:16]


def _entry_value(value: Any) -> str:
    return str(getattr(value, "value", value) or "")


def _requires_operator_approval(entry: Any) -> bool:
    mode = getattr(entry, "access_mode", AccessMode.BLOCKED_OR_NOT_CONFIGURED)
    status = getattr(entry, "credential_status", CredentialStatus.UNSUPPORTED)
    if mode in {
        AccessMode.API_KEY,
        AccessMode.OAUTH_OR_BROWSER_LOGIN,
        AccessMode.APP_PASSWORD,
        AccessMode.USER_AUTHENTICATED_BROWSER_PROFILE,
        AccessMode.DEDICATED_CAPTURE_BROWSER_PROFILE,
        AccessMode.BLOCKED_OR_NOT_CONFIGURED,
    }:
        return True
    if status in {
        CredentialStatus.REQUIRED_MISSING,
        CredentialStatus.CONFIGURED_UNTESTED,
        CredentialStatus.CONFIGURED_TEST_FAILED,
        CredentialStatus.EXPIRED_OR_REVOKED,
        CredentialStatus.BACKEND_UNAVAILABLE,
        CredentialStatus.STATUS_ERROR,
        CredentialStatus.UNSUPPORTED,
    }:
        return True
    return False


def build_access_provider_gate_records(
    catalog: AccessKeysCatalog,
) -> tuple[AccessProviderGateRecord, ...]:
    records = [
        AccessProviderGateRecord(
            entry_id=str(entry.entry_id),
            entry_kind=_entry_value(entry.entry_kind),
            display_name=str(entry.display_name),
            access_mode=_entry_value(entry.access_mode),
            credential_status=_entry_value(entry.credential_status),
            credentials_required=bool(entry.credentials_required),
            credentials_optional=bool(entry.credentials_optional),
            supports_connection_test=bool(entry.supports_connection_test),
            approval_required=_requires_operator_approval(entry),
        )
        for entry in catalog.entries
    ]
    return tuple(sorted(records, key=lambda record: record.entry_id))


def build_access_provider_gate_summary(
    catalog: AccessKeysCatalog,
) -> AccessProviderGateSummary:
    records = build_access_provider_gate_records(catalog)
    payload = {
        "entry_ids": tuple(record.entry_id for record in records),
        "entry_statuses": tuple(record.credential_status for record in records),
        "schema_version": ACCESS_PROVIDER_GATE_SCHEMA_VERSION,
    }
    return AccessProviderGateSummary(
        gate_summary_id="access_provider_gate_" + _sha16(payload),
        records=records,
    )


def validate_access_provider_gate_summary(data: Mapping[str, Any]) -> None:
    if data.get("schema_version") != ACCESS_PROVIDER_GATE_SCHEMA_VERSION:
        raise ValueError("Unsupported access provider gate schema version")
    for required_true in (
        "metadata_only",
        "local_only",
        "approval_required",
        "operator_review_required",
        "sensitive_inference_prohibited",
    ):
        if data.get(required_true) is not True:
            raise ValueError(f"Unsafe access provider gate flag: {required_true}")
    for required_false in (
        "credential_value_included",
        "credential_lookup_performed",
        "provider_call_performed",
        "browser_profile_access_performed",
        "archive_provider_call_performed",
        "download_performed",
        "live_fetch_or_api_call_performed",
        "automatic_classification",
    ):
        if data.get(required_false) is not False:
            raise ValueError(f"Unsafe access provider gate flag: {required_false}")
    records = data.get("records", [])
    if not isinstance(records, list) or not records:
        raise ValueError("Access provider gate summary requires records")
    for record in records:
        if not isinstance(record, Mapping):
            raise ValueError("Access provider gate record must be an object")
        if record.get("credential_value_included") is not False:
            raise ValueError("Access provider gate record must not include credential values")
        if record.get("provider_call_performed") is not False:
            raise ValueError("Access provider gate record must not perform provider calls")


def access_provider_gate_summary_to_json(summary: AccessProviderGateSummary) -> str:
    return _stable_json(summary.to_dict(), pretty=True)
