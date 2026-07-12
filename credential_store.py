from __future__ import annotations

import importlib
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Mapping


CREDENTIAL_STORE_SCOPE = (
    "row 2C1 backend-only credential-store layer; explicit save/clear "
    "operations only, no GUI/runtime wiring, no plaintext fallback, no "
    "environment writes, no provider calls, and no credential values in results"
)

YOUTUBE_CREDENTIAL_ID = "youtube_data_api_key"
KEYRING_SERVICE_NAME = "modified-yt-comments-extractor.cloud-asr"

SUPPORTED_CLOUD_ASR_CREDENTIAL_IDS = (
    "elevenlabs_scribe_api_key",
    "assemblyai_api_key",
    "deepgram_api_key",
    "speechmatics_api_key",
    "azure_speech_account",
    "google_stt_provider_credentials",
    "cohere_api_key",
    "aws_transcribe_account",
)


class _StringEnum(str, Enum):
    def __str__(self) -> str:
        return self.value


class CredentialStoreBackend(_StringEnum):
    MEMORY = "memory"
    SYSTEM_KEYRING = "system_keyring"


class CredentialStoreOperation(_StringEnum):
    SAVE = "save"
    CLEAR = "clear"
    PRESENCE = "presence"


class CredentialStoreStatus(_StringEnum):
    PRESENT = "present"
    SAVED = "saved"
    UPDATED = "updated"
    CLEARED = "cleared"
    NOT_FOUND = "not_found"
    BACKEND_UNAVAILABLE = "backend_unavailable"
    BACKEND_ERROR = "backend_error"
    UNSUPPORTED_CREDENTIAL = "unsupported_credential"
    YOUTUBE_CREDENTIAL_EXCLUDED = "youtube_credential_excluded"
    EMPTY_CREDENTIAL_REJECTED = "empty_credential_rejected"


@dataclass(frozen=True)
class CredentialLocator:
    credential_id: str
    service_name: str
    account_name: str

    def to_dict(self) -> dict[str, str]:
        return {
            "credential_id": self.credential_id,
            "service_name": self.service_name,
            "account_name": self.account_name,
        }


@dataclass(frozen=True)
class CredentialStoreResult:
    credential_id: str
    operation: CredentialStoreOperation
    backend: CredentialStoreBackend
    status: CredentialStoreStatus
    changed: bool = False
    safe_diagnostic: str = ""
    service_name: str = ""
    account_name: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "credential_id": self.credential_id,
            "operation": self.operation.value,
            "backend": self.backend.value,
            "status": self.status.value,
            "changed": self.changed,
            "safe_diagnostic": self.safe_diagnostic,
            "service_name": self.service_name,
            "account_name": self.account_name,
        }


class CredentialStore:
    def credential_present(self, credential_id: str) -> CredentialStoreResult:
        raise NotImplementedError

    def save_credential(
        self,
        credential_id: str,
        credential: str,
    ) -> CredentialStoreResult:
        raise NotImplementedError

    def clear_credential(self, credential_id: str) -> CredentialStoreResult:
        raise NotImplementedError


def _normalized_credential_id(credential_id: str) -> str:
    return " ".join((credential_id or "").split())


def _account_name_for_credential(credential_id: str) -> str:
    return f"asr.{credential_id}"


def credential_locator_for_id(credential_id: str) -> CredentialLocator | None:
    normalized = _normalized_credential_id(credential_id)
    if normalized not in SUPPORTED_CLOUD_ASR_CREDENTIAL_IDS:
        return None
    return CredentialLocator(
        credential_id=normalized,
        service_name=KEYRING_SERVICE_NAME,
        account_name=_account_name_for_credential(normalized),
    )


def supported_credential_locators() -> tuple[CredentialLocator, ...]:
    return tuple(
        CredentialLocator(
            credential_id=credential_id,
            service_name=KEYRING_SERVICE_NAME,
            account_name=_account_name_for_credential(credential_id),
        )
        for credential_id in SUPPORTED_CLOUD_ASR_CREDENTIAL_IDS
    )


def _unsupported_result(
    credential_id: str,
    *,
    operation: CredentialStoreOperation,
    backend: CredentialStoreBackend,
) -> CredentialStoreResult | None:
    normalized = _normalized_credential_id(credential_id)
    if normalized == YOUTUBE_CREDENTIAL_ID:
        return CredentialStoreResult(
            credential_id=normalized,
            operation=operation,
            backend=backend,
            status=CredentialStoreStatus.YOUTUBE_CREDENTIAL_EXCLUDED,
            safe_diagnostic=(
                "existing_youtube_credential_is_excluded_from_row_2c1_store"
            ),
        )
    if credential_locator_for_id(normalized) is None:
        return CredentialStoreResult(
            credential_id=normalized,
            operation=operation,
            backend=backend,
            status=CredentialStoreStatus.UNSUPPORTED_CREDENTIAL,
            safe_diagnostic="unsupported_credential_id",
        )
    return None


def _result(
    locator: CredentialLocator,
    *,
    operation: CredentialStoreOperation,
    backend: CredentialStoreBackend,
    status: CredentialStoreStatus,
    changed: bool = False,
    safe_diagnostic: str = "",
) -> CredentialStoreResult:
    return CredentialStoreResult(
        credential_id=locator.credential_id,
        operation=operation,
        backend=backend,
        status=status,
        changed=changed,
        safe_diagnostic=safe_diagnostic or status.value,
        service_name=locator.service_name,
        account_name=locator.account_name,
    )


class InMemoryCredentialStore(CredentialStore):
    """Session-only test backend; it never touches files, keyring, or env vars."""

    def __init__(
        self,
        *,
        available: bool = True,
        fail_presence: bool = False,
        fail_save: bool = False,
        fail_clear: bool = False,
    ) -> None:
        self._available = bool(available)
        self._fail_presence = bool(fail_presence)
        self._fail_save = bool(fail_save)
        self._fail_clear = bool(fail_clear)
        self._credentials: dict[str, str] = {}

    def __repr__(self) -> str:
        return (
            "InMemoryCredentialStore("
            f"available={self._available}, "
            f"stored_count={len(self._credentials)})"
        )

    def credential_present(self, credential_id: str) -> CredentialStoreResult:
        unsupported = _unsupported_result(
            credential_id,
            operation=CredentialStoreOperation.PRESENCE,
            backend=CredentialStoreBackend.MEMORY,
        )
        if unsupported is not None:
            return unsupported

        locator = credential_locator_for_id(credential_id)
        assert locator is not None

        if not self._available:
            return _result(
                locator,
                operation=CredentialStoreOperation.PRESENCE,
                backend=CredentialStoreBackend.MEMORY,
                status=CredentialStoreStatus.BACKEND_UNAVAILABLE,
            )
        if self._fail_presence:
            return _result(
                locator,
                operation=CredentialStoreOperation.PRESENCE,
                backend=CredentialStoreBackend.MEMORY,
                status=CredentialStoreStatus.BACKEND_ERROR,
            )
        return _result(
            locator,
            operation=CredentialStoreOperation.PRESENCE,
            backend=CredentialStoreBackend.MEMORY,
            status=(
                CredentialStoreStatus.PRESENT
                if locator.credential_id in self._credentials
                else CredentialStoreStatus.NOT_FOUND
            ),
        )

    def save_credential(
        self,
        credential_id: str,
        credential: str,
    ) -> CredentialStoreResult:
        unsupported = _unsupported_result(
            credential_id,
            operation=CredentialStoreOperation.SAVE,
            backend=CredentialStoreBackend.MEMORY,
        )
        if unsupported is not None:
            return unsupported

        locator = credential_locator_for_id(credential_id)
        assert locator is not None

        if not self._available:
            return _result(
                locator,
                operation=CredentialStoreOperation.SAVE,
                backend=CredentialStoreBackend.MEMORY,
                status=CredentialStoreStatus.BACKEND_UNAVAILABLE,
            )
        if self._fail_save:
            return _result(
                locator,
                operation=CredentialStoreOperation.SAVE,
                backend=CredentialStoreBackend.MEMORY,
                status=CredentialStoreStatus.BACKEND_ERROR,
            )
        if not str(credential):
            return _result(
                locator,
                operation=CredentialStoreOperation.SAVE,
                backend=CredentialStoreBackend.MEMORY,
                status=CredentialStoreStatus.EMPTY_CREDENTIAL_REJECTED,
            )

        existed = locator.credential_id in self._credentials
        self._credentials[locator.credential_id] = str(credential)
        return _result(
            locator,
            operation=CredentialStoreOperation.SAVE,
            backend=CredentialStoreBackend.MEMORY,
            status=(
                CredentialStoreStatus.UPDATED
                if existed
                else CredentialStoreStatus.SAVED
            ),
            changed=True,
        )

    def clear_credential(self, credential_id: str) -> CredentialStoreResult:
        unsupported = _unsupported_result(
            credential_id,
            operation=CredentialStoreOperation.CLEAR,
            backend=CredentialStoreBackend.MEMORY,
        )
        if unsupported is not None:
            return unsupported

        locator = credential_locator_for_id(credential_id)
        assert locator is not None

        if not self._available:
            return _result(
                locator,
                operation=CredentialStoreOperation.CLEAR,
                backend=CredentialStoreBackend.MEMORY,
                status=CredentialStoreStatus.BACKEND_UNAVAILABLE,
            )
        if self._fail_clear:
            return _result(
                locator,
                operation=CredentialStoreOperation.CLEAR,
                backend=CredentialStoreBackend.MEMORY,
                status=CredentialStoreStatus.BACKEND_ERROR,
            )
        if locator.credential_id not in self._credentials:
            return _result(
                locator,
                operation=CredentialStoreOperation.CLEAR,
                backend=CredentialStoreBackend.MEMORY,
                status=CredentialStoreStatus.NOT_FOUND,
            )

        del self._credentials[locator.credential_id]
        return _result(
            locator,
            operation=CredentialStoreOperation.CLEAR,
            backend=CredentialStoreBackend.MEMORY,
            status=CredentialStoreStatus.CLEARED,
            changed=True,
        )

    def _test_only_stored_credential(self, credential_id: str) -> str | None:
        """Test-only inspection hook; callers must not expose the returned value."""
        locator = credential_locator_for_id(credential_id)
        if locator is None:
            return None
        return self._credentials.get(locator.credential_id)


class SystemKeyringCredentialStore(CredentialStore):
    """Fail-closed OS-keyring store for future explicit callers."""

    def __init__(
        self,
        *,
        keyring_module: Any = None,
        keyring_module_factory: Callable[[], Any] | None = None,
    ) -> None:
        self._keyring_module = keyring_module
        self._keyring_module_factory = keyring_module_factory

    def __repr__(self) -> str:
        return "SystemKeyringCredentialStore()"

    def _load_keyring(self) -> Any:
        if self._keyring_module is not None:
            return self._keyring_module
        if self._keyring_module_factory is not None:
            return self._keyring_module_factory()
        return importlib.import_module("keyring")

    def _safe_keyring_module(self) -> tuple[Any | None, bool]:
        try:
            module = self._load_keyring()
        except Exception:
            return None, False
        required = ("get_password", "set_password", "delete_password")
        if any(not callable(getattr(module, name, None)) for name in required):
            return None, False
        return module, True

    def credential_present(self, credential_id: str) -> CredentialStoreResult:
        unsupported = _unsupported_result(
            credential_id,
            operation=CredentialStoreOperation.PRESENCE,
            backend=CredentialStoreBackend.SYSTEM_KEYRING,
        )
        if unsupported is not None:
            return unsupported

        locator = credential_locator_for_id(credential_id)
        assert locator is not None

        keyring_module, available = self._safe_keyring_module()
        if not available:
            return _result(
                locator,
                operation=CredentialStoreOperation.PRESENCE,
                backend=CredentialStoreBackend.SYSTEM_KEYRING,
                status=CredentialStoreStatus.BACKEND_UNAVAILABLE,
            )

        try:
            configured = keyring_module.get_password(
                locator.service_name,
                locator.account_name,
            ) is not None
        except Exception:
            return _result(
                locator,
                operation=CredentialStoreOperation.PRESENCE,
                backend=CredentialStoreBackend.SYSTEM_KEYRING,
                status=CredentialStoreStatus.BACKEND_ERROR,
            )

        return _result(
            locator,
            operation=CredentialStoreOperation.PRESENCE,
            backend=CredentialStoreBackend.SYSTEM_KEYRING,
            status=(
                CredentialStoreStatus.PRESENT
                if configured
                else CredentialStoreStatus.NOT_FOUND
            ),
        )

    def save_credential(
        self,
        credential_id: str,
        credential: str,
    ) -> CredentialStoreResult:
        unsupported = _unsupported_result(
            credential_id,
            operation=CredentialStoreOperation.SAVE,
            backend=CredentialStoreBackend.SYSTEM_KEYRING,
        )
        if unsupported is not None:
            return unsupported

        locator = credential_locator_for_id(credential_id)
        assert locator is not None

        if not str(credential):
            return _result(
                locator,
                operation=CredentialStoreOperation.SAVE,
                backend=CredentialStoreBackend.SYSTEM_KEYRING,
                status=CredentialStoreStatus.EMPTY_CREDENTIAL_REJECTED,
            )

        keyring_module, available = self._safe_keyring_module()
        if not available:
            return _result(
                locator,
                operation=CredentialStoreOperation.SAVE,
                backend=CredentialStoreBackend.SYSTEM_KEYRING,
                status=CredentialStoreStatus.BACKEND_UNAVAILABLE,
            )

        try:
            existing = keyring_module.get_password(
                locator.service_name,
                locator.account_name,
            )
            keyring_module.set_password(
                locator.service_name,
                locator.account_name,
                str(credential),
            )
        except Exception:
            return _result(
                locator,
                operation=CredentialStoreOperation.SAVE,
                backend=CredentialStoreBackend.SYSTEM_KEYRING,
                status=CredentialStoreStatus.BACKEND_ERROR,
            )

        return _result(
            locator,
            operation=CredentialStoreOperation.SAVE,
            backend=CredentialStoreBackend.SYSTEM_KEYRING,
            status=(
                CredentialStoreStatus.UPDATED
                if existing is not None
                else CredentialStoreStatus.SAVED
            ),
            changed=True,
        )

    def clear_credential(self, credential_id: str) -> CredentialStoreResult:
        unsupported = _unsupported_result(
            credential_id,
            operation=CredentialStoreOperation.CLEAR,
            backend=CredentialStoreBackend.SYSTEM_KEYRING,
        )
        if unsupported is not None:
            return unsupported

        locator = credential_locator_for_id(credential_id)
        assert locator is not None

        keyring_module, available = self._safe_keyring_module()
        if not available:
            return _result(
                locator,
                operation=CredentialStoreOperation.CLEAR,
                backend=CredentialStoreBackend.SYSTEM_KEYRING,
                status=CredentialStoreStatus.BACKEND_UNAVAILABLE,
            )

        password_delete_error = getattr(
            getattr(keyring_module, "errors", object()),
            "PasswordDeleteError",
            None,
        )
        if not isinstance(password_delete_error, type):
            password_delete_error = None

        try:
            keyring_module.delete_password(
                locator.service_name,
                locator.account_name,
            )
        except Exception as error:
            if password_delete_error is not None and isinstance(
                error,
                password_delete_error,
            ):
                return _result(
                    locator,
                    operation=CredentialStoreOperation.CLEAR,
                    backend=CredentialStoreBackend.SYSTEM_KEYRING,
                    status=CredentialStoreStatus.NOT_FOUND,
                )
            return _result(
                locator,
                operation=CredentialStoreOperation.CLEAR,
                backend=CredentialStoreBackend.SYSTEM_KEYRING,
                status=CredentialStoreStatus.BACKEND_ERROR,
            )

        return _result(
            locator,
            operation=CredentialStoreOperation.CLEAR,
            backend=CredentialStoreBackend.SYSTEM_KEYRING,
            status=CredentialStoreStatus.CLEARED,
            changed=True,
        )


def credential_store_result_contains_forbidden_fields(
    data: Mapping[str, object],
) -> tuple[str, ...]:
    forbidden_names = {
        "credential",
        "credential_value",
        "secret",
        "secret_value",
        "api_key",
        "password",
        "token",
        "access_token",
        "refresh_token",
        "exception",
        "traceback",
        "stack_trace",
    }
    return tuple(
        key
        for key in data
        if str(key).casefold() in forbidden_names
    )
