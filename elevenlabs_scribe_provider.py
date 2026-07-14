from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path
from typing import BinaryIO, Mapping, Protocol, Sequence

from asr_provider_action import ASR_PROVIDER_ACTION_TRANSCRIBE


ELEVENLABS_SCRIBE_PROVIDER_ID = "elevenlabs_scribe"
ELEVENLABS_SCRIBE_CREDENTIAL_ID = "elevenlabs_scribe_api_key"
ELEVENLABS_SCRIBE_MODEL_ID = "scribe_v2"
ELEVENLABS_SCRIBE_ENDPOINT_PATH = "/v1/speech-to-text"
ELEVENLABS_SCRIBE_API_KEY_HEADER = "xi-api-key"
ELEVENLABS_SCRIBE_SCOPE = (
    "ElevenLabs Scribe v2 batch provider adapter; local-file request validation, "
    "injected transport only, no SDK client construction, no live network call, "
    "no GUI wiring, no connection-test wiring, and no credential values in public results"
)

TIMESTAMPS_NONE = "none"
TIMESTAMPS_WORD = "word"
TIMESTAMPS_CHARACTER = "character"
SUPPORTED_TIMESTAMP_GRANULARITIES = (
    TIMESTAMPS_NONE,
    TIMESTAMPS_WORD,
    TIMESTAMPS_CHARACTER,
)

KEYTERM_MAX_COUNT = 1000
# The API reference says each keyterm must be less than 50 characters. This is
# intentionally stricter than the guide wording that summarizes the limit as 50.
KEYTERM_MAX_CHARACTERS = 49
KEYTERM_MAX_WORDS = 5
KEYTERM_UNSUPPORTED_CHARACTERS = frozenset("<>{}[]\\")

MIN_SPEAKER_COUNT = 1
MAX_SPEAKER_COUNT = 32
MAX_LOCAL_FILE_BYTES = 5_000_000_000


class _StringEnum(str, Enum):
    def __str__(self) -> str:
        return self.value


class ElevenLabsScribeStatus(_StringEnum):
    SUCCEEDED = "succeeded"
    FILE_UNAVAILABLE = "file_unavailable"
    TRANSPORT_UNAVAILABLE = "transport_unavailable"
    AUTHENTICATION_REJECTED = "authentication_rejected"
    PERMISSION_DENIED = "permission_denied"
    RATE_LIMITED = "rate_limited"
    QUOTA_OR_BILLING_BLOCKED = "quota_or_billing_blocked"
    REQUEST_TOO_LARGE = "request_too_large"
    UNSUPPORTED_MEDIA = "unsupported_media"
    PROVIDER_VALIDATION_ERROR = "provider_validation_error"
    PROVIDER_SERVICE_UNAVAILABLE = "provider_service_unavailable"
    TIMEOUT = "timeout"
    MALFORMED_PROVIDER_RESPONSE = "malformed_provider_response"
    CANCELLED = "cancelled"
    UNKNOWN_PROVIDER_FAILURE = "unknown_provider_failure"


class ElevenLabsScribeValidationError(ValueError):
    """Fixed non-secret local request validation failure."""


@dataclass(frozen=True)
class ElevenLabsScribeWord:
    text: str
    start: float | None = None
    end: float | None = None
    word_type: str = ""
    speaker_id: str = ""

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


class ElevenLabsScribeRequest:
    __slots__ = (
        "_file_path",
        "_language_code",
        "_keyterms",
        "_diarize",
        "_num_speakers",
        "_tag_audio_events",
        "_timestamps_granularity",
    )

    def __init__(
        self,
        *,
        file_path: str,
        language_code: str = "",
        keyterms: Sequence[str] = (),
        diarize: bool = False,
        num_speakers: int | None = None,
        tag_audio_events: bool = True,
        timestamps_granularity: str = TIMESTAMPS_WORD,
    ) -> None:
        file_path = str(file_path or "").strip()
        if not file_path:
            raise ElevenLabsScribeValidationError("file_path_missing")
        path = Path(file_path)
        if not path.exists():
            raise ElevenLabsScribeValidationError("file_path_not_found")
        if not path.is_file():
            raise ElevenLabsScribeValidationError("file_path_not_regular_file")
        if path.stat().st_size >= MAX_LOCAL_FILE_BYTES:
            raise ElevenLabsScribeValidationError("file_too_large")

        language_code = " ".join((language_code or "").split())
        if language_code and not _valid_language_code(language_code):
            raise ElevenLabsScribeValidationError("invalid_language_code")

        granularity = " ".join((timestamps_granularity or "").split()).casefold()
        if granularity not in SUPPORTED_TIMESTAMP_GRANULARITIES:
            raise ElevenLabsScribeValidationError("invalid_timestamps_granularity")

        normalized_keyterms = normalize_keyterms(keyterms)
        if num_speakers is not None:
            if isinstance(num_speakers, bool) or not isinstance(num_speakers, int):
                raise ElevenLabsScribeValidationError("invalid_num_speakers")
            if not MIN_SPEAKER_COUNT <= num_speakers <= MAX_SPEAKER_COUNT:
                raise ElevenLabsScribeValidationError("invalid_num_speakers")

        self._file_path = file_path
        self._language_code = language_code
        self._timestamps_granularity = granularity
        self._keyterms = normalized_keyterms
        self._num_speakers = num_speakers
        self._tag_audio_events = bool(tag_audio_events)
        self._diarize = bool(diarize)

    def __repr__(self) -> str:
        return (
            "ElevenLabsScribeRequest("
            "file_selected=True, "
            f"language_code_set={bool(self._language_code)!r}, "
            f"keyterm_count={len(self._keyterms)}, "
            f"num_speakers_set={self._num_speakers is not None!r})"
        )

    @property
    def file_path(self) -> str:
        return self._file_path

    @property
    def language_code(self) -> str:
        return self._language_code

    @property
    def keyterms(self) -> tuple[str, ...]:
        return self._keyterms

    @property
    def diarize(self) -> bool:
        return self._diarize

    @property
    def num_speakers(self) -> int | None:
        return self._num_speakers

    @property
    def tag_audio_events(self) -> bool:
        return self._tag_audio_events

    @property
    def timestamps_granularity(self) -> str:
        return self._timestamps_granularity

    def to_safe_dict(self) -> dict[str, object]:
        return {
            "provider_id": ELEVENLABS_SCRIBE_PROVIDER_ID,
            "model_id": ELEVENLABS_SCRIBE_MODEL_ID,
            "file_selected": True,
            "language_code_set": bool(self.language_code),
            "keyterm_count": len(self.keyterms),
            "num_speakers_set": self.num_speakers is not None,
        }

    def to_transport_parameters(self) -> dict[str, object]:
        parameters: dict[str, object] = {
            "model_id": ELEVENLABS_SCRIBE_MODEL_ID,
        }
        if self.language_code:
            parameters["language_code"] = self.language_code
        if self.tag_audio_events is False:
            parameters["tag_audio_events"] = False
        if self.diarize:
            parameters["diarize"] = True
        if self.num_speakers is not None:
            parameters["num_speakers"] = self.num_speakers
        if self.timestamps_granularity != TIMESTAMPS_WORD:
            parameters["timestamps_granularity"] = self.timestamps_granularity
        if self.keyterms:
            # Official docs note keyterms may incur provider-side surcharge.
            parameters["keyterms"] = list(self.keyterms)
        return parameters


@dataclass(frozen=True)
class ElevenLabsScribeResult:
    provider_id: str
    model_id: str
    status: ElevenLabsScribeStatus
    safe_diagnostic: str
    text: str = ""
    language_code: str = ""
    language_probability: float | None = None
    words: tuple[ElevenLabsScribeWord, ...] = ()
    transport_called: bool = False
    scope: str = ELEVENLABS_SCRIBE_SCOPE

    def to_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["status"] = self.status.value
        return data


class ElevenLabsScribeTransport(Protocol):
    def create_transcript(
        self,
        *,
        api_key: str,
        file_obj: BinaryIO,
        parameters: Mapping[str, object],
    ) -> Mapping[str, object]:
        """Submit an explicit transcript request.

        Implementations are trusted provider transport/client code, not a
        sandbox. They receive the credential and open file handle only during
        explicit action execution.
        """


class ElevenLabsScribeTransportError(Exception):
    def __init__(self, category: str = "unknown_provider_failure") -> None:
        super().__init__("elevenlabs_scribe_transport_error")
        self.category = category


def normalize_keyterms(values: Sequence[str]) -> tuple[str, ...]:
    normalized_terms: list[str] = []
    seen: set[str] = set()
    for value in values:
        if not isinstance(value, str):
            raise ElevenLabsScribeValidationError("invalid_keyterm_type")
        term = " ".join(value.split())
        if not term:
            raise ElevenLabsScribeValidationError("empty_keyterm")
        if len(term) > KEYTERM_MAX_CHARACTERS:
            raise ElevenLabsScribeValidationError("keyterm_too_long")
        if len(term.split()) > KEYTERM_MAX_WORDS:
            raise ElevenLabsScribeValidationError("keyterm_too_many_words")
        if any(character in KEYTERM_UNSUPPORTED_CHARACTERS for character in term):
            raise ElevenLabsScribeValidationError("keyterm_unsupported_character")
        key = term.casefold()
        if key not in seen:
            seen.add(key)
            normalized_terms.append(term)
        if len(normalized_terms) > KEYTERM_MAX_COUNT:
            raise ElevenLabsScribeValidationError("too_many_keyterms")
    return tuple(normalized_terms)


class ElevenLabsScribeBatchProvider:
    def __init__(self, *, transport: ElevenLabsScribeTransport | None = None) -> None:
        self._transport = transport

    def __repr__(self) -> str:
        return "ElevenLabsScribeBatchProvider()"

    def transcribe(
        self,
        request: ElevenLabsScribeRequest,
        *,
        credential: str,
    ) -> ElevenLabsScribeResult:
        if self._transport is None:
            return _failure(ElevenLabsScribeStatus.TRANSPORT_UNAVAILABLE)
        if not str(credential or "").strip():
            return _failure(ElevenLabsScribeStatus.AUTHENTICATION_REJECTED)

        try:
            with open(request.file_path, "rb") as file_obj:
                response = self._transport.create_transcript(
                    api_key=credential,
                    file_obj=file_obj,
                    parameters=request.to_transport_parameters(),
                )
        except (KeyboardInterrupt, SystemExit, GeneratorExit):
            raise
        except ElevenLabsScribeTransportError as exc:
            return _failure(_status_from_transport_category(exc.category), transport_called=True)
        except OSError:
            return _failure(ElevenLabsScribeStatus.FILE_UNAVAILABLE)
        except Exception:
            return _failure(ElevenLabsScribeStatus.UNKNOWN_PROVIDER_FAILURE, transport_called=True)

        return normalize_elevenlabs_scribe_response(response)


def create_elevenlabs_scribe_provider_executor(
    request: ElevenLabsScribeRequest,
    *,
    transport: ElevenLabsScribeTransport,
):
    provider = ElevenLabsScribeBatchProvider(transport=transport)

    def execute(provider_id: str, action_kind: str, credential: str) -> ElevenLabsScribeResult:
        if provider_id != ELEVENLABS_SCRIBE_PROVIDER_ID:
            raise ElevenLabsScribeValidationError("unexpected_provider_id")
        if action_kind != ASR_PROVIDER_ACTION_TRANSCRIBE:
            raise ElevenLabsScribeValidationError("unexpected_action_kind")
        result = provider.transcribe(request, credential=credential)
        if result.status is not ElevenLabsScribeStatus.SUCCEEDED:
            raise ElevenLabsScribeValidationError(result.safe_diagnostic)
        return result

    return execute


def normalize_elevenlabs_scribe_response(
    response: Mapping[str, object],
) -> ElevenLabsScribeResult:
    if not isinstance(response, Mapping):
        return _failure(ElevenLabsScribeStatus.MALFORMED_PROVIDER_RESPONSE, transport_called=True)
    if "transcripts" in response:
        return _failure(ElevenLabsScribeStatus.MALFORMED_PROVIDER_RESPONSE, transport_called=True)
    if response.get("webhook") is True or "transcript_id" in response and "text" not in response:
        return _failure(ElevenLabsScribeStatus.MALFORMED_PROVIDER_RESPONSE, transport_called=True)

    text = response.get("text")
    if not isinstance(text, str):
        return _failure(ElevenLabsScribeStatus.MALFORMED_PROVIDER_RESPONSE, transport_called=True)

    language_code = response.get("language_code", "")
    if language_code is None:
        language_code = ""
    if not isinstance(language_code, str):
        return _failure(ElevenLabsScribeStatus.MALFORMED_PROVIDER_RESPONSE, transport_called=True)

    language_probability_value = response.get("language_probability")
    language_probability: float | None = None
    if language_probability_value is not None:
        if not _finite_number(language_probability_value):
            return _failure(ElevenLabsScribeStatus.MALFORMED_PROVIDER_RESPONSE, transport_called=True)
        language_probability = float(language_probability_value)

    words_value = response.get("words", [])
    if words_value is None:
        words_value = []
    if not isinstance(words_value, list):
        return _failure(ElevenLabsScribeStatus.MALFORMED_PROVIDER_RESPONSE, transport_called=True)

    words: list[ElevenLabsScribeWord] = []
    for item in words_value:
        word = _normalize_word(item)
        if word is None:
            return _failure(ElevenLabsScribeStatus.MALFORMED_PROVIDER_RESPONSE, transport_called=True)
        words.append(word)

    return ElevenLabsScribeResult(
        provider_id=ELEVENLABS_SCRIBE_PROVIDER_ID,
        model_id=ELEVENLABS_SCRIBE_MODEL_ID,
        status=ElevenLabsScribeStatus.SUCCEEDED,
        safe_diagnostic="provider_transcription_completed",
        text=text,
        language_code=language_code,
        language_probability=language_probability,
        words=tuple(words),
        transport_called=True,
    )


def _normalize_word(item: object) -> ElevenLabsScribeWord | None:
    if not isinstance(item, Mapping):
        return None
    text = item.get("text")
    if not isinstance(text, str):
        return None
    start = _optional_timestamp(item.get("start"))
    end = _optional_timestamp(item.get("end"))
    if start == "invalid" or end == "invalid":
        return None
    if start is not None and end is not None and end < start:
        return None
    word_type = item.get("type", "")
    if word_type is None:
        word_type = ""
    speaker_id = item.get("speaker_id", "")
    if speaker_id is None:
        speaker_id = ""
    if not isinstance(word_type, str) or not isinstance(speaker_id, str):
        return None
    return ElevenLabsScribeWord(
        text=text,
        start=start,
        end=end,
        word_type=word_type,
        speaker_id=speaker_id,
    )


def _optional_timestamp(value: object) -> float | None | str:
    if value is None:
        return None
    if not _finite_number(value):
        return "invalid"
    timestamp = float(value)
    if timestamp < 0:
        return "invalid"
    return timestamp


def _finite_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _valid_language_code(value: str) -> bool:
    if not (2 <= len(value) <= 3):
        return False
    return value.isalpha()


def _failure(
    status: ElevenLabsScribeStatus,
    *,
    transport_called: bool = False,
) -> ElevenLabsScribeResult:
    return ElevenLabsScribeResult(
        provider_id=ELEVENLABS_SCRIBE_PROVIDER_ID,
        model_id=ELEVENLABS_SCRIBE_MODEL_ID,
        status=status,
        safe_diagnostic=status.value,
        transport_called=transport_called,
    )


def _status_from_transport_category(category: str) -> ElevenLabsScribeStatus:
    mapping = {
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
        "dependency_unavailable": ElevenLabsScribeStatus.TRANSPORT_UNAVAILABLE,
        "malformed_provider_response": ElevenLabsScribeStatus.MALFORMED_PROVIDER_RESPONSE,
    }
    return mapping.get(category, ElevenLabsScribeStatus.UNKNOWN_PROVIDER_FAILURE)
