"""Offline hidden/embedded URL discovery for preserved HTML/text artifacts.

R39 reimplements the useful ideas from jsluice/JSFinder/galer-style reference
tools in the app's stdlib-only style: inspect already-saved markup and script
strings, tag where each URL came from, and keep every result as provenance
metadata rather than source-role evidence.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import html
from html.parser import HTMLParser
import json
import re
from typing import Any, Iterable
from urllib.parse import urljoin


URL_RE = re.compile(r"(?:https?|wss?)://[^\s'\"<>\\]+|//[^\s'\"<>\\]+|www\.[^\s'\"<>\\]+", re.IGNORECASE)
FETCH_HINT_RE = re.compile(
    r"\b(fetch|XMLHttpRequest(?:\.open)?|WebSocket|EventSource|sendBeacon|import)\s*\([^)]*?(['\"])((?:https?|wss?)[:\\][/\\][^'\"]+|//[^'\"]+|www\.[^'\"]+)(?:\2)",
    re.IGNORECASE | re.DOTALL,
)
IMPORT_HINT_RE = re.compile(
    r"\bimport\s+(?:[^'\"]+\s+from\s+)?(['\"])((?:https?|wss?)[:\\][/\\][^'\"]+|//[^'\"]+|www\.[^'\"]+)\1",
    re.IGNORECASE,
)
JS_STRING_RE = re.compile(r"(['\"])((?:(?:https?|wss?):\\?/\\?/|//|www\.)[^'\"]+?)\1", re.IGNORECASE)
URL_ATTRS = {"href", "src", "poster", "action", "content"}
MEDIA_TAGS = {"video", "audio", "source", "track", "img", "picture"}


@dataclass(frozen=True)
class HiddenURLDiscovery:
    url: str
    discovery_source: str
    tag: str = ""
    attribute: str = ""
    context: str = ""
    confidence: str = "medium"
    reason: str = "Offline preserved artifact contained a URL-shaped value."

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _clean_url(value: object, *, base_url: str = "") -> str:
    text = html.unescape(str(value or "").strip()).replace("\\/", "/")
    try:
        text = json.loads(f'"{text}"')
    except Exception:
        try:
            text = text.encode("utf-8", errors="ignore").decode("unicode_escape", errors="ignore")
        except Exception:
            pass
    text = text.strip().strip("<>\"'").rstrip(".,;:)]}")
    if text.startswith("//"):
        text = "https:" + text
    elif text.startswith("www."):
        text = "https://" + text
    elif base_url and text.startswith(("/", "./", "../")):
        text = urljoin(base_url, text)
    return text


def _unique(rows: Iterable[HiddenURLDiscovery], *, limit: int = 200) -> list[dict[str, Any]]:
    seen: set[tuple[str, str, str, str]] = set()
    output: list[dict[str, Any]] = []
    for row in rows:
        if not row.url.startswith(("http://", "https://", "ws://", "wss://")):
            continue
        key = (row.url.casefold(), row.discovery_source, row.tag, row.attribute)
        if key in seen:
            continue
        seen.add(key)
        output.append(row.to_dict())
        if len(output) >= limit:
            break
    return output


class _HiddenURLHTMLParser(HTMLParser):
    def __init__(self, *, base_url: str = "") -> None:
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.rows: list[HiddenURLDiscovery] = []
        self.scripts: list[str] = []
        self.json_ld_blocks: list[str] = []
        self._in_script = False
        self._script_type = ""
        self._parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag_name = tag.casefold()
        attr = {str(key or "").casefold(): str(value or "") for key, value in attrs}
        for key, value in attr.items():
            if not value:
                continue
            source = ""
            if tag_name == "meta" and key == "content":
                source = "metadata"
            elif tag_name in {"iframe", "embed", "object"} and key in {"src", "data"}:
                source = "iframe"
            elif tag_name in MEDIA_TAGS and key in {"src", "poster", "srcset", "data"}:
                source = "media_element"
            elif key in URL_ATTRS or key.startswith("data-"):
                source = "html_attribute"
            if not source:
                continue
            values = [value]
            if key == "srcset":
                values = [part.strip().split()[0] for part in value.split(",")]
            for raw in values:
                for match in URL_RE.finditer(raw):
                    self.rows.append(
                        HiddenURLDiscovery(
                            url=_clean_url(match.group(0), base_url=self.base_url),
                            discovery_source=source,
                            tag=tag_name,
                            attribute=key,
                            context=str(attr.get("property") or attr.get("name") or ""),
                            reason=f"{tag_name} {key} attribute contained a URL.",
                        )
                    )
        if tag_name == "script":
            self._in_script = True
            self._script_type = attr.get("type", "").casefold()
            self._parts = []

    def handle_data(self, data: str) -> None:
        if self._in_script:
            self._parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.casefold() != "script" or not self._in_script:
            return
        text = "\n".join(self._parts)
        if "ld+json" in self._script_type:
            self.json_ld_blocks.append(text)
        else:
            self.scripts.append(text)
        self._in_script = False
        self._script_type = ""
        self._parts = []


def _decode_text(text: object) -> str:
    raw = str(text or "").replace("\\/", "/")
    try:
        return json.loads(f'"{raw[:500000]}"')
    except Exception:
        try:
            return raw.encode("utf-8", errors="ignore").decode("unicode_escape", errors="ignore")
        except Exception:
            return raw


def _walk_json_ld(value: Any) -> Iterable[str]:
    if isinstance(value, dict):
        for key, child in value.items():
            if str(key).casefold() in {"url", "@id", "image", "thumbnailurl", "contenturl", "embedurl", "sameas"}:
                if isinstance(child, str):
                    yield child
                elif isinstance(child, list):
                    for item in child:
                        if isinstance(item, str):
                            yield item
                        else:
                            yield from _walk_json_ld(item)
            else:
                yield from _walk_json_ld(child)
    elif isinstance(value, list):
        for item in value:
            yield from _walk_json_ld(item)


def discover_hidden_urls_from_html(
    html_text: object,
    *,
    base_url: str = "",
    saved_page_text: object = "",
    limit: int = 200,
) -> list[dict[str, Any]]:
    """Return tagged URL discoveries from already-captured HTML/text only."""

    parser = _HiddenURLHTMLParser(base_url=base_url)
    try:
        parser.feed(str(html_text or ""))
    except Exception:
        pass

    rows: list[HiddenURLDiscovery] = list(parser.rows)

    for block in parser.json_ld_blocks:
        try:
            data = json.loads(block)
            for value in _walk_json_ld(data):
                rows.append(
                    HiddenURLDiscovery(
                        url=_clean_url(value, base_url=base_url),
                        discovery_source="json_ld",
                        tag="script",
                        attribute="application/ld+json",
                        reason="schema.org JSON-LD field contained a URL.",
                    )
                )
        except Exception:
            for match in URL_RE.finditer(_decode_text(block)):
                rows.append(
                    HiddenURLDiscovery(
                        url=_clean_url(match.group(0), base_url=base_url),
                        discovery_source="json_ld",
                        tag="script",
                        attribute="application/ld+json",
                        confidence="low",
                        reason="schema.org JSON-LD text contained a URL-shaped string.",
                    )
                )

    for script in parser.scripts:
        decoded = _decode_text(script)
        for match in FETCH_HINT_RE.finditer(decoded):
            rows.append(
                HiddenURLDiscovery(
                    url=_clean_url(match.group(3), base_url=base_url),
                    discovery_source="fetch_or_xhr_hint",
                    tag="script",
                    attribute=match.group(1),
                    reason=f"JavaScript {match.group(1)} call contained a URL string.",
                )
            )
        for match in JS_STRING_RE.finditer(decoded):
            rows.append(
                HiddenURLDiscovery(
                    url=_clean_url(match.group(2), base_url=base_url),
                    discovery_source="javascript_string",
                    tag="script",
                    attribute="string_literal",
                    confidence="low",
                    reason="JavaScript string literal contained a URL-shaped value.",
                )
            )
        for match in IMPORT_HINT_RE.finditer(decoded):
            rows.append(
                HiddenURLDiscovery(
                    url=_clean_url(match.group(2), base_url=base_url),
                    discovery_source="javascript_import_hint",
                    tag="script",
                    attribute="import",
                    reason="JavaScript static import contained a URL string.",
                )
            )

    decoded_page_text = _decode_text(saved_page_text)
    for match in URL_RE.finditer(decoded_page_text):
        rows.append(
            HiddenURLDiscovery(
                url=_clean_url(match.group(0), base_url=base_url),
                discovery_source="javascript_string",
                tag="saved_page_text",
                attribute="text",
                confidence="low",
                reason="Saved page text contained a URL-shaped value.",
            )
        )
    return _unique(rows, limit=limit)


def discoveries_by_source(discoveries: Iterable[Mapping[str, Any]]) -> dict[str, list[str]]:
    """Group discovered URLs by discovery source for compact audit output."""

    output: dict[str, list[str]] = {}
    for row in discoveries:
        source = str(row.get("discovery_source") or "unknown")
        output.setdefault(source, [])
        url = str(row.get("url") or "").strip()
        if url and url not in output[source]:
            output[source].append(url)
    return output
