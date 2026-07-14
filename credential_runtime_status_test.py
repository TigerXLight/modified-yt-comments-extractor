from __future__ import annotations

import json
from pathlib import Path

from access_keys_metadata import (
    AccessEntryKind,
    AccessEntryMetadata,
    AccessKeysCatalog,
    AccessMode,
    CredentialStatus,
)
from credential_architecture import build_row2a_credential_architecture
from credential_runtime_status import (
    CredentialPresenceState,
    CredentialProvenance,
    LocalCredentialStatusProvider,
    SafeCredentialDiagnostic,
    apply_runtime_credential_statuses,
    cloud_asr_credential_id_for_entry_id,
    runtime_statuses_to_dict,
    validate_runtime_credential_statuses,
)
from credential_store import (
    SUPPORTED_CLOUD_ASR_CREDENTIAL_IDS,
    InMemoryCredentialStore,
)


SECRET_SENTINEL = "ROW2B-SECRET-MUST-NOT-APPEAR"


def _store_raw_test_credential(
    store: InMemoryCredentialStore,
    credential_id: str,
    value: str,
) -> None:
    store._credentials[credential_id] = value


class FakeSettingsManager:
    def __init__(
        self,
        storage_info: str,
        *,
        keyring_available: bool = True,
        last_error: str | None = None,
        raise_storage: bool = False,
    ) -> None:
        self._storage_info = storage_info
        self.keyring_available = keyring_available
        self._last_keyring_error = last_error
        self._raise_storage = raise_storage

    def get_storage_info(self) -> str:
        if self._raise_storage:
            raise RuntimeError(SECRET_SENTINEL)
        return self._storage_info


def _read(
    *,
    youtube_configured: bool = False,
    storage_info: str = "API key stored securely in system keyring",
    last_error: str | None = None,
    raise_storage: bool = False,
    environ: dict[str, str] | None = None,
    credential_store: object | None = None,
):
    provider = LocalCredentialStatusProvider(
        settings_manager=FakeSettingsManager(
            storage_info,
            last_error=last_error,
            raise_storage=raise_storage,
        ),
        youtube_configured=youtube_configured,
        environ=environ or {},
        credential_store=credential_store,
    )
    return provider.read_statuses()


def test_youtube_statuses() -> None:
    configured = _read(youtube_configured=True)
    youtube = configured["source:youtube"]
    assert youtube.state is CredentialPresenceState.CONFIGURED
    assert youtube.provenance is CredentialProvenance.EXISTING_YOUTUBE_KEYRING
    assert youtube.safe_diagnostic is SafeCredentialDiagnostic.CONFIGURED_PRESENCE_ONLY

    legacy = _read(
        youtube_configured=True,
        storage_info="API key stored in settings.json (install keyring)",
    )["source:youtube"]
    assert legacy.provenance is CredentialProvenance.EXISTING_YOUTUBE_LEGACY_SETTINGS

    both = _read(
        youtube_configured=True,
        storage_info="API key present in system keyring and legacy settings.json",
    )["source:youtube"]
    assert (
        both.provenance
        is CredentialProvenance.EXISTING_YOUTUBE_KEYRING_AND_LEGACY_SETTINGS
    )

    missing = _read(
        youtube_configured=False,
        storage_info="API key not configured",
    )["source:youtube"]
    assert missing.state is CredentialPresenceState.MISSING

    stored_without_entry_text = _read(youtube_configured=False)["source:youtube"]
    assert stored_without_entry_text.state is CredentialPresenceState.CONFIGURED
    assert (
        stored_without_entry_text.provenance
        is CredentialProvenance.EXISTING_YOUTUBE_KEYRING
    )

    failed = _read(
        youtube_configured=True,
        last_error=SECRET_SENTINEL,
    )["source:youtube"]
    assert failed.state is CredentialPresenceState.ERROR
    assert failed.safe_diagnostic is SafeCredentialDiagnostic.KEYRING_ACCESS_ERROR
    assert SECRET_SENTINEL not in json.dumps(failed.to_dict(), sort_keys=True)

    storage_error = _read(
        youtube_configured=True,
        raise_storage=True,
    )["source:youtube"]
    assert storage_error.state is CredentialPresenceState.ERROR
    assert SECRET_SENTINEL not in json.dumps(storage_error.to_dict(), sort_keys=True)


def test_environment_statuses() -> None:
    statuses = _read(
        environ={
            "ELEVENLABS_API_KEY": SECRET_SENTINEL,
            "AZURE_SPEECH_KEY": SECRET_SENTINEL,
            "AWS_PROFILE": "evidence-profile",
        }
    )
    assert statuses["asr:elevenlabs_scribe"].state is CredentialPresenceState.CONFIGURED
    assert statuses["asr:elevenlabs_scribe"].provenance is CredentialProvenance.ENVIRONMENT_VARIABLE
    assert statuses["asr:azure_speech"].state is CredentialPresenceState.MISSING
    assert (
        statuses["asr:azure_speech"].safe_diagnostic
        is SafeCredentialDiagnostic.COMPOUND_CREDENTIAL_INCOMPLETE
    )
    assert statuses["asr:aws_transcribe_custom_vocabulary"].state is CredentialPresenceState.CONFIGURED

    serialized = json.dumps(runtime_statuses_to_dict(statuses), sort_keys=True)
    assert SECRET_SENTINEL not in serialized
    assert validate_runtime_credential_statuses(statuses) == ()


def test_secure_store_presence_and_precedence() -> None:
    store = InMemoryCredentialStore()
    store.save_credential("elevenlabs_scribe_api_key", SECRET_SENTINEL)

    keyring_only = _read(credential_store=store)
    eleven = keyring_only["asr:elevenlabs_scribe"]
    assert eleven.state is CredentialPresenceState.CONFIGURED
    assert eleven.provenance is CredentialProvenance.SECURE_KEYRING
    assert eleven.backend_label == "Secure credential store"

    both = _read(
        credential_store=store,
        environ={"ELEVENLABS_API_KEY": SECRET_SENTINEL},
    )["asr:elevenlabs_scribe"]
    assert both.state is CredentialPresenceState.CONFIGURED
    assert both.provenance is CredentialProvenance.SECURE_KEYRING_AND_ENVIRONMENT

    store.clear_credential("elevenlabs_scribe_api_key")
    env_after_clear = _read(
        credential_store=store,
        environ={"ELEVENLABS_API_KEY": SECRET_SENTINEL},
    )["asr:elevenlabs_scribe"]
    assert env_after_clear.state is CredentialPresenceState.CONFIGURED
    assert env_after_clear.provenance is CredentialProvenance.ENVIRONMENT_VARIABLE

    serialized = json.dumps(
        runtime_statuses_to_dict(keyring_only),
        sort_keys=True,
    )
    assert SECRET_SENTINEL not in serialized
    assert validate_runtime_credential_statuses(keyring_only) == ()


def test_secure_store_presence_failures_are_safe() -> None:
    unavailable = _read(
        credential_store=InMemoryCredentialStore(available=False)
    )["asr:elevenlabs_scribe"]
    assert unavailable.state is CredentialPresenceState.BACKEND_UNAVAILABLE
    assert (
        unavailable.safe_diagnostic
        is SafeCredentialDiagnostic.KEYRING_BACKEND_UNAVAILABLE
    )

    error = _read(
        credential_store=InMemoryCredentialStore(fail_presence=True)
    )["asr:elevenlabs_scribe"]
    assert error.state is CredentialPresenceState.ERROR
    assert error.safe_diagnostic is SafeCredentialDiagnostic.KEYRING_ACCESS_ERROR

    env_with_error = _read(
        credential_store=InMemoryCredentialStore(fail_presence=True),
        environ={"ELEVENLABS_API_KEY": SECRET_SENTINEL},
    )["asr:elevenlabs_scribe"]
    assert env_with_error.state is CredentialPresenceState.CONFIGURED
    assert env_with_error.provenance is CredentialProvenance.ENVIRONMENT_VARIABLE

    serialized = json.dumps(error.to_dict(), sort_keys=True)
    assert SECRET_SENTINEL not in serialized


def test_invalid_secure_store_values_are_not_configured() -> None:
    for value in ("", "   "):
        store = InMemoryCredentialStore()
        _store_raw_test_credential(
            store,
            "elevenlabs_scribe_api_key",
            value,
        )
        invalid = _read(credential_store=store)["asr:elevenlabs_scribe"]
        assert invalid.state is CredentialPresenceState.ERROR
        assert invalid.provenance is CredentialProvenance.SECURE_KEYRING
        assert (
            invalid.safe_diagnostic
            is SafeCredentialDiagnostic.INVALID_SECURE_CREDENTIAL_VALUE
        )
        assert SECRET_SENTINEL not in json.dumps(invalid.to_dict(), sort_keys=True)

        invalid_with_env = _read(
            credential_store=store,
            environ={"ELEVENLABS_API_KEY": SECRET_SENTINEL},
        )["asr:elevenlabs_scribe"]
        assert invalid_with_env.state is CredentialPresenceState.ERROR
        assert (
            invalid_with_env.safe_diagnostic
            is SafeCredentialDiagnostic.INVALID_SECURE_CREDENTIAL_VALUE
        )

    entry = AccessEntryMetadata(
        entry_id="asr:elevenlabs_scribe",
        entry_kind=AccessEntryKind.ASR_PROVIDER,
        display_name="ElevenLabs Scribe",
        platform_family="asr_providers",
        access_mode=AccessMode.API_KEY,
        credential_status=CredentialStatus.REQUIRED_MISSING,
        credentials_required=True,
    )
    store = InMemoryCredentialStore()
    _store_raw_test_credential(store, "elevenlabs_scribe_api_key", "")
    updated = apply_runtime_credential_statuses(
        AccessKeysCatalog(entries=(entry,)),
        _read(credential_store=store),
    )
    assert updated.entries[0].credential_status is CredentialStatus.STATUS_ERROR
    assert "invalid_secure_credential_value" in updated.entries[0].access_limitations


def test_cloud_asr_entry_id_mapping_excludes_youtube_and_unknowns() -> None:
    plan = build_row2a_credential_architecture()
    mapped = {
        descriptor.credential_id: cloud_asr_credential_id_for_entry_id(
            descriptor.entry_id
        )
        for descriptor in plan.descriptors
    }
    assert tuple(
        credential_id
        for credential_id, mapped_id in mapped.items()
        if mapped_id
    ) == SUPPORTED_CLOUD_ASR_CREDENTIAL_IDS
    assert cloud_asr_credential_id_for_entry_id("source:youtube") == ""
    assert cloud_asr_credential_id_for_entry_id("asr:unknown") == ""


def test_catalog_overlay() -> None:
    entry = AccessEntryMetadata(
        entry_id="source:youtube",
        entry_kind=AccessEntryKind.SOURCE_ADAPTER,
        display_name="YouTube",
        platform_family="video_social",
        access_mode=AccessMode.API_KEY,
        credential_status=CredentialStatus.REQUIRED_MISSING,
        credentials_required=True,
        access_limitations="Existing limitation.",
    )
    catalog = AccessKeysCatalog(entries=(entry,))
    statuses = _read(youtube_configured=True)
    updated = apply_runtime_credential_statuses(catalog, statuses)
    updated_entry = updated.entries[0]
    assert updated_entry.credential_status is CredentialStatus.CONFIGURED_UNTESTED
    assert "Credential presence: CONFIGURED" in updated_entry.access_limitations
    assert SECRET_SENTINEL not in json.dumps(updated.to_dict(), sort_keys=True)


def test_runtime_integration_is_bounded() -> None:
    runtime_source = Path("credential_runtime_status.py").read_text(encoding="utf-8")
    dialog_source = Path("access_keys_dialog.py").read_text(encoding="utf-8")
    main_source = Path("main.py").read_text(encoding="utf-8")

    for forbidden in (
        "set_password(",
        "delete_password(",
        "get_password(",
        "requests.",
        "urllib.request",
        "httpx",
        "aiohttp",
        "socket.",
        "subprocess",
        "oauth",
        "connection test",
    ):
        assert forbidden not in runtime_source.casefold()

    compact_dialog_source = "".join(dialog_source.split())
    compact_main_source = "".join(main_source.split())

    assert (
        "credential_statuses:Optional[Mapping[str,CredentialRuntimeStatus]]"
        in compact_dialog_source
    )
    assert "credential_store:Optional[CredentialStore]" in compact_dialog_source
    assert "apply_runtime_credential_statuses(" in dialog_source
    assert "build_runtime_credential_statuses(" in main_source
    assert "credential_store=credential_store" in main_source
    assert (
        "youtube_configured=bool(self.api_key_entry.get().strip())"
        in compact_main_source
    )
    assert (
        "Existing keys are never displayed, and this window does not "
        in dialog_source
    )
    assert "test credentials or call providers." in dialog_source


def main() -> None:
    test_youtube_statuses()
    test_environment_statuses()
    test_secure_store_presence_and_precedence()
    test_secure_store_presence_failures_are_safe()
    test_invalid_secure_store_values_are_not_configured()
    test_cloud_asr_entry_id_mapping_excludes_youtube_and_unknowns()
    test_catalog_overlay()
    test_runtime_integration_is_bounded()
    print("Credential runtime status self-test passed.")


if __name__ == "__main__":
    main()
