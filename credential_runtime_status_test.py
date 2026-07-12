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
from credential_runtime_status import (
    CredentialPresenceState,
    CredentialProvenance,
    LocalCredentialStatusProvider,
    SafeCredentialDiagnostic,
    apply_runtime_credential_statuses,
    runtime_statuses_to_dict,
    validate_runtime_credential_statuses,
)


SECRET_SENTINEL = "ROW2B-SECRET-MUST-NOT-APPEAR"


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
):
    provider = LocalCredentialStatusProvider(
        settings_manager=FakeSettingsManager(
            storage_info,
            last_error=last_error,
            raise_storage=raise_storage,
        ),
        youtube_configured=youtube_configured,
        environ=environ or {},
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

    missing = _read(youtube_configured=False)["source:youtube"]
    assert missing.state is CredentialPresenceState.MISSING

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
    assert "apply_runtime_credential_statuses(" in dialog_source
    assert "build_runtime_credential_statuses(" in main_source
    assert (
        "youtube_configured=bool(self.api_key_entry.get().strip())"
        in compact_main_source
    )
    assert (
        "does not display values, store, migrate, clear, test, "
        in dialog_source
    )
    assert "or call providers." in dialog_source


def main() -> None:
    test_youtube_statuses()
    test_environment_statuses()
    test_catalog_overlay()
    test_runtime_integration_is_bounded()
    print("Credential runtime status self-test passed.")


if __name__ == "__main__":
    main()
