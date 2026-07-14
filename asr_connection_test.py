from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Callable, Mapping

from asr_provider_metadata import (
    CREDENTIAL_LOCAL_BINARY,
    CREDENTIAL_NONE,
    PROVIDER_STATUS_CANDIDATE,
    ASRProviderMetadata,
    get_asr_provider_metadata,
)
from credential_architecture import (
    build_row2a_credential_architecture,
    serialized_secret_field_paths,
)
from credential_consumption import (
    CloudASRCredentialConsumer,
    CredentialConsumptionResult,
    CredentialConsumptionStatus,
)
from credential_store import YOUTUBE_CREDENTIAL_ID, credential_locator_for_id


ASR_CONNECTION_TEST_SCOPE = (
    "explicit cloud-ASR connection-test seam only; no provider clients, "
    "no production testers, no network calls, no account/quota/model lookups, "
    "no uploads, no GUI wiring, and no credential values or tester return "
    "values in public results"
)

TrustedConnectionTester = Callable[[str, str], object]


class _StringEnum(str, Enum):
    def __str__(self) -> str:
        return self.value


class ASRConnectionTestStatus(_StringEnum):
    TESTER_COMPLETED = "tester_completed"
    TESTER_FAILED = "tester_failed"
    CREDENTIAL_UNAVAILABLE = "credential_unavailable"
    CONNECTION_TEST_NOT_REQUIRED = "connection_test_not_required"
    UNKNOWN_PROVIDER = "unknown_provider"
    YOUTUBE_PROVIDER_REJECTED = "youtube_provider_rejected"
    PROVIDER_NOT_TEST_DISPATCHABLE = "provider_not_test_dispatchable"
    TESTER_MISSING = "tester_missing"


@dataclass(frozen=True)
class ASRConnectionTestResult:
    provider_id: str
    status: ASRConnectionTestStatus
    safe_diagnostic: str
    credential_status: str = ""
    credential_provenance: str = ""
    tester_invoked: bool = False
    tester_completed: bool = False
    scope: str = ASR_CONNECTION_TEST_SCOPE

    def to_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["status"] = self.status.value
        return data


def _normalized(value: str) -> str:
    return " ".join((value or "").split())


def _result(
    provider_id: str,
    *,
    status: ASRConnectionTestStatus,
    safe_diagnostic: str,
    credential_status: str = "",
    credential_provenance: str = "",
    tester_invoked: bool = False,
    tester_completed: bool = False,
) -> ASRConnectionTestResult:
    return ASRConnectionTestResult(
        provider_id=_normalized(provider_id),
        status=status,
        safe_diagnostic=safe_diagnostic,
        credential_status=_normalized(credential_status),
        credential_provenance=_normalized(credential_provenance),
        tester_invoked=tester_invoked,
        tester_completed=tester_completed,
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


def _provider_has_consumable_cloud_credential(provider_id: str) -> bool:
    entry_id = "asr:" + _normalized(provider_id)
    for descriptor in build_row2a_credential_architecture().descriptors:
        if descriptor.entry_id != entry_id:
            continue
        return credential_locator_for_id(descriptor.credential_id) is not None
    return False


def _provider_is_test_dispatchable(provider: ASRProviderMetadata) -> bool:
    if _provider_is_local(provider):
        return False
    return (
        provider.status == PROVIDER_STATUS_CANDIDATE
        and provider.credentials_required
        and _provider_has_consumable_cloud_credential(provider.provider_id)
    )


def _credential_result_to_connection_result(
    provider_id: str,
    credential_result: CredentialConsumptionResult,
) -> ASRConnectionTestResult:
    if (
        credential_result.status is CredentialConsumptionStatus.CONSUMED
        and credential_result.action_succeeded
    ):
        status = ASRConnectionTestStatus.TESTER_COMPLETED
        diagnostic = "trusted_connection_tester_completed"
    elif credential_result.status is CredentialConsumptionStatus.ACTION_ERROR:
        status = ASRConnectionTestStatus.TESTER_FAILED
        diagnostic = "connection_tester_action_error"
    else:
        status = ASRConnectionTestStatus.CREDENTIAL_UNAVAILABLE
        diagnostic = credential_result.safe_diagnostic

    return _result(
        provider_id,
        status=status,
        safe_diagnostic=diagnostic,
        credential_status=credential_result.status.value,
        credential_provenance=credential_result.provenance.value,
        tester_invoked=credential_result.callback_invoked,
        tester_completed=credential_result.action_succeeded,
    )


class ASRConnectionTestCoordinator:
    """Run explicit local connection-test seams through trusted testers only.

    Testers are trusted internal provider-specific code, not a sandbox. This
    coordinator keeps credentials and tester return values out of public
    results, but a malicious tester can still retain or exfiltrate a credential
    through its own side effects. A completed tester call only means the
    injected tester returned normally; it does not prove provider
    authentication, credential validity, network reachability, account access,
    quota access, or model availability.
    """

    def __init__(
        self,
        *,
        credential_consumer: CloudASRCredentialConsumer | None = None,
    ) -> None:
        self._credential_consumer = (
            credential_consumer
            if credential_consumer is not None
            else CloudASRCredentialConsumer()
        )

    def __repr__(self) -> str:
        return "ASRConnectionTestCoordinator()"

    def test_provider_connection(
        self,
        provider_id: str,
        *,
        tester: TrustedConnectionTester | None = None,
    ) -> ASRConnectionTestResult:
        normalized_provider = _normalized(provider_id)

        if _is_youtube_provider_misuse(normalized_provider):
            return _result(
                normalized_provider,
                status=ASRConnectionTestStatus.YOUTUBE_PROVIDER_REJECTED,
                safe_diagnostic="youtube_credential_not_allowed_for_cloud_asr",
            )

        provider = get_asr_provider_metadata(normalized_provider)
        if provider is None:
            return _result(
                normalized_provider,
                status=ASRConnectionTestStatus.UNKNOWN_PROVIDER,
                safe_diagnostic="unknown_asr_provider_id",
            )

        if _provider_is_local(provider):
            return _result(
                normalized_provider,
                status=ASRConnectionTestStatus.CONNECTION_TEST_NOT_REQUIRED,
                safe_diagnostic="local_asr_provider_connection_test_not_required",
            )

        if not _provider_is_test_dispatchable(provider):
            return _result(
                normalized_provider,
                status=ASRConnectionTestStatus.PROVIDER_NOT_TEST_DISPATCHABLE,
                safe_diagnostic="asr_provider_not_connection_test_dispatchable",
            )

        if tester is None:
            return _result(
                normalized_provider,
                status=ASRConnectionTestStatus.TESTER_MISSING,
                safe_diagnostic="trusted_connection_tester_missing",
            )

        def trusted_test(credential: str) -> object:
            return tester(normalized_provider, credential)

        credential_result = self._credential_consumer.consume_provider_credential(
            normalized_provider,
            action=trusted_test,
        )
        return _credential_result_to_connection_result(
            normalized_provider,
            credential_result,
        )


def asr_connection_test_result_contains_forbidden_fields(
    data: Mapping[str, object],
) -> tuple[str, ...]:
    forbidden_names = {
        "credential",
        "credential_id",
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
        "tester_result",
        "provider_response",
        "response_body",
        "account",
        "quota",
        "models",
        "model_list",
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
