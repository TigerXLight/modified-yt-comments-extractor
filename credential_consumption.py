from __future__ import annotations

import importlib
import os
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Callable, Mapping

from asr_provider_metadata import (
    CREDENTIAL_LOCAL_BINARY,
    CREDENTIAL_NONE,
    get_asr_provider_metadata,
)
from credential_architecture import (
    CredentialDescriptor,
    build_row2a_credential_architecture,
    serialized_secret_field_paths,
)
from credential_store import (
    YOUTUBE_CREDENTIAL_ID,
    CredentialLocator,
    credential_locator_for_id,
)


CREDENTIAL_CONSUMPTION_SCOPE = (
    "explicit action-time cloud-ASR credential consumption only; no startup "
    "retrieval, no connection tests, no provider clients, no network calls, "
    "no persistent secret cache, and no credential values in public results"
)

_DEFAULT_KEYRING_MODULE = object()

_ENVIRONMENT_NOT_CONSUMABLE = {
    "azure_speech_account",
    "aws_transcribe_account",
    "google_stt_provider_credentials",
}


class _StringEnum(str, Enum):
    def __str__(self) -> str:
        return self.value


class CredentialConsumptionStatus(_StringEnum):
    CONSUMED = "consumed"
    MISSING = "missing"
    BACKEND_UNAVAILABLE = "backend_unavailable"
    STORAGE_ERROR = "storage_error"
    ACTION_ERROR = "action_error"
    UNKNOWN_CREDENTIAL = "unknown_credential"
    YOUTUBE_CREDENTIAL_REJECTED = "youtube_credential_rejected"
    CREDENTIAL_NOT_REQUIRED = "credential_not_required"
    NOT_CONSUMABLE = "not_consumable"


class CredentialConsumptionProvenance(_StringEnum):
    SECURE_KEYRING = "secure_keyring"
    ENVIRONMENT_VARIABLE = "environment_variable"
    NOT_FOUND = "not_found"
    NOT_REQUIRED = "not_required"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class CredentialConsumptionResult:
    credential_id: str
    status: CredentialConsumptionStatus
    provenance: CredentialConsumptionProvenance
    safe_diagnostic: str
    provider_id: str = ""
    callback_invoked: bool = False
    action_succeeded: bool = False
    scope: str = CREDENTIAL_CONSUMPTION_SCOPE

    def to_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["status"] = self.status.value
        data["provenance"] = self.provenance.value
        return data


def _descriptor_by_credential_id() -> dict[str, CredentialDescriptor]:
    return {
        descriptor.credential_id: descriptor
        for descriptor in build_row2a_credential_architecture().descriptors
    }


def _descriptor_for_credential_id(
    credential_id: str,
) -> CredentialDescriptor | None:
    return _descriptor_by_credential_id().get(" ".join((credential_id or "").split()))


def _descriptor_for_provider_id(
    provider_id: str,
) -> CredentialDescriptor | None:
    entry_id = "asr:" + " ".join((provider_id or "").split())
    for descriptor in build_row2a_credential_architecture().descriptors:
        if descriptor.entry_id == entry_id:
            return descriptor
    return None


def _result(
    credential_id: str,
    *,
    status: CredentialConsumptionStatus,
    provenance: CredentialConsumptionProvenance,
    safe_diagnostic: str,
    provider_id: str = "",
    callback_invoked: bool = False,
    action_succeeded: bool = False,
) -> CredentialConsumptionResult:
    return CredentialConsumptionResult(
        credential_id=" ".join((credential_id or "").split()),
        provider_id=" ".join((provider_id or "").split()),
        status=status,
        provenance=provenance,
        safe_diagnostic=safe_diagnostic,
        callback_invoked=callback_invoked,
        action_succeeded=action_succeeded,
    )


class CloudASRCredentialConsumer:
    """Resolve a cloud-ASR credential only for trusted explicit action code.

    The callback receives the raw credential and must be treated as trusted
    internal provider/action code. This helper keeps the credential out of
    public results and ignores callback return values, but a malicious callback
    can still retain or exfiltrate the string through its own side effects.
    """

    def __init__(
        self,
        *,
        environ: Mapping[str, str] | None = None,
        keyring_module: Any = _DEFAULT_KEYRING_MODULE,
        keyring_module_factory: Callable[[], Any] | None = None,
    ) -> None:
        self._environ = environ if environ is not None else os.environ
        self._keyring_module = keyring_module
        self._keyring_module_factory = keyring_module_factory

    def __repr__(self) -> str:
        return "CloudASRCredentialConsumer()"

    def _load_keyring(self) -> Any:
        if self._keyring_module is not _DEFAULT_KEYRING_MODULE:
            return self._keyring_module
        if self._keyring_module_factory is not None:
            return self._keyring_module_factory()
        return importlib.import_module("keyring")

    def _safe_keyring_module(self) -> tuple[Any | None, bool]:
        try:
            module = self._load_keyring()
        except Exception:
            return None, False
        if not callable(getattr(module, "get_password", None)):
            return None, False
        return module, True

    def _read_keyring_secret(
        self,
        locator: CredentialLocator,
    ) -> tuple[CredentialConsumptionStatus, str, str]:
        keyring_module, available = self._safe_keyring_module()
        if not available:
            return (
                CredentialConsumptionStatus.BACKEND_UNAVAILABLE,
                "",
                "secure_credential_backend_unavailable",
            )
        try:
            value = keyring_module.get_password(
                locator.service_name,
                locator.account_name,
            )
        except Exception:
            return (
                CredentialConsumptionStatus.STORAGE_ERROR,
                "",
                "secure_credential_read_error",
            )
        if value is None:
            return CredentialConsumptionStatus.MISSING, "", "secure_credential_missing"
        secret = str(value)
        if not secret.strip():
            return (
                CredentialConsumptionStatus.STORAGE_ERROR,
                "",
                "invalid_secure_credential_value",
            )
        return (
            CredentialConsumptionStatus.CONSUMED,
            secret,
            "credential_supplied_to_callback",
        )

    def _read_environment_secret(
        self,
        descriptor: CredentialDescriptor,
    ) -> tuple[CredentialConsumptionStatus, str]:
        names = tuple(descriptor.environment_variable_names)
        if not names:
            return CredentialConsumptionStatus.MISSING, ""
        if descriptor.credential_id in _ENVIRONMENT_NOT_CONSUMABLE:
            if any(str(self._environ.get(name, "")).strip() for name in names):
                return CredentialConsumptionStatus.NOT_CONSUMABLE, ""
            return CredentialConsumptionStatus.MISSING, ""
        for name in names:
            value = str(self._environ.get(name, "")).strip()
            if value:
                return CredentialConsumptionStatus.CONSUMED, value
        return CredentialConsumptionStatus.MISSING, ""

    def consume_credential(
        self,
        credential_id: str,
        *,
        action: Callable[[str], object],
    ) -> CredentialConsumptionResult:
        normalized = " ".join((credential_id or "").split())
        if normalized == YOUTUBE_CREDENTIAL_ID:
            return _result(
                normalized,
                status=CredentialConsumptionStatus.YOUTUBE_CREDENTIAL_REJECTED,
                provenance=CredentialConsumptionProvenance.UNKNOWN,
                safe_diagnostic="youtube_credential_not_allowed_for_cloud_asr",
            )

        descriptor = _descriptor_for_credential_id(normalized)
        locator = credential_locator_for_id(normalized)
        if descriptor is None or locator is None:
            return _result(
                normalized,
                status=CredentialConsumptionStatus.UNKNOWN_CREDENTIAL,
                provenance=CredentialConsumptionProvenance.UNKNOWN,
                safe_diagnostic="unknown_cloud_asr_credential_id",
            )

        keyring_status, secret, keyring_diagnostic = self._read_keyring_secret(locator)
        if keyring_status is CredentialConsumptionStatus.CONSUMED:
            return self._consume_secret(
                normalized,
                secret,
                action=action,
                provenance=CredentialConsumptionProvenance.SECURE_KEYRING,
                diagnostic=keyring_diagnostic,
            )

        if (
            keyring_status is CredentialConsumptionStatus.STORAGE_ERROR
            and keyring_diagnostic == "invalid_secure_credential_value"
        ):
            return _result(
                normalized,
                status=CredentialConsumptionStatus.STORAGE_ERROR,
                provenance=CredentialConsumptionProvenance.SECURE_KEYRING,
                safe_diagnostic=keyring_diagnostic,
            )

        env_status, env_secret = self._read_environment_secret(descriptor)
        if env_status is CredentialConsumptionStatus.CONSUMED:
            return self._consume_secret(
                normalized,
                env_secret,
                action=action,
                provenance=CredentialConsumptionProvenance.ENVIRONMENT_VARIABLE,
                diagnostic="environment_credential_supplied_to_callback",
            )
        if env_status is CredentialConsumptionStatus.NOT_CONSUMABLE:
            return _result(
                normalized,
                status=CredentialConsumptionStatus.NOT_CONSUMABLE,
                provenance=CredentialConsumptionProvenance.ENVIRONMENT_VARIABLE,
                safe_diagnostic="provider_specific_environment_shape_not_consumable",
            )

        if keyring_status is CredentialConsumptionStatus.STORAGE_ERROR:
            return _result(
                normalized,
                status=CredentialConsumptionStatus.STORAGE_ERROR,
                provenance=CredentialConsumptionProvenance.UNKNOWN,
                safe_diagnostic=keyring_diagnostic,
            )

        if keyring_status is CredentialConsumptionStatus.BACKEND_UNAVAILABLE:
            return _result(
                normalized,
                status=CredentialConsumptionStatus.BACKEND_UNAVAILABLE,
                provenance=CredentialConsumptionProvenance.UNKNOWN,
                safe_diagnostic="secure_credential_backend_unavailable",
            )
        return _result(
            normalized,
            status=CredentialConsumptionStatus.MISSING,
            provenance=CredentialConsumptionProvenance.NOT_FOUND,
            safe_diagnostic="cloud_asr_credential_missing",
        )

    def consume_provider_credential(
        self,
        provider_id: str,
        *,
        action: Callable[[str], object],
    ) -> CredentialConsumptionResult:
        normalized_provider = " ".join((provider_id or "").split())
        provider = get_asr_provider_metadata(normalized_provider)
        if provider is None:
            return _result(
                "",
                provider_id=normalized_provider,
                status=CredentialConsumptionStatus.UNKNOWN_CREDENTIAL,
                provenance=CredentialConsumptionProvenance.UNKNOWN,
                safe_diagnostic="unknown_asr_provider_id",
            )
        if (
            provider.local_runtime
            or not provider.credentials_required
            or provider.credential_type in {CREDENTIAL_LOCAL_BINARY, CREDENTIAL_NONE}
        ):
            return _result(
                "",
                provider_id=normalized_provider,
                status=CredentialConsumptionStatus.CREDENTIAL_NOT_REQUIRED,
                provenance=CredentialConsumptionProvenance.NOT_REQUIRED,
                safe_diagnostic="provider_does_not_require_cloud_credential",
            )

        descriptor = _descriptor_for_provider_id(normalized_provider)
        if descriptor is None or credential_locator_for_id(descriptor.credential_id) is None:
            return _result(
                "",
                provider_id=normalized_provider,
                status=CredentialConsumptionStatus.NOT_CONSUMABLE,
                provenance=CredentialConsumptionProvenance.UNKNOWN,
                safe_diagnostic="provider_credential_not_mapped_for_consumption",
            )

        base_result = self.consume_credential(
            descriptor.credential_id,
            action=action,
        )
        return _result(
            base_result.credential_id,
            provider_id=normalized_provider,
            status=base_result.status,
            provenance=base_result.provenance,
            safe_diagnostic=base_result.safe_diagnostic,
            callback_invoked=base_result.callback_invoked,
            action_succeeded=base_result.action_succeeded,
        )

    def _consume_secret(
        self,
        credential_id: str,
        secret: str,
        *,
        action: Callable[[str], object],
        provenance: CredentialConsumptionProvenance,
        diagnostic: str,
    ) -> CredentialConsumptionResult:
        try:
            action(secret)
        except (KeyboardInterrupt, SystemExit, GeneratorExit):
            raise
        except Exception:
            return _result(
                credential_id,
                status=CredentialConsumptionStatus.ACTION_ERROR,
                provenance=provenance,
                safe_diagnostic="credential_consumer_action_error",
                callback_invoked=True,
                action_succeeded=False,
            )
        finally:
            secret = ""

        return _result(
            credential_id,
            status=CredentialConsumptionStatus.CONSUMED,
            provenance=provenance,
            safe_diagnostic=diagnostic,
            callback_invoked=True,
            action_succeeded=True,
        )


def credential_consumption_result_contains_forbidden_fields(
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
        "action_result",
        "callback_result",
    }
    findings = [
        key
        for key in data
        if str(key).casefold() in forbidden_names
    ]
    findings.extend(serialized_secret_field_paths(data))
    return tuple(findings)
