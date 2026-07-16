from __future__ import annotations

from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Any

from capture_status import CAPTURE_STATUS_PARTIAL, CAPTURE_STATUS_SUCCESS


LIVECHAT_CAPTURE_SCOPE = (
    "local supplied-HTML livechat event extraction only; no fetch, browser, websocket, "
    "archive, download, provider, credential, scraping, external process, or GUI behavior"
)


@dataclass(frozen=True)
class LivechatEvent:
    event_id: str
    message: str
    author: str = ""
    timestamp_label: str = ""
    event_type: str = "message"
    ordinal: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "author": self.author,
            "event_id": self.event_id,
            "event_type": self.event_type,
            "message": self.message,
            "ordinal": self.ordinal,
            "timestamp_label": self.timestamp_label,
        }


@dataclass(frozen=True)
class LivechatCaptureResult:
    source_url: str
    status: str
    events: tuple[LivechatEvent, ...] = ()
    duplicate_event_ids: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    scope: str = LIVECHAT_CAPTURE_SCOPE

    def to_dict(self) -> dict[str, Any]:
        return {
            "duplicate_event_ids": list(self.duplicate_event_ids),
            "events": [event.to_dict() for event in self.events],
            "scope": self.scope,
            "source_url": self.source_url,
            "status": self.status,
            "warnings": list(self.warnings),
        }


class _LivechatHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.records: list[dict[str, Any]] = []
        self._active: dict[str, Any] | None = None
        self._active_depth = 0
        self._ignored_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        lowered = tag.lower()
        attr_map = {key.lower(): value or "" for key, value in attrs}
        if lowered in {"script", "style", "noscript"}:
            self._ignored_depth += 1
        event_id = attr_map.get("data-event-id", "")
        if event_id:
            self._active = {
                "author": attr_map.get("data-author", ""),
                "event_id": event_id,
                "event_type": attr_map.get("data-event-type", "message") or "message",
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


def extract_livechat_events_from_html(html: str, *, source_url: str = "") -> LivechatCaptureResult:
    parser = _LivechatHTMLParser()
    warnings: list[str] = []
    try:
        parser.feed(html or "")
    except Exception:
        warnings.append("HTML parser reported a non-secret parsing issue; livechat may be partial.")

    events: list[LivechatEvent] = []
    seen: set[str] = set()
    duplicates: list[str] = []
    ordinal = 0
    for raw_record in parser.records:
        event_id = str(raw_record.get("event_id") or "")
        if not event_id:
            continue
        if event_id in seen:
            duplicates.append(event_id)
            continue
        seen.add(event_id)
        ordinal += 1
        events.append(
            LivechatEvent(
                event_id=event_id,
                author=str(raw_record.get("author") or ""),
                event_type=str(raw_record.get("event_type") or "message"),
                timestamp_label=str(raw_record.get("timestamp_label") or ""),
                message=_normalize_text(" ".join(raw_record.get("message_parts") or [])),
                ordinal=ordinal,
            )
        )

    if not events:
        warnings.append("No livechat events found in supplied HTML.")
    if duplicates:
        warnings.append("Duplicate livechat event IDs were ignored: " + ", ".join(sorted(set(duplicates))))

    return LivechatCaptureResult(
        source_url=source_url,
        status=CAPTURE_STATUS_SUCCESS if events else CAPTURE_STATUS_PARTIAL,
        events=tuple(events),
        duplicate_event_ids=tuple(dict.fromkeys(duplicates)),
        warnings=tuple(warnings),
    )
