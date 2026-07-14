from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Callable, Mapping

from asr_provider_metadata import (
    CREDENTIAL_LOCAL_BINARY,
    CREDENTIAL_NONE,
    PROVIDER_STATUS_CANDIDATE,
    PROVIDER_STATUS_LOCAL_FALLBACK,
    ASRProviderMetadata,
    get_asr_provider_metadata,
)
from credential_architecture import serialized_secret_field_paths
from credential_consumption import (
    CloudASRCredentialConsumer,
    CredentialConsumptionProvenance,
    CredentialConsumptionResult,
    CredentialConsumptionStatus,
)
from credential_store import YOUTUBE_CREDENTIAL_ID


ASR_PROVIDER_ACTION_SCOPE = (
    "explicit cloud-ASR provider-action coordination only; no provider clients, "
    "no connection tests, no network calls, no uploads, no background actions, "
    "and no credential values or executor return values in public results"
)
ASR_PROVIDER_ACTION_TRANSCRIBE = "transcribe"
SUPPORTED_ASR_PROVIDER_ACTIONS = (ASR_PROVIDER_ACTION_TRANSCRIBE,)

TrustedProviderExecutor = Callable[[str, str, str], object]


class _StringEnum(str, Enum):
    def __str__(self) -> str:
        return self.value


class ASRProviderActionStatus(_StringEnum):
    ACTION_SUCCEEDED = "action_succeeded"
    ACTION_FAILED = "action_failed"
    CREDENTIAL_UNAVAILABLE = "credential_unavailable"
    CREDENTIAL_NOT_REQUIRED = "credential_not_required"
    UNKNOWN_PROVIDER = "unknown_provider"
    YOUTUBE_PROVIDER_REJECTED = "youtube_provider_rejected"
    UNSUPPORTED_ACTION = "unsupported_action"
    PROVIDER_NOT_DISPATCHABLE = "provider_not_dispatchable"
    EXECUTOR_MISSING = "executor_missing"


@dataclass(frozen=True)
class ASRProviderActionResult:
    provider_id: str
    action_kind: str
    status: ASRProviderActionStatus
    safe_diagnostic: str
    credential_status: str = ""
    credential_provenance: str = ""
    executor_invoked: bool = False
    action_succeeded: bool = False
    scope: str = ASR_PROVIDER_ACTION_SCOPE

    def to_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["status"] = self.status.value
        return data


def _normalized(value: str) -> str:
    return " ".join((value or "").split())


def _result(
    provider_id: str,
    action_kind: str,
    *,
    status: ASRProviderActionStatus,
    safe_diagnostic: str,
    credential_status: str = "",
    credential_provenance: str = "",
    executor_invoked: bool = False,
    action_succeeded: bool = False,
) -> ASRProviderActionResult:
    return ASRProviderActionResult(
        provider_id=_normalized(provider_id),
        action_kind=_normalized(action_kind),
        status=status,
        safe_diagnostic=safe_diagnostic,
        credential_status=_normalized(credential_status),
        credential_provenance=_normalized(credential_provenance),
        executor_invoked=executor_invoked,
        action_succeeded=action_succeeded,
    )


def _is_youtube_provider_misuse(provider_id: str) -> bool:
    normalized = _normalized(provider_id).casefold()
    return normalized in {
        "youtube",
        "source:youtube",
        YOUTUBE_CREDENTIAL_ID.casefold(),
    }


def _provider_is_local(provider: ASRProviderMetadata) -> bool:
    return (
        provider.local_runtime
        or not provider.credentials_required
        or provider.credential_type in {CREDENTIAL_LOCAL_BINARY, CREDENTIAL_NONE}
    )


def _provider_is_dispatchable_through_injected_executor(
    provider: ASRProviderMetadata,
) -> bool:
    if _provider_is_local(provider):
        return provider.status == PROVIDER_STATUS_LOCAL_FALLBACK
    return provider.status == PROVIDER_STATUS_CANDIDATE


def _executor_key(provider_id: str, action_kind: str) -> tuple[str, str]:
    return (_normalized(provider_id), _normalized(action_kind))


def _credential_result_to_action_result(
    provider_id: str,
    action_kind: str,
    credential_result: CredentialConsumptionResult,
) -> ASRProviderActionResult:
    if (
        credential_result.status is CredentialConsumptionStatus.CONSUMED
        and credential_result.action_succeeded
    ):
        status = ASRProviderActionStatus.ACTION_SUCCEEDED
        diagnostic = "provider_action_completed"
    elif credential_result.status is CredentialConsumptionStatus.ACTION_ERROR:
        status = ASRProviderActionStatus.ACTION_FAILED
        diagnostic = "provider_action_executor_error"
    elif credential_result.status is CredentialConsumptionStatus.CREDENTIAL_NOT_REQUIRED:
        status = ASRProviderActionStatus.CREDENTIAL_NOT_REQUIRED
        diagnostic = credential_result.safe_diagnostic
    else:
        status = ASRProviderActionStatus.CREDENTIAL_UNAVAILABLE
        diagnostic = credential_result.safe_diagnostic

    return _result(
        provider_id,
        action_kind,
        status=status,
        safe_diagnostic=diagnostic,
        credential_status=credential_result.status.value,
        credential_provenance=credential_result.provenance.value,
        executor_invoked=credential_result.callback_invoked,
        action_succeeded=credential_result.action_succeeded,
    )


class ASRProviderActionCoordinator:
    """Dispatch explicit ASR provider actions through trusted executors only.

    The executor is trusted internal provider/action code, not a sandbox. This
    coordinator keeps credentials and executor return values out of public
    results, but a malicious executor can still retain or exfiltrate a
    credential through its own side effects.
    """

    def __init__(
        self,
        *,
        credential_consumer: CloudASRCredentialConsumer | None = None,
        executors: Mapping[tuple[str, str], TrustedProviderExecutor] | None = None,
    ) -> None:
        self._credential_consumer = (
            credential_consumer
            if credential_consumer is not None
            else CloudASRCredentialConsumer()
        )
        self._executors = dict(executors or {})

    def __repr__(self) -> str:
        return "ASRProviderActionCoordinator()"

    def dispatch_provider_action(
        self,
        provider_id: str,
        *,
        action_kind: str = ASR_PROVIDER_ACTION_TRANSCRIBE,
    ) -> ASRProviderActionResult:
        normalized_provider = _normalized(provider_id)
        normalized_action = _normalized(action_kind)

        if normalized_action not in SUPPORTED_ASR_PROVIDER_ACTIONS:
            return _result(
                normalized_provider,
                normalized_action,
                status=ASRProviderActionStatus.UNSUPPORTED_ACTION,
                safe_diagnostic="unsupported_asr_provider_action",
            )
        if _is_youtube_provider_misuse(normalized_provider):
            return _result(
                normalized_provider,
                normalized_action,
                status=ASRProviderActionStatus.YOUTUBE_PROVIDER_REJECTED,
                safe_diagnostic="youtube_credential_not_allowed_for_cloud_asr",
            )

        provider = get_asr_provider_metadata(normalized_provider)
        if provider is None:
            return _result(
                normalized_provider,
                normalized_action,
                status=ASRProviderActionStatus.UNKNOWN_PROVIDER,
                safe_diagnostic="unknown_asr_provider_id",
            )
        if not _provider_is_dispatchable_through_injected_executor(provider):
            return _result(
                normalized_provider,
                normalized_action,
                status=ASRProviderActionStatus.PROVIDER_NOT_DISPATCHABLE,
                safe_diagnostic=(
                    "asr_provider_not_dispatchable_through_injected_executor"
                ),
            )

        executor = self._executors.get(_executor_key(normalized_provider, normalized_action))
        if executor is None:
            return _result(
                normalized_provider,
                normalized_action,
                status=ASRProviderActionStatus.EXECUTOR_MISSING,
                safe_diagnostic="trusted_provider_executor_missing",
            )

        if _provider_is_local(provider):
            return self._dispatch_local_provider(
                normalized_provider,
                normalized_action,
                executor,
            )

        def trusted_action(credential: str) -> object:
            return executor(normalized_provider, normalized_action, credential)

        credential_result = self._credential_consumer.consume_provider_credential(
            normalized_provider,
            action=trusted_action,
        )
        return _credential_result_to_action_result(
            normalized_provider,
            normalized_action,
            credential_result,
        )

    def _dispatch_local_provider(
        self,
        provider_id: str,
        action_kind: str,
        executor: TrustedProviderExecutor,
    ) -> ASRProviderActionResult:
        try:
            executor(provider_id, action_kind, "")
        except (KeyboardInterrupt, SystemExit, GeneratorExit):
            raise
        except Exception:
            return _result(
                provider_id,
                action_kind,
                status=ASRProviderActionStatus.ACTION_FAILED,
                safe_diagnostic="provider_action_executor_error",
                credential_status=CredentialConsumptionStatus.CREDENTIAL_NOT_REQUIRED.value,
                credential_provenance=CredentialConsumptionProvenance.NOT_REQUIRED.value,
                executor_invoked=True,
                action_succeeded=False,
            )
        return _result(
            provider_id,
            action_kind,
            status=ASRProviderActionStatus.ACTION_SUCCEEDED,
            safe_diagnostic="provider_action_completed",
            credential_status=CredentialConsumptionStatus.CREDENTIAL_NOT_REQUIRED.value,
            credential_provenance=CredentialConsumptionProvenance.NOT_REQUIRED.value,
            executor_invoked=True,
            action_succeeded=True,
        )


def asr_provider_action_result_contains_forbidden_fields(
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
        "executor_result",
        "provider_response",
        "response_body",
        "headers",
        "request_payload",
    }
    findings = [
        key
        for key in data
        if str(key).casefold() in forbidden_names
    ]
    findings.extend(serialized_secret_field_paths(data))
    return tuple(findings)
