from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping


ACTION_LOG_SCHEMA_VERSION = "rev4.0"

ACTOR_TYPE_USER = "USER"
ACTOR_TYPE_APPLICATION = "APPLICATION"
ACTOR_TYPE_EXTERNAL_TOOL = "EXTERNAL_TOOL"

ACTOR_TYPES = (
    ACTOR_TYPE_USER,
    ACTOR_TYPE_APPLICATION,
    ACTOR_TYPE_EXTERNAL_TOOL,
)

SECRET_KEY_FRAGMENTS = (
    "api_key",
    "apikey",
    "authorization",
    "cookie",
    "credential",
    "password",
    "secret",
    "session",
    "token",
)

REDACTED_VALUE = "[redacted]"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _is_secret_key(key: str) -> bool:
    lowered = str(key or "").lower().replace("-", "_")
    return any(fragment in lowered for fragment in SECRET_KEY_FRAGMENTS)


def sanitize_action_log_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        sanitized: dict[str, Any] = {}
        for key in sorted(value):
            str_key = str(key)
            if _is_secret_key(str_key):
                sanitized[str_key] = REDACTED_VALUE
            else:
                sanitized[str_key] = sanitize_action_log_value(value[key])
        return sanitized
    if isinstance(value, tuple):
        return [sanitize_action_log_value(item) for item in value]
    if isinstance(value, list):
        return [sanitize_action_log_value(item) for item in value]
    return value


def _canonical_json(data: Mapping[str, Any]) -> str:
    return json.dumps(data, separators=(",", ":"), sort_keys=True)


def compute_action_event_hash(event_dict_without_hash: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canonical_json(event_dict_without_hash).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class CaptureActionLogEvent:
    event_id: str
    timestamp_utc: str
    session_id: str
    actor_type: str
    action_type: str
    result: str
    previous_event_hash: str = ""
    actor_id: str = ""
    source_id: str = ""
    target_id: str = ""
    request_summary: Mapping[str, Any] | None = None
    artifact_ids: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    failure_code: str = ""
    app_version: str = ""
    event_hash: str = ""
    schema_version: str = ACTION_LOG_SCHEMA_VERSION

    def to_dict_without_hash(self) -> dict[str, Any]:
        return {
            "action_type": self.action_type,
            "actor_id": self.actor_id or None,
            "actor_type": self.actor_type,
            "app_version": self.app_version or None,
            "artifact_ids": list(self.artifact_ids),
            "event_id": self.event_id,
            "failure_code": self.failure_code or None,
            "previous_event_hash": self.previous_event_hash or "",
            "request_summary": sanitize_action_log_value(dict(self.request_summary or {}))
            if self.request_summary is not None
            else None,
            "result": self.result,
            "schema_version": self.schema_version,
            "session_id": self.session_id,
            "source_id": self.source_id or None,
            "target_id": self.target_id or None,
            "timestamp_utc": self.timestamp_utc,
            "warnings": list(self.warnings),
        }

    def to_dict(self) -> dict[str, Any]:
        data = self.to_dict_without_hash()
        data["event_hash"] = self.event_hash or compute_action_event_hash(data)
        return data


def stable_action_event_id(session_id: str, action_type: str, timestamp_utc: str) -> str:
    payload = _canonical_json(
        {
            "action_type": action_type,
            "session_id": session_id,
            "timestamp_utc": timestamp_utc,
        }
    )
    return "event_" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def build_action_log_event(
    *,
    session_id: str,
    actor_type: str,
    action_type: str,
    result: str,
    timestamp_utc: str = "",
    previous_event_hash: str = "",
    actor_id: str = "",
    source_id: str = "",
    target_id: str = "",
    request_summary: Mapping[str, Any] | None = None,
    artifact_ids: tuple[str, ...] = (),
    warnings: tuple[str, ...] = (),
    failure_code: str = "",
    app_version: str = "",
) -> CaptureActionLogEvent:
    if actor_type not in ACTOR_TYPES:
        raise ValueError(f"Unknown action-log actor type: {actor_type}")
    timestamp = timestamp_utc or utc_now_iso()
    event = CaptureActionLogEvent(
        event_id=stable_action_event_id(session_id, action_type, timestamp),
        timestamp_utc=timestamp,
        session_id=session_id,
        actor_type=actor_type,
        actor_id=actor_id,
        action_type=action_type,
        source_id=source_id,
        target_id=target_id,
        request_summary=request_summary,
        result=result,
        artifact_ids=tuple(artifact_ids),
        warnings=tuple(warnings),
        failure_code=failure_code,
        app_version=app_version,
        previous_event_hash=previous_event_hash,
    )
    return CaptureActionLogEvent(
        **{
            **event.__dict__,
            "event_hash": compute_action_event_hash(event.to_dict_without_hash()),
        }
    )


def action_log_event_to_json(event: CaptureActionLogEvent) -> str:
    return json.dumps(event.to_dict(), indent=2, sort_keys=True)
