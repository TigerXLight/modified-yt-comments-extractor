from __future__ import annotations

import hashlib
import html
import json
import re
from dataclasses import asdict, dataclass
from html.parser import HTMLParser
from typing import Any, Iterable


MSN_MANUAL_ARTICLE_EXTRACTION_SCHEMA_VERSION = "msn_manual_article_extraction_v1"

_SECRET_KEY_RE = re.compile(r"(?:api[_-]?key|secret|token|password|credential|bearer|authorization)", re.I)
_FULL_PATH_RE = re.compile(r"(?:^|[\s'\"])(?:[A-Za-z]:[\\/]|\\\\|/(?:home|mnt|Users|Volumes|tmp|var)/)")
_ALLOWED_URL_RE = re.compile(r"^https?://[^\s]+$", re.I)
_SAFE_FILE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_. -]{0,180}$")
_TAG_RE = re.compile(r"<[^>]+>")
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
    if field_name not in {"artifact_text", "article_text"} and _FULL_PATH_RE.search(text):
        raise ValueError(f"full local path is not allowed for {field_name}")
    return text


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
        return "operator_supplied_article_artifact"
    name = str(value).replace("\\", "/").rsplit("/", 1)[-1]
    if ":" in name or not _SAFE_FILE_RE.match(name):
        raise ValueError(f"unsafe artifact file name: {value!r}")
    return name


def _collapse_text(value: str) -> str:
    return _WS_RE.sub(" ", html.unescape(value)).strip()


class _ArticleHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._capture_title = False
        self._capture_h1 = False
        self.title_parts: list[str] = []
        self.h1_parts: list[str] = []
        self.visible_parts: list[str] = []
        self.meta: dict[str, str] = {}
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        attr_map = {name.lower(): value or "" for name, value in attrs}
        if tag in {"script", "style", "noscript", "svg"}:
            self._skip_depth += 1
        if tag == "title":
            self._capture_title = True
        if tag == "h1":
            self._capture_h1 = True
        if tag == "meta":
            key = (attr_map.get("property") or attr_map.get("name") or "").lower()
            content = attr_map.get("content", "")
            if key and content:
                self.meta[key] = _collapse_text(content)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in {"script", "style", "noscript", "svg"} and self._skip_depth:
            self._skip_depth -= 1
        if tag == "title":
            self._capture_title = False
        if tag == "h1":
            self._capture_h1 = False

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        text = _collapse_text(data)
        if not text:
            return
        if self._capture_title:
            self.title_parts.append(text)
        if self._capture_h1:
            self.h1_parts.append(text)
        if len(text) >= 2:
            self.visible_parts.append(text)


def _extract_from_html(artifact_text: str) -> tuple[str, str, tuple[str, ...]]:
    parser = _ArticleHTMLParser()
    parser.feed(artifact_text)
    title = parser.meta.get("og:title") or _collapse_text(" ".join(parser.h1_parts)) or _collapse_text(" ".join(parser.title_parts))
    visible = parser.visible_parts
    filtered: list[str] = []
    boilerplate = {"share", "comments", "sign in", "read more", "advertisement", "skip to content"}
    for item in visible:
        lowered = item.lower().strip(" .")
        if lowered in boilerplate:
            continue
        if item == title:
            continue
        filtered.append(item)
    article_text = "\n".join(dict.fromkeys(filtered)).strip()
    byline_candidates = []
    for key in ("author", "article:author", "og:site_name"):
        if parser.meta.get(key):
            byline_candidates.append(parser.meta[key])
    return title, article_text, tuple(byline_candidates)


def _extract_from_plain_text(artifact_text: str) -> tuple[str, str, tuple[str, ...]]:
    lines = [_collapse_text(line) for line in artifact_text.splitlines()]
    lines = [line for line in lines if line]
    if not lines:
        raise ValueError("article artifact does not contain extractable text")
    title = lines[0]
    byline: list[str] = []
    body_lines: list[str] = []
    for line in lines[1:]:
        if line.lower().startswith(("by ", "author:")) and not byline:
            byline.append(line)
        else:
            body_lines.append(line)
    body = "\n".join(body_lines or lines[1:]).strip()
    return title, body, tuple(byline)


@dataclass(frozen=True)
class MSNManualArticleExtraction:
    schema_version: str
    source_url: str
    source_url_host_hint: str
    title: str
    article_text: str
    byline_candidates: tuple[str, ...]
    artifact_file_name: str
    artifact_sha256: str
    artifact_byte_count: int
    article_text_sha256: str
    article_text_char_count: int
    manual_operator_artifact_supplied: bool = True
    data_extraction_implemented: bool = True
    review_required: bool = True
    raw_html_payload_included: bool = False
    full_local_path_serialized: bool = False
    live_network_request_performed_by_tool: bool = False
    browser_automation_performed_by_tool: bool = False
    archive_submission_performed_by_tool: bool = False
    credential_value_read: bool = False
    completed_capture_claimed: bool = False
    verified_capture_claimed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def extract_msn_manual_article(
    *,
    source_url: str,
    artifact_text: str,
    artifact_file_name: str | None = None,
) -> MSNManualArticleExtraction:
    url = _safe_url(source_url)
    text = _safe_text(artifact_text, field_name="artifact_text")
    file_name = _safe_file_name(artifact_file_name)
    if _TAG_RE.search(text):
        title, article_text, byline_candidates = _extract_from_html(text)
    else:
        title, article_text, byline_candidates = _extract_from_plain_text(text)
    title = _safe_text(title, field_name="article_title", max_length=1000)
    article_text = _safe_text(article_text, field_name="article_text")
    if len(article_text) < 20:
        raise ValueError("article_text is too short for a useful extraction")
    return MSNManualArticleExtraction(
        schema_version=MSN_MANUAL_ARTICLE_EXTRACTION_SCHEMA_VERSION,
        source_url=url,
        source_url_host_hint=_host_hint(url),
        title=title,
        article_text=article_text,
        byline_candidates=tuple(_safe_text(item, field_name="byline_candidate", max_length=300) for item in byline_candidates),
        artifact_file_name=file_name,
        artifact_sha256=_sha256_text(text),
        artifact_byte_count=len(text.encode("utf-8")),
        article_text_sha256=_sha256_text(article_text),
        article_text_char_count=len(article_text),
    )


def msn_manual_article_extraction_to_json(extraction: MSNManualArticleExtraction) -> str:
    return _json_bytes(extraction.to_dict()).decode("utf-8")
