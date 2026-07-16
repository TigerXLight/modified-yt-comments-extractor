from __future__ import annotations

import json
from dataclasses import dataclass, replace
from html.parser import HTMLParser
from typing import Any, Iterable

from capture_status import (
    CAPTURE_STATUS_CHALLENGE_REQUIRES_USER,
    CAPTURE_STATUS_LOGIN_REQUIRED,
    CAPTURE_STATUS_PARTIAL,
    CAPTURE_STATUS_SUCCESS,
    COMPLETENESS_COMPLETE,
    COMPLETENESS_PARTIAL_CHALLENGE,
    COMPLETENESS_PARTIAL_LOGIN_REQUIRED,
    COMPLETENESS_PARTIAL_UNKNOWN,
    COMPLETENESS_PARTIAL_VIRTUALIZED,
)


COMMENT_STATUS_VISIBLE = "visible"
COMMENT_STATUS_TOMBSTONE = "tombstone"
COMMENT_STATUS_DELETED = "deleted"

COMMENT_ROUTE_STATIC = "static"
COMMENT_ROUTE_LOAD_MORE = "load_more"
COMMENT_ROUTE_CURSOR = "cursor"
COMMENT_ROUTE_INFINITE_SCROLL = "infinite_scroll"
COMMENT_ROUTE_IFRAME = "iframe"
COMMENT_ROUTE_OPEN_SHADOW = "open_shadow"
COMMENT_ROUTE_CLOSED_SHADOW_PAYLOAD = "closed_shadow_payload"
COMMENT_ROUTE_NESTED_CONTAINER = "nested_container"
COMMENT_ROUTE_VIRTUALIZED = "virtualized"
COMMENT_ROUTE_DISAPPEARING = "disappearing"
COMMENT_ROUTE_ENCODED_STATE = "encoded_state"
COMMENT_ROUTE_LOGIN_REQUIRED = "login_required"
COMMENT_ROUTE_CHALLENGE = "challenge"

COMMENTS_CAPTURE_SCOPE = (
    "local supplied-HTML comments extraction only; no fetch, browser, scrolling, "
    "archive, download, provider, credential, scraping, external process, or GUI behavior"
)


@dataclass(frozen=True)
class CommentRecord:
    comment_id: str
    text: str
    author: str = ""
    parent_id: str = ""
    depth: int = 0
    first_seen_ordinal: int = 0
    last_seen_ordinal: int = 0
    status: str = COMMENT_STATUS_VISIBLE
    thread_id: str = ""
    posted_at: str = ""
    observed_at: str = ""
    reaction_count: int = 0
    reply_count: int = 0
    permalink: str = ""
    source_order: int = 0
    loaded_order: int = 0
    capture_method: str = ""
    raw_reference: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "author": self.author,
            "capture_method": self.capture_method,
            "comment_id": self.comment_id,
            "depth": self.depth,
            "first_seen_ordinal": self.first_seen_ordinal,
            "last_seen_ordinal": self.last_seen_ordinal,
            "loaded_order": self.loaded_order,
            "observed_at": self.observed_at,
            "parent_id": self.parent_id,
            "permalink": self.permalink,
            "posted_at": self.posted_at,
            "raw_reference": self.raw_reference,
            "reaction_count": self.reaction_count,
            "reply_count": self.reply_count,
            "source_order": self.source_order,
            "status": self.status,
            "text": self.text,
            "thread_id": self.thread_id,
        }


@dataclass(frozen=True)
class CommentCaptureResult:
    source_url: str
    status: str
    completeness: str
    comments: tuple[CommentRecord, ...] = ()
    duplicate_comment_ids: tuple[str, ...] = ()
    capture_routes: tuple[str, ...] = ()
    cursor: str = ""
    stop_reason: str = ""
    login_required: bool = False
    challenge_required: bool = False
    incremental_batches: int = 1
    warnings: tuple[str, ...] = ()
    scope: str = COMMENTS_CAPTURE_SCOPE

    def to_dict(self) -> dict[str, Any]:
        return {
            "capture_routes": list(self.capture_routes),
            "challenge_required": self.challenge_required,
            "comments": [comment.to_dict() for comment in self.comments],
            "completeness": self.completeness,
            "cursor": self.cursor,
            "duplicate_comment_ids": list(self.duplicate_comment_ids),
            "incremental_batches": self.incremental_batches,
            "login_required": self.login_required,
            "scope": self.scope,
            "source_url": self.source_url,
            "status": self.status,
            "stop_reason": self.stop_reason,
            "warnings": list(self.warnings),
        }


class _CommentHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.records: list[dict[str, Any]] = []
        self.markers: set[str] = set()
        self.cursor = ""
        self.stop_reason = ""
        self._active: dict[str, Any] | None = None
        self._active_depth = 0
        self._ignored_depth = 0
        self._active_script_id = ""
        self._script_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        lowered = tag.lower()
        attr_map = {key.lower(): value or "" for key, value in attrs}
        self._record_markers(lowered, attr_map)
        if lowered in {"script", "style", "noscript"}:
            if lowered == "script":
                self._active_script_id = attr_map.get("id", "")
                self._script_parts = []
            self._ignored_depth += 1
        comment_id = attr_map.get("data-comment-id", "")
        if comment_id:
            self._active = {
                "author": attr_map.get("data-author", ""),
                "capture_method": attr_map.get("data-capture-method", ""),
                "comment_id": comment_id,
                "depth": _int_or_zero(attr_map.get("data-depth", "")),
                "loaded_order": _int_or_zero(attr_map.get("data-loaded-order", "")),
                "observed_at": attr_map.get("data-observed-at", ""),
                "parent_id": attr_map.get("data-parent-id", ""),
                "permalink": attr_map.get("data-permalink", ""),
                "posted_at": attr_map.get("data-posted-at", ""),
                "raw_reference": attr_map.get("data-raw-reference", ""),
                "reaction_count": _int_or_zero(attr_map.get("data-reactions", "")),
                "reply_count": _int_or_zero(attr_map.get("data-reply-count", "")),
                "source_order": _int_or_zero(attr_map.get("data-source-order", "")),
                "status": attr_map.get("data-state", attr_map.get("data-comment-status", "")),
                "text_parts": [],
                "thread_id": attr_map.get("data-thread-id", ""),
            }
            self._active_depth = 1
        elif self._active is not None:
            self._active_depth += 1

    def handle_endtag(self, tag: str) -> None:
        lowered = tag.lower()
        if lowered in {"script", "style", "noscript"} and self._ignored_depth:
            self._ignored_depth -= 1
            if lowered == "script":
                self._flush_script()
        if self._active is not None:
            self._active_depth -= 1
            if self._active_depth <= 0:
                self.records.append(self._active)
                self._active = None
                self._active_depth = 0

    def handle_data(self, data: str) -> None:
        if self._active_script_id:
            self._script_parts.append(data)
            return
        if self._ignored_depth or self._active is None:
            return
        text = _normalize_text(data)
        if text:
            self._active["text_parts"].append(text)

    def _record_markers(self, tag: str, attrs: dict[str, str]) -> None:
        if tag == "iframe" and "comment" in attrs.get("title", attrs.get("src", "")).lower():
            self.markers.add(COMMENT_ROUTE_IFRAME)
        if attrs.get("data-load-more") == "true" or "load-more" in attrs.get("id", ""):
            self.markers.add(COMMENT_ROUTE_LOAD_MORE)
        if attrs.get("data-stop"):
            self.markers.add(COMMENT_ROUTE_INFINITE_SCROLL)
            self.stop_reason = attrs.get("data-stop", "")
        if attrs.get("data-shadow") == "open":
            self.markers.add(COMMENT_ROUTE_OPEN_SHADOW)
        if attrs.get("data-shadow") == "closed":
            self.markers.add(COMMENT_ROUTE_CLOSED_SHADOW_PAYLOAD)
        if attrs.get("data-scroll-container") == "true" or "scroll-container" in attrs.get("id", ""):
            self.markers.add(COMMENT_ROUTE_NESTED_CONTAINER)
        if attrs.get("data-virtualized") == "true":
            self.markers.add(COMMENT_ROUTE_VIRTUALIZED)
        if attrs.get("data-disappearing") == "true":
            self.markers.add(COMMENT_ROUTE_DISAPPEARING)
        if attrs.get("data-login-required") == "true":
            self.markers.add(COMMENT_ROUTE_LOGIN_REQUIRED)
        if attrs.get("data-challenge-required") == "true":
            self.markers.add(COMMENT_ROUTE_CHALLENGE)

    def _flush_script(self) -> None:
        script_id = self._active_script_id
        payload = "".join(self._script_parts).strip()
        self._active_script_id = ""
        self._script_parts = []
        if not payload:
            return
        if script_id == "cursor-state":
            self.markers.add(COMMENT_ROUTE_CURSOR)
            try:
                parsed = json.loads(payload)
            except json.JSONDecodeError:
                return
            self.cursor = str(parsed.get("cursor") or "")
            self.stop_reason = str(parsed.get("stop_reason") or self.stop_reason)
        elif script_id in {"encoded-comments", "closed-shadow-comments"}:
            self.markers.add(COMMENT_ROUTE_ENCODED_STATE)
            if script_id == "closed-shadow-comments":
                self.markers.add(COMMENT_ROUTE_CLOSED_SHADOW_PAYLOAD)
            try:
                parsed = json.loads(payload)
            except json.JSONDecodeError:
                return
            for raw in parsed.get("comments", ()):
                self.records.append(_structured_comment_to_record(raw))


def _structured_comment_to_record(raw: Any) -> dict[str, Any]:
    if isinstance(raw, str):
        return {"comment_id": raw, "text_parts": [raw]}
    if not isinstance(raw, dict):
        return {"comment_id": "", "text_parts": []}
    return {
        "author": str(raw.get("author") or ""),
        "capture_method": str(raw.get("capture_method") or ""),
        "comment_id": str(raw.get("id") or raw.get("comment_id") or ""),
        "depth": _int_or_zero(raw.get("depth", 0)),
        "loaded_order": _int_or_zero(raw.get("loaded_order", 0)),
        "observed_at": str(raw.get("observed_at") or ""),
        "parent_id": str(raw.get("parent_id") or ""),
        "permalink": str(raw.get("permalink") or ""),
        "posted_at": str(raw.get("posted_at") or ""),
        "raw_reference": str(raw.get("raw_reference") or ""),
        "reaction_count": _int_or_zero(raw.get("reaction_count", raw.get("reactions", 0))),
        "reply_count": _int_or_zero(raw.get("reply_count", 0)),
        "source_order": _int_or_zero(raw.get("source_order", 0)),
        "status": str(raw.get("status") or raw.get("state") or ""),
        "text_parts": [str(raw.get("text") or "")],
        "thread_id": str(raw.get("thread_id") or ""),
    }


def _normalize_text(value: str) -> str:
    return " ".join(str(value or "").split())


def _int_or_zero(value: object) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _record_to_comment(raw_record: dict[str, Any], ordinal: int) -> CommentRecord:
    status = str(raw_record.get("status") or COMMENT_STATUS_VISIBLE)
    return CommentRecord(
        comment_id=str(raw_record.get("comment_id") or ""),
        author=str(raw_record.get("author") or ""),
        parent_id=str(raw_record.get("parent_id") or ""),
        depth=int(raw_record.get("depth") or 0),
        text=_normalize_text(" ".join(raw_record.get("text_parts") or [])),
        first_seen_ordinal=ordinal,
        last_seen_ordinal=ordinal,
        status=status,
        thread_id=str(raw_record.get("thread_id") or ""),
        posted_at=str(raw_record.get("posted_at") or ""),
        observed_at=str(raw_record.get("observed_at") or ""),
        reaction_count=int(raw_record.get("reaction_count") or 0),
        reply_count=int(raw_record.get("reply_count") or 0),
        permalink=str(raw_record.get("permalink") or ""),
        source_order=int(raw_record.get("source_order") or ordinal),
        loaded_order=int(raw_record.get("loaded_order") or ordinal),
        capture_method=str(raw_record.get("capture_method") or ""),
        raw_reference=str(raw_record.get("raw_reference") or ""),
    )


def _status_and_completeness(
    *,
    comments: tuple[CommentRecord, ...],
    markers: tuple[str, ...],
) -> tuple[str, str]:
    if COMMENT_ROUTE_LOGIN_REQUIRED in markers:
        return CAPTURE_STATUS_LOGIN_REQUIRED, COMPLETENESS_PARTIAL_LOGIN_REQUIRED
    if COMMENT_ROUTE_CHALLENGE in markers:
        return CAPTURE_STATUS_CHALLENGE_REQUIRES_USER, COMPLETENESS_PARTIAL_CHALLENGE
    if COMMENT_ROUTE_VIRTUALIZED in markers:
        return CAPTURE_STATUS_PARTIAL if not comments else CAPTURE_STATUS_SUCCESS, COMPLETENESS_PARTIAL_VIRTUALIZED
    if comments:
        return CAPTURE_STATUS_SUCCESS, COMPLETENESS_COMPLETE
    return CAPTURE_STATUS_PARTIAL, COMPLETENESS_PARTIAL_UNKNOWN


def extract_comments_from_html(html: str, *, source_url: str = "") -> CommentCaptureResult:
    parser = _CommentHTMLParser()
    warnings: list[str] = []
    try:
        parser.feed(html or "")
    except Exception:
        warnings.append("HTML parser reported a non-secret parsing issue; comments may be partial.")

    comments: list[CommentRecord] = []
    seen: set[str] = set()
    duplicates: list[str] = []
    ordinal = 0
    for raw_record in parser.records:
        comment_id = str(raw_record.get("comment_id") or "")
        if not comment_id:
            continue
        if comment_id in seen:
            duplicates.append(comment_id)
            continue
        seen.add(comment_id)
        ordinal += 1
        comments.append(_record_to_comment(raw_record, ordinal))

    markers = tuple(sorted(parser.markers or {COMMENT_ROUTE_STATIC if comments else ""} - {""}))
    if not comments and COMMENT_ROUTE_LOGIN_REQUIRED not in markers and COMMENT_ROUTE_CHALLENGE not in markers:
        warnings.append("No comment records found in supplied HTML.")
    if duplicates:
        warnings.append("Duplicate comment IDs were ignored: " + ", ".join(sorted(set(duplicates))))
    if COMMENT_ROUTE_LOGIN_REQUIRED in markers:
        warnings.append("Login-required comment state detected; bypass was not attempted.")
    if COMMENT_ROUTE_CHALLENGE in markers:
        warnings.append("Challenge-required comment state detected; bypass was not attempted.")

    comments_tuple = tuple(comments)
    status, completeness = _status_and_completeness(comments=comments_tuple, markers=markers)
    return CommentCaptureResult(
        source_url=source_url,
        status=status,
        completeness=completeness,
        comments=comments_tuple,
        duplicate_comment_ids=tuple(dict.fromkeys(duplicates)),
        capture_routes=markers,
        cursor=parser.cursor,
        stop_reason=parser.stop_reason,
        login_required=COMMENT_ROUTE_LOGIN_REQUIRED in markers,
        challenge_required=COMMENT_ROUTE_CHALLENGE in markers,
        warnings=tuple(warnings),
    )


def extract_comments_from_html_sequence(
    html_pages: Iterable[str],
    *,
    source_url: str = "",
) -> CommentCaptureResult:
    merged: tuple[CommentRecord, ...] = ()
    duplicates: list[str] = []
    routes: set[str] = set()
    warnings: list[str] = []
    cursor = ""
    stop_reason = ""
    page_count = 0
    ordinal_offset = 0
    for page_count, html in enumerate(html_pages, start=1):
        result = extract_comments_from_html(html, source_url=source_url)
        adjusted_comments = tuple(
            replace(
                comment,
                first_seen_ordinal=comment.first_seen_ordinal + ordinal_offset,
                last_seen_ordinal=comment.last_seen_ordinal + ordinal_offset,
            )
            for comment in result.comments
        )
        ordinal_offset += len(result.comments)
        merged = merge_comment_records(merged, adjusted_comments)
        duplicates.extend(result.duplicate_comment_ids)
        routes.update(result.capture_routes)
        warnings.extend(result.warnings)
        cursor = result.cursor or cursor
        stop_reason = result.stop_reason or stop_reason

    comments_tuple = tuple(merged)
    markers = tuple(sorted(routes))
    status, completeness = _status_and_completeness(comments=comments_tuple, markers=markers)
    return CommentCaptureResult(
        source_url=source_url,
        status=status,
        completeness=completeness,
        comments=comments_tuple,
        duplicate_comment_ids=tuple(dict.fromkeys(duplicates)),
        capture_routes=markers,
        cursor=cursor,
        stop_reason=stop_reason,
        incremental_batches=page_count,
        warnings=tuple(dict.fromkeys(warnings)),
    )


def merge_comment_records(
    existing: Iterable[CommentRecord],
    new: Iterable[CommentRecord],
) -> tuple[CommentRecord, ...]:
    merged: dict[str, CommentRecord] = {comment.comment_id: comment for comment in existing}
    for comment in new:
        previous = merged.get(comment.comment_id)
        if previous is None:
            merged[comment.comment_id] = comment
            continue
        merged[comment.comment_id] = CommentRecord(
            comment_id=previous.comment_id,
            text=comment.text or previous.text,
            author=comment.author or previous.author,
            parent_id=comment.parent_id or previous.parent_id,
            depth=comment.depth or previous.depth,
            first_seen_ordinal=previous.first_seen_ordinal,
            last_seen_ordinal=max(previous.last_seen_ordinal, comment.last_seen_ordinal),
            status=comment.status or previous.status,
            thread_id=comment.thread_id or previous.thread_id,
            posted_at=comment.posted_at or previous.posted_at,
            observed_at=comment.observed_at or previous.observed_at,
            reaction_count=comment.reaction_count or previous.reaction_count,
            reply_count=comment.reply_count or previous.reply_count,
            permalink=comment.permalink or previous.permalink,
            source_order=previous.source_order or comment.source_order,
            loaded_order=comment.loaded_order or previous.loaded_order,
            capture_method=comment.capture_method or previous.capture_method,
            raw_reference=comment.raw_reference or previous.raw_reference,
        )
    return tuple(sorted(merged.values(), key=lambda item: (item.first_seen_ordinal, item.comment_id)))
