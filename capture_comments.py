from __future__ import annotations

from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Any, Iterable

from capture_status import (
    CAPTURE_STATUS_PARTIAL,
    CAPTURE_STATUS_SUCCESS,
    COMPLETENESS_COMPLETE,
    COMPLETENESS_PARTIAL_UNKNOWN,
)


COMMENT_STATUS_VISIBLE = "visible"
COMMENT_STATUS_TOMBSTONE = "tombstone"

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

    def to_dict(self) -> dict[str, Any]:
        return {
            "author": self.author,
            "comment_id": self.comment_id,
            "depth": self.depth,
            "first_seen_ordinal": self.first_seen_ordinal,
            "last_seen_ordinal": self.last_seen_ordinal,
            "parent_id": self.parent_id,
            "status": self.status,
            "text": self.text,
        }


@dataclass(frozen=True)
class CommentCaptureResult:
    source_url: str
    status: str
    completeness: str
    comments: tuple[CommentRecord, ...] = ()
    duplicate_comment_ids: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    scope: str = COMMENTS_CAPTURE_SCOPE

    def to_dict(self) -> dict[str, Any]:
        return {
            "comments": [comment.to_dict() for comment in self.comments],
            "completeness": self.completeness,
            "duplicate_comment_ids": list(self.duplicate_comment_ids),
            "scope": self.scope,
            "source_url": self.source_url,
            "status": self.status,
            "warnings": list(self.warnings),
        }


class _CommentHTMLParser(HTMLParser):
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
        comment_id = attr_map.get("data-comment-id", "")
        if comment_id:
            self._active = {
                "author": attr_map.get("data-author", ""),
                "comment_id": comment_id,
                "depth": _int_or_zero(attr_map.get("data-depth", "")),
                "parent_id": attr_map.get("data-parent-id", ""),
                "text_parts": [],
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
            self._active["text_parts"].append(text)


def _normalize_text(value: str) -> str:
    return " ".join(str(value or "").split())


def _int_or_zero(value: str) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


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
        comments.append(
            CommentRecord(
                comment_id=comment_id,
                author=str(raw_record.get("author") or ""),
                parent_id=str(raw_record.get("parent_id") or ""),
                depth=int(raw_record.get("depth") or 0),
                text=_normalize_text(" ".join(raw_record.get("text_parts") or [])),
                first_seen_ordinal=ordinal,
                last_seen_ordinal=ordinal,
            )
        )

    if not comments:
        warnings.append("No comment records found in supplied HTML.")
    if duplicates:
        warnings.append("Duplicate comment IDs were ignored: " + ", ".join(sorted(set(duplicates))))

    return CommentCaptureResult(
        source_url=source_url,
        status=CAPTURE_STATUS_SUCCESS if comments else CAPTURE_STATUS_PARTIAL,
        completeness=COMPLETENESS_COMPLETE if comments else COMPLETENESS_PARTIAL_UNKNOWN,
        comments=tuple(comments),
        duplicate_comment_ids=tuple(dict.fromkeys(duplicates)),
        warnings=tuple(warnings),
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
            status=COMMENT_STATUS_VISIBLE,
        )
    return tuple(sorted(merged.values(), key=lambda item: (item.first_seen_ordinal, item.comment_id)))
