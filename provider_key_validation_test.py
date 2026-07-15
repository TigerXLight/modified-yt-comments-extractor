from __future__ import annotations

import json

from access_keys_metadata import (
    AccessEntryKind,
    AccessEntryMetadata,
    AccessKeysCatalog,
    AccessMode,
    CredentialStatus,
)
from provider_key_validation import (
    KEY_VALIDATION_COULD_NOT_COMPLETE,
    KEY_VALIDATION_FAILED,
    KEY_VALIDATION_NOT_CONFIGURED,
    KEY_VALIDATION_NOT_YET_VALIDATED,
    KEY_VALIDATION_VALIDATED,
    KEY_STATUS_NO_KEY_CONFIGURED,
    KEY_STATUS_SAVED_NOT_VALIDATED,
    KEY_STATUS_VALIDATED,
    KEY_STATUS_VALIDATION_COULD_NOT_COMPLETE,
    KEY_STATUS_VALIDATION_FAILED,
    ProviderKeyValidationRecord,
    apply_provider_key_validation_records,
    normalize_validation_records,
    validation_icon_key_for_state,
    validation_records_to_settings_dict,
    validation_status_text_for_state,
)


def test_public_validation_status_text_and_icons_are_stable() -> None:
    assert validation_status_text_for_state(KEY_VALIDATION_NOT_CONFIGURED) == KEY_STATUS_NO_KEY_CONFIGURED
    assert validation_status_text_for_state(KEY_VALIDATION_NOT_YET_VALIDATED) == KEY_STATUS_SAVED_NOT_VALIDATED
    assert validation_status_text_for_state(KEY_VALIDATION_VALIDATED) == KEY_STATUS_VALIDATED
    assert validation_status_text_for_state(KEY_VALIDATION_FAILED) == KEY_STATUS_VALIDATION_FAILED
    assert validation_status_text_for_state(KEY_VALIDATION_COULD_NOT_COMPLETE) == KEY_STATUS_VALIDATION_COULD_NOT_COMPLETE

    assert validation_icon_key_for_state(KEY_VALIDATION_NOT_CONFIGURED) == "missing"
    assert validation_icon_key_for_state(KEY_VALIDATION_NOT_YET_VALIDATED) == "saved"
    assert validation_icon_key_for_state(KEY_VALIDATION_VALIDATED) == "verified"
    assert validation_icon_key_for_state(KEY_VALIDATION_FAILED) == "warning"
    assert validation_icon_key_for_state(KEY_VALIDATION_COULD_NOT_COMPLETE) == "warning"


def test_validation_records_settings_shape_is_non_secret_and_deterministic() -> None:
    records = {
        "elevenlabs_scribe": ProviderKeyValidationRecord(
            provider_id="elevenlabs_scribe",
            state=KEY_VALIDATION_VALIDATED,
            checked_at_utc="2026-07-15T12:00:00+00:00",
            safe_diagnostic="key_validation_succeeded",
        )
    }

    data = validation_records_to_settings_dict(records)
    blob = json.dumps(data, sort_keys=True)

    assert list(data) == ["elevenlabs_scribe"]
    assert "credential" not in blob.casefold()
    assert "secret" not in blob.casefold()
    assert "api_key" not in blob.casefold()
    assert normalize_validation_records(data)["elevenlabs_scribe"] == records["elevenlabs_scribe"]


def test_validation_records_update_catalog_status_without_raw_values() -> None:
    catalog = AccessKeysCatalog(
        entries=(
            AccessEntryMetadata(
                entry_id="asr:elevenlabs_scribe",
                entry_kind=AccessEntryKind.ASR_PROVIDER,
                display_name="ElevenLabs Scribe v2",
                platform_family="asr",
                access_mode=AccessMode.API_KEY,
                credential_status=CredentialStatus.CONFIGURED_UNTESTED,
            ),
        )
    )

    validated = apply_provider_key_validation_records(
        catalog,
        {
            "elevenlabs_scribe": ProviderKeyValidationRecord(
                provider_id="elevenlabs_scribe",
                state=KEY_VALIDATION_VALIDATED,
                safe_diagnostic="key_validation_succeeded",
            )
        },
    )
    assert validated.entries[0].credential_status is CredentialStatus.CONFIGURED_TEST_PASSED

    failed = apply_provider_key_validation_records(
        catalog,
        {
            "elevenlabs_scribe": ProviderKeyValidationRecord(
                provider_id="elevenlabs_scribe",
                state=KEY_VALIDATION_FAILED,
                safe_diagnostic="authentication_rejected",
            )
        },
    )
    assert failed.entries[0].credential_status is CredentialStatus.CONFIGURED_TEST_FAILED


if __name__ == "__main__":
    test_public_validation_status_text_and_icons_are_stable()
    test_validation_records_settings_shape_is_non_secret_and_deterministic()
    test_validation_records_update_catalog_status_without_raw_values()
    print("Provider key validation self-test passed.")
