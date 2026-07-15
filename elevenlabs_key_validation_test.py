from __future__ import annotations

from elevenlabs_key_validation import (
    ELEVENLABS_KEY_VALIDATION_AUTH_FAILED,
    ELEVENLABS_KEY_VALIDATION_COULD_NOT_COMPLETE,
    ELEVENLABS_KEY_VALIDATION_TIMEOUT_SECONDS,
    ElevenLabsKeyValidationError,
    ElevenLabsModelsListKeyValidator,
)
from elevenlabs_scribe_provider import ELEVENLABS_SCRIBE_PROVIDER_ID


SECRET_SENTINEL = "VALIDATION-SECRET-MUST-NOT-LEAK"
RAW_RESPONSE_SENTINEL = "RAW-VALIDATION-RESPONSE-MUST-NOT-LEAK"


class FakeModelsService:
    def __init__(self, *, exception: Exception | None = None) -> None:
        self.exception = exception
        self.calls: list[dict[str, object]] = []

    def list(self, *, request_options: dict[str, object]) -> list[object]:
        self.calls.append(dict(request_options))
        if self.exception is not None:
            raise self.exception
        return [{"model_id": RAW_RESPONSE_SENTINEL}]


class FakeClient:
    def __init__(self, models: FakeModelsService) -> None:
        self.models = models


class FakeApiError(Exception):
    def __init__(self, status_code: int) -> None:
        super().__init__(RAW_RESPONSE_SENTINEL)
        self.status_code = status_code
        self.body = RAW_RESPONSE_SENTINEL
        self.headers = {"x-request-id": RAW_RESPONSE_SENTINEL}


class FakeTimeout(Exception):
    pass


def _validator(models: FakeModelsService) -> ElevenLabsModelsListKeyValidator:
    def factory(api_key: str, timeout_seconds: int) -> FakeClient:
        assert api_key == SECRET_SENTINEL
        assert timeout_seconds == ELEVENLABS_KEY_VALIDATION_TIMEOUT_SECONDS
        return FakeClient(models)

    return ElevenLabsModelsListKeyValidator(client_factory=factory)


def _assert_secret_absent(value: object) -> None:
    blob = repr(value) + str(value)
    assert SECRET_SENTINEL not in blob
    assert RAW_RESPONSE_SENTINEL not in blob


def test_models_list_validator_uses_one_attempt_request_options_and_discards_response() -> None:
    models = FakeModelsService()
    validator = _validator(models)

    assert repr(validator) == "ElevenLabsModelsListKeyValidator()"
    validator(ELEVENLABS_SCRIBE_PROVIDER_ID, SECRET_SENTINEL)

    assert models.calls == [
        {
            "max_retries": 0,
            "timeout_in_seconds": ELEVENLABS_KEY_VALIDATION_TIMEOUT_SECONDS,
        }
    ]
    _assert_secret_absent(validator)


def test_models_list_validator_maps_auth_failure_to_safe_category() -> None:
    validator = _validator(FakeModelsService(exception=FakeApiError(401)))

    try:
        validator(ELEVENLABS_SCRIBE_PROVIDER_ID, SECRET_SENTINEL)
    except ElevenLabsKeyValidationError as exc:
        assert exc.category == ELEVENLABS_KEY_VALIDATION_AUTH_FAILED
        _assert_secret_absent(exc)
    else:
        raise AssertionError("auth failure was not reported")


def test_models_list_validator_maps_ambiguous_failures_to_could_not_complete() -> None:
    for exception in (
        FakeApiError(403),
        FakeApiError(408),
        FakeApiError(429),
        FakeApiError(500),
        FakeTimeout(),
        RuntimeError(RAW_RESPONSE_SENTINEL),
    ):
        validator = _validator(FakeModelsService(exception=exception))
        try:
            validator(ELEVENLABS_SCRIBE_PROVIDER_ID, SECRET_SENTINEL)
        except ElevenLabsKeyValidationError as exc:
            assert exc.category == ELEVENLABS_KEY_VALIDATION_COULD_NOT_COMPLETE
            _assert_secret_absent(exc)
        else:
            raise AssertionError("ambiguous failure was not reported")


def test_validator_rejects_invalid_provider_without_request() -> None:
    models = FakeModelsService()
    validator = _validator(models)

    try:
        validator("youtube", SECRET_SENTINEL)
    except ElevenLabsKeyValidationError as exc:
        assert exc.category == ELEVENLABS_KEY_VALIDATION_COULD_NOT_COMPLETE
    else:
        raise AssertionError("invalid provider was not rejected")
    assert models.calls == []


if __name__ == "__main__":
    test_models_list_validator_uses_one_attempt_request_options_and_discards_response()
    test_models_list_validator_maps_auth_failure_to_safe_category()
    test_models_list_validator_maps_ambiguous_failures_to_could_not_complete()
    test_validator_rejects_invalid_provider_without_request()
    print("ElevenLabs key validation self-test passed.")
