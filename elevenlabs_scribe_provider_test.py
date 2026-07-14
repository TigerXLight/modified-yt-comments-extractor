from __future__ import annotations

import ast
import json
import tempfile
from dataclasses import asdict, is_dataclass
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
    ELEVENLABS_SCRIBE_API_KEY_HEADER,
    ELEVENLABS_SCRIBE_ENDPOINT_PATH,
    ELEVENLABS_SCRIBE_MODEL_ID,
    ELEVENLABS_SCRIBE_PROVIDER_ID,
    KEYTERM_MAX_CHARACTERS,
    KEYTERM_MAX_COUNT,
    MAX_LOCAL_FILE_BYTES,
    MAX_SPEAKER_COUNT,
    TIMESTAMPS_CHARACTER,
    TIMESTAMPS_NONE,
    TIMESTAMPS_WORD,
    ElevenLabsScribeBatchProvider,
    ElevenLabsScribeRequest,
    ElevenLabsScribeStatus,
    ElevenLabsScribeTransportError,
    ElevenLabsScribeValidationError,
    create_elevenlabs_scribe_provider_executor,
    normalize_elevenlabs_scribe_response,
    normalize_keyterms,
)


SECRET_SENTINEL = "SCRIBE-SECRET-MUST-NOT-LEAK"
ALT_SECRET_SENTINEL = "SCRIBE-ALT-SECRET-MUST-NOT-LEAK"
SENSITIVE_KEYTERM = "SensitiveKeytermMustNotLeak"
SENSITIVE_PATH_FRAGMENT = "sensitive_path_fragment_must_not_leak"
MEDIA_SENTINEL = b"fake media bytes only"


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


class FakeTransport:
    def __init__(
        self,
        *,
        response: Mapping[str, object] | None = None,
        error_category: str = "",
        process_exception: type[BaseException] | None = None,
        ordinary_exception: bool = False,
    ) -> None:
        self.response = response if response is not None else _valid_response()
        self.error_category = error_category
        self.process_exception = process_exception
        self.ordinary_exception = ordinary_exception
        self.calls: list[dict[str, object]] = []
        self.file_closed_during_call: bool | None = None
        self.last_file_obj: BinaryIO | None = None

    def create_transcript(
        self,
        *,
        api_key: str,
        file_obj: BinaryIO,
        parameters: Mapping[str, object],
    ) -> Mapping[str, object]:
        self.file_closed_during_call = file_obj.closed
        self.last_file_obj = file_obj
        self.calls.append(
            {
                "api_key": api_key,
                "parameters": dict(parameters),
                "file_name": Path(getattr(file_obj, "name", "")).name,
            }
        )
        if self.process_exception is not None:
            raise self.process_exception()
        if self.ordinary_exception:
            raise RuntimeError(SECRET_SENTINEL)
        if self.error_category:
            raise ElevenLabsScribeTransportError(self.error_category)
        return self.response


def _valid_response() -> dict[str, object]:
    return {
        "language_code": "en",
        "language_probability": 0.98,
        "text": "Hello world!",
        "words": [
            {
                "text": "Hello",
                "start": 0,
                "end": 0.5,
                "type": "word",
                "speaker_id": "speaker_1",
            },
            {
                "text": "(laughter)",
                "start": 0.6,
                "end": 0.7,
                "type": "audio_event",
                "speaker_id": "speaker_1",
            },
        ],
    }


def _media_file(tmpdir: str, name: str = "sample.wav") -> Path:
    path = Path(tmpdir) / name
    path.write_bytes(MEDIA_SENTINEL)
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


def _assert_no_secret_or_raw_body(value: object) -> None:
    blob = repr(value)
    if hasattr(value, "to_dict"):
        blob += json.dumps(value.to_dict(), sort_keys=True)
    if hasattr(value, "to_safe_dict"):
        blob += json.dumps(value.to_safe_dict(), sort_keys=True)
    elif is_dataclass(value):
        blob += json.dumps(asdict(value), sort_keys=True)
    else:
        blob += str(value)
    forbidden = (
        SECRET_SENTINEL,
        ALT_SECRET_SENTINEL,
        SENSITIVE_KEYTERM,
        SENSITIVE_PATH_FRAGMENT,
        MEDIA_SENTINEL.decode("ascii"),
        "traceback",
        "request_payload",
    )
    for item in forbidden:
        if item in blob:
            raise AssertionError("secret or raw provider detail leaked")


def test_static_no_network_sdk_or_logging_imports() -> None:
    tree = ast.parse(Path("elevenlabs_scribe_provider.py").read_text(encoding="utf-8"))
    forbidden_import_roots = {
        "requests",
        "httpx",
        "urllib",
        "socket",
        "aiohttp",
        "elevenlabs",
        "logging",
    }
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported = {alias.name.split(".")[0] for alias in node.names}
            assert not (imported & forbidden_import_roots)
        if isinstance(node, ast.ImportFrom) and node.module:
            assert node.module.split(".")[0] not in forbidden_import_roots
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id != "print"


def test_request_validation_and_safe_dict() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        media = _media_file(tmpdir, name=f"{SENSITIVE_PATH_FRAGMENT}.wav")
        request = ElevenLabsScribeRequest(
            file_path=str(media),
            language_code=" eng ",
            keyterms=(f" {SENSITIVE_KEYTERM} ", SENSITIVE_KEYTERM.casefold(), "specialist term"),
            diarize=True,
            num_speakers=2,
            tag_audio_events=False,
            timestamps_granularity="character",
        )

        if request.file_path != str(media):
            raise AssertionError("request did not retain the trusted internal file path")
        if request.keyterms != (SENSITIVE_KEYTERM, "specialist term"):
            raise AssertionError("request did not normalize trusted internal keyterms")

        safe_request = request.to_safe_dict()
        serialized_safe_request = json.dumps(safe_request, sort_keys=True)
        request_repr = repr(request)
        for forbidden in (str(media), media.name, SENSITIVE_PATH_FRAGMENT, SENSITIVE_KEYTERM):
            if forbidden in request_repr or forbidden in serialized_safe_request:
                raise AssertionError("request safe representation leaked sensitive input metadata")
        try:
            asdict(request)  # type: ignore[arg-type]
        except TypeError:
            pass
        else:
            raise AssertionError("request unexpectedly supports dataclass serialization")

        assert safe_request["file_selected"] is True
        assert safe_request["language_code_set"] is True
        assert safe_request["keyterm_count"] == 2
        assert safe_request["num_speakers_set"] is True
        assert "file_path" not in safe_request
        assert "file_name" not in safe_request
        assert "language_code" not in safe_request
        assert "num_speakers" not in safe_request
        params = request.to_transport_parameters()
        assert params["model_id"] == ELEVENLABS_SCRIBE_MODEL_ID
        assert params["language_code"] == "eng"
        if params["keyterms"] != [SENSITIVE_KEYTERM, "specialist term"]:
            raise AssertionError("trusted transport parameters did not include normalized keyterms")
        assert params["num_speakers"] == 2
        assert params["tag_audio_events"] is False
        assert params["diarize"] is True
        assert params["timestamps_granularity"] == "character"
        assert "source_url" not in params
        assert "webhook" not in params
        assert ELEVENLABS_SCRIBE_ENDPOINT_PATH == "/v1/speech-to-text"
        assert ELEVENLABS_SCRIBE_API_KEY_HEADER == "xi-api-key"


def test_invalid_paths_language_keyterms_and_speaker_counts() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        media = _media_file(tmpdir)
        directory = Path(tmpdir) / "folder"
        directory.mkdir()

        invalid_specs = [
            {"file_path": ""},
            {"file_path": str(Path(tmpdir) / "missing.wav")},
            {"file_path": str(directory)},
            {"file_path": str(media), "language_code": "english"},
            {"file_path": str(media), "timestamps_granularity": "sentence"},
            {"file_path": str(media), "num_speakers": 0},
            {"file_path": str(media), "num_speakers": MAX_SPEAKER_COUNT + 1},
            {"file_path": str(media), "num_speakers": True},
            {"file_path": str(media), "keyterms": ("",)},
            {"file_path": str(media), "keyterms": ("   ",)},
            {"file_path": str(media), "keyterms": (123,)},
            {"file_path": str(media), "keyterms": ("one two three four five six",)},
            {"file_path": str(media), "keyterms": ("bad<term",)},
            {"file_path": str(media), "keyterms": ("x" * (KEYTERM_MAX_CHARACTERS + 1),)},
        ]

        for spec in invalid_specs:
            try:
                ElevenLabsScribeRequest(**spec)  # type: ignore[arg-type]
            except ElevenLabsScribeValidationError as exc:
                _assert_no_secret_or_raw_body(exc)
            else:
                raise AssertionError("invalid request accepted")

        speaker_request = ElevenLabsScribeRequest(
            file_path=str(media),
            num_speakers=2,
            diarize=False,
        )
        speaker_params = speaker_request.to_transport_parameters()
        assert speaker_params["num_speakers"] == 2
        assert "diarize" not in speaker_params

        original_stat = Path.stat

        class FakeStat:
            st_size = MAX_LOCAL_FILE_BYTES
            st_mode = 0o100000

        try:
            Path.stat = lambda self: FakeStat()  # type: ignore[method-assign]
            try:
                ElevenLabsScribeRequest(file_path=str(media))
            except ElevenLabsScribeValidationError as exc:
                assert str(exc) == "file_too_large"
            else:
                raise AssertionError("oversized local file was accepted")
        finally:
            Path.stat = original_stat  # type: ignore[method-assign]


def test_timestamp_granularity_parameters_are_supported() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        media = _media_file(tmpdir)

        word_request = ElevenLabsScribeRequest(
            file_path=str(media),
            timestamps_granularity=TIMESTAMPS_WORD,
        )
        none_request = ElevenLabsScribeRequest(
            file_path=str(media),
            timestamps_granularity=TIMESTAMPS_NONE,
        )
        character_request = ElevenLabsScribeRequest(
            file_path=str(media),
            timestamps_granularity=TIMESTAMPS_CHARACTER,
        )

        assert "timestamps_granularity" not in word_request.to_transport_parameters()
        assert none_request.to_transport_parameters()["timestamps_granularity"] == TIMESTAMPS_NONE
        assert character_request.to_transport_parameters()["timestamps_granularity"] == TIMESTAMPS_CHARACTER


def test_keyterm_boundary_cases() -> None:
    near_boundary = "x" * (KEYTERM_MAX_CHARACTERS - 1)
    exact_boundary = "x" * KEYTERM_MAX_CHARACTERS
    too_long = "x" * (KEYTERM_MAX_CHARACTERS + 1)
    combining_boundary = "e\u0301" * (KEYTERM_MAX_CHARACTERS // 2)
    five_words = "one two three four five"

    assert normalize_keyterms((near_boundary,)) == (near_boundary,)
    assert normalize_keyterms((exact_boundary,)) == (exact_boundary,)
    assert normalize_keyterms((combining_boundary,)) == (combining_boundary,)
    assert normalize_keyterms((five_words,)) == (five_words,)

    try:
        normalize_keyterms((too_long,))
    except ElevenLabsScribeValidationError as exc:
        assert str(exc) == "keyterm_too_long"
    else:
        raise AssertionError("overlong keyterm was accepted")

    unicode_terms = normalize_keyterms(("Nyxara", "Caltheris", "Nyxara", "\u540d\u8a5e"))
    if unicode_terms != ("Nyxara", "Caltheris", "\u540d\u8a5e"):
        raise AssertionError("unicode keyterm normalization did not preserve first occurrence order")

    at_count_boundary = tuple(f"term{i}" for i in range(KEYTERM_MAX_COUNT))
    assert len(normalize_keyterms(at_count_boundary)) == KEYTERM_MAX_COUNT

    too_many = tuple(f"term{i}" for i in range(KEYTERM_MAX_COUNT + 1))
    try:
        normalize_keyterms(too_many)
    except ElevenLabsScribeValidationError as exc:
        assert str(exc) == "too_many_keyterms"
    else:
        raise AssertionError("too many keyterms were accepted")


def test_no_construction_time_file_open_or_transport_call() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        media = _media_file(tmpdir)
        transport = FakeTransport()
        provider = ElevenLabsScribeBatchProvider(transport=transport)
        request = ElevenLabsScribeRequest(file_path=str(media))

        assert repr(provider) == "ElevenLabsScribeBatchProvider()"
        assert transport.calls == []
        assert request.to_safe_dict()["keyterm_count"] == 0


def test_fake_transport_called_once_with_exact_parameters_and_closes_file() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        media = _media_file(tmpdir)
        request = ElevenLabsScribeRequest(
            file_path=str(media),
            keyterms=(SENSITIVE_KEYTERM,),
            diarize=True,
            num_speakers=3,
        )
        transport = FakeTransport()
        result = ElevenLabsScribeBatchProvider(transport=transport).transcribe(
            request,
            credential=SECRET_SENTINEL,
        )

        assert result.status is ElevenLabsScribeStatus.SUCCEEDED
        assert len(transport.calls) == 1
        if transport.calls[0]["api_key"] != SECRET_SENTINEL:
            raise AssertionError("credential was not supplied only to the trusted transport")
        assert transport.calls[0]["parameters"]["model_id"] == ELEVENLABS_SCRIBE_MODEL_ID
        if transport.calls[0]["parameters"]["keyterms"] != [SENSITIVE_KEYTERM]:
            raise AssertionError("trusted transport parameters did not include the normalized keyterm")
        assert transport.file_closed_during_call is False
        assert transport.last_file_obj is not None and transport.last_file_obj.closed
        _assert_no_secret_or_raw_body(result)


def test_file_handle_closes_after_failure_and_process_control_reraises() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        request = ElevenLabsScribeRequest(file_path=str(_media_file(tmpdir)))
        failing = FakeTransport(ordinary_exception=True)
        result = ElevenLabsScribeBatchProvider(transport=failing).transcribe(
            request,
            credential=SECRET_SENTINEL,
        )
        assert result.status is ElevenLabsScribeStatus.UNKNOWN_PROVIDER_FAILURE
        assert failing.last_file_obj is not None and failing.last_file_obj.closed
        _assert_no_secret_or_raw_body(result)

        malformed = FakeTransport(response={})
        malformed_result = ElevenLabsScribeBatchProvider(transport=malformed).transcribe(
            request,
            credential=SECRET_SENTINEL,
        )
        assert malformed_result.status is ElevenLabsScribeStatus.MALFORMED_PROVIDER_RESPONSE
        assert malformed.last_file_obj is not None and malformed.last_file_obj.closed
        _assert_no_secret_or_raw_body(malformed_result)

        for exception_type in (KeyboardInterrupt, SystemExit, GeneratorExit):
            transport = FakeTransport(process_exception=exception_type)
            try:
                ElevenLabsScribeBatchProvider(transport=transport).transcribe(
                    request,
                    credential=SECRET_SENTINEL,
                )
            except exception_type:
                assert transport.last_file_obj is not None and transport.last_file_obj.closed
            else:
                raise AssertionError("process-control exception was swallowed")


def test_response_normalization_success_and_optional_fields() -> None:
    result = normalize_elevenlabs_scribe_response(_valid_response())

    assert result.status is ElevenLabsScribeStatus.SUCCEEDED
    assert result.text == "Hello world!"
    assert result.language_code == "en"
    assert result.language_probability == 0.98
    assert len(result.words) == 2
    assert result.words[0].text == "Hello"
    assert result.words[0].start == 0.0
    assert result.words[0].end == 0.5
    assert result.words[0].speaker_id == "speaker_1"
    assert result.words[1].word_type == "audio_event"
    _assert_no_secret_or_raw_body(result)

    minimal = normalize_elevenlabs_scribe_response({"text": ""})
    assert minimal.status is ElevenLabsScribeStatus.SUCCEEDED
    assert minimal.language_code == ""
    assert minimal.language_probability is None
    assert minimal.words == ()

    no_timing = normalize_elevenlabs_scribe_response(
        {"text": "No timing", "words": [{"text": "No"}, {"text": "timing"}]}
    )
    assert no_timing.status is ElevenLabsScribeStatus.SUCCEEDED
    assert no_timing.words[0].start is None
    assert no_timing.words[1].end is None


def test_malformed_response_shapes_are_rejected() -> None:
    malformed_responses = [
        {},
        {"text": 123},
        {"text": "ok", "words": {}},
        {"text": "ok", "language_probability": float("nan")},
        {"text": "ok", "language_probability": True},
        {"text": "ok", "words": [{"text": "x", "start": -1, "end": 2}]},
        {"text": "ok", "words": [{"text": "x", "start": 2, "end": 1}]},
        {"text": "ok", "words": [{"text": "x", "start": True, "end": 1}]},
        {"text": "ok", "words": [{"text": 2}]},
        {"transcripts": []},
        {"transcript_id": "async-job"},
    ]

    for response in malformed_responses:
        result = normalize_elevenlabs_scribe_response(response)
        assert result.status is ElevenLabsScribeStatus.MALFORMED_PROVIDER_RESPONSE
        _assert_no_secret_or_raw_body(result)


def test_transport_error_mapping() -> None:
    categories = {
        "authentication_rejected": ElevenLabsScribeStatus.AUTHENTICATION_REJECTED,
        "permission_denied": ElevenLabsScribeStatus.PERMISSION_DENIED,
        "rate_limited": ElevenLabsScribeStatus.RATE_LIMITED,
        "quota_or_billing_blocked": ElevenLabsScribeStatus.QUOTA_OR_BILLING_BLOCKED,
        "request_too_large": ElevenLabsScribeStatus.REQUEST_TOO_LARGE,
        "unsupported_media": ElevenLabsScribeStatus.UNSUPPORTED_MEDIA,
        "provider_validation_error": ElevenLabsScribeStatus.PROVIDER_VALIDATION_ERROR,
        "provider_service_unavailable": ElevenLabsScribeStatus.PROVIDER_SERVICE_UNAVAILABLE,
        "timeout": ElevenLabsScribeStatus.TIMEOUT,
        "cancelled": ElevenLabsScribeStatus.CANCELLED,
        "unexpected": ElevenLabsScribeStatus.UNKNOWN_PROVIDER_FAILURE,
    }
    with tempfile.TemporaryDirectory() as tmpdir:
        request = ElevenLabsScribeRequest(file_path=str(_media_file(tmpdir)))
        for category, expected_status in categories.items():
            result = ElevenLabsScribeBatchProvider(
                transport=FakeTransport(error_category=category),
            ).transcribe(request, credential=SECRET_SENTINEL)
            assert result.status is expected_status
            _assert_no_secret_or_raw_body(result)


def test_transport_unavailable_and_blank_credential_are_safe_failures() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        request = ElevenLabsScribeRequest(file_path=str(_media_file(tmpdir)))
        unavailable = ElevenLabsScribeBatchProvider().transcribe(
            request,
            credential=SECRET_SENTINEL,
        )
        blank = ElevenLabsScribeBatchProvider(transport=FakeTransport()).transcribe(
            request,
            credential=" ",
        )

        assert unavailable.status is ElevenLabsScribeStatus.TRANSPORT_UNAVAILABLE
        assert unavailable.transport_called is False
        assert blank.status is ElevenLabsScribeStatus.AUTHENTICATION_REJECTED
        assert blank.transport_called is False
        _assert_no_secret_or_raw_body(unavailable)
        _assert_no_secret_or_raw_body(blank)


def test_action_coordinator_integration_secure_and_environment_credentials() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        request = ElevenLabsScribeRequest(file_path=str(_media_file(tmpdir)))

        fake = FakeKeyring()
        _store_secret(fake, SECRET_SENTINEL)
        secure_transport = FakeTransport()
        secure_executor = create_elevenlabs_scribe_provider_executor(
            request,
            transport=secure_transport,
        )
        secure_result = ASRProviderActionCoordinator(
            credential_consumer=_consumer(fake=fake),
            executors={
                (
                    ELEVENLABS_SCRIBE_PROVIDER_ID,
                    ASR_PROVIDER_ACTION_TRANSCRIBE,
                ): secure_executor
            },
        ).dispatch_provider_action(ELEVENLABS_SCRIBE_PROVIDER_ID)

        assert secure_result.status is ASRProviderActionStatus.ACTION_SUCCEEDED
        assert secure_result.credential_status == CredentialConsumptionStatus.CONSUMED.value
        assert secure_result.credential_provenance == CredentialConsumptionProvenance.SECURE_KEYRING.value
        if secure_transport.calls[0]["api_key"] != SECRET_SENTINEL:
            raise AssertionError("secure credential was not supplied only to the trusted executor")
        _assert_no_secret_or_raw_body(secure_result)

        env_transport = FakeTransport()
        env_executor = create_elevenlabs_scribe_provider_executor(
            request,
            transport=env_transport,
        )
        env_result = ASRProviderActionCoordinator(
            credential_consumer=_consumer(environ={"ELEVENLABS_API_KEY": ALT_SECRET_SENTINEL}),
            executors={
                (
                    ELEVENLABS_SCRIBE_PROVIDER_ID,
                    ASR_PROVIDER_ACTION_TRANSCRIBE,
                ): env_executor
            },
        ).dispatch_provider_action(ELEVENLABS_SCRIBE_PROVIDER_ID)

        assert env_result.status is ASRProviderActionStatus.ACTION_SUCCEEDED
        assert env_result.credential_provenance == CredentialConsumptionProvenance.ENVIRONMENT_VARIABLE.value
        if env_transport.calls[0]["api_key"] != ALT_SECRET_SENTINEL:
            raise AssertionError("environment credential was not supplied only to the trusted executor")
        _assert_no_secret_or_raw_body(env_result)


def test_invalid_secure_value_missing_credentials_and_executor_fail_before_upload() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        request = ElevenLabsScribeRequest(file_path=str(_media_file(tmpdir)))
        transport = FakeTransport()
        executor = create_elevenlabs_scribe_provider_executor(request, transport=transport)

        fake = FakeKeyring()
        _store_secret(fake, "   ")
        invalid = ASRProviderActionCoordinator(
            credential_consumer=_consumer(
                fake=fake,
                environ={"ELEVENLABS_API_KEY": ALT_SECRET_SENTINEL},
            ),
            executors={
                (
                    ELEVENLABS_SCRIBE_PROVIDER_ID,
                    ASR_PROVIDER_ACTION_TRANSCRIBE,
                ): executor
            },
        ).dispatch_provider_action(ELEVENLABS_SCRIBE_PROVIDER_ID)

        assert invalid.status is ASRProviderActionStatus.CREDENTIAL_UNAVAILABLE
        assert invalid.safe_diagnostic == "invalid_secure_credential_value"
        assert transport.calls == []
        _assert_no_secret_or_raw_body(invalid)

        missing = ASRProviderActionCoordinator(
            credential_consumer=_consumer(),
            executors={
                (
                    ELEVENLABS_SCRIBE_PROVIDER_ID,
                    ASR_PROVIDER_ACTION_TRANSCRIBE,
                ): executor
            },
        ).dispatch_provider_action(ELEVENLABS_SCRIBE_PROVIDER_ID)
        assert missing.status is ASRProviderActionStatus.CREDENTIAL_UNAVAILABLE
        assert transport.calls == []
        _assert_no_secret_or_raw_body(missing)

        no_executor = ASRProviderActionCoordinator(
            credential_consumer=_consumer(environ={"ELEVENLABS_API_KEY": ALT_SECRET_SENTINEL}),
            executors={},
        ).dispatch_provider_action(ELEVENLABS_SCRIBE_PROVIDER_ID)
        assert no_executor.status is ASRProviderActionStatus.EXECUTOR_MISSING
        assert transport.calls == []
        _assert_no_secret_or_raw_body(no_executor)


def test_pattern_adjacent_youtube_and_unsupported_actions_rejected_before_credential_lookup() -> None:
    fake = FakeKeyring()
    result_unknown = ASRProviderActionCoordinator(
        credential_consumer=_consumer(fake=fake),
        executors={},
    ).dispatch_provider_action("elevenlabs_scribe_extra")
    result_youtube = ASRProviderActionCoordinator(
        credential_consumer=_consumer(fake=fake),
        executors={},
    ).dispatch_provider_action("youtube_data_api_key")
    result_unsupported = ASRProviderActionCoordinator(
        credential_consumer=_consumer(fake=fake),
        executors={},
    ).dispatch_provider_action(ELEVENLABS_SCRIBE_PROVIDER_ID, action_kind="connection_test")

    assert result_unknown.status is ASRProviderActionStatus.UNKNOWN_PROVIDER
    assert result_youtube.status is ASRProviderActionStatus.YOUTUBE_PROVIDER_REJECTED
    assert result_unsupported.status is ASRProviderActionStatus.UNSUPPORTED_ACTION
    assert fake.calls == []
    for result in (result_unknown, result_youtube, result_unsupported):
        _assert_no_secret_or_raw_body(result)


def run_all_tests() -> None:
    test_static_no_network_sdk_or_logging_imports()
    test_request_validation_and_safe_dict()
    test_invalid_paths_language_keyterms_and_speaker_counts()
    test_timestamp_granularity_parameters_are_supported()
    test_keyterm_boundary_cases()
    test_no_construction_time_file_open_or_transport_call()
    test_fake_transport_called_once_with_exact_parameters_and_closes_file()
    test_file_handle_closes_after_failure_and_process_control_reraises()
    test_response_normalization_success_and_optional_fields()
    test_malformed_response_shapes_are_rejected()
    test_transport_error_mapping()
    test_transport_unavailable_and_blank_credential_are_safe_failures()
    test_action_coordinator_integration_secure_and_environment_credentials()
    test_invalid_secure_value_missing_credentials_and_executor_fail_before_upload()
    test_pattern_adjacent_youtube_and_unsupported_actions_rejected_before_credential_lookup()


if __name__ == "__main__":
    run_all_tests()
    print("ElevenLabs Scribe provider self-test passed.")
