from __future__ import annotations

import ast
import json
import os
from dataclasses import asdict
from pathlib import Path

from asr_connection_test import (
    ASR_CONNECTION_TEST_SCOPE,
    ASRConnectionTestCoordinator,
    ASRConnectionTestStatus,
    asr_connection_test_result_contains_forbidden_fields,
)
from asr_provider_metadata import (
    available_asr_provider_metadata,
    get_asr_provider_metadata,
)
from credential_consumption import (
    CloudASRCredentialConsumer,
    CredentialConsumptionProvenance,
    CredentialConsumptionStatus,
)
from credential_store import YOUTUBE_CREDENTIAL_ID, credential_locator_for_id


SECRET_SENTINEL = "ROW2C5-CONNECTION-SECRET-MUST-NOT-APPEAR"
ALT_SECRET_SENTINEL = "ROW2C5-CONNECTION-ALT-SECRET-MUST-NOT-APPEAR"
PROVIDER_RESPONSE_SENTINEL = "ROW2C5-PROVIDER-RESPONSE-MUST-NOT-APPEAR"
CLOUD_PROVIDER_ID = "elevenlabs_scribe"
LOCAL_PROVIDER_ID = "whisper_cpp_vulkan_large_v3_turbo"
SUPPORTED_CREDENTIAL_ID = "elevenlabs_scribe_api_key"


class FakeKeyring:
    def __init__(self, *, fail_get: bool = False) -> None:
        self.fail_get = fail_get
        self.store: dict[tuple[str, str], str] = {}
        self.calls: list[tuple[str, str, str]] = []

    def get_password(self, service_name: str, account_name: str) -> str | None:
        self.calls.append(("get_password", service_name, account_name))
        if self.fail_get:
            raise RuntimeError(SECRET_SENTINEL)
        return self.store.get((service_name, account_name))


class RecordingTester:
    def __init__(
        self,
        *,
        return_value: object | None = None,
        fail: bool = False,
        process_exception: type[BaseException] | None = None,
    ) -> None:
        self.return_value = return_value
        self.fail = fail
        self.process_exception = process_exception
        self.calls: list[tuple[str, str]] = []

    def __call__(self, provider_id: str, credential: str) -> object:
        self.calls.append((provider_id, credential))
        if self.process_exception is not None:
            raise self.process_exception()
        if self.fail:
            raise RuntimeError(SECRET_SENTINEL)
        if self.return_value is not None:
            return self.return_value
        return PROVIDER_RESPONSE_SENTINEL


def _store_secret(
    fake: FakeKeyring,
    credential_id: str,
    secret: str,
) -> None:
    locator = credential_locator_for_id(credential_id)
    assert locator is not None
    fake.store[(locator.service_name, locator.account_name)] = secret


def _consumer(
    *,
    fake: FakeKeyring | None = None,
    environ: dict[str, str] | None = None,
) -> CloudASRCredentialConsumer:
    return CloudASRCredentialConsumer(
        keyring_module=fake if fake is not None else FakeKeyring(),
        environ=environ or {},
    )


def _coordinator(
    *,
    fake: FakeKeyring | None = None,
    environ: dict[str, str] | None = None,
    consumer: CloudASRCredentialConsumer | None = None,
) -> ASRConnectionTestCoordinator:
    return ASRConnectionTestCoordinator(
        credential_consumer=consumer
        if consumer is not None
        else _consumer(fake=fake, environ=environ),
    )


def _assert_secret_not_exposed(result: object) -> None:
    blob = (
        repr(result)
        + json.dumps(asdict(result), sort_keys=True)
        + json.dumps(result.to_dict(), sort_keys=True)
    )
    for forbidden in (
        SECRET_SENTINEL,
        ALT_SECRET_SENTINEL,
        PROVIDER_RESPONSE_SENTINEL,
    ):
        if forbidden in blob:
            raise AssertionError("secret/provider sentinel leaked through public connection-test result")
    assert not asr_connection_test_result_contains_forbidden_fields(result.to_dict())


def test_no_lookup_or_tester_dispatch_at_import_or_construction() -> None:
    fake = FakeKeyring()
    tester = RecordingTester()
    coordinator = _coordinator(fake=fake)

    assert repr(coordinator) == "ASRConnectionTestCoordinator()"
    assert ASR_CONNECTION_TEST_SCOPE
    assert fake.calls == []
    assert tester.calls == []


def test_explicit_method_call_required_before_lookup_or_dispatch() -> None:
    fake = FakeKeyring()
    _store_secret(fake, SUPPORTED_CREDENTIAL_ID, SECRET_SENTINEL)
    tester = RecordingTester()
    coordinator = _coordinator(fake=fake)

    assert fake.calls == []
    assert tester.calls == []

    result = coordinator.test_provider_connection(CLOUD_PROVIDER_ID, tester=tester)

    assert result.status is ASRConnectionTestStatus.TESTER_COMPLETED
    assert len(fake.calls) == 1
    if len(tester.calls) != 1:
        raise AssertionError("trusted tester was not invoked exactly once")
    _assert_secret_not_exposed(result)


def test_supported_cloud_provider_uses_secure_credential_once() -> None:
    fake = FakeKeyring()
    _store_secret(fake, SUPPORTED_CREDENTIAL_ID, SECRET_SENTINEL)
    tester = RecordingTester()

    result = _coordinator(fake=fake).test_provider_connection(
        CLOUD_PROVIDER_ID,
        tester=tester,
    )

    assert result.status is ASRConnectionTestStatus.TESTER_COMPLETED
    assert "credential_id" not in result.to_dict()
    assert result.credential_status == CredentialConsumptionStatus.CONSUMED.value
    assert result.credential_provenance == CredentialConsumptionProvenance.SECURE_KEYRING.value
    assert result.tester_invoked is True
    assert result.tester_completed is True
    if len(tester.calls) != 1 or tester.calls[0][1] != SECRET_SENTINEL:
        raise AssertionError("secure credential was not supplied only to the trusted tester")
    _assert_secret_not_exposed(result)


def test_missing_secure_value_falls_back_to_environment() -> None:
    tester = RecordingTester()

    result = _coordinator(
        environ={"ELEVENLABS_API_KEY": ALT_SECRET_SENTINEL},
    ).test_provider_connection(CLOUD_PROVIDER_ID, tester=tester)

    assert result.status is ASRConnectionTestStatus.TESTER_COMPLETED
    assert result.credential_provenance == CredentialConsumptionProvenance.ENVIRONMENT_VARIABLE.value
    if len(tester.calls) != 1 or tester.calls[0][1] != ALT_SECRET_SENTINEL:
        raise AssertionError("environment credential was not supplied only to the trusted tester")
    _assert_secret_not_exposed(result)


def test_invalid_secure_value_blocks_tester_and_environment_fallback() -> None:
    for stored_value in ("", "   "):
        fake = FakeKeyring()
        _store_secret(fake, SUPPORTED_CREDENTIAL_ID, stored_value)
        tester = RecordingTester()

        result = _coordinator(
            fake=fake,
            environ={"ELEVENLABS_API_KEY": ALT_SECRET_SENTINEL},
        ).test_provider_connection(CLOUD_PROVIDER_ID, tester=tester)

        assert result.status is ASRConnectionTestStatus.CREDENTIAL_UNAVAILABLE
        assert result.credential_status == CredentialConsumptionStatus.STORAGE_ERROR.value
        assert result.safe_diagnostic == "invalid_secure_credential_value"
        assert result.tester_invoked is False
        assert tester.calls == []
        _assert_secret_not_exposed(result)


def test_missing_all_credentials_blocks_tester() -> None:
    tester = RecordingTester()

    result = _coordinator().test_provider_connection(CLOUD_PROVIDER_ID, tester=tester)

    assert result.status is ASRConnectionTestStatus.CREDENTIAL_UNAVAILABLE
    assert result.credential_status == CredentialConsumptionStatus.MISSING.value
    assert result.tester_invoked is False
    assert tester.calls == []
    _assert_secret_not_exposed(result)


def test_backend_unavailable_and_error_use_environment_fallback() -> None:
    unavailable_tester = RecordingTester()
    factory_calls: list[str] = []

    def unavailable_factory() -> object:
        factory_calls.append("called")
        raise ImportError(SECRET_SENTINEL)

    unavailable_result = _coordinator(
        consumer=CloudASRCredentialConsumer(
            keyring_module_factory=unavailable_factory,
            environ={"ELEVENLABS_API_KEY": ALT_SECRET_SENTINEL},
        )
    ).test_provider_connection(CLOUD_PROVIDER_ID, tester=unavailable_tester)

    assert unavailable_result.status is ASRConnectionTestStatus.TESTER_COMPLETED
    assert unavailable_result.credential_provenance == CredentialConsumptionProvenance.ENVIRONMENT_VARIABLE.value
    assert factory_calls == ["called"]

    error_tester = RecordingTester()
    error_result = _coordinator(
        fake=FakeKeyring(fail_get=True),
        environ={"ELEVENLABS_API_KEY": ALT_SECRET_SENTINEL},
    ).test_provider_connection(CLOUD_PROVIDER_ID, tester=error_tester)

    assert error_result.status is ASRConnectionTestStatus.TESTER_COMPLETED
    assert error_result.credential_provenance == CredentialConsumptionProvenance.ENVIRONMENT_VARIABLE.value
    for result in (unavailable_result, error_result):
        _assert_secret_not_exposed(result)


def test_unknown_pattern_adjacent_youtube_local_and_non_testable_providers_reject_before_lookup() -> None:
    fake = FakeKeyring()
    tester = RecordingTester()
    non_testable_provider_ids = [
        provider.provider_id
        for provider in available_asr_provider_metadata()
        if provider.provider_id not in {CLOUD_PROVIDER_ID, LOCAL_PROVIDER_ID}
    ]
    coordinator = _coordinator(fake=fake)

    unknown = coordinator.test_provider_connection("unknown_provider", tester=tester)
    pattern_adjacent = coordinator.test_provider_connection(
        "elevenlabs_scribe_extra",
        tester=tester,
    )
    youtube = coordinator.test_provider_connection(YOUTUBE_CREDENTIAL_ID, tester=tester)
    local = coordinator.test_provider_connection(LOCAL_PROVIDER_ID, tester=tester)
    non_testable_results = [
        coordinator.test_provider_connection(provider_id, tester=tester)
        for provider_id in non_testable_provider_ids
    ]

    assert unknown.status is ASRConnectionTestStatus.UNKNOWN_PROVIDER
    assert pattern_adjacent.status is ASRConnectionTestStatus.UNKNOWN_PROVIDER
    assert youtube.status is ASRConnectionTestStatus.YOUTUBE_PROVIDER_REJECTED
    assert local.status is ASRConnectionTestStatus.CONNECTION_TEST_NOT_REQUIRED
    assert non_testable_provider_ids == [
        "assemblyai_universal_3_5_pro",
        "deepgram_nova_3",
        "speechmatics_enhanced",
        "azure_speech",
        "google_stt_video_enhanced",
        "cohere_transcribe",
        "google_stt_latest_long",
        "aws_transcribe_custom_vocabulary",
    ]
    assert all(
        result.status is ASRConnectionTestStatus.PROVIDER_NOT_TEST_DISPATCHABLE
        for result in non_testable_results
    )
    assert fake.calls == []
    assert tester.calls == []
    for result in (
        unknown,
        pattern_adjacent,
        youtube,
        local,
        *non_testable_results,
    ):
        _assert_secret_not_exposed(result)


def test_missing_tester_rejected_before_credential_lookup() -> None:
    fake = FakeKeyring()
    _store_secret(fake, SUPPORTED_CREDENTIAL_ID, SECRET_SENTINEL)

    result = _coordinator(fake=fake).test_provider_connection(CLOUD_PROVIDER_ID)

    assert result.status is ASRConnectionTestStatus.TESTER_MISSING
    assert fake.calls == []
    _assert_secret_not_exposed(result)


def test_tester_returns_are_ignored_and_not_exposed() -> None:
    return_values = (
        True,
        False,
        ALT_SECRET_SENTINEL,
        {
            "provider_response": PROVIDER_RESPONSE_SENTINEL,
            "account": SECRET_SENTINEL,
            "quota": ALT_SECRET_SENTINEL,
            "models": ["fake-model"],
        },
    )

    for return_value in return_values:
        returned_tester = RecordingTester(return_value=return_value)
        returned = _coordinator(
            environ={"ELEVENLABS_API_KEY": SECRET_SENTINEL},
        ).test_provider_connection(CLOUD_PROVIDER_ID, tester=returned_tester)
        assert returned.status is ASRConnectionTestStatus.TESTER_COMPLETED
        assert returned.tester_invoked is True
        assert returned.tester_completed is True
        assert "tester_result" not in returned.to_dict()
        _assert_secret_not_exposed(returned)


def test_ordinary_tester_exception_is_fixed_safe_failure() -> None:

    failing_tester = RecordingTester(fail=True)
    error = _coordinator(
        environ={"ELEVENLABS_API_KEY": SECRET_SENTINEL},
    ).test_provider_connection(CLOUD_PROVIDER_ID, tester=failing_tester)
    assert error.status is ASRConnectionTestStatus.TESTER_FAILED
    assert error.safe_diagnostic == "connection_tester_action_error"
    _assert_secret_not_exposed(error)


def test_process_control_exceptions_are_not_swallowed() -> None:
    for exception_type in (KeyboardInterrupt, SystemExit, GeneratorExit):
        tester = RecordingTester(process_exception=exception_type)
        try:
            _coordinator(
                environ={"ELEVENLABS_API_KEY": SECRET_SENTINEL},
            ).test_provider_connection(CLOUD_PROVIDER_ID, tester=tester)
        except exception_type:
            pass
        else:
            raise AssertionError("process-control exception was swallowed")


def test_no_global_or_instance_credential_cache() -> None:
    fake = FakeKeyring()
    tester = RecordingTester()
    coordinator = _coordinator(fake=fake)

    _store_secret(fake, SUPPORTED_CREDENTIAL_ID, SECRET_SENTINEL)
    first = coordinator.test_provider_connection(CLOUD_PROVIDER_ID, tester=tester)
    _store_secret(fake, SUPPORTED_CREDENTIAL_ID, ALT_SECRET_SENTINEL)
    second = coordinator.test_provider_connection(CLOUD_PROVIDER_ID, tester=tester)

    assert first.status is ASRConnectionTestStatus.TESTER_COMPLETED
    assert second.status is ASRConnectionTestStatus.TESTER_COMPLETED
    if len(tester.calls) != 2:
        raise AssertionError("trusted tester was not invoked twice")
    if tester.calls[0][1] == tester.calls[1][1]:
        raise AssertionError("coordinator appeared to reuse a cached credential")
    _assert_secret_not_exposed(first)
    _assert_secret_not_exposed(second)


def test_environment_mapping_and_os_environ_are_not_mutated() -> None:
    local_env = {"ELEVENLABS_API_KEY": SECRET_SENTINEL}
    before_local_env = dict(local_env)
    before_os_environ = dict(os.environ)
    tester = RecordingTester()

    result = _coordinator(
        environ=local_env,
    ).test_provider_connection(CLOUD_PROVIDER_ID, tester=tester)

    assert result.status is ASRConnectionTestStatus.TESTER_COMPLETED
    assert local_env == before_local_env
    assert dict(os.environ) == before_os_environ
    _assert_secret_not_exposed(result)


def test_provider_metadata_mapping_is_exact_and_local_seam_only() -> None:
    assert get_asr_provider_metadata(CLOUD_PROVIDER_ID) is not None
    assert get_asr_provider_metadata(LOCAL_PROVIDER_ID) is not None
    assert get_asr_provider_metadata("elevenlabs_scribe_extra") is None
    assert not any(
        provider.test_connection_supported
        for provider in available_asr_provider_metadata()
    )

    fake = FakeKeyring()
    _store_secret(fake, SUPPORTED_CREDENTIAL_ID, SECRET_SENTINEL)
    tester = RecordingTester()
    result = _coordinator(fake=fake).test_provider_connection(
        "elevenlabs_scribe_extra",
        tester=tester,
    )

    assert result.status is ASRConnectionTestStatus.UNKNOWN_PROVIDER
    assert fake.calls == []
    assert tester.calls == []
    _assert_secret_not_exposed(result)


def test_static_safety_no_network_provider_or_secret_sinks() -> None:
    source_path = Path("asr_connection_test.py")
    source = source_path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(source_path))

    imported_roots = {
        alias.name.split(".", 1)[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    imported_roots.update(
        node.module.split(".", 1)[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    )

    assert imported_roots.isdisjoint(
        {
            "keyring",
            "requests",
            "urllib",
            "httpx",
            "aiohttp",
            "socket",
            "subprocess",
            "openai",
            "elevenlabs",
            "deepgram",
            "speechmatics",
            "boto3",
        }
    )
    assert "print(" not in source
    assert "logging" not in source
    assert "set_password(" not in source
    assert "delete_password(" not in source
    assert "putenv" not in source
    assert "environ[" not in source
    assert "requests." not in source
    assert "urllib.request" not in source
    assert "create_client" not in source
    assert "open(" not in source


def run_self_test() -> None:
    test_no_lookup_or_tester_dispatch_at_import_or_construction()
    test_explicit_method_call_required_before_lookup_or_dispatch()
    test_supported_cloud_provider_uses_secure_credential_once()
    test_missing_secure_value_falls_back_to_environment()
    test_invalid_secure_value_blocks_tester_and_environment_fallback()
    test_missing_all_credentials_blocks_tester()
    test_backend_unavailable_and_error_use_environment_fallback()
    test_unknown_pattern_adjacent_youtube_local_and_non_testable_providers_reject_before_lookup()
    test_missing_tester_rejected_before_credential_lookup()
    test_tester_returns_are_ignored_and_not_exposed()
    test_ordinary_tester_exception_is_fixed_safe_failure()
    test_process_control_exceptions_are_not_swallowed()
    test_no_global_or_instance_credential_cache()
    test_environment_mapping_and_os_environ_are_not_mutated()
    test_provider_metadata_mapping_is_exact_and_local_seam_only()
    test_static_safety_no_network_provider_or_secret_sinks()


if __name__ == "__main__":
    run_self_test()
    print("ASR connection-test seam self-test passed.")
