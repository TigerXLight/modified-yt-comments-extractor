from __future__ import annotations

from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Any, Mapping


ARTICLE_STATUS_EXTRACTED = "extracted"
ARTICLE_STATUS_LOW_CONFIDENCE = "low_confidence"
ARTICLE_STATUS_EMPTY = "empty"

ARTICLE_EXTRACTION_SCOPE = (
    "local HTML article extraction only; no fetch, browser, screenshot, download, "
    "archive, provider, credential, scraping, external process, or GUI behavior"
)


@dataclass(frozen=True)
class ArticleExtractionResult:
    source_url: str
    status: str
    title: str = ""
    text: str = ""
    method: str = "semantic_html"
    confidence: float = 0.0
    contamination_signals: tuple[str, ...] = ()
    excluded_region_counts: Mapping[str, int] | None = None
    warnings: tuple[str, ...] = ()
    scope: str = ARTICLE_EXTRACTION_SCOPE

    def to_dict(self) -> dict[str, Any]:
        return {
            "confidence": self.confidence,
            "contamination_signals": list(self.contamination_signals),
            "excluded_region_counts": dict(self.excluded_region_counts or {}),
            "method": self.method,
            "scope": self.scope,
            "source_url": self.source_url,
            "status": self.status,
            "text": self.text,
            "title": self.title,
            "warnings": list(self.warnings),
        }


class _ArticleTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title_parts: list[str] = []
        self.article_parts: list[str] = []
        self.main_parts: list[str] = []
        self.body_parts: list[str] = []
        self._in_title = False
        self._article_depth = 0
        self._main_depth = 0
        self._body_depth = 0
        self._ignored_depth = 0
        self._ignored_tag_stack: list[str] = []
        self.excluded_region_counts: dict[str, int] = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        lowered = tag.lower()
        ignored_reason = _ignored_region_reason(lowered, attrs)
        if ignored_reason:
            self._ignored_depth += 1
            self._ignored_tag_stack.append(lowered)
            self.excluded_region_counts[ignored_reason] = (
                self.excluded_region_counts.get(ignored_reason, 0) + 1
            )
        if lowered == "title":
            self._in_title = True
        if lowered == "article":
            self._article_depth += 1
        if lowered == "main":
            self._main_depth += 1
        if lowered == "body":
            self._body_depth += 1

    def handle_endtag(self, tag: str) -> None:
        lowered = tag.lower()
        if self._ignored_tag_stack and lowered == self._ignored_tag_stack[-1]:
            self._ignored_depth = max(0, self._ignored_depth - 1)
            self._ignored_tag_stack.pop()
        if lowered == "title":
            self._in_title = False
        if lowered == "article":
            self._article_depth = max(0, self._article_depth - 1)
        if lowered == "main":
            self._main_depth = max(0, self._main_depth - 1)
        if lowered == "body":
            self._body_depth = max(0, self._body_depth - 1)

    def handle_data(self, data: str) -> None:
        text = _normalize_text(data)
        if not text:
            return
        if self._in_title:
            self.title_parts.append(text)
            return
        if self._ignored_depth:
            return
        if self._article_depth:
            self.article_parts.append(text)
        if self._main_depth:
            self.main_parts.append(text)
        if self._body_depth:
            self.body_parts.append(text)


def _normalize_text(value: str) -> str:
    return " ".join(str(value or "").split())


def _ignored_region_reason(tag: str, attrs: list[tuple[str, str | None]]) -> str:
    if tag in {"script", "style", "noscript"}:
        return "non_content"
    attr_text = " ".join(
        f"{key or ''} {value or ''}".lower()
        for key, value in attrs
    )
    if any(token in attr_text for token in ("comment", "discussion", "reply")):
        return "comments"
    if any(token in attr_text for token in ("advert", "ad-", " ad ", "sponsor", "promo")):
        return "advertising"
    if any(token in attr_text for token in ("related", "share", "subscription", "cookie")):
        return "page_chrome"
    if tag in {"nav", "footer", "form"}:
        return "page_chrome"
    if tag == "aside":
        return "side_chrome"
    return ""


def _join_paragraph_text(parts: list[str]) -> str:
    return "\n\n".join(part for part in (_normalize_text(part) for part in parts) if part)


def extract_article_text_from_html(html: str, *, source_url: str = "") -> ArticleExtractionResult:
    parser = _ArticleTextParser()
    warnings: list[str] = []
    try:
        parser.feed(html or "")
    except Exception:
        warnings.append("HTML parser reported a non-secret parsing issue; article text may be partial.")

    title = _normalize_text(" ".join(parser.title_parts))
    excluded_counts = dict(sorted(parser.excluded_region_counts.items()))
    contamination_signals = tuple(
        f"excluded_{reason}_region"
        for reason in sorted(excluded_counts)
        if reason in {"advertising", "comments", "page_chrome", "side_chrome"}
    )
    if "comments" in excluded_counts:
        warnings.append("Comment/discussion regions were excluded from article text.")
    if "advertising" in excluded_counts:
        warnings.append("Advertising or promotional regions were excluded from article text.")
    method = "semantic_article"
    confidence = 0.0
    selected_parts = parser.article_parts
    if selected_parts:
        confidence = 0.9
    elif parser.main_parts:
        method = "semantic_main"
        selected_parts = parser.main_parts
        confidence = 0.7
        warnings.append("No article element found; used main element text.")
    elif parser.body_parts:
        method = "body_fallback"
        selected_parts = parser.body_parts
        confidence = 0.35
        warnings.append("No article or main element found; used low-confidence body fallback.")
    else:
        method = "empty"
        warnings.append("No extractable page text found.")

    text = _join_paragraph_text(selected_parts)
    if not text:
        status = ARTICLE_STATUS_EMPTY
        confidence = 0.0
    elif confidence < 0.5:
        status = ARTICLE_STATUS_LOW_CONFIDENCE
    else:
        status = ARTICLE_STATUS_EXTRACTED

    return ArticleExtractionResult(
        source_url=source_url,
        status=status,
        title=title,
        text=text,
        method=method,
        confidence=confidence,
        contamination_signals=contamination_signals,
        excluded_region_counts=excluded_counts,
        warnings=tuple(warnings),
    )
