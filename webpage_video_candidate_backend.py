from __future__ import annotations

import hashlib
import html
import re
from dataclasses import asdict, dataclass, is_dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Iterable, Mapping
from urllib.parse import urljoin, urlparse

from jdownloader_capability_router import build_jdownloader_capability_decision


VIDEO_CANDIDATE_KIND_FILE = "file"
VIDEO_CANDIDATE_KIND_STREAM = "stream"
VIDEO_CANDIDATE_KIND_EMBED = "embed"
VIDEO_CANDIDATE_KIND_UNKNOWN = "unknown"

VIDEO_DISCOVERY_METHOD_STATIC_HTML = "static_html_media_url_scan"
VIDEO_ROUTE_PREFERENCE = "try_jdownloader_api3128_before_yt_dlp"

_MEDIA_EXTENSIONS = (
    ".mp4",
    ".m4v",
    ".webm",
    ".mov",
    ".mkv",
    ".avi",
    ".flv",
    ".ts",
    ".m2ts",
    ".3gp",
    ".mp3",
    ".m4a",
    ".aac",
    ".ogg",
    ".opus",
)
_STREAM_EXTENSIONS = (
    ".m3u8",
    ".mpd",
    ".f4m",
    ".ism/manifest",
)
_VIDEO_MIME_HINTS = (
    "video/",
    "audio/",
    "application/vnd.apple.mpegurl",
    "application/x-mpegurl",
    "application/dash+xml",
)
_EMBED_HOST_HINTS = (
    "youtube.com",
    "youtu.be",
    "player.vimeo.com",
    "vimeo.com",
    "dailymotion.com",
    "facebook.com",
    "twitter.com",
    "x.com",
    "tiktok.com",
)


@dataclass(frozen=True)
class WebpageVideoCandidate:
    candidate_id: str
    url: str
    source_url: str = ""
    kind: str = VIDEO_CANDIDATE_KIND_UNKNOWN
    mime_type: str = ""
    extension: str = ""
    title: str = ""
    width: int = 0
    height: int = 0
    source_tag: str = ""
    source_attr: str = ""
    detection_reason: str = ""
    selected_by_default: bool = False
    route_preference: str = VIDEO_ROUTE_PREFERENCE

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class WebpageVideoDiscoveryResult:
    source_url: str
    canonical_url: str
    discovery_method: str = VIDEO_DISCOVERY_METHOD_STATIC_HTML
    candidates: tuple[WebpageVideoCandidate, ...] = ()
    candidate_count: int = 0
    jdownloader_capability_decision: Mapping[str, Any] | None = None
    recommended_backend_id: str = ""
    route_preference: str = VIDEO_ROUTE_PREFERENCE
    warnings: tuple[str, ...] = ()

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


def _clean_url(value: Any) -> str:
    text = html.unescape(str(value or "")).strip().strip('"').strip("'")
    if not text or text.lower().startswith(("javascript:", "data:text", "mailto:")):
        return ""
    return text


def _safe_int(value: Any) -> int:
    try:
        text = re.sub(r"[^0-9]", "", str(value or ""))
        return int(text or 0)
    except Exception:
        return 0


def _path_extension(url: str) -> str:
    parsed = urlparse(url)
    path = parsed.path.lower()
    for suffix in sorted((*_STREAM_EXTENSIONS, *_MEDIA_EXTENSIONS), key=len, reverse=True):
        if path.endswith(suffix):
            return suffix
    return Path(path).suffix.lower()


def classify_video_candidate_url(url: str, *, mime_type: str = "") -> tuple[str, str]:
    extension = _path_extension(url)
    mime = str(mime_type or "").lower()
    if extension in _STREAM_EXTENSIONS or any(token in mime for token in ("mpegurl", "dash+xml")):
        return VIDEO_CANDIDATE_KIND_STREAM, extension
    if extension in _MEDIA_EXTENSIONS or mime.startswith(("video/", "audio/")):
        return VIDEO_CANDIDATE_KIND_FILE, extension
    host = (urlparse(url).netloc or "").lower()
    if any(hint in host for hint in _EMBED_HOST_HINTS):
        return VIDEO_CANDIDATE_KIND_EMBED, extension
    return VIDEO_CANDIDATE_KIND_UNKNOWN, extension


def _candidate_id(url: str, source_tag: str, source_attr: str) -> str:
    digest = hashlib.sha1(f"{source_tag}\\0{source_attr}\\0{url}".encode("utf-8", "replace")).hexdigest()
    return f"video-{digest[:16]}"


def _looks_like_media_url(url: str, *, mime_type: str = "") -> bool:
    kind, _extension = classify_video_candidate_url(url, mime_type=mime_type)
    if kind != VIDEO_CANDIDATE_KIND_UNKNOWN:
        return True
    lower = url.lower()
    return any(token in lower for token in ("/video/", "videoplayback", "playlist.m3u8", "manifest.mpd"))


class _VideoHtmlParser(HTMLParser):
    def __init__(self, base_url: str) -> None:
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.candidates: list[WebpageVideoCandidate] = []
        self._seen_urls: set[str] = set()
        self._inside_video = 0
        self._current_title = ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        lower_tag = tag.lower()
        attr = {str(k or "").lower(): str(v or "") for k, v in attrs}
        if lower_tag == "title":
            self._current_title = ""
        if lower_tag == "video":
            self._inside_video += 1
        if lower_tag in {"video", "audio", "source", "track", "a", "link", "iframe", "embed"}:
            for attr_name in ("src", "href", "data-src", "data-url"):
                self._add_from_attr(lower_tag, attr, attr_name)
        if lower_tag == "meta":
            property_name = (attr.get("property") or attr.get("name") or "").lower()
            if property_name in {
                "og:video",
                "og:video:url",
                "og:video:secure_url",
                "twitter:player",
                "twitter:player:stream",
                "twitter:player:stream:content_type",
            }:
                self._add_url(attr.get("content", ""), lower_tag, "content", attr, reason=f"meta {property_name}")

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "video" and self._inside_video:
            self._inside_video -= 1

    def _add_from_attr(self, tag: str, attr: Mapping[str, str], attr_name: str) -> None:
        raw = attr.get(attr_name, "")
        if not raw:
            return
        mime = attr.get("type", "")
        reason = f"{tag}[{attr_name}]"
        if tag == "source" and self._inside_video:
            reason = "video/source element"
        self._add_url(raw, tag, attr_name, attr, reason=reason, mime_type=mime)

    def _add_url(
        self,
        raw_url: str,
        tag: str,
        attr_name: str,
        attr: Mapping[str, str],
        *,
        reason: str,
        mime_type: str = "",
    ) -> None:
        cleaned = _clean_url(raw_url)
        if not cleaned:
            return
        absolute = urljoin(self.base_url, cleaned)
        mime = mime_type or attr.get("type", "")
        if not _looks_like_media_url(absolute, mime_type=mime):
            return
        if absolute in self._seen_urls:
            return
        kind, extension = classify_video_candidate_url(absolute, mime_type=mime)
        self._seen_urls.add(absolute)
        title = attr.get("title") or attr.get("aria-label") or attr.get("alt") or ""
        self.candidates.append(
            WebpageVideoCandidate(
                candidate_id=_candidate_id(absolute, tag, attr_name),
                url=absolute,
                source_url=self.base_url,
                kind=kind,
                mime_type=str(mime or ""),
                extension=extension,
                title=str(title or ""),
                width=_safe_int(attr.get("width")),
                height=_safe_int(attr.get("height")),
                source_tag=tag,
                source_attr=attr_name,
                detection_reason=reason,
                selected_by_default=kind in {VIDEO_CANDIDATE_KIND_FILE, VIDEO_CANDIDATE_KIND_STREAM},
            )
        )


def discover_webpage_video_candidates_from_html(
    source_url: str,
    html_text: str,
    *,
    capability_decision: Mapping[str, Any] | None = None,
) -> WebpageVideoDiscoveryResult:
    parser = _VideoHtmlParser(source_url)
    warnings: list[str] = []
    try:
        parser.feed(str(html_text or ""))
    except Exception as exc:
        warnings.append(f"Static HTML video scan parse warning: {type(exc).__name__}: {exc}")
    decision = dict(capability_decision or build_jdownloader_capability_decision(source_url).to_dict())
    candidates = tuple(parser.candidates)
    return WebpageVideoDiscoveryResult(
        source_url=str(source_url or ""),
        canonical_url=str(source_url or ""),
        candidates=candidates,
        candidate_count=len(candidates),
        jdownloader_capability_decision=decision,
        recommended_backend_id=str(decision.get("recommended_backend_id") or ""),
        warnings=tuple(warnings),
    )


def summarize_webpage_video_candidate_kinds(candidates: Iterable[WebpageVideoCandidate]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for candidate in candidates:
        counts[candidate.kind] = counts.get(candidate.kind, 0) + 1
    return counts
