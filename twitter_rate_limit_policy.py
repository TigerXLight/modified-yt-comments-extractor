from __future__ import annotations

import time
from dataclasses import asdict, dataclass, is_dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any, Mapping, Sequence

RATE_LIMIT_POLICY_SCHEMA_VERSION = "twitter_rate_limit_policy.v74e"
RATE_LIMIT_STATE_SCHEMA_VERSION = "twitter_rate_limit_state.v74e"

RATE_LIMIT_HEADER_NAMES = (
    "x-rate-limit-limit",
    "x-rate-limit-remaining",
    "x-rate-limit-reset",
    "retry-after",
)

TRANSIENT_HTTP_STATUSES = {408, 425, 500, 502, 503, 504}
AUTH_ACCESS_HTTP_STATUSES = {401, 403}
RATE_LIMIT_HTTP_STATUS = 429


@dataclass(frozen=True)
class TwitterRateLimitObservation:
    schema_version: str
    response_status: int
    rate_limit_limit: int | None = None
    rate_limit_remaining: int | None = None
    rate_limit_reset_epoch: int | None = None
    retry_after_seconds: int | None = None
    reset_utc: str = ""
    retry_after_utc: str = ""
    header_source: str = "response_headers"
    body_error_codes: tuple[str, ...] = ()
    body_error_messages: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class TwitterRateLimitDecision:
    schema_version: str
    decision: str
    reason: str
    should_continue: bool
    should_pause: bool
    should_stop: bool
    delay_ms: int = 0
    cooldown_until_epoch: int | None = None
    cooldown_until_utc: str = ""
    safety_floor_reached: bool = False
    soft_page_budget_reached: bool = False
    transient_error: bool = False
    auth_or_access_boundary: bool = False
    rate_limited: bool = False

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class TwitterRateLimitState:
    schema_version: str
    latest_decision: str
    latest_reason: str
    response_status: int = 0
    rate_limit_limit: int | None = None
    rate_limit_remaining: int | None = None
    rate_limit_reset_epoch: int | None = None
    retry_after_seconds: int | None = None
    cooldown_until_epoch: int | None = None
    cooldown_until_utc: str = ""
    safety_floor: int = 1
    soft_page_budget: int = 0
    pages_since_cooldown: int = 0
    transient_error_count: int = 0
    body_error_codes: tuple[str, ...] = ()
    body_error_messages: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


def _value_for_dict(value: Any) -> Any:
    if is_dataclass(value):
        return {key: _value_for_dict(item) for key, item in asdict(value).items()}
    if isinstance(value, tuple):
        return [_value_for_dict(item) for item in value]
    if isinstance(value, list):
        return [_value_for_dict(item) for item in value]
    if isinstance(value, Mapping):
        return {str(key): _value_for_dict(item) for key, item in value.items()}
    return value


def _utc_from_epoch(epoch: int | None) -> str:
    if epoch is None:
        return ""
    try:
        return datetime.fromtimestamp(int(epoch), tz=timezone.utc).isoformat().replace("+00:00", "Z")
    except Exception:
        return ""


def _int_or_none(value: Any) -> int | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        return int(float(text))
    except Exception:
        return None


def _headers_lower(headers: Mapping[str, Any] | None) -> dict[str, str]:
    return {str(k).lower(): str(v) for k, v in (headers or {}).items() if v is not None}


def _retry_after_seconds(value: Any) -> int | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    direct = _int_or_none(raw)
    if direct is not None:
        return max(0, direct)
    try:
        dt = parsedate_to_datetime(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return max(0, int(dt.timestamp() - time.time()))
    except Exception:
        return None


def _errors_from_body(body: Any) -> tuple[tuple[str, ...], tuple[str, ...]]:
    errors: list[Any] = []
    if isinstance(body, Mapping):
        raw = body.get("errors")
        if isinstance(raw, list):
            errors.extend(raw)
        elif raw:
            errors.append(raw)
    codes: list[str] = []
    messages: list[str] = []
    for err in errors:
        if isinstance(err, Mapping):
            code = err.get("code") or err.get("kind") or err.get("error_code") or err.get("name")
            message = err.get("message") or err.get("detail") or err.get("title")
            if code is not None:
                codes.append(str(code))
            if message is not None:
                messages.append(str(message))
        elif err is not None:
            messages.append(str(err))
    return tuple(codes), tuple(messages)


def observe_rate_limit(
    *,
    response_status: int,
    headers: Mapping[str, Any] | None = None,
    body: Any = None,
) -> TwitterRateLimitObservation:
    lowered = _headers_lower(headers)
    limit = _int_or_none(lowered.get("x-rate-limit-limit"))
    remaining = _int_or_none(lowered.get("x-rate-limit-remaining"))
    reset_epoch = _int_or_none(lowered.get("x-rate-limit-reset"))
    retry_after = _retry_after_seconds(lowered.get("retry-after"))
    codes, messages = _errors_from_body(body)
    retry_after_epoch = int(time.time()) + int(retry_after) if retry_after is not None else None
    return TwitterRateLimitObservation(
        schema_version=RATE_LIMIT_POLICY_SCHEMA_VERSION,
        response_status=int(response_status or 0),
        rate_limit_limit=limit,
        rate_limit_remaining=remaining,
        rate_limit_reset_epoch=reset_epoch,
        retry_after_seconds=retry_after,
        reset_utc=_utc_from_epoch(reset_epoch),
        retry_after_utc=_utc_from_epoch(retry_after_epoch),
        body_error_codes=codes,
        body_error_messages=messages,
    )


def decide_rate_limit_action(
    *,
    observation: TwitterRateLimitObservation,
    normal_delay_ms: int,
    pages_since_cooldown: int = 0,
    safety_floor: int = 1,
    soft_page_budget: int = 0,
    transient_error_count: int = 0,
    max_transient_retries: int = 2,
    transient_base_delay_ms: int = 15000,
    reset_jitter_ms: int = 3000,
) -> TwitterRateLimitDecision:
    status = int(observation.response_status or 0)
    now = int(time.time())

    def cooldown_decision(reason: str, target_epoch: int | None, fallback_ms: int, *, rate_limited: bool = False) -> TwitterRateLimitDecision:
        if target_epoch is None:
            delay_ms = max(0, int(fallback_ms))
            epoch = now + int(delay_ms / 1000) if delay_ms else None
        else:
            delay_ms = max(0, int((target_epoch - now) * 1000) + max(0, int(reset_jitter_ms)))
            epoch = target_epoch
        return TwitterRateLimitDecision(
            schema_version=RATE_LIMIT_POLICY_SCHEMA_VERSION,
            decision="pause_until_reset" if rate_limited else "pause_before_continue",
            reason=reason,
            should_continue=False,
            should_pause=True,
            should_stop=True,
            delay_ms=delay_ms,
            cooldown_until_epoch=epoch,
            cooldown_until_utc=_utc_from_epoch(epoch),
            rate_limited=rate_limited,
        )

    if status == RATE_LIMIT_HTTP_STATUS:
        retry_epoch = now + int(observation.retry_after_seconds) if observation.retry_after_seconds is not None else None
        target = retry_epoch or observation.rate_limit_reset_epoch
        return cooldown_decision("http_429_rate_limited", target, fallback_ms=15 * 60 * 1000, rate_limited=True)

    if observation.rate_limit_remaining is not None and observation.rate_limit_remaining <= int(safety_floor):
        return cooldown_decision(
            "rate_limit_remaining_safety_floor",
            observation.rate_limit_reset_epoch,
            fallback_ms=15 * 60 * 1000,
            rate_limited=True,
        )

    if status in AUTH_ACCESS_HTTP_STATUSES:
        return TwitterRateLimitDecision(
            schema_version=RATE_LIMIT_POLICY_SCHEMA_VERSION,
            decision="stop_auth_or_access_boundary",
            reason=f"http_{status}_auth_or_access_boundary",
            should_continue=False,
            should_pause=False,
            should_stop=True,
            auth_or_access_boundary=True,
        )

    if status in TRANSIENT_HTTP_STATUSES:
        if int(transient_error_count) >= int(max_transient_retries):
            return TwitterRateLimitDecision(
                schema_version=RATE_LIMIT_POLICY_SCHEMA_VERSION,
                decision="stop_transient_retry_exhausted",
                reason=f"http_{status}_transient_retry_exhausted",
                should_continue=False,
                should_pause=False,
                should_stop=True,
                transient_error=True,
            )
        delay = max(1000, int(transient_base_delay_ms)) * (2 ** max(0, int(transient_error_count)))
        return TwitterRateLimitDecision(
            schema_version=RATE_LIMIT_POLICY_SCHEMA_VERSION,
            decision="retry_after_backoff",
            reason=f"http_{status}_transient_backoff",
            should_continue=True,
            should_pause=True,
            should_stop=False,
            delay_ms=delay,
            transient_error=True,
        )

    if int(soft_page_budget or 0) > 0 and int(pages_since_cooldown) >= int(soft_page_budget):
        return TwitterRateLimitDecision(
            schema_version=RATE_LIMIT_POLICY_SCHEMA_VERSION,
            decision="soft_page_budget_pause",
            reason="soft_page_budget_reached_without_header_reset_signal",
            should_continue=False,
            should_pause=True,
            should_stop=True,
            delay_ms=15 * 60 * 1000,
            cooldown_until_epoch=now + 15 * 60,
            cooldown_until_utc=_utc_from_epoch(now + 15 * 60),
            soft_page_budget_reached=True,
        )

    return TwitterRateLimitDecision(
        schema_version=RATE_LIMIT_POLICY_SCHEMA_VERSION,
        decision="continue_after_delay",
        reason="ok_continue",
        should_continue=True,
        should_pause=False,
        should_stop=False,
        delay_ms=max(0, int(normal_delay_ms)),
    )


def build_rate_limit_state(
    *,
    observation: TwitterRateLimitObservation | None,
    decision: TwitterRateLimitDecision | None,
    safety_floor: int,
    soft_page_budget: int,
    pages_since_cooldown: int,
    transient_error_count: int,
) -> TwitterRateLimitState:
    observation = observation or TwitterRateLimitObservation(schema_version=RATE_LIMIT_POLICY_SCHEMA_VERSION, response_status=0)
    decision = decision or TwitterRateLimitDecision(
        schema_version=RATE_LIMIT_POLICY_SCHEMA_VERSION,
        decision="not_observed",
        reason="no_rate_limit_observation_recorded",
        should_continue=False,
        should_pause=False,
        should_stop=False,
    )
    return TwitterRateLimitState(
        schema_version=RATE_LIMIT_STATE_SCHEMA_VERSION,
        latest_decision=decision.decision,
        latest_reason=decision.reason,
        response_status=observation.response_status,
        rate_limit_limit=observation.rate_limit_limit,
        rate_limit_remaining=observation.rate_limit_remaining,
        rate_limit_reset_epoch=observation.rate_limit_reset_epoch,
        retry_after_seconds=observation.retry_after_seconds,
        cooldown_until_epoch=decision.cooldown_until_epoch,
        cooldown_until_utc=decision.cooldown_until_utc,
        safety_floor=safety_floor,
        soft_page_budget=soft_page_budget,
        pages_since_cooldown=pages_since_cooldown,
        transient_error_count=transient_error_count,
        body_error_codes=observation.body_error_codes,
        body_error_messages=observation.body_error_messages,
    )
