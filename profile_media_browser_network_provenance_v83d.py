"""Offline browser/network provenance enrichment for link-source objects.

R37 adds read-only evidence fields gathered from already-captured HTML/text and
existing link metadata.  This module never fetches URLs, launches a browser, or
changes semantic/media/link roles by itself.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import html
from html.parser import HTMLParser
import json
import re
from typing import Any, Iterable, Mapping

try:
    from profile_media_url_normalizer import normalise_url_record
    from profile_media_hidden_url_discovery_v83d import discover_hidden_urls_from_html
except ModuleNotFoundError:  # pragma: no cover - direct script fallback
    from pathlib import Path
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from profile_media_url_normalizer import normalise_url_record
    from profile_media_hidden_url_discovery_v83d import discover_hidden_urls_from_html


R37_MARKER = "YTCE_V83D_R37_BROWSER_NETWORK_PROVENANCE_ENRICHMENT"
MEDIA_URL_RE = re.compile(
    r"https?://[^\s'\"<>\\]+?\.(?:mp4|webm|m3u8|mpd|mov|m4v|mp3|m4a|wav|jpg|jpeg|png|webp|gif)(?:\?[^\s'\"<>\\]*)?",
    re.IGNORECASE,
)
URL_RE = re.compile(r"https?://[^\s'\"<>\\]+", re.IGNORECASE)


@dataclass
class BrowserNetworkProvenance:
    final_url: str = ""
    requested_url: str = ""
    normalised_url: str = ""
    redirect_chain: list[str] = field(default_factory=list)
    canonical_url: str = ""
    og_url: str = ""
    og_title: str = ""
    og_description: str = ""
    og_image: str = ""
    og_video: str = ""
    html_title: str = ""
    twitter_url: str = ""
    twitter_title: str = ""
    twitter_description: str = ""
    twitter_image: str = ""
    twitter_player: str = ""
    metadata_author: str = ""
    metadata_publisher: str = ""
    json_ld_headline: str = ""
    json_ld_author: str = ""
    json_ld_publisher: str = ""
    json_ld_date_published: str = ""
    json_ld_date_modified: str = ""
    json_ld_urls: list[str] = field(default_factory=list)
    json_ld_images: list[str] = field(default_factory=list)
    json_ld_videos: list[str] = field(default_factory=list)
    hidden_url_discoveries: list[dict[str, Any]] = field(default_factory=list)
    oembed_endpoint_hints: list[str] = field(default_factory=list)
    body_text_preview: str = ""
    article_source_links: list[str] = field(default_factory=list)
    article_published_time: str = ""
    article_modified_time: str = ""
    iframe_sources: list[str] = field(default_factory=list)
    embedded_media_urls: list[str] = field(default_factory=list)
    network_loaded_media: list[str] = field(default_factory=list)
    script_discovered_urls: list[str] = field(default_factory=list)
    loaded_script_urls: list[str] = field(default_factory=list)
    loaded_stylesheet_urls: list[str] = field(default_factory=list)
    loaded_image_urls: list[str] = field(default_factory=list)
    loaded_document_urls: list[str] = field(default_factory=list)
    xhr_or_fetch_urls: list[str] = field(default_factory=list)
    websocket_urls: list[str] = field(default_factory=list)
    console_messages: list[dict[str, Any]] = field(default_factory=list)
    capture_artifact_paths: dict[str, str] = field(default_factory=dict)
    archive_capture_url: str = ""
    archive_target_url: str = ""
    capture_timestamp: str = ""
    capture_method: str = ""
    source_evidence_confidence: str = "low"
    provenance_notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class _ProvenanceHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.canonical_url = ""
        self.og: dict[str, str] = {}
        self.iframe_sources: list[str] = []
        self.embedded_media_urls: list[str] = []
        self.scripts: list[str] = []
        self.json_ld_blocks: list[str] = []
        self.body_text_parts: list[str] = []
        self._in_script = False
        self._in_title = False
        self._in_body = False
        self._script_type = ""
        self._script_parts: list[str] = []
        self._title_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr = {str(key or "").casefold(): str(value or "") for key, value in attrs}
        tag_name = tag.casefold()
        if tag_name == "link" and "canonical" in attr.get("rel", "").casefold():
            self.canonical_url = html.unescape(attr.get("href", "")).strip()
        elif tag_name == "meta":
            key = attr.get("property") or attr.get("name")
            value = attr.get("content")
            if key and value:
                self.og[key.casefold()] = html.unescape(value).strip()
        elif tag_name == "title":
            self._in_title = True
            self._title_parts = []
        elif tag_name == "body":
            self._in_body = True
        elif tag_name == "iframe" and attr.get("src"):
            self.iframe_sources.append(html.unescape(attr["src"]).strip())
        elif tag_name in {"embed", "object"} and (attr.get("src") or attr.get("data")):
            self.iframe_sources.append(html.unescape(attr.get("src") or attr.get("data") or "").strip())
        elif tag_name in {"video", "audio", "source", "img"} and (attr.get("src") or attr.get("poster")):
            if attr.get("src"):
                self.embedded_media_urls.append(html.unescape(attr["src"]).strip())
            if attr.get("poster"):
                self.embedded_media_urls.append(html.unescape(attr["poster"]).strip())
        elif tag_name == "script":
            self._in_script = True
            self._script_type = attr.get("type", "").casefold()
            self._script_parts = []

    def handle_data(self, data: str) -> None:
        if self._in_script:
            self._script_parts.append(data)
        elif self._in_title:
            self._title_parts.append(data)
        elif self._in_body:
            text = _clean(data)
            if text:
                self.body_text_parts.append(text)

    def handle_endtag(self, tag: str) -> None:
        if tag.casefold() == "script" and self._in_script:
            text = "\n".join(self._script_parts)
            if "ld+json" in self._script_type:
                self.json_ld_blocks.append(text)
            else:
                self.scripts.append(text)
            self._in_script = False
            self._script_type = ""
            self._script_parts = []
        elif tag.casefold() == "title":
            self._in_title = False
        elif tag.casefold() == "body":
            self._in_body = False


def _clean(value: object) -> str:
    return " ".join(str(value or "").replace("\r", " ").split()).strip()


def _unique(values: Iterable[object], *, limit: int = 50) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for value in values:
        text = html.unescape(str(value or "").strip())
        if not text:
            continue
        key = text.casefold()
        if key in seen:
            continue
        seen.add(key)
        output.append(text)
        if len(output) >= limit:
            break
    return output


def _normalised_url(url: object) -> str:
    try:
        return str(normalise_url_record(str(url or "")).get("normalised_url") or "").strip()
    except Exception:
        return str(url or "").strip()


def _decode_script_text(text: str) -> str:
    raw = str(text or "")
    decoded = raw.replace("\\/", "/")
    try:
        decoded = json.loads(f'"{decoded[:200000]}"')
    except Exception:
        try:
            decoded = decoded.encode("utf-8", errors="ignore").decode("unicode_escape", errors="ignore")
        except Exception:
            pass
    return decoded


def _script_urls(html_text: str, saved_page_text: str = "") -> list[str]:
    haystacks = [str(saved_page_text or "")]
    parser = _ProvenanceHTMLParser()
    try:
        parser.feed(str(html_text or ""))
        haystacks.extend(parser.scripts)
    except Exception:
        haystacks.append(str(html_text or ""))
    values: list[str] = []
    for text in haystacks:
        decoded = _decode_script_text(text)
        values.extend(match.group(0).rstrip(").,;]") for match in URL_RE.finditer(decoded))
    return _unique(values, limit=80)


def _json_ld_field_urls(discoveries: Iterable[Mapping[str, Any]], source: str) -> list[str]:
    return _unique(
        row.get("url")
        for row in discoveries
        if str(row.get("discovery_source") or "") == "json_ld"
        and (not source or source in str(row.get("context") or row.get("attribute") or ""))
    )


def _name_from_json_ld(value: Any) -> str:
    if isinstance(value, str):
        return _clean(value)
    if isinstance(value, Mapping):
        return _clean(value.get("name") or value.get("@id") or value.get("url"))
    if isinstance(value, list):
        names = [_name_from_json_ld(item) for item in value]
        return ", ".join(name for name in names if name)
    return ""


def _json_ld_summary(blocks: Iterable[str]) -> dict[str, str]:
    summary = {
        "headline": "",
        "author": "",
        "publisher": "",
        "date_published": "",
        "date_modified": "",
    }

    def visit(value: Any) -> None:
        if isinstance(value, Mapping):
            type_text = str(value.get("@type") or "").casefold()
            if not type_text or any(token in type_text for token in ("article", "newsarticle", "blogposting", "webpage", "videoobject")):
                summary["headline"] = summary["headline"] or _clean(value.get("headline") or value.get("name"))
                summary["author"] = summary["author"] or _name_from_json_ld(value.get("author"))
                summary["publisher"] = summary["publisher"] or _name_from_json_ld(value.get("publisher"))
                summary["date_published"] = summary["date_published"] or _clean(value.get("datePublished"))
                summary["date_modified"] = summary["date_modified"] or _clean(value.get("dateModified"))
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for item in value:
                visit(item)

    for block in blocks:
        try:
            visit(json.loads(block))
        except Exception:
            continue
    return summary


def _oembed_hints(discoveries: Iterable[Mapping[str, Any]]) -> list[str]:
    output: list[str] = []
    for row in discoveries:
        url = str(row.get("url") or "")
        if not url:
            continue
        if "oembed" in url.casefold() or any(domain in url.casefold() for domain in ("youtube.com", "vimeo.com", "x.com", "twitter.com", "tiktok.com")):
            output.append(url)
    return _unique(output, limit=30)


def _body_preview(parts: Iterable[str], *, limit: int = 1200) -> str:
    text = _clean(" ".join(parts))
    if len(text) <= limit:
        return text
    return text[:limit].rsplit(" ", 1)[0].rstrip() + "..."


def _article_source_links(discoveries: Iterable[Mapping[str, Any]]) -> list[str]:
    return _unique(
        row.get("url")
        for row in discoveries
        if str(row.get("discovery_source") or "") in {"html_attribute", "metadata"}
    )


def extract_browser_network_provenance(
    *,
    requested_url: object = "",
    final_url: object = "",
    rendered_html: object = "",
    saved_page_text: object = "",
    link_source_object: Mapping[str, object] | None = None,
    redirect_chain: Iterable[object] | None = None,
    network_loaded_media: Iterable[object] | None = None,
    capture_timestamp: object = "",
    capture_method: object = "",
) -> dict[str, Any]:
    """Return JSON-serialisable offline provenance fields for one link/source.

    Missing evidence remains empty.  URL roles and counters are deliberately not
    included in the output so callers cannot accidentally treat provenance as a
    role decision.
    """

    record = dict(link_source_object or {})
    html_text = str(rendered_html or "")
    page_text = str(saved_page_text or "")
    parser = _ProvenanceHTMLParser()
    if html_text:
        try:
            parser.feed(html_text)
        except Exception:
            pass

    req_url = _clean(requested_url or record.get("requested_url") or record.get("url") or record.get("normalised_url"))
    fin_url = _clean(final_url or record.get("final_url") or record.get("normalised_url") or record.get("url"))
    normalised = _normalised_url(fin_url or req_url)
    chain = _unique(redirect_chain or record.get("redirect_chain") or [], limit=20)
    network_media = _unique(network_loaded_media or record.get("network_loaded_media") or [], limit=80)
    script_urls = _script_urls(html_text, page_text)
    hidden_discoveries = discover_hidden_urls_from_html(html_text, base_url=fin_url or req_url, saved_page_text=page_text, limit=160)
    embedded = _unique(
        list(parser.embedded_media_urls)
        + [match.group(0).rstrip(").,;]") for match in MEDIA_URL_RE.finditer(_decode_script_text(html_text + "\n" + page_text))]
        + [
            row.get("url", "")
            for row in hidden_discoveries
            if str(row.get("discovery_source") or "") in {"media_element", "iframe"}
        ],
        limit=80,
    )

    archive_capture_url = ""
    if bool(record.get("is_archive_url")):
        archive_capture_url = _clean(record.get("normalised_url") or record.get("url"))

    notes: list[str] = []
    if html_text:
        notes.append("Offline rendered/static HTML inspected; no browser or network fetch performed.")
    if page_text and not html_text:
        notes.append("Saved page text inspected; no browser or network fetch performed.")
    if embedded or network_media:
        notes.append("Nested media URLs are provenance candidates only; roles remain governed by link/media decisions.")
    if bool(record.get("is_archive_url")):
        notes.append("Archive wrapper metadata is retained separately from target URL role inheritance.")
    if not notes:
        notes.append("No browser/network provenance metadata supplied.")

    confidence = "low"
    if parser.canonical_url or parser.og or embedded or network_media:
        confidence = "medium"
    if (parser.canonical_url or parser.og.get("og:url")) and (embedded or parser.og.get("og:image")):
        confidence = "medium"
    json_ld_urls = _json_ld_field_urls(hidden_discoveries, "")
    json_ld_summary = _json_ld_summary(parser.json_ld_blocks)

    return BrowserNetworkProvenance(
        final_url=fin_url,
        requested_url=req_url,
        normalised_url=normalised,
        redirect_chain=chain,
        canonical_url=_clean(parser.canonical_url),
        og_url=_clean(parser.og.get("og:url")),
        og_title=_clean(parser.og.get("og:title")),
        og_description=_clean(parser.og.get("og:description")),
        og_image=_clean(parser.og.get("og:image")),
        og_video=_clean(parser.og.get("og:video") or parser.og.get("og:video:url") or parser.og.get("og:video:secure_url")),
        html_title=_clean(" ".join(parser._title_parts)),
        twitter_url=_clean(parser.og.get("twitter:url")),
        twitter_title=_clean(parser.og.get("twitter:title")),
        twitter_description=_clean(parser.og.get("twitter:description")),
        twitter_image=_clean(parser.og.get("twitter:image") or parser.og.get("twitter:image:src")),
        twitter_player=_clean(parser.og.get("twitter:player") or parser.og.get("twitter:player:stream")),
        metadata_author=_clean(parser.og.get("author") or parser.og.get("article:author") or parser.og.get("twitter:creator")),
        metadata_publisher=_clean(parser.og.get("og:site_name") or parser.og.get("twitter:site") or parser.og.get("publisher")),
        json_ld_headline=json_ld_summary["headline"],
        json_ld_author=json_ld_summary["author"],
        json_ld_publisher=json_ld_summary["publisher"],
        json_ld_date_published=json_ld_summary["date_published"],
        json_ld_date_modified=json_ld_summary["date_modified"],
        json_ld_urls=json_ld_urls,
        json_ld_images=[
            url for url in json_ld_urls
            if re.search(r"\.(?:jpg|jpeg|png|webp|gif)(?:\?|$)", url, flags=re.IGNORECASE)
        ][:30],
        json_ld_videos=[
            url for url in json_ld_urls
            if re.search(r"\.(?:mp4|webm|m3u8|mpd|mov|m4v)(?:\?|$)", url, flags=re.IGNORECASE)
        ][:30],
        hidden_url_discoveries=hidden_discoveries,
        oembed_endpoint_hints=_oembed_hints(hidden_discoveries),
        body_text_preview=_body_preview(parser.body_text_parts),
        article_source_links=_article_source_links(hidden_discoveries),
        article_published_time=_clean(parser.og.get("article:published_time")),
        article_modified_time=_clean(parser.og.get("article:modified_time")),
        iframe_sources=_unique(parser.iframe_sources),
        embedded_media_urls=embedded,
        network_loaded_media=network_media,
        script_discovered_urls=script_urls,
        loaded_script_urls=[],
        loaded_stylesheet_urls=[],
        loaded_image_urls=[],
        loaded_document_urls=[],
        xhr_or_fetch_urls=[],
        websocket_urls=[],
        console_messages=[],
        capture_artifact_paths={},
        archive_capture_url=archive_capture_url,
        archive_target_url=_clean(record.get("archive_target_url") or record.get("preservation_for_url")),
        capture_timestamp=_clean(capture_timestamp or record.get("capture_timestamp")),
        capture_method=_clean(capture_method or record.get("capture_method") or ("offline_html" if html_text else "link_source_object")),
        source_evidence_confidence=confidence,
        provenance_notes=notes,
    ).to_dict()


def enrich_link_source_objects_with_browser_network_provenance(
    link_source_objects: Iterable[Mapping[str, object]],
    *,
    rendered_html: object = "",
    saved_page_text: object = "",
    requested_url: object = "",
    final_url: object = "",
    redirect_chain: Iterable[object] | None = None,
    network_loaded_media: Iterable[object] | None = None,
    capture_timestamp: object = "",
    capture_method: object = "",
) -> list[dict[str, Any]]:
    """Attach R37 provenance dicts without mutating role/count fields."""

    output: list[dict[str, Any]] = []
    for record in link_source_objects:
        if not isinstance(record, Mapping):
            continue
        item = dict(record)
        item["browser_network_provenance"] = extract_browser_network_provenance(
            requested_url=requested_url or item.get("url") or item.get("normalised_url"),
            final_url=final_url or item.get("normalised_url") or item.get("url"),
            rendered_html=rendered_html,
            saved_page_text=saved_page_text,
            link_source_object=item,
            redirect_chain=redirect_chain,
            network_loaded_media=network_loaded_media,
            capture_timestamp=capture_timestamp,
            capture_method=capture_method,
        )
        item["browser_network_provenance_schema"] = "profile-media-browser-network-provenance-v83d-r37"
        item[R37_MARKER] = True
        output.append(item)
    return output


def browser_capture_summary_to_provenance(
    capture_summary: Mapping[str, Any],
    *,
    base_provenance: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Bridge live/imported capture telemetry into the R37/R39B schema.

    The returned payload is provenance metadata only.  It deliberately does not
    contain source-role decisions or count overrides.
    """

    source = dict(base_provenance or {})
    capture = dict(capture_summary or {})
    loaded = capture.get("loaded_resources") if isinstance(capture.get("loaded_resources"), Mapping) else {}
    frames = capture.get("frames") if isinstance(capture.get("frames"), list) else []
    frame_urls = [
        str(frame.get("url") or "")
        for frame in frames
        if isinstance(frame, Mapping) and str(frame.get("url") or "").strip()
    ]
    source.update(
        {
            "final_url": _clean(capture.get("final_url") or source.get("final_url")),
            "requested_url": _clean(capture.get("requested_url") or capture.get("source_url") or source.get("requested_url")),
            "normalised_url": _normalised_url(capture.get("final_url") or capture.get("requested_url") or source.get("normalised_url")),
            "redirect_chain": _unique(list(source.get("redirect_chain") or []) + list(capture.get("redirect_chain") or []), limit=80),
            "network_loaded_media": _unique(list(source.get("network_loaded_media") or []) + list(loaded.get("network_loaded_media") or []), limit=120),
            "iframe_sources": _unique(list(source.get("iframe_sources") or []) + frame_urls, limit=80),
            "loaded_script_urls": _unique(list(source.get("loaded_script_urls") or []) + list(loaded.get("loaded_script_urls") or []), limit=120),
            "loaded_stylesheet_urls": _unique(list(source.get("loaded_stylesheet_urls") or []) + list(loaded.get("loaded_stylesheet_urls") or []), limit=120),
            "loaded_image_urls": _unique(list(source.get("loaded_image_urls") or []) + list(loaded.get("loaded_image_urls") or []), limit=120),
            "loaded_document_urls": _unique(list(source.get("loaded_document_urls") or []) + list(loaded.get("loaded_document_urls") or []), limit=120),
            "xhr_or_fetch_urls": _unique(list(source.get("xhr_or_fetch_urls") or []) + list(loaded.get("xhr_or_fetch_urls") or []), limit=120),
            "websocket_urls": _unique(list(source.get("websocket_urls") or []) + list(loaded.get("websocket_urls") or []), limit=80),
            "console_messages": list(capture.get("console_messages") or []),
            "capture_timestamp": _clean(capture.get("capture_timestamp") or source.get("capture_timestamp")),
            "capture_method": _clean(capture.get("capture_method") or source.get("capture_method") or "cdp_capture"),
            "capture_artifact_paths": {str(key): str(value) for key, value in dict(capture.get("capture_artifact_paths") or {}).items()},
            "source_evidence_confidence": "medium" if capture.get("network_requests") else str(source.get("source_evidence_confidence") or "low"),
            "provenance_notes": _unique(
                list(source.get("provenance_notes") or [])
                + [
                    "Live/imported CDP telemetry attached as provenance metadata only.",
                    "No semantic, media/source, link-source role, archive inheritance, or count decisions were changed.",
                ],
                limit=20,
            ),
        }
    )
    for forbidden in ("visible_link_role", "source_record_count_breakdown", "claim_role", "semantic_role"):
        source.pop(forbidden, None)
    return source


def compact_browser_network_provenance_lines(record: Mapping[str, object]) -> list[str]:
    """Return compact display lines for the per-link details window."""

    payload = record.get("browser_network_provenance") if isinstance(record, Mapping) else None
    if not isinstance(payload, Mapping):
        return []

    lines: list[str] = []

    def add(label: str, value: object) -> None:
        text = _clean(value)
        if text:
            lines.append(f"{label}: {text}")

    add("Final URL", payload.get("final_url"))
    add("Canonical URL", payload.get("canonical_url"))
    add("OG URL", payload.get("og_url"))
    add("Title", payload.get("og_title") or payload.get("twitter_title") or payload.get("json_ld_headline") or payload.get("html_title"))
    add("OG image", payload.get("og_image"))
    add("OG video", payload.get("og_video"))
    add("Twitter URL", payload.get("twitter_url"))
    add("Twitter image", payload.get("twitter_image"))
    add("Twitter player", payload.get("twitter_player"))
    add("Author", payload.get("metadata_author") or payload.get("json_ld_author"))
    add("Publisher", payload.get("metadata_publisher") or payload.get("json_ld_publisher"))
    add("Archive target", payload.get("archive_target_url"))
    for label, key in (
        ("Embedded media", "embedded_media_urls"),
        ("Script-discovered URLs", "script_discovered_urls"),
        ("Hidden URL discoveries", "hidden_url_discoveries"),
        ("JSON-LD URLs", "json_ld_urls"),
        ("oEmbed hints", "oembed_endpoint_hints"),
        ("Article/source links", "article_source_links"),
        ("Network-loaded media", "network_loaded_media"),
        ("Iframe sources", "iframe_sources"),
        ("Loaded scripts", "loaded_script_urls"),
        ("Loaded stylesheets", "loaded_stylesheet_urls"),
        ("Loaded images", "loaded_image_urls"),
        ("Loaded documents", "loaded_document_urls"),
        ("XHR/fetch URLs", "xhr_or_fetch_urls"),
        ("WebSocket URLs", "websocket_urls"),
    ):
        values = payload.get(key)
        if isinstance(values, list) and values:
            lines.append(f"{label}: {len(values)}")
    messages = payload.get("console_messages")
    if isinstance(messages, list) and messages:
        lines.append(f"Console messages: {len(messages)}")
    artifacts = payload.get("capture_artifact_paths")
    if isinstance(artifacts, Mapping) and artifacts:
        lines.append(f"Capture artifacts: {len(artifacts)}")
    add("Body preview", payload.get("body_text_preview"))
    add("Confidence", payload.get("source_evidence_confidence"))
    if lines:
        return ["", "Browser/network provenance:"] + lines
    return []
