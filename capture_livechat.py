from __future__ import annotations

from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Any

from capture_status import CAPTURE_STATUS_PARTIAL, CAPTURE_STATUS_SUCCESS


LIVECHAT_CAPTURE_SCOPE = (
    "local supplied-HTML livechat event extraction only; no fetch, browser, websocket, "
    "archive, download, provider, credential, scraping, external process, or GUI behavior"
)

LIVECHAT_STOP_MESSAGE_LIMIT = "message_limit"
LIVECHAT_STOP_DURATION_LIMIT_METADATA = "duration_limit_metadata_only"


@dataclass(frozen=True)
class LivechatEvent:
    event_id: str
    message: str
    author: str = ""
    timestamp_label: str = ""
    event_type: str = "message"
    ordinal: int = 0
    service_timestamp: str = ""
    observed_at: str = ""
    removed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "author": self.author,
            "event_id": self.event_id,
            "event_type": self.event_type,
            "message": self.message,
            "observed_at": self.observed_at,
            "ordinal": self.ordinal,
            "removed": self.removed,
            "service_timestamp": self.service_timestamp,
            "timestamp_label": self.timestamp_label,
        }


@dataclass(frozen=True)
class LivechatScreenshotFrame:
    frame_id: str
    timestamp_label: str
    relative_path: str
    sha256: str = ""
    complete_chat_capture: bool = False
    note: str = "timestamped supporting frame only; not a complete livechat capture"

    def to_dict(self) -> dict[str, Any]:
        return {
            "complete_chat_capture": self.complete_chat_capture,
            "frame_id": self.frame_id,
            "note": self.note,
            "relative_path": self.relative_path,
            "sha256": self.sha256,
            "timestamp_label": self.timestamp_label,
        }


@dataclass(frozen=True)
class LivechatCaptureResult:
    source_url: str
    status: str
    events: tuple[LivechatEvent, ...] = ()
    duplicate_event_ids: tuple[str, ...] = ()
    duration_limit_seconds: int = 0
    message_limit: int = 0
    stop_reason: str = ""
    reconnect_count: int = 0
    removed_event_ids: tuple[str, ...] = ()
    screenshot_frames: tuple[LivechatScreenshotFrame, ...] = ()
    warnings: tuple[str, ...] = ()
    scope: str = LIVECHAT_CAPTURE_SCOPE

    def to_dict(self) -> dict[str, Any]:
        return {
            "duplicate_event_ids": list(self.duplicate_event_ids),
            "duration_limit_seconds": self.duration_limit_seconds,
            "events": [event.to_dict() for event in self.events],
            "message_limit": self.message_limit,
            "reconnect_count": self.reconnect_count,
            "removed_event_ids": list(self.removed_event_ids),
            "scope": self.scope,
            "screenshot_frames": [frame.to_dict() for frame in self.screenshot_frames],
            "source_url": self.source_url,
            "status": self.status,
            "stop_reason": self.stop_reason,
            "warnings": list(self.warnings),
        }


class _LivechatHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.records: list[dict[str, Any]] = []
        self.reconnect_count = 0
        self._active: dict[str, Any] | None = None
        self._active_depth = 0
        self._ignored_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        lowered = tag.lower()
        attr_map = {key.lower(): value or "" for key, value in attrs}
        if lowered in {"script", "style", "noscript"}:
            self._ignored_depth += 1
        if attr_map.get("data-reconnect") == "true":
            self.reconnect_count += 1
        event_id = attr_map.get("data-event-id", "")
        if event_id:
            event_type = attr_map.get("data-event-type", "message") or "message"
            if event_type == "reconnect":
                self.reconnect_count += 1
            self._active = {
                "author": attr_map.get("data-author", ""),
                "event_id": event_id,
                "event_type": event_type,
                "observed_at": attr_map.get("data-observed-at", ""),
                "removed": _bool_attr(attr_map.get("data-removed", "")) or event_type == "removed",
                "service_timestamp": attr_map.get("data-service-timestamp", ""),
                "timestamp_label": attr_map.get("data-timestamp", ""),
                "message_parts": [],
            }
            self._active_depth = 1
        elif self._active is not None:
            self._active_depth += 1

    def handle_endtag(self, tag: str) -> None:
        lowered = tag.lower()
        if lowered in {"script", "style", "noscript"} and self._ignored_depth:
            self._ignored_depth -= 1
        if self._active is not None:
            self._active_depth -= 1
            if self._active_depth <= 0:
                self.records.append(self._active)
                self._active = None
                self._active_depth = 0

    def handle_data(self, data: str) -> None:
        if self._ignored_depth or self._active is None:
            return
        text = _normalize_text(data)
        if text:
            self._active["message_parts"].append(text)


def _normalize_text(value: str) -> str:
    return " ".join(str(value or "").split())


def _bool_attr(value: str) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes"}


def extract_livechat_events_from_html(
    html: str,
    *,
    source_url: str = "",
    duration_limit_seconds: int = 0,
    message_limit: int = 0,
    screenshot_frames: tuple[LivechatScreenshotFrame, ...] = (),
) -> LivechatCaptureResult:
    parser = _LivechatHTMLParser()
    warnings: list[str] = []
    try:
        parser.feed(html or "")
    except Exception:
        warnings.append("HTML parser reported a non-secret parsing issue; livechat may be partial.")

    events: list[LivechatEvent] = []
    seen: set[str] = set()
    duplicates: list[str] = []
    removed_ids: list[str] = []
    ordinal = 0
    for raw_record in parser.records:
        event_id = str(raw_record.get("event_id") or "")
        if not event_id:
            continue
        if event_id in seen:
            duplicates.append(event_id)
            continue
        seen.add(event_id)
        if message_limit > 0 and len(events) >= message_limit:
            continue
        ordinal += 1
        removed = bool(raw_record.get("removed"))
        if removed:
            removed_ids.append(event_id)
        events.append(
            LivechatEvent(
                event_id=event_id,
                author=str(raw_record.get("author") or ""),
                event_type=str(raw_record.get("event_type") or "message"),
                timestamp_label=str(raw_record.get("timestamp_label") or ""),
                message=_normalize_text(" ".join(raw_record.get("message_parts") or [])),
                ordinal=ordinal,
                service_timestamp=str(raw_record.get("service_timestamp") or ""),
                observed_at=str(raw_record.get("observed_at") or ""),
                removed=removed,
            )
        )

    stop_reason = ""
    if message_limit > 0 and len(seen) > message_limit:
        stop_reason = LIVECHAT_STOP_MESSAGE_LIMIT
        warnings.append("Livechat message limit metadata was reached in supplied fixture data.")
    elif duration_limit_seconds > 0:
        stop_reason = LIVECHAT_STOP_DURATION_LIMIT_METADATA
    if not events:
        warnings.append("No livechat events found in supplied HTML.")
    if duplicates:
        warnings.append("Duplicate livechat event IDs were ignored: " + ", ".join(sorted(set(duplicates))))
    if screenshot_frames:
        warnings.append("Livechat screenshot frames are supporting timestamped frames only, not complete chat capture.")

    safe_frames = tuple(
        LivechatScreenshotFrame(
            frame_id=frame.frame_id,
            timestamp_label=frame.timestamp_label,
            relative_path=frame.relative_path,
            sha256=frame.sha256,
            complete_chat_capture=False,
            note=frame.note,
        )
        for frame in screenshot_frames
    )
    return LivechatCaptureResult(
        source_url=source_url,
        status=CAPTURE_STATUS_SUCCESS if events else CAPTURE_STATUS_PARTIAL,
        events=tuple(events),
        duplicate_event_ids=tuple(dict.fromkeys(duplicates)),
        duration_limit_seconds=max(0, int(duration_limit_seconds or 0)),
        message_limit=max(0, int(message_limit or 0)),
        stop_reason=stop_reason,
        reconnect_count=parser.reconnect_count,
        removed_event_ids=tuple(dict.fromkeys(removed_ids)),
        screenshot_frames=safe_frames,
        warnings=tuple(warnings),
    )
