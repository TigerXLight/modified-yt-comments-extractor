from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from enum import Enum
from typing import Any, Mapping, Protocol

from access_keys_metadata import AccessKeysCatalog, CredentialStatus
from credential_architecture import (
    CredentialDescriptor,
    build_row2a_credential_architecture,
    serialized_secret_field_paths,
)
from credential_store import (
    CredentialStore,
    CredentialStoreStatus,
    credential_locator_for_id,
)


CREDENTIAL_RUNTIME_STATUS_SCOPE = (
    "row 2B read-only local credential presence/provenance status only; no "
    "credential values are returned, stored, migrated, cleared, revealed, copied, "
    "tested against providers, or sent over a network"
)
CREDENTIAL_RUNTIME_STATUS_SCHEMA_VERSION = "1.0"


class _StringEnum(str, Enum):
    def __str__(self) -> str:
        return self.value


class CredentialPresenceState(_StringEnum):
    CONFIGURED = "CONFIGURED"
    MISSING = "MISSING"
    BACKEND_UNAVAILABLE = "BACKEND_UNAVAILABLE"
    ERROR = "ERROR"


class CredentialProvenance(_StringEnum):
    EXISTING_YOUTUBE_KEYRING = "EXISTING_YOUTUBE_KEYRING"
    EXISTING_YOUTUBE_LEGACY_SETTINGS = "EXISTING_YOUTUBE_LEGACY_SETTINGS"
    EXISTING_YOUTUBE_KEYRING_AND_LEGACY_SETTINGS = (
        "EXISTING_YOUTUBE_KEYRING_AND_LEGACY_SETTINGS"
    )
    SECURE_KEYRING = "SECURE_KEYRING"
    SECURE_KEYRING_AND_ENVIRONMENT = "SECURE_KEYRING_AND_ENVIRONMENT"
    ENVIRONMENT_VARIABLE = "ENVIRONMENT_VARIABLE"
    NOT_FOUND = "NOT_FOUND"
    UNKNOWN = "UNKNOWN"


class SafeCredentialDiagnostic(_StringEnum):
    CONFIGURED_PRESENCE_ONLY = "configured_presence_only"
    REQUIRED_CREDENTIAL_MISSING = "required_credential_missing"
    KEYRING_BACKEND_UNAVAILABLE = "keyring_backend_unavailable"
    KEYRING_ACCESS_ERROR = "keyring_access_error"
    STORAGE_STATUS_ERROR = "storage_status_error"
    STATUS_PROVIDER_UNAVAILABLE = "status_provider_unavailable"
    COMPOUND_CREDENTIAL_INCOMPLETE = "compound_credential_incomplete"


@dataclass(frozen=True)
class CredentialRuntimeStatus:
    credential_id: str
    entry_id: str
    state: CredentialPresenceState
    provenance: CredentialProvenance
    safe_diagnostic: SafeCredentialDiagnostic
    backend_label: str = ""
    presence_checked: bool = True
    value_exposed: bool = False
    provider_tested: bool = False
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["state"] = self.state.value
        data["provenance"] = self.provenance.value
        data["safe_diagnostic"] = self.safe_diagnostic.value
        return data


class CredentialStatusProvider(Protocol):
    def read_statuses(self) -> Mapping[str, CredentialRuntimeStatus]:
        """Return statuses keyed by Access & Keys entry ID without secret values."""


class StaticCredentialStatusProvider:
    """Deterministic provider for tests and dependency injection."""

    def __init__(self, statuses: Mapping[str, CredentialRuntimeStatus]) -> None:
        self._statuses = dict(statuses)

    def read_statuses(self) -> Mapping[str, CredentialRuntimeStatus]:
        return dict(self._statuses)


def _environment_value_present(environ: Mapping[str, str], name: str) -> bool:
    try:
        return bool(str(environ.get(name, "")).strip())
    except Exception:
        return False


def _environment_requirement(
    descriptor: CredentialDescriptor,
    environ: Mapping[str, str],
) -> tuple[bool, bool]:
    """Return (configured, compound_incomplete) without returning any value."""
    names = tuple(descriptor.environment_variable_names)
    if not names:
        return False, False

    present = {name: _environment_value_present(environ, name) for name in names}

    if descriptor.credential_id == "azure_speech_account":
        configured = all(present.get(name, False) for name in ("AZURE_SPEECH_KEY", "AZURE_SPEECH_REGION"))
        return configured, any(present.values()) and not configured

    if descriptor.credential_id == "aws_transcribe_account":
        profile = present.get("AWS_PROFILE", False)
        key_pair = present.get("AWS_ACCESS_KEY_ID", False) and present.get("AWS_SECRET_ACCESS_KEY", False)
        configured = profile or key_pair
        relevant_present = profile or present.get("AWS_ACCESS_KEY_ID", False) or present.get("AWS_SECRET_ACCESS_KEY", False)
        return configured, relevant_present and not configured

    configured = any(present.values())
    return configured, False


def _status(
    descriptor: CredentialDescriptor,
    *,
    state: CredentialPresenceState,
    provenance: CredentialProvenance,
    diagnostic: SafeCredentialDiagnostic,
    backend_label: str = "",
    notes: str = "",
) -> CredentialRuntimeStatus:
    return CredentialRuntimeStatus(
        credential_id=descriptor.credential_id,
        entry_id=descriptor.entry_id,
        state=state,
        provenance=provenance,
        safe_diagnostic=diagnostic,
        backend_label=backend_label,
        notes=notes,
    )


def _youtube_status(
    descriptor: CredentialDescriptor,
    *,
    settings_manager: Any,
    configured: bool,
) -> CredentialRuntimeStatus:
    if settings_manager is None:
        return _status(
            descriptor,
            state=CredentialPresenceState.BACKEND_UNAVAILABLE,
            provenance=CredentialProvenance.UNKNOWN,
            diagnostic=SafeCredentialDiagnostic.STATUS_PROVIDER_UNAVAILABLE,
            notes="The existing settings manager was not supplied.",
        )

    if getattr(settings_manager, "_last_keyring_error", None):
        return _status(
            descriptor,
            state=CredentialPresenceState.ERROR,
            provenance=CredentialProvenance.UNKNOWN,
            diagnostic=SafeCredentialDiagnostic.KEYRING_ACCESS_ERROR,
            backend_label="Existing YouTube credential storage",
            notes="Fail-closed status: a keyring error was recorded; no fallback is reported as healthy.",
        )

    try:
        storage_info = str(settings_manager.get_storage_info())
    except Exception:
        return _status(
            descriptor,
            state=CredentialPresenceState.ERROR,
            provenance=CredentialProvenance.UNKNOWN,
            diagnostic=SafeCredentialDiagnostic.STORAGE_STATUS_ERROR,
            backend_label="Existing YouTube credential storage",
        )

    storage_lower = storage_info.casefold()
    # Check the explicit legacy-storage wording before "keyring": the
    # existing SettingsManager message can say
    # "settings.json (install keyring for secure storage)".
    if "keyring and legacy" in storage_lower or (
        "keyring" in storage_lower and "legacy" in storage_lower
    ):
        provenance = CredentialProvenance.EXISTING_YOUTUBE_KEYRING_AND_LEGACY_SETTINGS
        backend_label = "System keyring and legacy settings.json"
    elif (
        "legacy settings.json" in storage_lower
        or "settings.json" in storage_lower
        or "stored in file" in storage_lower
    ):
        provenance = CredentialProvenance.EXISTING_YOUTUBE_LEGACY_SETTINGS
        backend_label = "Legacy settings.json"
    elif "keyring" in storage_lower:
        provenance = CredentialProvenance.EXISTING_YOUTUBE_KEYRING
        backend_label = "System keyring"
    elif "unavailable" in storage_lower:
        provenance = CredentialProvenance.UNKNOWN
        backend_label = "Secure storage unavailable"
    elif "error" in storage_lower:
        provenance = CredentialProvenance.UNKNOWN
        backend_label = "Existing YouTube credential storage"
    else:
        provenance = CredentialProvenance.UNKNOWN
        backend_label = "Existing YouTube credential storage"

    storage_configured = provenance in {
        CredentialProvenance.EXISTING_YOUTUBE_KEYRING,
        CredentialProvenance.EXISTING_YOUTUBE_LEGACY_SETTINGS,
        CredentialProvenance.EXISTING_YOUTUBE_KEYRING_AND_LEGACY_SETTINGS,
    }

    if configured or storage_configured:
        return _status(
            descriptor,
            state=CredentialPresenceState.CONFIGURED,
            provenance=provenance,
            diagnostic=SafeCredentialDiagnostic.CONFIGURED_PRESENCE_ONLY,
            backend_label=backend_label,
            notes=(
                "Presence was derived from the already-loaded YouTube field "
                "or safe storage status; the value is not returned."
            ),
        )

    if provenance is CredentialProvenance.EXISTING_YOUTUBE_KEYRING and not bool(
        getattr(settings_manager, "keyring_available", True)
    ):
        return _status(
            descriptor,
            state=CredentialPresenceState.BACKEND_UNAVAILABLE,
            provenance=provenance,
            diagnostic=SafeCredentialDiagnostic.KEYRING_BACKEND_UNAVAILABLE,
            backend_label=backend_label,
        )

    return _status(
        descriptor,
        state=CredentialPresenceState.MISSING,
        provenance=CredentialProvenance.NOT_FOUND,
        diagnostic=SafeCredentialDiagnostic.REQUIRED_CREDENTIAL_MISSING,
        backend_label=backend_label,
    )


class LocalCredentialStatusProvider:
    """Read local presence/provenance only; never return or persist credential values."""

    def __init__(
        self,
        *,
        settings_manager: Any = None,
        youtube_configured: bool = False,
        environ: Mapping[str, str] | None = None,
        credential_store: CredentialStore | None = None,
    ) -> None:
        self._settings_manager = settings_manager
        self._youtube_configured = bool(youtube_configured)
        self._environ = environ if environ is not None else __import__("os").environ
        self._credential_store = credential_store

    def _cloud_asr_status(
        self,
        descriptor: CredentialDescriptor,
    ) -> CredentialRuntimeStatus:
        configured, incomplete = _environment_requirement(descriptor, self._environ)
        if self._credential_store is None:
            if configured:
                return _status(
                    descriptor,
                    state=CredentialPresenceState.CONFIGURED,
                    provenance=CredentialProvenance.ENVIRONMENT_VARIABLE,
                    diagnostic=SafeCredentialDiagnostic.CONFIGURED_PRESENCE_ONLY,
                    backend_label="Environment variable (read-only presence check)",
                )
            if incomplete:
                return _status(
                    descriptor,
                    state=CredentialPresenceState.MISSING,
                    provenance=CredentialProvenance.ENVIRONMENT_VARIABLE,
                    diagnostic=SafeCredentialDiagnostic.COMPOUND_CREDENTIAL_INCOMPLETE,
                    backend_label="Environment variable (read-only presence check)",
                )
            return _status(
                descriptor,
                state=CredentialPresenceState.MISSING,
                provenance=CredentialProvenance.NOT_FOUND,
                diagnostic=SafeCredentialDiagnostic.REQUIRED_CREDENTIAL_MISSING,
                backend_label="Environment variable (read-only presence check)",
            )

        result = self._credential_store.credential_present(
            descriptor.credential_id
        )
        if result.status is CredentialStoreStatus.PRESENT:
            if configured:
                return _status(
                    descriptor,
                    state=CredentialPresenceState.CONFIGURED,
                    provenance=CredentialProvenance.SECURE_KEYRING_AND_ENVIRONMENT,
                    diagnostic=SafeCredentialDiagnostic.CONFIGURED_PRESENCE_ONLY,
                    backend_label="Secure store and environment variable presence",
                )
            return _status(
                descriptor,
                state=CredentialPresenceState.CONFIGURED,
                provenance=CredentialProvenance.SECURE_KEYRING,
                diagnostic=SafeCredentialDiagnostic.CONFIGURED_PRESENCE_ONLY,
                backend_label="Secure credential store",
            )

        if result.status is CredentialStoreStatus.NOT_FOUND:
            if configured:
                return _status(
                    descriptor,
                    state=CredentialPresenceState.CONFIGURED,
                    provenance=CredentialProvenance.ENVIRONMENT_VARIABLE,
                    diagnostic=SafeCredentialDiagnostic.CONFIGURED_PRESENCE_ONLY,
                    backend_label="Environment variable (read-only presence check)",
                )
            if incomplete:
                return _status(
                    descriptor,
                    state=CredentialPresenceState.MISSING,
                    provenance=CredentialProvenance.ENVIRONMENT_VARIABLE,
                    diagnostic=SafeCredentialDiagnostic.COMPOUND_CREDENTIAL_INCOMPLETE,
                    backend_label="Environment variable (read-only presence check)",
                )
            return _status(
                descriptor,
                state=CredentialPresenceState.MISSING,
                provenance=CredentialProvenance.NOT_FOUND,
                diagnostic=SafeCredentialDiagnostic.REQUIRED_CREDENTIAL_MISSING,
                backend_label="Secure credential store",
            )

        if result.status is CredentialStoreStatus.BACKEND_UNAVAILABLE:
            if configured:
                return _status(
                    descriptor,
                    state=CredentialPresenceState.CONFIGURED,
                    provenance=CredentialProvenance.ENVIRONMENT_VARIABLE,
                    diagnostic=SafeCredentialDiagnostic.CONFIGURED_PRESENCE_ONLY,
                    backend_label="Environment variable; secure store unavailable",
                )
            return _status(
                descriptor,
                state=CredentialPresenceState.BACKEND_UNAVAILABLE,
                provenance=CredentialProvenance.UNKNOWN,
                diagnostic=SafeCredentialDiagnostic.KEYRING_BACKEND_UNAVAILABLE,
                backend_label="Secure credential store",
            )

        if result.status is CredentialStoreStatus.BACKEND_ERROR:
            if configured:
                return _status(
                    descriptor,
                    state=CredentialPresenceState.CONFIGURED,
                    provenance=CredentialProvenance.ENVIRONMENT_VARIABLE,
                    diagnostic=SafeCredentialDiagnostic.CONFIGURED_PRESENCE_ONLY,
                    backend_label="Environment variable; secure store status error",
                )
            return _status(
                descriptor,
                state=CredentialPresenceState.ERROR,
                provenance=CredentialProvenance.UNKNOWN,
                diagnostic=SafeCredentialDiagnostic.KEYRING_ACCESS_ERROR,
                backend_label="Secure credential store",
            )

        return _status(
            descriptor,
            state=CredentialPresenceState.ERROR,
            provenance=CredentialProvenance.UNKNOWN,
            diagnostic=SafeCredentialDiagnostic.STORAGE_STATUS_ERROR,
            backend_label="Secure credential store",
        )

    def read_statuses(self) -> Mapping[str, CredentialRuntimeStatus]:
        plan = build_row2a_credential_architecture()
        statuses: dict[str, CredentialRuntimeStatus] = {}

        for descriptor in plan.descriptors:
            if descriptor.credential_id == "youtube_data_api_key":
                status = _youtube_status(
                    descriptor,
                    settings_manager=self._settings_manager,
                    configured=self._youtube_configured,
                )
            else:
                status = self._cloud_asr_status(descriptor)
            statuses[descriptor.entry_id] = status

        return statuses


def build_runtime_credential_statuses(
    *,
    settings_manager: Any = None,
    youtube_configured: bool = False,
    environ: Mapping[str, str] | None = None,
    credential_store: CredentialStore | None = None,
) -> Mapping[str, CredentialRuntimeStatus]:
    return LocalCredentialStatusProvider(
        settings_manager=settings_manager,
        youtube_configured=youtube_configured,
        environ=environ,
        credential_store=credential_store,
    ).read_statuses()


def cloud_asr_credential_id_for_entry_id(entry_id: str) -> str:
    normalized = " ".join((entry_id or "").split())
    for descriptor in build_row2a_credential_architecture().descriptors:
        if descriptor.entry_id != normalized:
            continue
        if credential_locator_for_id(descriptor.credential_id) is not None:
            return descriptor.credential_id
    return ""


def _metadata_status(state: CredentialPresenceState) -> CredentialStatus:
    if state is CredentialPresenceState.CONFIGURED:
        return CredentialStatus.CONFIGURED_UNTESTED
    if state is CredentialPresenceState.MISSING:
        return CredentialStatus.REQUIRED_MISSING
    if state is CredentialPresenceState.BACKEND_UNAVAILABLE:
        return CredentialStatus.BACKEND_UNAVAILABLE
    return CredentialStatus.STATUS_ERROR


def runtime_status_note(status: CredentialRuntimeStatus) -> str:
    backend = status.backend_label or status.provenance.value
    return (
        f"Credential presence: {status.state.value}; provenance: {backend}; "
        f"safe diagnostic: {status.safe_diagnostic.value}."
    )


def _merge_note(existing: str, note: str) -> str:
    existing = existing.strip()
    if not existing:
        return note
    if note in existing:
        return existing
    return f"{existing} {note}"


def apply_runtime_credential_statuses(
    catalog: AccessKeysCatalog,
    statuses: Mapping[str, CredentialRuntimeStatus],
) -> AccessKeysCatalog:
    updated_entries = []
    for entry in catalog.entries:
        status = statuses.get(entry.entry_id)
        if status is None:
            updated_entries.append(entry)
            continue
        updated_entries.append(
            replace(
                entry,
                credential_status=_metadata_status(status.state),
                access_limitations=_merge_note(
                    entry.access_limitations,
                    runtime_status_note(status),
                ),
            )
        )
    return replace(catalog, entries=tuple(updated_entries))


def runtime_statuses_to_dict(
    statuses: Mapping[str, CredentialRuntimeStatus],
) -> dict[str, Any]:
    return {
        "schema_version": CREDENTIAL_RUNTIME_STATUS_SCHEMA_VERSION,
        "scope": CREDENTIAL_RUNTIME_STATUS_SCOPE,
        "status_count": len(statuses),
        "statuses": [statuses[key].to_dict() for key in sorted(statuses)],
    }


def validate_runtime_credential_statuses(
    statuses: Mapping[str, CredentialRuntimeStatus],
) -> tuple[str, ...]:
    errors: list[str] = []
    entry_ids = [status.entry_id for status in statuses.values()]
    if len(entry_ids) != len(set(entry_ids)):
        errors.append("duplicate entry_id")
    for key, status in statuses.items():
        if key != status.entry_id:
            errors.append(f"mapping key mismatch: {key}")
        if status.value_exposed:
            errors.append(f"value exposure enabled: {key}")
        if status.provider_tested:
            errors.append(f"provider testing enabled: {key}")
    secret_paths = serialized_secret_field_paths(runtime_statuses_to_dict(statuses))
    if secret_paths:
        errors.append("secret-bearing serialized fields: " + ", ".join(secret_paths))
    return tuple(errors)
