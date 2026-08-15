from __future__ import annotations

import html
import json
import re
import struct
from dataclasses import asdict, dataclass, is_dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence
from urllib.parse import urljoin, urlsplit


TWITTER_STATUS_EVIDENCE_SCHEMA_VERSION = "twitter_status_evidence.v73"
TWITTER_SCREENSHOT_MANIFEST_SCHEMA_VERSION = "twitter_status_screenshot_manifest.v73"
TWITTER_DIRECT_MEDIA_HOSTS = {"pbs.twimg.com", "video.twimg.com"}


@dataclass(frozen=True)
class TwitterStatusLink:
    url: str
    display_text: str = ""
    link_type: str = ""
    source: str = "rendered_dom_anchor"

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class TwitterStatusCounter:
    name: str
    raw_value: str
    normalized_value: int | None = None
    source: str = "rendered_dom"
    needs_review: bool = False

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class TwitterStatusMediaMarker:
    status_id: str
    screen_name: str
    media_id: str
    media_type: str
    direct_url: str
    source_url: str
    source_kind: str
    safe_to_handoff_to_jd: bool
    provenance: str = ""

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class TwitterScreenshotTile:
    path: str
    exists: bool
    size_bytes: int = 0
    width: int = 0
    height: int = 0
    tile_index: int = 0
    scroll_x: int = 0
    scroll_y: int = 0
    capture_role: str = "full_page_or_viewport_capture"

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class TwitterStatusScreenshotManifest:
    schema_version: str
    source_url: str
    status_id: str
    screen_name: str
    capture_strategy: str
    tiles: tuple[TwitterScreenshotTile, ...]
    stitched_full_page_path: str = ""
    document_height: int = 0
    viewport_width: int = 0
    viewport_height: int = 0
    tweet_text_visible: bool = False
    media_visible: bool = False
    counters_visible: bool = False
    notes: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class TwitterStatusEvidenceBundle:
    schema_version: str
    source_url: str
    canonical_url: str
    status_id: str
    author_name: str
    screen_name: str
    post_text: str
    posted_at: str
    views: str
    counters: tuple[TwitterStatusCounter, ...]
    links: tuple[TwitterStatusLink, ...]
    media_markers: tuple[TwitterStatusMediaMarker, ...]
    screenshot_manifest_path: str
    extraction_source: str
    completion_state: str
    warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


class _RenderedDomParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title_parts: list[str] = []
        self._in_title = False
        self._skip_depth = 0
        self.text_tokens: list[str] = []
        self.metas: dict[str, list[str]] = {}
        self.links: list[dict[str, str]] = []
        self.anchors: list[dict[str, str]] = []
        self.images: list[dict[str, str]] = []
        self._anchor: dict[str, Any] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        attr = {str(k).lower(): str(v or "") for k, v in attrs}
        if tag in {"script", "style", "noscript", "svg"}:
            self._skip_depth += 1
        if tag == "title":
            self._in_title = True
        elif tag == "meta":
            key = attr.get("property") or attr.get("name")
            content = attr.get("content", "")
            if key and content:
                self.metas.setdefault(key, []).append(html.unescape(content).strip())
        elif tag == "link":
            self.links.append(attr)
        elif tag == "a":
            self._anchor = {"href": attr.get("href", ""), "text_parts": []}
        elif tag == "img":
            self.images.append(attr)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in {"script", "style", "noscript", "svg"} and self._skip_depth:
            self._skip_depth -= 1
        if tag == "title":
            self._in_title = False
        if tag == "a" and self._anchor is not None:
            parts = [str(part) for part in self._anchor.get("text_parts", [])]
            text = _clean_space(" ".join(parts))
            self.anchors.append({"href": str(self._anchor.get("href") or ""), "text": text})
            self._anchor = None

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        if self._in_title:
            self.title_parts.append(data)
        text = _clean_space(data)
        if not text:
            return
        self.text_tokens.append(text)
        if self._anchor is not None:
            self._anchor.setdefault("text_parts", []).append(text)


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


def _clean_space(value: Any) -> str:
    return re.sub(r"\s+", " ", html.unescape(str(value or ""))).strip()


def _read_json(path: Path, default: Any) -> Any:
    try:
        if path.is_file():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default
    return default


def _read_jsonl(path: Path) -> list[Any]:
    rows: list[Any] = []
    if not path.is_file():
        return rows
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            try:
                rows.append(json.loads(stripped))
            except json.JSONDecodeError:
                continue
    except Exception:
        return rows
    return rows


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")


def _extract_status_id(url: str) -> str:
    match = re.search(r"/status/(\d+)", str(url or ""))
    return match.group(1) if match else ""


def _extract_screen_name(url: str) -> str:
    parsed = urlsplit(str(url or ""))
    parts = [part for part in parsed.path.split("/") if part]
    if parts and parts[0].lower() not in {"i", "intent"}:
        return parts[0]
    return ""


def _canonical_url_from_capture(capture_dir: Path, source_url: str = "") -> str:
    manifest = _read_json(capture_dir / "browser_session_manifest.json", {})
    for key in ("canonical_url", "source_url"):
        value = str(manifest.get(key) or "").strip() if isinstance(manifest, Mapping) else ""
        if value:
            return value
    return str(source_url or "").strip()


def _parse_dom(dom: str) -> _RenderedDomParser:
    parser = _RenderedDomParser()
    parser.feed(dom or "")
    return parser


def _first_meta(parser: _RenderedDomParser, *keys: str) -> str:
    for key in keys:
        values = parser.metas.get(key) or []
        for value in values:
            if value:
                return value
    return ""


def _title_text(parser: _RenderedDomParser) -> str:
    return _clean_space(" ".join(parser.title_parts))


def _author_from_dom(parser: _RenderedDomParser, source_url: str) -> tuple[str, str]:
    title = _title_text(parser)
    meta_title = _first_meta(parser, "og:title", "twitter:title", "title")
    for value in (meta_title, title):
        match = re.match(r"^(.*?)\s+\(@([^)]+)\)\s+on\s+X\b", value)
        if match:
            return _clean_space(match.group(1)), match.group(2).strip()
        match = re.match(r"^(.*?)\s+on\s+X\s*:", value)
        if match:
            return _clean_space(match.group(1)), _extract_screen_name(source_url)
    tokens = parser.text_tokens
    for index, token in enumerate(tokens):
        if token.startswith("@") and index > 0:
            return tokens[index - 1], token.lstrip("@")
    return "", _extract_screen_name(source_url)


def _post_text_from_dom(parser: _RenderedDomParser, author_name: str, screen_name: str) -> str:
    meta_description = _first_meta(parser, "og:description", "twitter:description", "description")
    if meta_description:
        return meta_description.strip()
    tokens = parser.text_tokens
    handle = f"@{screen_name}" if screen_name else ""
    start = -1
    for index, token in enumerate(tokens):
        if handle and token == handle:
            start = index + 1
            break
    if start < 0 and author_name:
        for index, token in enumerate(tokens):
            if token == author_name:
                start = index + 1
                break
    collected: list[str] = []
    for token in tokens[start:] if start >= 0 else []:
        if _looks_like_posted_at(token) or token == "Views" or token.endswith("Views"):
            break
        collected.append(token)
    return _join_status_text_tokens(collected)


def _join_status_text_tokens(tokens: Sequence[str]) -> str:
    text = ""
    for token in tokens:
        if not text:
            text = token
        elif token.startswith((".", ",", ":", ";", "!", "?")):
            text += token
        elif text.endswith(("@", "#", "/", ":", "\n")):
            text += token
        else:
            text += " " + token
    return text.strip()


def _looks_like_posted_at(token: str) -> bool:
    text = _clean_space(token)
    return bool(re.search(r"\b\d{1,2}:\d{2}\s*(?:AM|PM)?\s*·\s*[^·]+?\b20\d{2}\b", text, flags=re.I))


def _posted_at_from_dom(parser: _RenderedDomParser) -> str:
    for token in parser.text_tokens:
        if _looks_like_posted_at(token):
            return token
    for anchor in parser.anchors:
        text = str(anchor.get("text") or "")
        if _looks_like_posted_at(text):
            return text
    return ""


def _normalize_count(raw: str) -> int | None:
    text = _clean_space(raw).lower().replace(",", "")
    match = re.match(r"^([0-9]+(?:\.[0-9]+)?)([kmb])?$", text)
    if not match:
        return None
    value = float(match.group(1))
    suffix = match.group(2)
    if suffix == "k":
        value *= 1_000
    elif suffix == "m":
        value *= 1_000_000
    elif suffix == "b":
        value *= 1_000_000_000
    return int(round(value))


def _counter_row_from_dom(parser: _RenderedDomParser) -> tuple[str, tuple[TwitterStatusCounter, ...], tuple[str, ...]]:
    warnings: list[str] = []
    tokens = parser.text_tokens
    views = ""
    view_index = -1
    for index, token in enumerate(tokens):
        if token.lower() == "views":
            if index > 0:
                views = tokens[index - 1]
                view_index = index
                break
        match = re.match(r"^(.+?)\s*Views$", token, flags=re.I)
        if match:
            views = match.group(1).strip()
            view_index = index
            break
    counters: list[TwitterStatusCounter] = []
    labels = ("comments", "retweets", "likes", "bookmarks")
    if view_index >= 0:
        raw_values: list[str] = []
        for token in tokens[view_index + 1 : view_index + 12]:
            clean = _clean_space(token)
            if not clean:
                continue
            if re.match(r"^[0-9][0-9,.]*\s*[kmbKMB]?$", clean):
                raw_values.append(clean)
                if len(raw_values) >= 4:
                    break
            elif raw_values:
                break
        for label, raw in zip(labels, raw_values):
            counters.append(
                TwitterStatusCounter(
                    name=label,
                    raw_value=raw,
                    normalized_value=_normalize_count(raw),
                    source="rendered_dom_positional_counter_row",
                    needs_review=True,
                )
            )
        if raw_values:
            warnings.append("Counter labels inferred positionally from rendered DOM after Views; review against screenshot/API when available.")
    return views, tuple(counters), tuple(warnings)


def _absolute_url(url: str, base: str) -> str:
    raw = str(url or "").strip()
    if not raw:
        return ""
    return urljoin(base or "https://x.com/", raw)


def _is_internal_x_host(host: str) -> bool:
    lower = str(host or "").lower()
    return lower in {"x.com", "twitter.com"} or lower.endswith(".x.com") or lower.endswith(".twitter.com")


def _extract_links(parser: _RenderedDomParser, source_url: str, post_text: str) -> tuple[TwitterStatusLink, ...]:
    links: list[TwitterStatusLink] = []
    seen: set[str] = set()
    source_path = urlsplit(source_url).path.rstrip("/")

    def include_link(absolute: str) -> bool:
        parsed = urlsplit(absolute)
        host = parsed.hostname or ""
        if not _is_internal_x_host(host):
            return True
        path = parsed.path.rstrip("/")
        if path == source_path:
            return True
        if source_path and path.startswith(source_path + "/photo/"):
            return True
        return False

    def add(url: str, display: str, source: str) -> None:
        absolute = _absolute_url(url, source_url)
        if not absolute or absolute in seen or not include_link(absolute):
            return
        seen.add(absolute)
        host = urlsplit(absolute).hostname or ""
        link_type = "internal_x" if _is_internal_x_host(host) else "external"
        links.append(TwitterStatusLink(url=absolute, display_text=_clean_space(display), link_type=link_type, source=source))

    for anchor in parser.anchors:
        add(str(anchor.get("href") or ""), str(anchor.get("text") or ""), "rendered_dom_anchor")

    for match in re.finditer(r"https?://[^\s)]+", post_text):
        add(match.group(0).rstrip(".,;"), match.group(0).rstrip(".,;"), "post_text_url")

    # Display-only domains such as shift.gearbox.com in rendered text.
    for token in parser.text_tokens:
        if re.match(r"^[a-z0-9][a-z0-9.-]+\.[a-z]{2,}(?:/[^\s]*)?$", token, flags=re.I):
            add("http://" + token, token, "rendered_dom_display_domain")

    return tuple(links)


def _media_id_from_twitter_media_url(url: str) -> str:
    parsed = urlsplit(str(url or ""))
    match = re.search(r"/media/([^/?#:]+)", parsed.path)
    if not match:
        return ""
    media = match.group(1)
    media = re.sub(r"\.(?:jpg|jpeg|png|webp|gif)$", "", media, flags=re.I)
    return media


def _is_direct_twitter_media(url: str) -> bool:
    parsed = urlsplit(str(url or ""))
    return (parsed.scheme in {"http", "https"}) and ((parsed.hostname or "").lower() in TWITTER_DIRECT_MEDIA_HOSTS)


def _normalize_media_url(url: str) -> str:
    raw = html.unescape(str(url or "").strip())
    if not raw:
        return ""
    parsed = urlsplit(raw)
    if (parsed.hostname or "").lower() == "pbs.twimg.com" and parsed.path.startswith("/media/"):
        name = ""
        fmt = ""
        for part in parsed.query.split("&"):
            if part.startswith("name="):
                name = part.split("=", 1)[1]
            elif part.startswith("format="):
                fmt = part.split("=", 1)[1]
        if fmt and "." not in Path(parsed.path).name:
            suffix = ":" + name if name else ""
            return f"{parsed.scheme}://{parsed.netloc}{parsed.path}.{fmt}{suffix}"
    return raw


def _extract_imagesrcset_urls(value: str) -> list[str]:
    urls: list[str] = []
    for part in str(value or "").split(","):
        item = part.strip().split(" ", 1)[0].strip()
        if item:
            urls.append(html.unescape(item))
    return urls


def _extract_media_urls_from_dom(parser: _RenderedDomParser) -> list[tuple[str, str]]:
    urls: list[tuple[str, str]] = []
    for key in ("og:image", "og:image:secure_url", "twitter:image", "twitter:image:src"):
        for url in parser.metas.get(key, []) or []:
            urls.append((url, f"rendered_dom_meta:{key}"))
    for link in parser.links:
        if (link.get("as") or "").lower() == "image":
            if link.get("href"):
                urls.append((str(link.get("href") or ""), "rendered_dom_preload_href"))
            if link.get("imagesrcset"):
                for url in _extract_imagesrcset_urls(str(link.get("imagesrcset") or "")):
                    urls.append((url, "rendered_dom_preload_imagesrcset"))
    for image in parser.images:
        for key in ("src", "data-src"):
            if image.get(key):
                urls.append((str(image.get(key) or ""), f"rendered_dom_img:{key}"))
        if image.get("srcset"):
            for url in _extract_imagesrcset_urls(str(image.get("srcset") or "")):
                urls.append((url, "rendered_dom_img_srcset"))
    return urls


def _extract_media_urls_from_network(capture_dir: Path) -> list[tuple[str, str]]:
    urls: list[tuple[str, str]] = []
    for row in _read_jsonl(capture_dir / "network_events.jsonl"):
        if not isinstance(row, Mapping):
            continue
        url = str(row.get("url") or "")
        if _is_direct_twitter_media(url):
            urls.append((url, "network_event_url"))
    return urls


def _extract_media_markers(
    capture_dir: Path,
    parser: _RenderedDomParser,
    *,
    source_url: str,
    status_id: str,
    screen_name: str,
) -> tuple[TwitterStatusMediaMarker, ...]:
    media_rows: list[tuple[str, str, str, str]] = []
    media_inventory = _read_json(capture_dir / "media_inventory.json", [])
    if isinstance(media_inventory, list):
        for item in media_inventory:
            if not isinstance(item, Mapping):
                continue
            url = str(item.get("media_url") or item.get("preview_url") or "")
            if url:
                media_rows.append((url, str(item.get("source_url") or source_url), str(item.get("source_kind") or item.get("from_query_name") or "media_inventory"), str(item.get("media_type") or "")))
    for url, kind in _extract_media_urls_from_dom(parser):
        media_rows.append((url, source_url, kind, ""))
    for url, kind in _extract_media_urls_from_network(capture_dir):
        media_rows.append((url, source_url, kind, ""))

    markers: list[TwitterStatusMediaMarker] = []
    seen: set[str] = set()
    for raw_url, item_source_url, source_kind, media_type in media_rows:
        direct = _normalize_media_url(raw_url)
        if not _is_direct_twitter_media(direct):
            continue
        media_id = _media_id_from_twitter_media_url(direct)
        if not media_id or direct in seen:
            continue
        seen.add(direct)
        safe = bool(status_id and screen_name and media_id and _is_direct_twitter_media(direct) and "](" not in direct and not direct.startswith("["))
        inferred_type = media_type or ("video" if (urlsplit(direct).hostname or "").lower() == "video.twimg.com" else "image")
        markers.append(
            TwitterStatusMediaMarker(
                status_id=status_id,
                screen_name=screen_name,
                media_id=media_id,
                media_type=inferred_type,
                direct_url=direct,
                source_url=item_source_url or source_url,
                source_kind=source_kind,
                safe_to_handoff_to_jd=safe,
                provenance="locked_to_status_user_media_marker_v73",
            )
        )
    return tuple(markers)


def _png_dimensions(path: Path) -> tuple[int, int]:
    try:
        with path.open("rb") as fh:
            header = fh.read(24)
        if len(header) >= 24 and header[:8] == b"\x89PNG\r\n\x1a\n" and header[12:16] == b"IHDR":
            width, height = struct.unpack(">II", header[16:24])
            return int(width), int(height)
    except Exception:
        return (0, 0)
    return (0, 0)


def build_screenshot_manifest(
    *,
    capture_dir: str | Path,
    source_url: str,
    status_id: str,
    screen_name: str,
    post_text: str,
    media_markers: Sequence[TwitterStatusMediaMarker],
    counters: Sequence[TwitterStatusCounter],
) -> TwitterStatusScreenshotManifest:
    capture = Path(capture_dir)
    screenshot = capture / "screenshot.png"
    width, height = _png_dimensions(screenshot)
    tile = TwitterScreenshotTile(
        path=str(screenshot),
        exists=screenshot.is_file() and screenshot.stat().st_size > 0 if screenshot.exists() else False,
        size_bytes=screenshot.stat().st_size if screenshot.exists() else 0,
        width=width,
        height=height,
        tile_index=0,
        scroll_x=0,
        scroll_y=0,
        capture_role="full_page_capture_single_image_or_viewport_fallback",
    )
    notes = (
        "V73 records screenshot evidence with a GoFullPage-style manifest: tile path, dimensions, scroll offsets, and stitched/full-page role.",
        "Current Playwright capture may be one full_page image; future V73B/V74 can split very long pages into numbered tiles like GoFullPage/mrcoles/marugoto-style capture.",
    )
    return TwitterStatusScreenshotManifest(
        schema_version=TWITTER_SCREENSHOT_MANIFEST_SCHEMA_VERSION,
        source_url=source_url,
        status_id=status_id,
        screen_name=screen_name,
        capture_strategy="go_full_page_style_full_page_or_tiled_manifest",
        tiles=(tile,),
        stitched_full_page_path=str(screenshot) if tile.exists else "",
        document_height=height,
        viewport_width=width,
        viewport_height=height,
        tweet_text_visible=bool(post_text and tile.exists),
        media_visible=bool(media_markers and tile.exists),
        counters_visible=bool(counters and tile.exists),
        notes=notes,
    )


def render_human_readable_status(bundle: TwitterStatusEvidenceBundle) -> str:
    lines: list[str] = []
    if bundle.author_name:
        lines.append(bundle.author_name)
    if bundle.screen_name:
        lines.append(f"@{bundle.screen_name}")
    if bundle.post_text:
        lines.append(bundle.post_text.strip())
    media_time = ""
    # Future video extraction may populate this from GraphQL or media-player DOM.
    if media_time:
        lines.append(media_time)
    date_line_parts = []
    if bundle.posted_at:
        date_line_parts.append(bundle.posted_at)
    if bundle.views:
        date_line_parts.append(f"{bundle.views} Views")
    if date_line_parts:
        lines.append(" · ".join(date_line_parts))
    counter_map = {counter.name: counter.raw_value for counter in bundle.counters}
    counter_labels = (
        ("comments", "comments"),
        ("retweets", "retweets"),
        ("likes", "likes"),
        ("bookmarks", "bookmarks"),
    )
    counter_line = " ".join(f"{counter_map[key]} {label}" for key, label in counter_labels if counter_map.get(key))
    if counter_line:
        lines.append(counter_line)
    if bundle.canonical_url:
        lines.append(bundle.canonical_url)
    return "\n".join(lines).strip() + "\n"


def extract_status_evidence_from_capture(
    capture_dir: str | Path,
    *,
    source_url: str = "",
    output_dir: str | Path | None = None,
) -> TwitterStatusEvidenceBundle:
    capture = Path(capture_dir)
    output = Path(output_dir) if output_dir is not None else capture
    output.mkdir(parents=True, exist_ok=True)
    canonical_url = _canonical_url_from_capture(capture, source_url=source_url)
    status_id = _extract_status_id(canonical_url)
    dom_path = capture / "rendered_dom_snapshot.html"
    dom = dom_path.read_text(encoding="utf-8", errors="replace") if dom_path.is_file() else ""
    parser = _parse_dom(dom)
    author_name, screen_name = _author_from_dom(parser, canonical_url)
    post_text = _post_text_from_dom(parser, author_name, screen_name)
    posted_at = _posted_at_from_dom(parser)
    views, counters, counter_warnings = _counter_row_from_dom(parser)
    links = _extract_links(parser, canonical_url, post_text)
    media_markers = _extract_media_markers(capture, parser, source_url=canonical_url, status_id=status_id, screen_name=screen_name)
    screenshot_manifest = build_screenshot_manifest(
        capture_dir=capture,
        source_url=canonical_url,
        status_id=status_id,
        screen_name=screen_name,
        post_text=post_text,
        media_markers=media_markers,
        counters=counters,
    )

    warnings: list[str] = list(counter_warnings)
    if not dom:
        warnings.append("rendered_dom_snapshot.html missing; extracted fields are incomplete.")
    if not post_text:
        warnings.append("post text was not extracted.")
    if not posted_at:
        warnings.append("posted date/time was not extracted.")
    if not counters:
        warnings.append("engagement counters were not extracted.")
    if not media_markers:
        warnings.append("no status-locked media markers were extracted.")

    screenshot_manifest_path = output / "screenshot_manifest.json"
    _write_json(screenshot_manifest_path, screenshot_manifest.to_dict())

    completion = "rendered_dom_status_evidence_captured"
    if warnings:
        completion = "rendered_dom_status_evidence_captured_needs_review"

    bundle = TwitterStatusEvidenceBundle(
        schema_version=TWITTER_STATUS_EVIDENCE_SCHEMA_VERSION,
        source_url=canonical_url,
        canonical_url=canonical_url,
        status_id=status_id,
        author_name=author_name,
        screen_name=screen_name,
        post_text=post_text,
        posted_at=posted_at,
        views=views,
        counters=counters,
        links=links,
        media_markers=media_markers,
        screenshot_manifest_path=str(screenshot_manifest_path),
        extraction_source="rendered_dom_snapshot_plus_network_and_screenshot_manifest",
        completion_state=completion,
        warnings=tuple(warnings),
    )

    _write_json(output / "status_evidence_bundle.json", bundle.to_dict())
    _write_json(output / "status_links_inventory.json", [link.to_dict() for link in links])
    _write_json(output / "status_counters_inventory.json", [counter.to_dict() for counter in counters])
    _write_json(output / "status_media_markers.json", [marker.to_dict() for marker in media_markers])
    (output / "human_readable_status.txt").write_text(render_human_readable_status(bundle), encoding="utf-8", newline="\n")
    return bundle


def main(argv: Sequence[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Extract text, counters, links, media markers, and screenshot evidence from a Twitter/X browser capture directory.")
    parser.add_argument("--capture-dir", required=True)
    parser.add_argument("--source-url", default="")
    parser.add_argument("--output-dir", default="")
    args = parser.parse_args(list(argv) if argv is not None else None)
    bundle = extract_status_evidence_from_capture(
        args.capture_dir,
        source_url=args.source_url,
        output_dir=args.output_dir or None,
    )
    print(json.dumps(bundle.to_dict(), indent=2, ensure_ascii=False, sort_keys=True))
    return 0 if bundle.post_text and bundle.status_id else 1


if __name__ == "__main__":
    raise SystemExit(main())
