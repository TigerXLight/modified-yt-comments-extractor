from __future__ import annotations

from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Any


PAGE_OUTLINE_SCOPE = (
    "local HTML page-outline extraction only; no fetch, browser, screenshot, download, "
    "archive, provider, credential, scraping, external process, or GUI behavior"
)


@dataclass(frozen=True)
class PageHeading:
    level: int
    text: str

    def to_dict(self) -> dict[str, Any]:
        return {"level": self.level, "text": self.text}


@dataclass(frozen=True)
class PageMediaReference:
    tag_name: str
    source: str = ""
    alt_text: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "alt_text": self.alt_text,
            "source": self.source,
            "tag_name": self.tag_name,
        }


@dataclass(frozen=True)
class PageOutlineResult:
    source_url: str
    title: str = ""
    headings: tuple[PageHeading, ...] = ()
    link_count: int = 0
    image_count: int = 0
    video_count: int = 0
    audio_count: int = 0
    media_references: tuple[PageMediaReference, ...] = ()
    text_sample: str = ""
    warnings: tuple[str, ...] = ()
    scope: str = PAGE_OUTLINE_SCOPE

    def to_dict(self) -> dict[str, Any]:
        return {
            "audio_count": self.audio_count,
            "headings": [heading.to_dict() for heading in self.headings],
            "image_count": self.image_count,
            "link_count": self.link_count,
            "media_references": [reference.to_dict() for reference in self.media_references],
            "scope": self.scope,
            "source_url": self.source_url,
            "text_sample": self.text_sample,
            "title": self.title,
            "video_count": self.video_count,
            "warnings": list(self.warnings),
        }


class _PageOutlineParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title_parts: list[str] = []
        self.heading_parts: list[str] = []
        self.current_heading_level = 0
        self.current_tag_stack: list[str] = []
        self.headings: list[PageHeading] = []
        self.link_count = 0
        self.image_count = 0
        self.video_count = 0
        self.audio_count = 0
        self.media_references: list[PageMediaReference] = []
        self.text_parts: list[str] = []
        self._in_title = False
        self._ignored_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        lowered = tag.lower()
        attr_map = {key.lower(): value or "" for key, value in attrs}
        self.current_tag_stack.append(lowered)
        if lowered in {"script", "style", "noscript"}:
            self._ignored_depth += 1
        if lowered == "title":
            self._in_title = True
        if lowered.startswith("h") and len(lowered) == 2 and lowered[1].isdigit():
            level = int(lowered[1])
            if 1 <= level <= 6:
                self.current_heading_level = level
                self.heading_parts = []
        if lowered == "a":
            self.link_count += 1
        if lowered == "img":
            self.image_count += 1
            self.media_references.append(
                PageMediaReference(
                    tag_name="img",
                    source=attr_map.get("src", ""),
                    alt_text=attr_map.get("alt", ""),
                )
            )
        if lowered == "video":
            self.video_count += 1
            self.media_references.append(
                PageMediaReference(tag_name="video", source=attr_map.get("src", ""))
            )
        if lowered == "audio":
            self.audio_count += 1
            self.media_references.append(
                PageMediaReference(tag_name="audio", source=attr_map.get("src", ""))
            )

    def handle_endtag(self, tag: str) -> None:
        lowered = tag.lower()
        if lowered in {"script", "style", "noscript"} and self._ignored_depth:
            self._ignored_depth -= 1
        if lowered == "title":
            self._in_title = False
        if self.current_heading_level and lowered == f"h{self.current_heading_level}":
            text = _normalize_text(" ".join(self.heading_parts))
            if text:
                self.headings.append(PageHeading(level=self.current_heading_level, text=text))
            self.current_heading_level = 0
            self.heading_parts = []
        if self.current_tag_stack:
            self.current_tag_stack.pop()

    def handle_data(self, data: str) -> None:
        if self._ignored_depth:
            return
        text = _normalize_text(data)
        if not text:
            return
        if self._in_title:
            self.title_parts.append(text)
        if self.current_heading_level:
            self.heading_parts.append(text)
        if not self._in_title:
            self.text_parts.append(text)


def _normalize_text(value: str) -> str:
    return " ".join(str(value or "").split())


def build_page_outline_from_html(html: str, *, source_url: str = "") -> PageOutlineResult:
    parser = _PageOutlineParser()
    warnings: list[str] = []
    try:
        parser.feed(html or "")
    except Exception:
        warnings.append("HTML parser reported a non-secret parsing issue; outline may be partial.")
    title = _normalize_text(" ".join(parser.title_parts))
    text_sample = _normalize_text(" ".join(parser.text_parts))[:500]
    if not title:
        warnings.append("No page title found.")
    if not parser.headings:
        warnings.append("No heading structure found.")
    return PageOutlineResult(
        source_url=source_url,
        title=title,
        headings=tuple(parser.headings),
        link_count=parser.link_count,
        image_count=parser.image_count,
        video_count=parser.video_count,
        audio_count=parser.audio_count,
        media_references=tuple(parser.media_references),
        text_sample=text_sample,
        warnings=tuple(warnings),
    )
