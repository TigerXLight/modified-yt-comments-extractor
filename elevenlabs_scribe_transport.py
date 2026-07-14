from __future__ import annotations

import importlib
from collections.abc import Mapping
from enum import Enum
from typing import BinaryIO, Callable

from asr_provider_action import TrustedProviderExecutor
from elevenlabs_scribe_provider import (
    ELEVENLABS_SCRIBE_MODEL_ID,
    ElevenLabsScribeRequest,
    ElevenLabsScribeTransportError,
    create_elevenlabs_scribe_provider_executor,
)


ELEVENLABS_SDK_PACKAGE_NAME = "elevenlabs"
ELEVENLABS_SDK_VERSION_SPEC = "elevenlabs>=2.58.0,<3"
ELEVENLABS_SDK_DEFAULT_TIMEOUT_SECONDS = 240
ELEVENLABS_SDK_MAX_RETRIES = 0

_SUPPORTED_TRANSPORT_PARAMETERS = frozenset(
    {
        "model_id",
        "language_code",
        "tag_audio_events",
        "diarize",
        "num_speakers",
        "timestamps_granularity",
        "keyterms",
    }
)
_QUOTA_OR_BILLING_CODES = frozenset(
    {
        "billing_hard_limit_reached",
        "billing_limit_reached",
        "insufficient_quota",
        "monthly_limit_exceeded",
        "quota_exceeded",
        "quota_or_billing_blocked",
    }
)
_UNSUPPORTED_MEDIA_CODES = frozenset(
    {
        "invalid_audio_file",
        "invalid_file",
        "invalid_file_format",
        "unsupported_file",
        "unsupported_file_format",
        "unsupported_media",
    }
)

SDKClientFactory = Callable[[str, int], object]
SDKLoader = Callable[[], object]


class ElevenLabsScribeSDKTransport:
    """ElevenLabs SDK-backed Scribe transport.

    The official SDK client is trusted third-party provider code. It is
    constructed only for an explicit transcription invocation and is not a
    credential sandbox.
    """

    def __init__(
        self,
        *,
        client_factory: SDKClientFactory | None = None,
        sdk_loader: SDKLoader | None = None,
        timeout_seconds: int = ELEVENLABS_SDK_DEFAULT_TIMEOUT_SECONDS,
        max_retries: int = ELEVENLABS_SDK_MAX_RETRIES,
    ) -> None:
        self._timeout_seconds = _validate_timeout_seconds(timeout_seconds)
        self._max_retries = _validate_max_retries(max_retries)
        self._client_factory = client_factory
        self._sdk_loader = sdk_loader

    def __repr__(self) -> str:
        return "ElevenLabsScribeSDKTransport()"

    @property
    def timeout_seconds(self) -> int:
        return self._timeout_seconds

    @property
    def max_retries(self) -> int:
        return self._max_retries

    def create_transcript(
        self,
        *,
        api_key: str,
        file_obj: BinaryIO,
        parameters: Mapping[str, object],
    ) -> Mapping[str, object]:
        if not str(api_key or "").strip():
            raise ElevenLabsScribeTransportError("authentication_rejected")

        kwargs = build_elevenlabs_scribe_sdk_convert_kwargs(
            file_obj=file_obj,
            parameters=parameters,
            timeout_seconds=self._timeout_seconds,
            max_retries=self._max_retries,
        )
        client = self._create_client(api_key)
        try:
            response = client.speech_to_text.convert(**kwargs)
        except (KeyboardInterrupt, SystemExit, GeneratorExit):
            raise
        except Exception as exc:
            raise ElevenLabsScribeTransportError(_transport_category_from_exception(exc)) from None
        return sdk_response_to_provider_mapping(response)

    def _create_client(self, api_key: str) -> object:
        if self._client_factory is not None:
            try:
                return self._client_factory(api_key, self._timeout_seconds)
            except (KeyboardInterrupt, SystemExit, GeneratorExit):
                raise
            except ModuleNotFoundError as exc:
                if exc.name == ELEVENLABS_SDK_PACKAGE_NAME:
                    raise ElevenLabsScribeTransportError("dependency_unavailable") from None
                raise
            except ElevenLabsScribeTransportError:
                raise
            except Exception:
                raise ElevenLabsScribeTransportError("unknown_provider_failure") from None

        sdk_client_class = _load_official_elevenlabs_client(self._sdk_loader)
        return sdk_client_class(api_key=api_key, timeout=self._timeout_seconds)


def build_elevenlabs_scribe_sdk_convert_kwargs(
    *,
    file_obj: BinaryIO,
    parameters: Mapping[str, object],
    timeout_seconds: int = ELEVENLABS_SDK_DEFAULT_TIMEOUT_SECONDS,
    max_retries: int = ELEVENLABS_SDK_MAX_RETRIES,
) -> dict[str, object]:
    try:
        timeout_seconds = _validate_timeout_seconds(timeout_seconds)
        max_retries = _validate_max_retries(max_retries)
    except ValueError:
        raise ElevenLabsScribeTransportError("provider_validation_error") from None

    if not isinstance(parameters, Mapping):
        raise ElevenLabsScribeTransportError("provider_validation_error")
    unknown_keys = set(parameters) - _SUPPORTED_TRANSPORT_PARAMETERS
    if unknown_keys:
        raise ElevenLabsScribeTransportError("provider_validation_error")
    if parameters.get("model_id") != ELEVENLABS_SCRIBE_MODEL_ID:
        raise ElevenLabsScribeTransportError("provider_validation_error")
    kwargs: dict[str, object] = {
        "file": file_obj,
        "model_id": ELEVENLABS_SCRIBE_MODEL_ID,
        "request_options": {
            "max_retries": ELEVENLABS_SDK_MAX_RETRIES,
            "timeout_in_seconds": timeout_seconds,
        },
    }
    for key in (
        "language_code",
        "tag_audio_events",
        "diarize",
        "num_speakers",
        "timestamps_granularity",
    ):
        if key in parameters:
            value = parameters[key]
            if value is None:
                raise ElevenLabsScribeTransportError("provider_validation_error")
            kwargs[key] = value
    if "keyterms" in parameters:
        keyterms = parameters["keyterms"]
        if not isinstance(keyterms, list) or not all(isinstance(item, str) for item in keyterms):
            raise ElevenLabsScribeTransportError("provider_validation_error")
        kwargs["keyterms"] = list(keyterms)
    if isinstance(kwargs.get("num_speakers"), bool):
        raise ElevenLabsScribeTransportError("provider_validation_error")
    return kwargs


def sdk_response_to_provider_mapping(response: object) -> Mapping[str, object]:
    data = _sdk_model_to_mapping(response)
    if data is None:
        raise ElevenLabsScribeTransportError("malformed_provider_response")
    if "transcripts" in data:
        raise ElevenLabsScribeTransportError("malformed_provider_response")
    if data.get("webhook") is True or ("transcript_id" in data and "text" not in data):
        raise ElevenLabsScribeTransportError("malformed_provider_response")

    text = _sdk_plain_value(data.get("text"))
    if not isinstance(text, str):
        raise ElevenLabsScribeTransportError("malformed_provider_response")
    result: dict[str, object] = {"text": text}
    if "language_code" in data:
        result["language_code"] = _sdk_plain_value(data["language_code"])
    if "language_probability" in data:
        result["language_probability"] = _sdk_plain_value(data["language_probability"])
    if "words" in data:
        words = data["words"]
        if words is None:
            result["words"] = []
        elif isinstance(words, list):
            converted_words: list[dict[str, object]] = []
            for item in words:
                word = _sdk_model_to_mapping(item)
                if word is None:
                    raise ElevenLabsScribeTransportError("malformed_provider_response")
                converted_words.append(
                    {
                        key: _sdk_plain_value(word[key])
                        for key in ("text", "start", "end", "type", "speaker_id")
                        if key in word
                    }
                )
            result["words"] = converted_words
        else:
            raise ElevenLabsScribeTransportError("malformed_provider_response")
    return result


def create_elevenlabs_scribe_sdk_provider_executor(
    request: ElevenLabsScribeRequest,
    *,
    transport: ElevenLabsScribeSDKTransport | None = None,
    client_factory: SDKClientFactory | None = None,
) -> TrustedProviderExecutor:
    sdk_transport = transport or ElevenLabsScribeSDKTransport(client_factory=client_factory)
    return create_elevenlabs_scribe_provider_executor(request, transport=sdk_transport)


def _load_official_elevenlabs_client(sdk_loader: SDKLoader | None) -> object:
    try:
        module = sdk_loader() if sdk_loader is not None else importlib.import_module("elevenlabs.client")
    except ModuleNotFoundError as exc:
        if exc.name == ELEVENLABS_SDK_PACKAGE_NAME:
            raise ElevenLabsScribeTransportError("dependency_unavailable") from None
        raise
    client_class = getattr(module, "ElevenLabs", None)
    if client_class is None:
        raise ElevenLabsScribeTransportError("dependency_unavailable")
    return client_class


def _sdk_model_to_mapping(value: object) -> dict[str, object] | None:
    if isinstance(value, Mapping):
        return dict(value)
    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        dumped = model_dump()
        return dict(dumped) if isinstance(dumped, Mapping) else None
    dict_method = getattr(value, "dict", None)
    if callable(dict_method):
        dumped = dict_method()
        return dict(dumped) if isinstance(dumped, Mapping) else None
    return None


def _sdk_plain_value(value: object) -> object:
    if isinstance(value, Enum):
        return value.value
    return value


def _validate_timeout_seconds(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("invalid_timeout_seconds")
    if value <= 0:
        raise ValueError("invalid_timeout_seconds")
    return value


def _validate_max_retries(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("invalid_max_retries")
    if value != 0:
        raise ValueError("sdk_retries_must_be_disabled")
    return value


def _transport_category_from_exception(exc: Exception) -> str:
    if _is_timeout_exception(exc):
        return "timeout"
    status_code = getattr(exc, "status_code", None)
    if not isinstance(status_code, int):
        return "unknown_provider_failure"

    tokens = _structured_error_tokens(getattr(exc, "body", None))
    if status_code == 401:
        return "authentication_rejected"
    if tokens & _QUOTA_OR_BILLING_CODES:
        return "quota_or_billing_blocked"
    if status_code == 403:
        return "permission_denied"
    if status_code == 408:
        return "timeout"
    if status_code == 413:
        return "request_too_large"
    if status_code == 415:
        return "unsupported_media"
    if status_code == 422:
        if tokens & _UNSUPPORTED_MEDIA_CODES:
            return "unsupported_media"
        return "provider_validation_error"
    if status_code == 429:
        return "rate_limited"
    if 500 <= status_code <= 599:
        return "provider_service_unavailable"
    return "unknown_provider_failure"


def _structured_error_tokens(body: object) -> set[str]:
    tokens: set[str] = set()

    def collect(value: object) -> None:
        if isinstance(value, Mapping):
            for key in ("type", "code", "status", "error_code", "reason", "category"):
                item = value.get(key)
                if isinstance(item, str):
                    tokens.add(item.casefold())
            detail = value.get("detail")
            if isinstance(detail, Mapping):
                collect(detail)
            elif isinstance(detail, list):
                for child in detail:
                    collect(child)
        elif isinstance(value, list):
            for child in value:
                collect(child)

    collect(body)
    return tokens


def _is_timeout_exception(exc: Exception) -> bool:
    for cls in type(exc).__mro__:
        if cls.__module__.split(".", 1)[0] == "httpx" and "Timeout" in cls.__name__:
            return True
    return "Timeout" in type(exc).__name__
