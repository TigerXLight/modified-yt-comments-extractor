from __future__ import annotations

import ast
import json
import tempfile
from dataclasses import asdict
from enum import Enum
from pathlib import Path
from typing import BinaryIO, Mapping

from asr_provider_action import (
    ASR_PROVIDER_ACTION_TRANSCRIBE,
    ASRProviderActionCoordinator,
    ASRProviderActionStatus,
)
from credential_consumption import (
    CloudASRCredentialConsumer,
    CredentialConsumptionProvenance,
    CredentialConsumptionStatus,
)
from credential_store import credential_locator_for_id
from elevenlabs_scribe_provider import (
    ELEVENLABS_SCRIBE_CREDENTIAL_ID,
    ELEVENLABS_SCRIBE_MODEL_ID,
    ELEVENLABS_SCRIBE_PROVIDER_ID,
    ElevenLabsScribeBatchProvider,
    ElevenLabsScribeRequest,
    ElevenLabsScribeStatus,
    ElevenLabsScribeTransportError,
)
from elevenlabs_scribe_transport import (
    ELEVENLABS_SDK_DEFAULT_TIMEOUT_SECONDS,
    ELEVENLABS_SDK_MAX_RETRIES,
    ELEVENLABS_SDK_VERSION_SPEC,
    ElevenLabsScribeSDKTransport,
    build_elevenlabs_scribe_sdk_convert_kwargs,
    create_elevenlabs_scribe_sdk_provider_executor,
    sdk_response_to_provider_mapping,
)


SECRET_SENTINEL = "SDK-TRANSPORT-SECRET-MUST-NOT-LEAK"
ALT_SECRET_SENTINEL = "SDK-TRANSPORT-ALT-SECRET-MUST-NOT-LEAK"
SENSITIVE_KEYTERM = "TransportSensitiveKeyterm"
SENSITIVE_PATH_FRAGMENT = "transport_sensitive_path"
RAW_RESPONSE_SENTINEL = "RAW-SDK-RESPONSE-MUST-NOT-LEAK"
MEDIA_BYTES = b"tiny fake media"


class FakeKeyring:
    def __init__(self) -> None:
        self.store: dict[tuple[str, str], str] = {}
        self.calls: list[tuple[str, str, str]] = []

    def get_password(self, service_name: str, account_name: str) -> str | None:
        self.calls.append(("get_password", service_name, account_name))
        return self.store.get((service_name, account_name))


class FakeSDKModel:
    def __init__(self, data: Mapping[str, object]) -> None:
        self._data = dict(data)
        self.dump_calls = 0

    def model_dump(self) -> dict[str, object]:
        self.dump_calls += 1
        return dict(self._data)

    def __repr__(self) -> str:
        return "FakeSDKModel()"


class FakeSpeechToTextService:
    def __init__(
        self,
        *,
        response: object | None = None,
        exception: Exception | None = None,
        process_exception: type[BaseException] | None = None,
    ) -> None:
        self.response = response if response is not None else _sdk_model_response()
        self.exception = exception
        self.process_exception = process_exception
        self.convert_calls: list[dict[str, object]] = []
        self.file_closed_during_call: bool | None = None

    def convert(self, **kwargs: object) -> object:
        self.file_closed_during_call = bool(getattr(kwargs.get("file"), "closed", False))
        self.convert_calls.append(dict(kwargs))
        if self.process_exception is not None:
            raise self.process_exception()
        if self.exception is not None:
            raise self.exception
        return self.response


class FakeSDKClient:
    def __init__(self, service: FakeSpeechToTextService) -> None:
        self.speech_to_text = service


class RecordingClientFactory:
    def __init__(self, service: FakeSpeechToTextService | None = None) -> None:
        self.service = service if service is not None else FakeSpeechToTextService()
        self.calls: list[tuple[str, int]] = []
        self.clients: list[FakeSDKClient] = []

    def __call__(self, api_key: str, timeout_seconds: int) -> FakeSDKClient:
        self.calls.append((api_key, timeout_seconds))
        client = FakeSDKClient(self.service)
        self.clients.append(client)
        return client


class FakeApiError(Exception):
    def __init__(self, *, status_code: int | None = None, body: object = None) -> None:
        super().__init__(RAW_RESPONSE_SENTINEL)
        self.status_code = status_code
        self.body = body
        self.headers = {"x-request-id": RAW_RESPONSE_SENTINEL}


class FakeTimeoutException(Exception):
    pass


class FakeWordType(Enum):
    WORD = "word"
    AUDIO_EVENT = "audio_event"


def _sdk_model_response() -> FakeSDKModel:
    return FakeSDKModel(
        {
            "text": "Hello world!",
            "language_code": "en",
            "language_probability": 0.99,
            "words": [
                FakeSDKModel(
                    {
                        "text": "Hello",
                        "start": 0.0,
                        "end": 0.5,
                        "type": "word",
                        "speaker_id": "speaker_1",
                        "logprob": -0.1,
                    }
                ),
                FakeSDKModel(
                    {
                        "text": "(laughter)",
                        "start": 0.6,
                        "end": 0.7,
                        "type": "audio_event",
                        "speaker_id": "speaker_1",
                    }
                ),
            ],
            "transcription_id": RAW_RESPONSE_SENTINEL,
            "audio_duration_secs": 1.0,
        }
    )


def _media_file(tmpdir: str, name: str = "sample.wav") -> Path:
    path = Path(tmpdir) / name
    path.write_bytes(MEDIA_BYTES)
    return path


def _store_secret(fake: FakeKeyring, secret: str) -> None:
    locator = credential_locator_for_id(ELEVENLABS_SCRIBE_CREDENTIAL_ID)
    assert locator is not None
    fake.store[(locator.service_name, locator.account_name)] = secret


def _consumer(fake: FakeKeyring | None = None, environ: dict[str, str] | None = None) -> CloudASRCredentialConsumer:
    return CloudASRCredentialConsumer(
        keyring_module=fake if fake is not None else FakeKeyring(),
        environ=environ or {},
    )


def _assert_private_values_absent(value: object) -> None:
    blob = repr(value)
    if hasattr(value, "to_dict"):
        blob += json.dumps(value.to_dict(), sort_keys=True)
    elif hasattr(value, "to_safe_dict"):
        blob += json.dumps(value.to_safe_dict(), sort_keys=True)
    else:
        try:
            blob += json.dumps(asdict(value), sort_keys=True)
        except TypeError:
            blob += str(value)
    for forbidden in (
        SECRET_SENTINEL,
        ALT_SECRET_SENTINEL,
        SENSITIVE_KEYTERM,
        SENSITIVE_PATH_FRAGMENT,
        RAW_RESPONSE_SENTINEL,
        MEDIA_BYTES.decode("ascii"),
    ):
        if forbidden in blob:
            raise AssertionError("private transport value leaked")


def test_static_lazy_sdk_import_and_no_logging_or_direct_network() -> None:
    source = Path("elevenlabs_scribe_transport.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    module_level_imports = [
        node
        for node in tree.body
        if isinstance(node, (ast.Import, ast.ImportFrom))
    ]
    imported_roots: set[str] = set()
    for node in module_level_imports:
        if isinstance(node, ast.Import):
            imported_roots.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif node.module:
            imported_roots.add(node.module.split(".", 1)[0])

    assert "elevenlabs" not in imported_roots
    assert imported_roots.isdisjoint({"requests", "urllib", "socket", "aiohttp", "httpx", "logging"})
    assert "print(" not in source
    assert "dotenv" not in source
    assert "ELEVENLABS_API_KEY" not in source


def test_dependency_declarations_include_official_sdk_range() -> None:
    assert ELEVENLABS_SDK_VERSION_SPEC in Path("requirements.txt").read_text(encoding="utf-8")
    assert f'"{ELEVENLABS_SDK_VERSION_SPEC}"' in Path("pyproject.toml").read_text(encoding="utf-8")


def test_transport_construction_does_not_load_sdk_or_create_client() -> None:
    calls: list[str] = []

    def loader() -> object:
        calls.append("loaded")
        raise AssertionError("loader should not run during construction")

    transport = ElevenLabsScribeSDKTransport(sdk_loader=loader)

    assert repr(transport) == "ElevenLabsScribeSDKTransport()"
    assert transport.timeout_seconds == ELEVENLABS_SDK_DEFAULT_TIMEOUT_SECONDS
    assert transport.max_retries == ELEVENLABS_SDK_MAX_RETRIES
    assert calls == []
    _assert_private_values_absent(transport)


def test_transport_constructor_rejects_invalid_timeout_and_retry_options() -> None:
    for timeout_value in (True, False, 0, -1, 1.5, float("nan"), float("inf"), "240"):
        try:
            ElevenLabsScribeSDKTransport(timeout_seconds=timeout_value)  # type: ignore[arg-type]
        except ValueError as exc:
            assert str(exc) == "invalid_timeout_seconds"
        else:
            raise AssertionError("invalid constructor timeout accepted")

    for retry_value in (True, False, -1, 1, 1.5, "0"):
        try:
            ElevenLabsScribeSDKTransport(max_retries=retry_value)  # type: ignore[arg-type]
        except ValueError as exc:
            assert str(exc) in {"invalid_max_retries", "sdk_retries_must_be_disabled"}
        else:
            raise AssertionError("invalid constructor retry policy accepted")


def test_missing_sdk_maps_to_dependency_unavailable_without_raw_import_text() -> None:
    def missing_loader() -> object:
        raise ModuleNotFoundError("No module named 'elevenlabs'", name="elevenlabs")

    transport = ElevenLabsScribeSDKTransport(sdk_loader=missing_loader)
    with tempfile.TemporaryDirectory() as tmpdir:
        media = _media_file(tmpdir)
        with media.open("rb") as file_obj:
            try:
                transport.create_transcript(
                    api_key=SECRET_SENTINEL,
                    file_obj=file_obj,
                    parameters={"model_id": ELEVENLABS_SCRIBE_MODEL_ID},
                )
            except ElevenLabsScribeTransportError as exc:
                assert exc.category == "dependency_unavailable"
                _assert_private_values_absent(exc)
            else:
                raise AssertionError("missing SDK did not fail safely")


def test_internal_import_bug_is_not_reported_as_missing_sdk() -> None:
    def broken_loader() -> object:
        raise ModuleNotFoundError("No module named 'broken_dependency'", name="broken_dependency")

    transport = ElevenLabsScribeSDKTransport(sdk_loader=broken_loader)
    with tempfile.TemporaryDirectory() as tmpdir:
        media = _media_file(tmpdir)
        with media.open("rb") as file_obj:
            try:
                transport.create_transcript(
                    api_key=SECRET_SENTINEL,
                    file_obj=file_obj,
                    parameters={"model_id": ELEVENLABS_SCRIBE_MODEL_ID},
                )
            except ModuleNotFoundError as exc:
                assert exc.name == "broken_dependency"
            else:
                raise AssertionError("internal import bug was swallowed")


def test_arbitrary_sdk_import_error_is_not_reported_as_missing_dependency() -> None:
    def broken_loader() -> object:
        raise RuntimeError("sdk import side effect failure")

    transport = ElevenLabsScribeSDKTransport(sdk_loader=broken_loader)
    with tempfile.TemporaryDirectory() as tmpdir:
        media = _media_file(tmpdir)
        with media.open("rb") as file_obj:
            try:
                transport.create_transcript(
                    api_key=SECRET_SENTINEL,
                    file_obj=file_obj,
                    parameters={"model_id": ELEVENLABS_SCRIBE_MODEL_ID},
                )
            except RuntimeError as exc:
                assert str(exc) == "sdk import side effect failure"
            else:
                raise AssertionError("arbitrary SDK import error was swallowed")


def test_exact_sdk_call_mapping_and_request_options() -> None:
    service = FakeSpeechToTextService()
    factory = RecordingClientFactory(service)
    transport = ElevenLabsScribeSDKTransport(client_factory=factory)
    with tempfile.TemporaryDirectory() as tmpdir:
        media = _media_file(tmpdir)
        with media.open("rb") as file_obj:
            response = transport.create_transcript(
                api_key=SECRET_SENTINEL,
                file_obj=file_obj,
                parameters={
                    "model_id": ELEVENLABS_SCRIBE_MODEL_ID,
                    "language_code": "en",
                    "tag_audio_events": False,
                    "diarize": True,
                    "num_speakers": 2,
                    "timestamps_granularity": "character",
                    "keyterms": [SENSITIVE_KEYTERM, "second term"],
                },
            )

        assert len(factory.calls) == 1
        assert factory.calls[0] == (SECRET_SENTINEL, ELEVENLABS_SDK_DEFAULT_TIMEOUT_SECONDS)
        assert len(factory.clients) == 1
        assert len(service.convert_calls) == 1
        kwargs = service.convert_calls[0]
        assert service.file_closed_during_call is False
        assert kwargs["model_id"] == ELEVENLABS_SCRIBE_MODEL_ID
        assert kwargs["language_code"] == "en"
        assert kwargs["tag_audio_events"] is False
        assert kwargs["diarize"] is True
        assert kwargs["num_speakers"] == 2
        assert kwargs["timestamps_granularity"] == "character"
        assert kwargs["keyterms"] == [SENSITIVE_KEYTERM, "second term"]
        assert kwargs["request_options"] == {
            "max_retries": 0,
            "timeout_in_seconds": ELEVENLABS_SDK_DEFAULT_TIMEOUT_SECONDS,
        }
        forbidden_kwargs = {
            "cloud_storage_url",
            "source_url",
            "webhook",
            "webhook_id",
            "use_multi_channel",
            "multichannel_output_style",
            "entity_detection",
            "enable_logging",
            "additional_formats",
        }
        assert forbidden_kwargs.isdisjoint(kwargs)
        assert SECRET_SENTINEL not in json.dumps({key: value for key, value in kwargs.items() if key != "file"}, default=str)
        assert response["text"] == "Hello world!"
        assert response["words"][1]["type"] == "audio_event"  # type: ignore[index]


def test_unset_options_are_omitted_and_convert_called_once_per_invocation() -> None:
    service = FakeSpeechToTextService(response={"text": "minimal"})
    factory = RecordingClientFactory(service)
    transport = ElevenLabsScribeSDKTransport(client_factory=factory)
    with tempfile.TemporaryDirectory() as tmpdir:
        media = _media_file(tmpdir)
        with media.open("rb") as file_obj:
            response = transport.create_transcript(
                api_key=SECRET_SENTINEL,
                file_obj=file_obj,
                parameters={"model_id": ELEVENLABS_SCRIBE_MODEL_ID},
            )

    assert response == {"text": "minimal"}
    assert len(factory.calls) == 1
    assert len(factory.clients) == 1
    assert len(service.convert_calls) == 1
    kwargs = service.convert_calls[0]
    assert sorted(kwargs) == ["file", "model_id", "request_options"]


def test_build_convert_kwargs_rejects_unsupported_and_invalid_parameters_before_sdk_call() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        media = _media_file(tmpdir)
        with media.open("rb") as file_obj:
            invalid_specs = [
                {"model_id": "scribe_v1"},
                {"model_id": ELEVENLABS_SCRIBE_MODEL_ID, "source_url": "https://example.invalid/a.mp3"},
                {"model_id": ELEVENLABS_SCRIBE_MODEL_ID, "webhook": True},
                {"model_id": ELEVENLABS_SCRIBE_MODEL_ID, "num_speakers": True},
                {"model_id": ELEVENLABS_SCRIBE_MODEL_ID, "keyterms": (SENSITIVE_KEYTERM,)},
            ]
            for spec in invalid_specs:
                try:
                    build_elevenlabs_scribe_sdk_convert_kwargs(
                        file_obj=file_obj,
                        parameters=spec,
                    )
                except ElevenLabsScribeTransportError as exc:
                    assert exc.category == "provider_validation_error"
                    _assert_private_values_absent(exc)
                else:
                    raise AssertionError("invalid SDK parameter set accepted")


def test_build_convert_kwargs_rejects_invalid_timeout_and_retry_options() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        media = _media_file(tmpdir)
        with media.open("rb") as file_obj:
            for timeout_value in (True, False, 0, -1, 1.5, float("nan"), float("inf"), "240"):
                try:
                    build_elevenlabs_scribe_sdk_convert_kwargs(
                        file_obj=file_obj,
                        parameters={"model_id": ELEVENLABS_SCRIBE_MODEL_ID},
                        timeout_seconds=timeout_value,  # type: ignore[arg-type]
                    )
                except ElevenLabsScribeTransportError as exc:
                    assert exc.category == "provider_validation_error"
                    _assert_private_values_absent(exc)
                else:
                    raise AssertionError("invalid SDK timeout accepted")

            for retry_value in (True, False, -1, 1, 1.5, "0"):
                try:
                    build_elevenlabs_scribe_sdk_convert_kwargs(
                        file_obj=file_obj,
                        parameters={"model_id": ELEVENLABS_SCRIBE_MODEL_ID},
                        max_retries=retry_value,  # type: ignore[arg-type]
                    )
                except ElevenLabsScribeTransportError as exc:
                    assert exc.category == "provider_validation_error"
                    _assert_private_values_absent(exc)
                else:
                    raise AssertionError("invalid SDK retry policy accepted")


def test_sdk_model_and_plain_mapping_response_conversion() -> None:
    model = _sdk_model_response()
    converted = sdk_response_to_provider_mapping(model)

    assert model.dump_calls == 1
    assert converted["text"] == "Hello world!"
    assert converted["language_code"] == "en"
    assert converted["language_probability"] == 0.99
    assert "transcription_id" not in converted
    assert "audio_duration_secs" not in converted
    words = converted["words"]
    assert isinstance(words, list)
    assert words[0] == {
        "text": "Hello",
        "start": 0.0,
        "end": 0.5,
        "type": "word",
        "speaker_id": "speaker_1",
    }
    assert sdk_response_to_provider_mapping({"text": "plain"}) == {"text": "plain"}


def test_sdk_response_enum_values_are_normalized_to_plain_values() -> None:
    converted = sdk_response_to_provider_mapping(
        {
            "text": "enum response",
            "words": [
                {
                    "text": "event",
                    "start": 0.0,
                    "end": 0.1,
                    "type": FakeWordType.AUDIO_EVENT,
                    "speaker_id": "speaker_1",
                }
            ],
        }
    )

    words = converted["words"]
    assert isinstance(words, list)
    assert words[0]["type"] == "audio_event"
    _assert_private_values_absent(converted)


def test_unexpected_response_shapes_are_rejected_safely() -> None:
    malformed = [
        object(),
        {},
        {"text": 123},
        {"transcripts": [{"text": "channel"}]},
        {"transcript_id": "async-job"},
        {"text": "bad", "words": [object()]},
    ]
    for response in malformed:
        try:
            sdk_response_to_provider_mapping(response)
        except ElevenLabsScribeTransportError as exc:
            assert exc.category == "malformed_provider_response"
            _assert_private_values_absent(exc)
        else:
            raise AssertionError("malformed SDK response accepted")


def test_structured_sdk_error_mapping_and_no_raw_leakage() -> None:
    cases = [
        (FakeApiError(status_code=401, body={"detail": {"status": "auth"}}), "authentication_rejected"),
        (FakeApiError(status_code=403, body={"detail": {"code": "ip_restricted"}}), "permission_denied"),
        (FakeApiError(status_code=403, body={"detail": {"code": "quota_exceeded"}}), "quota_or_billing_blocked"),
        (FakeApiError(status_code=408, body={}), "timeout"),
        (FakeApiError(status_code=413, body={}), "request_too_large"),
        (FakeApiError(status_code=415, body={}), "unsupported_media"),
        (FakeApiError(status_code=422, body={"detail": {"type": "invalid_file_format"}}), "unsupported_media"),
        (FakeApiError(status_code=422, body={"detail": {"type": "invalid_parameters"}}), "provider_validation_error"),
        (FakeApiError(status_code=429, body={"detail": {"code": "rate_limit"}}), "rate_limited"),
        (FakeApiError(status_code=500, body={}), "provider_service_unavailable"),
        (FakeApiError(status_code=None, body={"detail": RAW_RESPONSE_SENTINEL}), "unknown_provider_failure"),
        (FakeTimeoutException(RAW_RESPONSE_SENTINEL), "timeout"),
    ]

    with tempfile.TemporaryDirectory() as tmpdir:
        media = _media_file(tmpdir)
        for exception, expected_category in cases:
            service = FakeSpeechToTextService(exception=exception)
            transport = ElevenLabsScribeSDKTransport(client_factory=RecordingClientFactory(service))
            with media.open("rb") as file_obj:
                try:
                    transport.create_transcript(
                        api_key=SECRET_SENTINEL,
                        file_obj=file_obj,
                        parameters={"model_id": ELEVENLABS_SCRIBE_MODEL_ID},
                    )
                except ElevenLabsScribeTransportError as exc:
                    assert exc.category == expected_category
                    _assert_private_values_absent(exc)
                else:
                    raise AssertionError("SDK exception did not become a transport error")
            assert len(service.convert_calls) == 1


def test_retryable_sdk_failures_are_not_retried_by_transport_layer() -> None:
    retryable_cases = [
        FakeApiError(status_code=408, body={}),
        FakeApiError(status_code=429, body={}),
        FakeApiError(status_code=500, body={}),
        FakeTimeoutException(RAW_RESPONSE_SENTINEL),
    ]

    with tempfile.TemporaryDirectory() as tmpdir:
        media = _media_file(tmpdir)
        for exception in retryable_cases:
            service = FakeSpeechToTextService(exception=exception)
            transport = ElevenLabsScribeSDKTransport(client_factory=RecordingClientFactory(service))
            with media.open("rb") as file_obj:
                try:
                    transport.create_transcript(
                        api_key=SECRET_SENTINEL,
                        file_obj=file_obj,
                        parameters={"model_id": ELEVENLABS_SCRIBE_MODEL_ID},
                    )
                except ElevenLabsScribeTransportError as exc:
                    _assert_private_values_absent(exc)
                else:
                    raise AssertionError("retryable SDK failure unexpectedly succeeded")

            assert len(service.convert_calls) == 1
            assert service.convert_calls[0]["request_options"]["max_retries"] == 0  # type: ignore[index]


def test_process_control_exceptions_are_not_swallowed() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        media = _media_file(tmpdir)
        for exception_type in (KeyboardInterrupt, SystemExit, GeneratorExit):
            service = FakeSpeechToTextService(process_exception=exception_type)
            transport = ElevenLabsScribeSDKTransport(client_factory=RecordingClientFactory(service))
            with media.open("rb") as file_obj:
                try:
                    transport.create_transcript(
                        api_key=SECRET_SENTINEL,
                        file_obj=file_obj,
                        parameters={"model_id": ELEVENLABS_SCRIBE_MODEL_ID},
                    )
                except exception_type:
                    pass
                else:
                    raise AssertionError("process-control exception was swallowed")
            assert len(service.convert_calls) == 1


def test_provider_adapter_closes_file_after_sdk_transport_success_and_failure() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        request = ElevenLabsScribeRequest(
            file_path=str(_media_file(tmpdir, name=f"{SENSITIVE_PATH_FRAGMENT}.wav")),
            keyterms=(SENSITIVE_KEYTERM,),
        )

        success_service = FakeSpeechToTextService()
        success_transport = ElevenLabsScribeSDKTransport(
            client_factory=RecordingClientFactory(success_service),
        )
        success = ElevenLabsScribeBatchProvider(transport=success_transport).transcribe(
            request,
            credential=SECRET_SENTINEL,
        )
        assert success.status is ElevenLabsScribeStatus.SUCCEEDED
        assert success_service.file_closed_during_call is False
        _assert_private_values_absent(success)

        failing_service = FakeSpeechToTextService(exception=FakeApiError(status_code=429, body={}))
        failure_transport = ElevenLabsScribeSDKTransport(
            client_factory=RecordingClientFactory(failing_service),
        )
        failure = ElevenLabsScribeBatchProvider(transport=failure_transport).transcribe(
            request,
            credential=SECRET_SENTINEL,
        )
        assert failure.status is ElevenLabsScribeStatus.RATE_LIMITED
        assert failing_service.file_closed_during_call is False
        _assert_private_values_absent(failure)

        malformed_service = FakeSpeechToTextService(response={"transcripts": []})
        malformed_transport = ElevenLabsScribeSDKTransport(
            client_factory=RecordingClientFactory(malformed_service),
        )
        malformed = ElevenLabsScribeBatchProvider(transport=malformed_transport).transcribe(
            request,
            credential=SECRET_SENTINEL,
        )
        assert malformed.status is ElevenLabsScribeStatus.MALFORMED_PROVIDER_RESPONSE
        assert malformed_service.file_closed_during_call is False
        _assert_private_values_absent(malformed)


def test_action_coordinator_composes_sdk_executor_with_secure_and_environment_credentials() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        request = ElevenLabsScribeRequest(file_path=str(_media_file(tmpdir)))

        fake = FakeKeyring()
        _store_secret(fake, SECRET_SENTINEL)
        secure_service = FakeSpeechToTextService()
        secure_executor = create_elevenlabs_scribe_sdk_provider_executor(
            request,
            client_factory=RecordingClientFactory(secure_service),
        )
        secure = ASRProviderActionCoordinator(
            credential_consumer=_consumer(fake=fake),
            executors={
                (
                    ELEVENLABS_SCRIBE_PROVIDER_ID,
                    ASR_PROVIDER_ACTION_TRANSCRIBE,
                ): secure_executor
            },
        ).dispatch_provider_action(ELEVENLABS_SCRIBE_PROVIDER_ID)

        assert secure.status is ASRProviderActionStatus.ACTION_SUCCEEDED
        assert secure.credential_status == CredentialConsumptionStatus.CONSUMED.value
        assert secure.credential_provenance == CredentialConsumptionProvenance.SECURE_KEYRING.value
        assert len(secure_service.convert_calls) == 1
        _assert_private_values_absent(secure)

        env_service = FakeSpeechToTextService()
        env_executor = create_elevenlabs_scribe_sdk_provider_executor(
            request,
            client_factory=RecordingClientFactory(env_service),
        )
        env = ASRProviderActionCoordinator(
            credential_consumer=_consumer(environ={"ELEVENLABS_API_KEY": ALT_SECRET_SENTINEL}),
            executors={
                (
                    ELEVENLABS_SCRIBE_PROVIDER_ID,
                    ASR_PROVIDER_ACTION_TRANSCRIBE,
                ): env_executor
            },
        ).dispatch_provider_action(ELEVENLABS_SCRIBE_PROVIDER_ID)

        assert env.status is ASRProviderActionStatus.ACTION_SUCCEEDED
        assert env.credential_provenance == CredentialConsumptionProvenance.ENVIRONMENT_VARIABLE.value
        assert len(env_service.convert_calls) == 1
        _assert_private_values_absent(env)


def test_validation_and_missing_executor_fail_before_client_factory() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        missing_media = Path(tmpdir) / "missing.wav"
        factory = RecordingClientFactory()
        try:
            ElevenLabsScribeRequest(file_path=str(missing_media))
        except Exception:
            pass
        else:
            raise AssertionError("invalid request unexpectedly constructed")
        assert factory.calls == []

        request = ElevenLabsScribeRequest(file_path=str(_media_file(tmpdir)))
        executor = create_elevenlabs_scribe_sdk_provider_executor(
            request,
            client_factory=factory,
        )
        result = ASRProviderActionCoordinator(
            credential_consumer=_consumer(environ={"ELEVENLABS_API_KEY": SECRET_SENTINEL}),
            executors={},
        ).dispatch_provider_action(ELEVENLABS_SCRIBE_PROVIDER_ID)

        assert result.status is ASRProviderActionStatus.EXECUTOR_MISSING
        assert factory.calls == []
        assert callable(executor)
        _assert_private_values_absent(result)


def test_transport_parameter_rejection_happens_before_client_factory() -> None:
    factory = RecordingClientFactory()
    transport = ElevenLabsScribeSDKTransport(client_factory=factory)
    with tempfile.TemporaryDirectory() as tmpdir:
        media = _media_file(tmpdir)
        with media.open("rb") as file_obj:
            try:
                transport.create_transcript(
                    api_key=SECRET_SENTINEL,
                    file_obj=file_obj,
                    parameters={
                        "model_id": ELEVENLABS_SCRIBE_MODEL_ID,
                        "source_url": "https://example.invalid/media.mp3",
                    },
                )
            except ElevenLabsScribeTransportError as exc:
                assert exc.category == "provider_validation_error"
            else:
                raise AssertionError("invalid transport parameter set accepted")
    assert factory.calls == []


def test_transport_does_not_reopen_close_or_duplicate_read_file_object() -> None:
    class GuardedFile:
        name = f"{SENSITIVE_PATH_FRAGMENT}.wav"
        closed = False

        def read(self, *args: object, **kwargs: object) -> bytes:
            raise AssertionError("transport should not read the media file itself")

        def close(self) -> None:
            raise AssertionError("transport should not close caller-owned handle")

    service = FakeSpeechToTextService(response={"text": "ok"})
    transport = ElevenLabsScribeSDKTransport(client_factory=RecordingClientFactory(service))
    response = transport.create_transcript(
        api_key=SECRET_SENTINEL,
        file_obj=GuardedFile(),  # type: ignore[arg-type]
        parameters={"model_id": ELEVENLABS_SCRIBE_MODEL_ID},
    )

    assert response == {"text": "ok"}
    assert service.convert_calls[0]["file"].name == GuardedFile.name


def run_all_tests() -> None:
    test_static_lazy_sdk_import_and_no_logging_or_direct_network()
    test_dependency_declarations_include_official_sdk_range()
    test_transport_construction_does_not_load_sdk_or_create_client()
    test_transport_constructor_rejects_invalid_timeout_and_retry_options()
    test_missing_sdk_maps_to_dependency_unavailable_without_raw_import_text()
    test_internal_import_bug_is_not_reported_as_missing_sdk()
    test_arbitrary_sdk_import_error_is_not_reported_as_missing_dependency()
    test_exact_sdk_call_mapping_and_request_options()
    test_unset_options_are_omitted_and_convert_called_once_per_invocation()
    test_build_convert_kwargs_rejects_unsupported_and_invalid_parameters_before_sdk_call()
    test_build_convert_kwargs_rejects_invalid_timeout_and_retry_options()
    test_sdk_model_and_plain_mapping_response_conversion()
    test_sdk_response_enum_values_are_normalized_to_plain_values()
    test_unexpected_response_shapes_are_rejected_safely()
    test_structured_sdk_error_mapping_and_no_raw_leakage()
    test_retryable_sdk_failures_are_not_retried_by_transport_layer()
    test_process_control_exceptions_are_not_swallowed()
    test_provider_adapter_closes_file_after_sdk_transport_success_and_failure()
    test_action_coordinator_composes_sdk_executor_with_secure_and_environment_credentials()
    test_validation_and_missing_executor_fail_before_client_factory()
    test_transport_parameter_rejection_happens_before_client_factory()
    test_transport_does_not_reopen_close_or_duplicate_read_file_object()


if __name__ == "__main__":
    run_all_tests()
    print("ElevenLabs Scribe SDK transport self-test passed.")
