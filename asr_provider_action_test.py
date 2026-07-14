from __future__ import annotations

import ast
import json
import os
from dataclasses import asdict
from pathlib import Path

from asr_provider_action import (
    ASR_PROVIDER_ACTION_SCOPE,
    ASR_PROVIDER_ACTION_TRANSCRIBE,
    ASRProviderActionCoordinator,
    ASRProviderActionStatus,
    asr_provider_action_result_contains_forbidden_fields,
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


SECRET_SENTINEL = "ROW2C4-SECRET-MUST-NOT-APPEAR"
ALT_SECRET_SENTINEL = "ROW2C4-ALT-SECRET-MUST-NOT-APPEAR"
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


class RecordingExecutor:
    def __init__(self, *, fail: bool = False, process_exception: type[BaseException] | None = None) -> None:
        self.fail = fail
        self.process_exception = process_exception
        self.calls: list[tuple[str, str, str]] = []

    def __call__(self, provider_id: str, action_kind: str, credential: str) -> object:
        self.calls.append((provider_id, action_kind, credential))
        if self.process_exception is not None:
            raise self.process_exception()
        if self.fail:
            raise RuntimeError(SECRET_SENTINEL)
        return ALT_SECRET_SENTINEL


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
    executors: dict[tuple[str, str], RecordingExecutor] | None = None,
) -> ASRProviderActionCoordinator:
    return ASRProviderActionCoordinator(
        credential_consumer=_consumer(fake=fake, environ=environ),
        executors=executors or {},
    )


def _assert_secret_not_exposed(result: object) -> None:
    blob = (
        repr(result)
        + json.dumps(asdict(result), sort_keys=True)
        + json.dumps(result.to_dict(), sort_keys=True)
    )
    if SECRET_SENTINEL in blob or ALT_SECRET_SENTINEL in blob:
        raise AssertionError("secret sentinel leaked through public action result")
    assert not asr_provider_action_result_contains_forbidden_fields(result.to_dict())


def _executor_mapping(provider_id: str, executor: RecordingExecutor) -> dict[tuple[str, str], RecordingExecutor]:
    return {(provider_id, ASR_PROVIDER_ACTION_TRANSCRIBE): executor}


def test_no_lookup_or_dispatch_at_import_or_construction() -> None:
    fake = FakeKeyring()
    executor = RecordingExecutor()
    coordinator = _coordinator(
        fake=fake,
        executors=_executor_mapping(CLOUD_PROVIDER_ID, executor),
    )

    assert repr(coordinator) == "ASRProviderActionCoordinator()"
    assert ASR_PROVIDER_ACTION_SCOPE
    assert fake.calls == []
    assert executor.calls == []


def test_no_action_until_explicit_dispatch() -> None:
    fake = FakeKeyring()
    _store_secret(fake, SUPPORTED_CREDENTIAL_ID, SECRET_SENTINEL)
    executor = RecordingExecutor()
    coordinator = _coordinator(
        fake=fake,
        executors=_executor_mapping(CLOUD_PROVIDER_ID, executor),
    )

    assert fake.calls == []
    assert executor.calls == []

    result = coordinator.dispatch_provider_action(CLOUD_PROVIDER_ID)

    assert result.status is ASRProviderActionStatus.ACTION_SUCCEEDED
    assert len(fake.calls) == 1
    if len(executor.calls) != 1:
        raise AssertionError("executor was not invoked exactly once")
    _assert_secret_not_exposed(result)


def test_local_provider_dispatches_without_cloud_credential() -> None:
    fake = FakeKeyring()
    executor = RecordingExecutor()
    result = _coordinator(
        fake=fake,
        executors=_executor_mapping(LOCAL_PROVIDER_ID, executor),
    ).dispatch_provider_action(LOCAL_PROVIDER_ID)

    assert result.status is ASRProviderActionStatus.ACTION_SUCCEEDED
    assert result.credential_status == CredentialConsumptionStatus.CREDENTIAL_NOT_REQUIRED.value
    assert result.credential_provenance == CredentialConsumptionProvenance.NOT_REQUIRED.value
    assert fake.calls == []
    if executor.calls != [(LOCAL_PROVIDER_ID, ASR_PROVIDER_ACTION_TRANSCRIBE, "")]:
        raise AssertionError("local executor did not receive the expected non-secret call")
    _assert_secret_not_exposed(result)


def test_cloud_provider_uses_secure_credential_once() -> None:
    fake = FakeKeyring()
    _store_secret(fake, SUPPORTED_CREDENTIAL_ID, SECRET_SENTINEL)
    executor = RecordingExecutor()

    result = _coordinator(
        fake=fake,
        executors=_executor_mapping(CLOUD_PROVIDER_ID, executor),
    ).dispatch_provider_action(CLOUD_PROVIDER_ID)

    assert result.status is ASRProviderActionStatus.ACTION_SUCCEEDED
    assert "credential_id" not in result.to_dict()
    assert result.credential_status == CredentialConsumptionStatus.CONSUMED.value
    assert result.credential_provenance == CredentialConsumptionProvenance.SECURE_KEYRING.value
    assert result.executor_invoked is True
    assert result.action_succeeded is True
    if len(executor.calls) != 1 or executor.calls[0][2] != SECRET_SENTINEL:
        raise AssertionError("secure credential was not supplied only to the trusted executor")
    _assert_secret_not_exposed(result)


def test_missing_secure_value_falls_back_to_environment() -> None:
    executor = RecordingExecutor()
    local_env = {"ELEVENLABS_API_KEY": ALT_SECRET_SENTINEL}

    result = _coordinator(
        environ=local_env,
        executors=_executor_mapping(CLOUD_PROVIDER_ID, executor),
    ).dispatch_provider_action(CLOUD_PROVIDER_ID)

    assert result.status is ASRProviderActionStatus.ACTION_SUCCEEDED
    assert result.credential_provenance == CredentialConsumptionProvenance.ENVIRONMENT_VARIABLE.value
    if len(executor.calls) != 1 or executor.calls[0][2] != ALT_SECRET_SENTINEL:
        raise AssertionError("environment credential was not supplied only to the trusted executor")
    _assert_secret_not_exposed(result)


def test_invalid_secure_value_blocks_dispatch_and_environment_fallback() -> None:
    for stored_value in ("", "   "):
        fake = FakeKeyring()
        _store_secret(fake, SUPPORTED_CREDENTIAL_ID, stored_value)
        executor = RecordingExecutor()

        result = _coordinator(
            fake=fake,
            environ={"ELEVENLABS_API_KEY": ALT_SECRET_SENTINEL},
            executors=_executor_mapping(CLOUD_PROVIDER_ID, executor),
        ).dispatch_provider_action(CLOUD_PROVIDER_ID)

        assert result.status is ASRProviderActionStatus.CREDENTIAL_UNAVAILABLE
        assert result.credential_status == CredentialConsumptionStatus.STORAGE_ERROR.value
        assert result.safe_diagnostic == "invalid_secure_credential_value"
        assert result.executor_invoked is False
        assert executor.calls == []
        _assert_secret_not_exposed(result)


def test_missing_all_sources_blocks_dispatch() -> None:
    executor = RecordingExecutor()

    result = _coordinator(
        executors=_executor_mapping(CLOUD_PROVIDER_ID, executor),
    ).dispatch_provider_action(CLOUD_PROVIDER_ID)

    assert result.status is ASRProviderActionStatus.CREDENTIAL_UNAVAILABLE
    assert result.credential_status == CredentialConsumptionStatus.MISSING.value
    assert result.executor_invoked is False
    assert executor.calls == []
    _assert_secret_not_exposed(result)


def test_backend_unavailable_and_error_use_environment_fallback() -> None:
    executor_unavailable = RecordingExecutor()
    factory_calls: list[str] = []

    def unavailable_factory() -> object:
        factory_calls.append("called")
        raise ImportError(SECRET_SENTINEL)

    unavailable_result = ASRProviderActionCoordinator(
        credential_consumer=CloudASRCredentialConsumer(
            keyring_module_factory=unavailable_factory,
            environ={"ELEVENLABS_API_KEY": ALT_SECRET_SENTINEL},
        ),
        executors=_executor_mapping(CLOUD_PROVIDER_ID, executor_unavailable),
    ).dispatch_provider_action(CLOUD_PROVIDER_ID)

    assert unavailable_result.status is ASRProviderActionStatus.ACTION_SUCCEEDED
    assert unavailable_result.credential_provenance == CredentialConsumptionProvenance.ENVIRONMENT_VARIABLE.value
    assert factory_calls == ["called"]

    executor_error = RecordingExecutor()
    error_result = _coordinator(
        fake=FakeKeyring(fail_get=True),
        environ={"ELEVENLABS_API_KEY": ALT_SECRET_SENTINEL},
        executors=_executor_mapping(CLOUD_PROVIDER_ID, executor_error),
    ).dispatch_provider_action(CLOUD_PROVIDER_ID)

    assert error_result.status is ASRProviderActionStatus.ACTION_SUCCEEDED
    assert error_result.credential_provenance == CredentialConsumptionProvenance.ENVIRONMENT_VARIABLE.value
    for result in (unavailable_result, error_result):
        _assert_secret_not_exposed(result)


def test_unknown_rejected_blocked_unmapped_and_youtube_provider_ids_are_rejected() -> None:
    fake = FakeKeyring()
    executor = RecordingExecutor()
    non_dispatchable_provider_ids = [
        provider.provider_id
        for provider in available_asr_provider_metadata()
        if provider.provider_id not in {CLOUD_PROVIDER_ID, LOCAL_PROVIDER_ID}
    ]
    executors = {
        ("unknown_provider", ASR_PROVIDER_ACTION_TRANSCRIBE): executor,
        (YOUTUBE_CREDENTIAL_ID, ASR_PROVIDER_ACTION_TRANSCRIBE): executor,
    }
    executors.update(
        {
            (provider_id, ASR_PROVIDER_ACTION_TRANSCRIBE): executor
            for provider_id in non_dispatchable_provider_ids
        }
    )
    coordinator = _coordinator(fake=fake, executors=executors)

    unknown = coordinator.dispatch_provider_action("unknown_provider")
    non_dispatchable_results = [
        coordinator.dispatch_provider_action(provider_id)
        for provider_id in non_dispatchable_provider_ids
    ]
    youtube = coordinator.dispatch_provider_action(YOUTUBE_CREDENTIAL_ID)
    unsupported_action = coordinator.dispatch_provider_action(
        CLOUD_PROVIDER_ID,
        action_kind="connection_test",
    )

    assert unknown.status is ASRProviderActionStatus.UNKNOWN_PROVIDER
    assert non_dispatchable_provider_ids == [
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
        result.status is ASRProviderActionStatus.PROVIDER_NOT_DISPATCHABLE
        for result in non_dispatchable_results
    )
    assert youtube.status is ASRProviderActionStatus.YOUTUBE_PROVIDER_REJECTED
    assert unsupported_action.status is ASRProviderActionStatus.UNSUPPORTED_ACTION
    assert fake.calls == []
    assert executor.calls == []
    for result in (
        unknown,
        *non_dispatchable_results,
        youtube,
        unsupported_action,
    ):
        _assert_secret_not_exposed(result)


def test_executor_missing_does_not_resolve_credential() -> None:
    fake = FakeKeyring()
    _store_secret(fake, SUPPORTED_CREDENTIAL_ID, SECRET_SENTINEL)

    result = _coordinator(fake=fake).dispatch_provider_action(CLOUD_PROVIDER_ID)

    assert result.status is ASRProviderActionStatus.EXECUTOR_MISSING
    assert fake.calls == []
    _assert_secret_not_exposed(result)


def test_executor_return_ignored_and_ordinary_exception_safe() -> None:
    executor = RecordingExecutor()
    returned = _coordinator(
        environ={"ELEVENLABS_API_KEY": SECRET_SENTINEL},
        executors=_executor_mapping(CLOUD_PROVIDER_ID, executor),
    ).dispatch_provider_action(CLOUD_PROVIDER_ID)
    assert returned.status is ASRProviderActionStatus.ACTION_SUCCEEDED
    assert "executor_result" not in returned.to_dict()
    _assert_secret_not_exposed(returned)

    failing = RecordingExecutor(fail=True)
    error = _coordinator(
        environ={"ELEVENLABS_API_KEY": SECRET_SENTINEL},
        executors=_executor_mapping(CLOUD_PROVIDER_ID, failing),
    ).dispatch_provider_action(CLOUD_PROVIDER_ID)
    assert error.status is ASRProviderActionStatus.ACTION_FAILED
    assert error.safe_diagnostic == "provider_action_executor_error"
    _assert_secret_not_exposed(error)


def test_process_control_exceptions_are_not_swallowed() -> None:
    for exception_type in (KeyboardInterrupt, SystemExit, GeneratorExit):
        executor = RecordingExecutor(process_exception=exception_type)
        try:
            _coordinator(
                environ={"ELEVENLABS_API_KEY": SECRET_SENTINEL},
                executors=_executor_mapping(CLOUD_PROVIDER_ID, executor),
            ).dispatch_provider_action(CLOUD_PROVIDER_ID)
        except exception_type:
            pass
        else:
            raise AssertionError("process-control exception was swallowed")


def test_no_global_or_instance_credential_cache() -> None:
    fake = FakeKeyring()
    executor = RecordingExecutor()
    coordinator = _coordinator(
        fake=fake,
        executors=_executor_mapping(CLOUD_PROVIDER_ID, executor),
    )

    _store_secret(fake, SUPPORTED_CREDENTIAL_ID, SECRET_SENTINEL)
    first = coordinator.dispatch_provider_action(CLOUD_PROVIDER_ID)
    _store_secret(fake, SUPPORTED_CREDENTIAL_ID, ALT_SECRET_SENTINEL)
    second = coordinator.dispatch_provider_action(CLOUD_PROVIDER_ID)

    assert first.status is ASRProviderActionStatus.ACTION_SUCCEEDED
    assert second.status is ASRProviderActionStatus.ACTION_SUCCEEDED
    if len(executor.calls) != 2:
        raise AssertionError("executor was not invoked twice")
    if executor.calls[0][2] == executor.calls[1][2]:
        raise AssertionError("coordinator appeared to reuse a cached credential")
    _assert_secret_not_exposed(first)
    _assert_secret_not_exposed(second)


def test_environment_mapping_is_not_mutated() -> None:
    local_env = {"ELEVENLABS_API_KEY": SECRET_SENTINEL}
    before_local_env = dict(local_env)
    before_os_environ = dict(os.environ)
    executor = RecordingExecutor()

    result = _coordinator(
        environ=local_env,
        executors=_executor_mapping(CLOUD_PROVIDER_ID, executor),
    ).dispatch_provider_action(CLOUD_PROVIDER_ID)

    assert result.status is ASRProviderActionStatus.ACTION_SUCCEEDED
    assert local_env == before_local_env
    assert dict(os.environ) == before_os_environ
    _assert_secret_not_exposed(result)


def test_provider_metadata_mapping_is_exact_and_non_pattern_based() -> None:
    assert get_asr_provider_metadata(CLOUD_PROVIDER_ID) is not None
    assert get_asr_provider_metadata(LOCAL_PROVIDER_ID) is not None
    assert get_asr_provider_metadata("elevenlabs_scribe_extra") is None

    executor = RecordingExecutor()
    fake = FakeKeyring()
    _store_secret(fake, SUPPORTED_CREDENTIAL_ID, SECRET_SENTINEL)
    result = _coordinator(
        fake=fake,
        executors=_executor_mapping("elevenlabs_scribe_extra", executor),
    ).dispatch_provider_action("elevenlabs_scribe_extra")

    assert result.status is ASRProviderActionStatus.UNKNOWN_PROVIDER
    assert fake.calls == []
    assert executor.calls == []
    _assert_secret_not_exposed(result)


def test_static_safety_no_network_or_secret_sinks() -> None:
    source_path = Path("asr_provider_action.py")
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


def run_self_test() -> None:
    test_no_lookup_or_dispatch_at_import_or_construction()
    test_no_action_until_explicit_dispatch()
    test_local_provider_dispatches_without_cloud_credential()
    test_cloud_provider_uses_secure_credential_once()
    test_missing_secure_value_falls_back_to_environment()
    test_invalid_secure_value_blocks_dispatch_and_environment_fallback()
    test_missing_all_sources_blocks_dispatch()
    test_backend_unavailable_and_error_use_environment_fallback()
    test_unknown_rejected_blocked_unmapped_and_youtube_provider_ids_are_rejected()
    test_executor_missing_does_not_resolve_credential()
    test_executor_return_ignored_and_ordinary_exception_safe()
    test_process_control_exceptions_are_not_swallowed()
    test_no_global_or_instance_credential_cache()
    test_environment_mapping_is_not_mutated()
    test_provider_metadata_mapping_is_exact_and_non_pattern_based()
    test_static_safety_no_network_or_secret_sinks()


if __name__ == "__main__":
    run_self_test()
    print("ASR provider action self-test passed.")
