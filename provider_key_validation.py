from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone
from enum import Enum
from typing import Mapping

from access_keys_metadata import (
    AccessKeysCatalog,
    ConnectionTestStatus,
    CredentialStatus,
)


KEY_VALIDATION_NOT_CONFIGURED = "not_configured"
KEY_VALIDATION_NOT_YET_VALIDATED = "not_yet_validated"
KEY_VALIDATION_VALIDATED = "validated"
KEY_VALIDATION_FAILED = "validation_failed"
KEY_VALIDATION_COULD_NOT_COMPLETE = "validation_could_not_complete"

KEY_STATUS_NO_KEY_CONFIGURED = "No key configured"
KEY_STATUS_SAVED_NOT_VALIDATED = "Key saved — not yet validated"
KEY_STATUS_VALIDATED = "Key validated successfully"
KEY_STATUS_VALIDATION_FAILED = "Key validation failed"
KEY_STATUS_VALIDATION_COULD_NOT_COMPLETE = "Key could not be validated"
KEY_STATUS_NO_KEY_NEEDED = "No key needed"


class _StringEnum(str, Enum):
    def __str__(self) -> str:
        return self.value


class ProviderKeyValidationState(_StringEnum):
    NOT_CONFIGURED = KEY_VALIDATION_NOT_CONFIGURED
    NOT_YET_VALIDATED = KEY_VALIDATION_NOT_YET_VALIDATED
    VALIDATED = KEY_VALIDATION_VALIDATED
    VALIDATION_FAILED = KEY_VALIDATION_FAILED
    VALIDATION_COULD_NOT_COMPLETE = KEY_VALIDATION_COULD_NOT_COMPLETE


@dataclass(frozen=True)
class ProviderKeyValidationRecord:
    provider_id: str
    state: str = KEY_VALIDATION_NOT_CONFIGURED
    checked_at_utc: str = ""
    safe_diagnostic: str = ""

    def to_dict(self) -> dict[str, str]:
        return {
            "provider_id": self.provider_id,
            "state": normalize_validation_state(self.state),
            "checked_at_utc": self.checked_at_utc,
            "safe_diagnostic": self.safe_diagnostic,
        }


def current_utc_timestamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def normalize_provider_id(provider_id: str) -> str:
    return " ".join(str(provider_id or "").split())


def provider_id_for_access_entry_id(entry_id: str) -> str:
    normalized = normalize_provider_id(entry_id)
    return normalized[4:] if normalized.startswith("asr:") else ""


def access_entry_id_for_provider_id(provider_id: str) -> str:
    normalized = normalize_provider_id(provider_id)
    return f"asr:{normalized}" if normalized else ""


def normalize_validation_state(state: str) -> str:
    normalized = " ".join(str(state or "").split()).casefold()
    valid = {
        KEY_VALIDATION_NOT_CONFIGURED,
        KEY_VALIDATION_NOT_YET_VALIDATED,
        KEY_VALIDATION_VALIDATED,
        KEY_VALIDATION_FAILED,
        KEY_VALIDATION_COULD_NOT_COMPLETE,
    }
    return normalized if normalized in valid else KEY_VALIDATION_NOT_CONFIGURED


def validation_record_from_mapping(
    provider_id: str,
    data: Mapping[str, object],
) -> ProviderKeyValidationRecord:
    normalized_provider = normalize_provider_id(
        str(data.get("provider_id") or provider_id)
    )
    return ProviderKeyValidationRecord(
        provider_id=normalized_provider,
        state=normalize_validation_state(str(data.get("state") or "")),
        checked_at_utc=" ".join(str(data.get("checked_at_utc") or "").split()),
        safe_diagnostic=" ".join(str(data.get("safe_diagnostic") or "").split()),
    )


def normalize_validation_records(
    records: Mapping[str, object] | None,
) -> dict[str, ProviderKeyValidationRecord]:
    result: dict[str, ProviderKeyValidationRecord] = {}
    if not isinstance(records, Mapping):
        return result
    for key, value in records.items():
        provider_id = normalize_provider_id(str(key or ""))
        if not provider_id or not isinstance(value, Mapping):
            continue
        record = validation_record_from_mapping(provider_id, value)
        if record.provider_id:
            result[record.provider_id] = record
    return result


def validation_records_to_settings_dict(
    records: Mapping[str, ProviderKeyValidationRecord],
) -> dict[str, dict[str, str]]:
    return {
        provider_id: records[provider_id].to_dict()
        for provider_id in sorted(records)
    }


def validation_status_text_for_state(state: str) -> str:
    normalized = normalize_validation_state(state)
    if normalized == KEY_VALIDATION_VALIDATED:
        return KEY_STATUS_VALIDATED
    if normalized == KEY_VALIDATION_FAILED:
        return KEY_STATUS_VALIDATION_FAILED
    if normalized == KEY_VALIDATION_COULD_NOT_COMPLETE:
        return KEY_STATUS_VALIDATION_COULD_NOT_COMPLETE
    if normalized == KEY_VALIDATION_NOT_YET_VALIDATED:
        return KEY_STATUS_SAVED_NOT_VALIDATED
    return KEY_STATUS_NO_KEY_CONFIGURED


def validation_icon_key_for_state(state: str) -> str:
    normalized = normalize_validation_state(state)
    if normalized == KEY_VALIDATION_VALIDATED:
        return "verified"
    if normalized in {
        KEY_VALIDATION_FAILED,
        KEY_VALIDATION_COULD_NOT_COMPLETE,
    }:
        return "warning"
    if normalized == KEY_VALIDATION_NOT_YET_VALIDATED:
        return "saved"
    return "missing"


def validation_record_for_saved_key(
    provider_id: str,
) -> ProviderKeyValidationRecord:
    return ProviderKeyValidationRecord(
        provider_id=normalize_provider_id(provider_id),
        state=KEY_VALIDATION_NOT_YET_VALIDATED,
        safe_diagnostic="key_saved_not_validated",
    )


def validation_record_for_cleared_key(
    provider_id: str,
) -> ProviderKeyValidationRecord:
    return ProviderKeyValidationRecord(
        provider_id=normalize_provider_id(provider_id),
        state=KEY_VALIDATION_NOT_CONFIGURED,
        safe_diagnostic="key_not_configured",
    )


def apply_provider_key_validation_records(
    catalog: AccessKeysCatalog,
    records: Mapping[str, ProviderKeyValidationRecord],
) -> AccessKeysCatalog:
    updated_entries = []
    for entry in catalog.entries:
        provider_id = provider_id_for_access_entry_id(entry.entry_id)
        record = records.get(provider_id) if provider_id else None
        if record is None:
            updated_entries.append(entry)
            continue

        state = normalize_validation_state(record.state)
        if state == KEY_VALIDATION_NOT_CONFIGURED:
            updated_entries.append(
                replace(
                    entry,
                    credential_status=CredentialStatus.REQUIRED_MISSING,
                    last_test_status=ConnectionTestStatus.TEST_NOT_RUN,
                    access_limitations=record.safe_diagnostic,
                )
            )
            continue

        if entry.credential_status in {
            CredentialStatus.REQUIRED_MISSING,
            CredentialStatus.BACKEND_UNAVAILABLE,
            CredentialStatus.STATUS_ERROR,
            CredentialStatus.UNSUPPORTED,
        }:
            updated_entries.append(entry)
            continue

        if state == KEY_VALIDATION_VALIDATED:
            updated_entries.append(
                replace(
                    entry,
                    credential_status=CredentialStatus.CONFIGURED_TEST_PASSED,
                    last_test_status=ConnectionTestStatus.TEST_PASSED,
                    access_limitations=record.safe_diagnostic or "key_validation_succeeded",
                )
            )
        elif state == KEY_VALIDATION_FAILED:
            updated_entries.append(
                replace(
                    entry,
                    credential_status=CredentialStatus.CONFIGURED_TEST_FAILED,
                    last_test_status=ConnectionTestStatus.TEST_FAILED,
                    access_limitations=record.safe_diagnostic or "authentication_rejected",
                )
            )
        elif state == KEY_VALIDATION_COULD_NOT_COMPLETE:
            updated_entries.append(
                replace(
                    entry,
                    credential_status=CredentialStatus.CONFIGURED_TEST_FAILED,
                    last_test_status=ConnectionTestStatus.TEST_FAILED,
                    access_limitations=record.safe_diagnostic or "validation_could_not_complete",
                )
            )
        else:
            updated_entries.append(
                replace(
                    entry,
                    credential_status=CredentialStatus.CONFIGURED_UNTESTED,
                    last_test_status=ConnectionTestStatus.TEST_NOT_RUN,
                    access_limitations=record.safe_diagnostic or "key_saved_not_validated",
                )
            )
    return replace(catalog, entries=tuple(updated_entries))
