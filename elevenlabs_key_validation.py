from __future__ import annotations

from typing import Callable

from elevenlabs_scribe_provider import ELEVENLABS_SCRIBE_PROVIDER_ID
from elevenlabs_scribe_transport import (
    ELEVENLABS_SDK_DEFAULT_TIMEOUT_SECONDS,
    ELEVENLABS_SDK_MAX_RETRIES,
    SDKClientFactory,
    _load_official_elevenlabs_client,
)


ELEVENLABS_KEY_VALIDATION_TIMEOUT_SECONDS = 30

ELEVENLABS_KEY_VALIDATION_SUCCEEDED = "validated"
ELEVENLABS_KEY_VALIDATION_AUTH_FAILED = "validation_failed"
ELEVENLABS_KEY_VALIDATION_COULD_NOT_COMPLETE = "validation_could_not_complete"

ELEVENLABS_KEY_VALIDATION_SCOPE = (
    "explicit user-triggered ElevenLabs key validation only; no media upload, "
    "no transcription, no retained model/account/quota data, no response bodies "
    "or headers in public diagnostics, and no retry"
)


ConnectionClientFactory = Callable[[str, int], object]


class ElevenLabsKeyValidationError(Exception):
    def __init__(self, category: str) -> None:
        super().__init__(category)
        self.category = category

    def __str__(self) -> str:
        return self.category


class ElevenLabsModelsListKeyValidator:
    """Validate an ElevenLabs key with a short-lived read-only models-list call."""

    def __init__(
        self,
        *,
        client_factory: ConnectionClientFactory | None = None,
        sdk_loader: Callable[[], object] | None = None,
        timeout_seconds: int = ELEVENLABS_KEY_VALIDATION_TIMEOUT_SECONDS,
        max_retries: int = ELEVENLABS_SDK_MAX_RETRIES,
    ) -> None:
        self._client_factory = client_factory
        self._sdk_loader = sdk_loader
        self._timeout_seconds = _validate_timeout_seconds(timeout_seconds)
        self._max_retries = _validate_max_retries(max_retries)

    def __repr__(self) -> str:
        return "ElevenLabsModelsListKeyValidator()"

    @property
    def timeout_seconds(self) -> int:
        return self._timeout_seconds

    @property
    def max_retries(self) -> int:
        return self._max_retries

    def __call__(self, provider_id: str, credential: str) -> None:
        if provider_id != ELEVENLABS_SCRIBE_PROVIDER_ID:
            raise ElevenLabsKeyValidationError(
                ELEVENLABS_KEY_VALIDATION_COULD_NOT_COMPLETE
            )
        if not str(credential or "").strip():
            raise ElevenLabsKeyValidationError(ELEVENLABS_KEY_VALIDATION_AUTH_FAILED)
        client = self._create_client(str(credential))
        try:
            # GET /v1/models via the official SDK. The returned model list is
            # intentionally discarded; success means only that this read-only
            # validation call returned normally.
            client.models.list(
                request_options={
                    "max_retries": self._max_retries,
                    "timeout_in_seconds": self._timeout_seconds,
                }
            )
        except (KeyboardInterrupt, SystemExit, GeneratorExit):
            raise
        except ElevenLabsKeyValidationError:
            raise
        except Exception as exc:
            raise ElevenLabsKeyValidationError(
                _validation_category_from_exception(exc)
            ) from None

    def _create_client(self, credential: str) -> object:
        if self._client_factory is not None:
            try:
                return self._client_factory(credential, self._timeout_seconds)
            except (KeyboardInterrupt, SystemExit, GeneratorExit):
                raise
            except ElevenLabsKeyValidationError:
                raise
            except Exception:
                raise ElevenLabsKeyValidationError(
                    ELEVENLABS_KEY_VALIDATION_COULD_NOT_COMPLETE
                ) from None
        client_class = _load_official_elevenlabs_client(self._sdk_loader)
        return client_class(api_key=credential, timeout=self._timeout_seconds)


def create_elevenlabs_models_list_key_validator(
    *,
    client_factory: SDKClientFactory | None = None,
    timeout_seconds: int = ELEVENLABS_KEY_VALIDATION_TIMEOUT_SECONDS,
) -> ElevenLabsModelsListKeyValidator:
    return ElevenLabsModelsListKeyValidator(
        client_factory=client_factory,
        timeout_seconds=timeout_seconds,
        max_retries=ELEVENLABS_SDK_MAX_RETRIES,
    )


def _validate_timeout_seconds(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("invalid_timeout_seconds")
    if value <= 0 or value > ELEVENLABS_SDK_DEFAULT_TIMEOUT_SECONDS:
        raise ValueError("invalid_timeout_seconds")
    return value


def _validate_max_retries(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("invalid_max_retries")
    if value != 0:
        raise ValueError("validation_retries_must_be_disabled")
    return value


def _validation_category_from_exception(exc: Exception) -> str:
    if _is_timeout_exception(exc):
        return ELEVENLABS_KEY_VALIDATION_COULD_NOT_COMPLETE
    status_code = getattr(exc, "status_code", None)
    if status_code == 401:
        return ELEVENLABS_KEY_VALIDATION_AUTH_FAILED
    if status_code in {403, 408, 429}:
        return ELEVENLABS_KEY_VALIDATION_COULD_NOT_COMPLETE
    if isinstance(status_code, int) and 500 <= status_code <= 599:
        return ELEVENLABS_KEY_VALIDATION_COULD_NOT_COMPLETE
    return ELEVENLABS_KEY_VALIDATION_COULD_NOT_COMPLETE


def _is_timeout_exception(exc: Exception) -> bool:
    for cls in type(exc).__mro__:
        if cls.__module__.split(".", 1)[0] == "httpx" and "Timeout" in cls.__name__:
            return True
    return "Timeout" in type(exc).__name__
