from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from typing import Any, Iterable, Mapping, Sequence


MSN_MANUAL_COMMENTS_EXTRACTION_SCHEMA_VERSION = "msn_manual_comments_extraction_v1"

_SECRET_KEY_RE = re.compile(r"(?:api[_-]?key|secret|token|password|credential|bearer|authorization)", re.I)
_FULL_PATH_RE = re.compile(r"(?:^|[\s'\"])(?:[A-Za-z]:[\\/]|\\\\|/(?:home|mnt|Users|Volumes|tmp|var)/)")
_ALLOWED_URL_RE = re.compile(r"^https?://[^\s]+$", re.I)
_SAFE_FILE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_. -]{0,180}$")
_WS_RE = re.compile(r"\s+")


def _json_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False).encode("utf-8")


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _safe_text(value: Any, *, field_name: str, allow_empty: bool = False, max_length: int = 200000) -> str:
    if _SECRET_KEY_RE.search(field_name):
        raise ValueError(f"secret-like field is not allowed: {field_name}")
    text = str(value or "").replace("\x00", " ")
    if not text.strip() and not allow_empty:
        raise ValueError(f"{field_name} must not be empty")
    if len(text) > max_length:
        raise ValueError(f"{field_name} is too long")
    if _SECRET_KEY_RE.search(text):
        raise ValueError(f"secret-like value is not allowed for {field_name}")
    if field_name != "artifact_text" and _FULL_PATH_RE.search(text):
        raise ValueError(f"full local path is not allowed for {field_name}")
    if field_name == "artifact_text":
        return text.strip()
    return _WS_RE.sub(" ", text).strip()


def _safe_url(value: str) -> str:
    text = _safe_text(value, field_name="source_url", max_length=2000)
    if not _ALLOWED_URL_RE.match(text):
        raise ValueError("source_url must be an http(s) URL")
    return text


def _host_hint(url: str) -> str:
    host = re.sub(r"^https?://", "", url, flags=re.I).split("/", 1)[0].lower()
    return host[:80] or "unknown-host"


def _safe_file_name(value: str | None) -> str:
    if not value:
        return "operator_supplied_comments_artifact"
    name = str(value).replace("\\", "/").rsplit("/", 1)[-1]
    if ":" in name or not _SAFE_FILE_RE.match(name):
        raise ValueError(f"unsafe artifact file name: {value!r}")
    return name


@dataclass(frozen=True)
class MSNManualComment:
    comment_id: str
    author_display: str
    text: str
    timestamp_text: str = ""
    like_count: int | None = None
    reply_count: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class MSNManualCommentsExtraction:
    schema_version: str
    source_url: str
    source_url_host_hint: str
    comments: tuple[MSNManualComment, ...]
    artifact_file_name: str
    artifact_sha256: str
    artifact_byte_count: int
    comment_count: int
    comments_text_sha256: str
    manual_operator_artifact_supplied: bool = True
    data_extraction_implemented: bool = True
    review_required: bool = True
    full_local_path_serialized: bool = False
    raw_payload_included: bool = False
    live_network_request_performed_by_tool: bool = False
    browser_automation_performed_by_tool: bool = False
    archive_submission_performed_by_tool: bool = False
    credential_value_read: bool = False
    completed_capture_claimed: bool = False
    verified_capture_claimed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _comment_from_mapping(index: int, item: Mapping[str, Any]) -> MSNManualComment:
    author = item.get("author") or item.get("author_display") or item.get("user") or item.get("name") or "unknown"
    text = item.get("text") or item.get("comment") or item.get("body") or item.get("content") or ""
    timestamp = item.get("timestamp") or item.get("timestamp_text") or item.get("time") or ""
    comment_id = item.get("id") or item.get("comment_id") or f"operator_comment_{index:04d}"
    like_count = item.get("like_count") or item.get("likes")
    reply_count = item.get("reply_count") or item.get("replies")
    return MSNManualComment(
        comment_id=_safe_text(comment_id, field_name="comment_id", max_length=120),
        author_display=_safe_text(author, field_name="author_display", max_length=200),
        text=_safe_text(text, field_name="comment_text", max_length=5000),
        timestamp_text=_safe_text(timestamp, field_name="timestamp_text", allow_empty=True, max_length=200),
        like_count=int(like_count) if isinstance(like_count, int) or str(like_count).isdigit() else None,
        reply_count=int(reply_count) if isinstance(reply_count, int) or str(reply_count).isdigit() else None,
    )


def _parse_json_comments(text: str) -> list[MSNManualComment]:
    parsed = json.loads(text)
    if isinstance(parsed, Mapping):
        items = parsed.get("comments") or parsed.get("items") or parsed.get("data")
    else:
        items = parsed
    if not isinstance(items, list):
        raise ValueError("comments JSON must be a list or an object with comments/items/data list")
    comments: list[MSNManualComment] = []
    for index, item in enumerate(items, start=1):
        if isinstance(item, Mapping):
            comments.append(_comment_from_mapping(index, item))
        else:
            comments.append(MSNManualComment(f"operator_comment_{index:04d}", "unknown", _safe_text(item, field_name="comment_text", max_length=5000)))
    return comments


def _parse_text_comments(text: str) -> list[MSNManualComment]:
    comments: list[MSNManualComment] = []
    blocks = [block.strip() for block in re.split(r"\n\s*\n", text) if block.strip()]
    if len(blocks) <= 1:
        blocks = [line.strip() for line in text.splitlines() if line.strip()]
    for index, block in enumerate(blocks, start=1):
        author = "unknown"
        comment = block
        if ":" in block:
            possible_author, possible_text = block.split(":", 1)
            if 0 < len(possible_author) <= 80 and possible_text.strip():
                author = possible_author
                comment = possible_text
        comments.append(
            MSNManualComment(
                comment_id=f"operator_comment_{index:04d}",
                author_display=_safe_text(author, field_name="author_display", max_length=200),
                text=_safe_text(comment, field_name="comment_text", max_length=5000),
            )
        )
    return comments


def _parse_comments(text: str) -> list[MSNManualComment]:
    stripped = text.strip()
    if stripped.startswith("[") or stripped.startswith("{"):
        return _parse_json_comments(stripped)
    lines = [line for line in stripped.splitlines() if line.strip()]
    if lines and all(line.lstrip().startswith("{") for line in lines):
        return [_comment_from_mapping(index, json.loads(line)) for index, line in enumerate(lines, start=1)]
    return _parse_text_comments(stripped)


def extract_msn_manual_comments(
    *,
    source_url: str,
    artifact_text: str,
    artifact_file_name: str | None = None,
) -> MSNManualCommentsExtraction:
    url = _safe_url(source_url)
    text = str(_safe_text(artifact_text, field_name="artifact_text"))
    file_name = _safe_file_name(artifact_file_name)
    comments = tuple(_parse_comments(text))
    if not comments:
        raise ValueError("no comments were extracted")
    joined = "\n".join(comment.text for comment in comments)
    return MSNManualCommentsExtraction(
        schema_version=MSN_MANUAL_COMMENTS_EXTRACTION_SCHEMA_VERSION,
        source_url=url,
        source_url_host_hint=_host_hint(url),
        comments=comments,
        artifact_file_name=file_name,
        artifact_sha256=_sha256_text(text),
        artifact_byte_count=len(text.encode("utf-8")),
        comment_count=len(comments),
        comments_text_sha256=_sha256_text(joined),
    )


def msn_manual_comments_extraction_to_json(extraction: MSNManualCommentsExtraction) -> str:
    return _json_bytes(extraction.to_dict()).decode("utf-8")
