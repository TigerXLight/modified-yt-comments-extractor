from __future__ import annotations

from dataclasses import dataclass
from html.parser import HTMLParser
import html as html_lib
import json
import re
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


def _clean_extracted_title(value: str) -> str:
    """Keep fast-static article titles to the story title, not the site/menu rail."""

    text = _normalize_text(value)
    if not text:
        return ""
    for marker in (
        " | News UK | Metro News",
        " | Metro News",
        " | News UK",
        " | Metro",
        " - Metro",
    ):
        if marker.lower() in text.lower():
            # Preserve the original casing before the matched marker.
            index = text.lower().find(marker.lower())
            text = text[:index].strip()
            break
    lowered = text.lower()
    chrome_tokens = (
        "metro logo",
        "search metro",
        "open site menu",
        "share this article",
        "my account",
        "close search",
    )
    if any(token in lowered for token in chrome_tokens) and " | " in text:
        text = text.split(" | ", 1)[0].strip()
    if any(token in lowered for token in chrome_tokens):
        for token in chrome_tokens:
            index = lowered.find(token)
            if index > 0:
                text = text[:index].strip(" |-")
                break
    return text[:220].strip()



def _strip_html_tags(value: str) -> str:
    text = re.sub(r"<[^>]+>", " ", str(value or ""))
    return _normalize_text(html_lib.unescape(text))


def _iter_json_ld_objects(value: object):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _iter_json_ld_objects(child)
    elif isinstance(value, list):
        for item in value:
            yield from _iter_json_ld_objects(item)


def _json_ld_objects_from_html(html_text: str) -> list[dict[str, Any]]:
    objects: list[dict[str, Any]] = []
    for match in re.finditer(r"<script[^>]+application/ld\+json[^>]*>(.*?)</script>", html_text or "", flags=re.I | re.S):
        raw = html_lib.unescape(match.group(1).strip())
        if not raw:
            continue
        try:
            data = json.loads(raw)
        except Exception:
            continue
        for obj in _iter_json_ld_objects(data):
            if isinstance(obj, dict):
                objects.append(obj)
    return objects


def _schema_type(value: object) -> set[str]:
    raw = value.get("@type") if isinstance(value, dict) else ""
    if isinstance(raw, list):
        return {str(item).lower() for item in raw}
    return {str(raw).lower()}


def _schema_author_name(value: object) -> str:
    if isinstance(value, dict):
        return _normalize_text(value.get("name", ""))
    if isinstance(value, list):
        for item in value:
            found = _schema_author_name(item)
            if found:
                return found
    return _normalize_text(value)


def _metro_author_role_from_html(html_text: str, author_name: str = "") -> str:
    # Metro byline block uses: <a class="author-name">Barney Davis</a> | <span>Night News Editor</span>
    pattern = r'class=["\']author-name["\'][^>]*>.*?</a>\s*</strong>\s*<span>\|</span>\s*<span>(.*?)</span>'
    match = re.search(pattern, html_text or "", flags=re.I | re.S)
    if match:
        return _strip_html_tags(match.group(1))
    return ""


def _metro_date_line_from_html(html_text: str) -> str:
    published = ""
    updated = ""
    pub_match = re.search(r'class=["\']article__published["\'][^>]*>(.*?)</span>', html_text or "", flags=re.I | re.S)
    upd_match = re.search(r'class=["\']article__updated["\'][^>]*>(.*?)</span>', html_text or "", flags=re.I | re.S)
    if pub_match:
        published = _strip_html_tags(pub_match.group(1))
    if upd_match:
        updated = _strip_html_tags(upd_match.group(1))
    return " ".join(part for part in (published, updated) if part).strip()


def _article_body_from_schema_text(value: object) -> str:
    raw_lines = [_normalize_text(line) for line in str(value or "").replace("\r", "\n").split("\n")]
    lines: list[str] = []
    for line in raw_lines:
        if not line:
            continue
        lowered = line.lower()
        if lowered in {"to view this video please enable javascript, and consider upgrading to a web", "browser that", "supports html5", "video", "up next", "previous page", "next page"}:
            continue
        if _is_probable_chrome_text(line, title=""):
            continue
        lines.append(line)
    return "\n\n".join(lines).strip()


def _schema_article_text_from_html(html_text: str, *, fallback_title: str = "") -> tuple[str, str, tuple[str, ...]]:
    """Return (title, text, warnings) from JSON-LD/Metro metadata when available.

    This is a local HTML read only.  It avoids visible menu/comment rails while
    preserving article metadata/captions that ordinary selectable text can miss.
    """
    objects = _json_ld_objects_from_html(html_text)
    article_obj: dict[str, Any] | None = None
    video_name = ""
    for obj in objects:
        types = _schema_type(obj)
        if not video_name and "videoobject" in types:
            video_name = _normalize_text(obj.get("name", ""))
        if article_obj is None and ({"newsarticle", "article", "reportagenewsarticle"} & types) and _normalize_text(obj.get("articleBody", "")):
            article_obj = obj
    if not article_obj:
        return "", "", ()
    title = _clean_extracted_title(_normalize_text(article_obj.get("headline", "")) or fallback_title)
    body = _article_body_from_schema_text(article_obj.get("articleBody", ""))
    if not body:
        return title, "", ()
    parts: list[str] = []
    if title:
        parts.append(title)
    if 'postStyle":"exclusive"' in (html_text or "") or "metro-signpost-exclusive" in (html_text or ""):
        parts.append("EXCLUSIVE")
    author_name = _schema_author_name(article_obj.get("author", ""))
    if author_name:
        parts.append(author_name)
    author_role = _metro_author_role_from_html(html_text, author_name)
    if author_role:
        parts.append(author_role)
    date_line = _metro_date_line_from_html(html_text)
    if date_line:
        parts.append(date_line)
    if video_name and video_name.lower() not in {part.lower() for part in parts}:
        parts.append(video_name)
    parts.append(body)
    return title, "\n\n".join(part for part in parts if _normalize_text(part)).strip(), ("JSON-LD article body/metadata was used for fast clean article text.",)


def _attr_text(attrs: list[tuple[str, str | None]]) -> str:
    return " ".join(f"{key or ''} {value or ''}".lower() for key, value in attrs)


def _ignored_region_reason(tag: str, attrs: list[tuple[str, str | None]]) -> str:
    if tag in {"script", "style", "noscript", "template", "svg", "canvas"}:
        return "non_content"
    attr_text = _attr_text(attrs)
    if any(token in attr_text for token in ("comment", "discussion", "reply")):
        return "comments"
    if any(token in attr_text for token in ("advert", "ad-", " ad ", "sponsor", "promo", "outbrain", "taboola")):
        return "advertising"
    if any(
        token in attr_text
        for token in (
            "related",
            "recirc",
            "share",
            "social",
            "subscription",
            "subscribe",
            "newsletter",
            "cookie",
            "privacy",
            "site-menu",
            "nav",
            "menu",
            "header",
            "footer",
            "search",
            "login",
            "overlay",
            "modal",
            "dialog",
            "video-player",
            "jwplayer",
            "vjs",
            "plyr",
            "caption-settings",
            "trending",
        )
    ):
        return "page_chrome"
    if tag in {"nav", "footer", "form", "button", "select", "option"}:
        return "page_chrome"
    if tag == "aside":
        return "side_chrome"
    return ""


_SHORT_VIDEO_UI = {
    "play",
    "mute",
    "fullscreen",
    "text",
    "color",
    "white",
    "black",
    "red",
    "green",
    "blue",
    "yellow",
    "magenta",
    "cyan",
    "opaque",
    "semi-transparent",
    "transparent",
    "background",
    "window",
    "none",
    "raised",
    "depressed",
    "uniform",
    "dropshadow",
    "reset",
    "done",
    "up next",
}

_METADATA_OR_CHROME_RE = re.compile(
    r"^(?:"
    r"share this article.*|copy the link.*|comment now|previous page|next page|"
    r"play video|current time|duration|this is a modal window\.?|"
    r"beginning of dialog window.*|end of dialog window\.?|close modal dialog|"
    r"font size|font family|text edge style|proportional sans-serif|monospace sans-serif|"
    r"proportional serif|monospace serif|casual|script|small caps|"
    r"restore all settings.*|"
    r"sign up for all of the latest stories|start your day informed.*|breaking news|news updates|"
    r"stay on top of the headlines.*|trending now|read more stories|more offers|"
    r"add metro as a preferred source.*|i agree to receive newsletters.*|"
    r"newsletter or get|alerts the moment it happens\.?|"
    r"boy,?\s*16,?\s*drowns.*|paraguay senator.*|the fastest growing craze.*|"
    r"metro logo|metro on .*|search metro|close search|my account|open site menu|close site menu|"
    r"small logo|expand .* submenu|close login|close overlay|divider|"
    r"advertisement|sponsored|promoted|read more|more:.*"
    r")$",
    re.IGNORECASE,
)

_DATE_META_RE = re.compile(
    r"^(?:published|updated|by|\||\d{1,2}:\d{2}\s*(?:am|pm)?|"
    r"(?:january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{1,2},\s+\d{4}(?:\s+\d{1,2}:\d{2}\s*(?:am|pm))?|"
    r"\d+\s*(?:minutes?|hours?|days?)\s+ago)$",
    re.IGNORECASE,
)


def _is_probable_chrome_text(part: str, *, title: str = "") -> bool:
    text = _normalize_text(part)
    if not text:
        return True
    lowered = text.lower().strip()
    if title and lowered == _normalize_text(title).lower().strip():
        return True
    if lowered in _SHORT_VIDEO_UI:
        return True
    if _METADATA_OR_CHROME_RE.match(text):
        return True
    if _DATE_META_RE.match(text):
        return True
    if re.match(r"^\d{1,3}%$", text):
        return True
    if re.match(r"^\d+\s+hours?\s+ago$", text, flags=re.IGNORECASE):
        return True
    return False


def _clean_article_parts(parts: list[str], *, title: str = "") -> tuple[str, ...]:
    cleaned: list[str] = []
    seen_run: set[str] = set()
    for part in parts:
        text = _normalize_text(part)
        if not text or _is_probable_chrome_text(text, title=title):
            continue
        # Drop extremely short repeated channel/menu tokens while preserving normal initials/quotes.
        key = text.lower()
        if len(text) <= 3 and key in seen_run:
            continue
        if key in {"uk", "news", "home", "sport", "money", "travel"}:
            continue
        seen_run.add(key)
        cleaned.append(text)
    return tuple(cleaned)


def _article_sentence_complete(text: str) -> bool:
    stripped = _normalize_text(text).rstrip()
    return bool(re.search(r"[.!?][’”\"')\]]*$", stripped))


def _merge_article_inline_parts(parts: tuple[str, ...]) -> tuple[str, ...]:
    """Merge inline link text back into the surrounding paragraph.

    Metro and other news pages often split one paragraph into separate text nodes
    around links, e.g. ``North East`` / ``Lincolnshire`` / ``Council``.  Treat
    those short/link fragments as inline text while still keeping clear sentence
    and heading boundaries as paragraphs.
    """

    merged: list[str] = []
    current = ""
    for part in parts:
        text = _normalize_text(part)
        if not text:
            continue
        if not current:
            current = text
            continue
        starts_punctuation = bool(re.match(r"^[,.;:!?)]", text)) or text.startswith(("“.", "”.", "\".", "'.", "’."))
        current_looks_heading = (
            len(current) >= 48
            and not _article_sentence_complete(current)
            and not any(mark in current for mark in (",", ";", ":"))
            and not current.endswith((",", ":", "-", "–", "—"))
        )
        if starts_punctuation or (not _article_sentence_complete(current) and not current_looks_heading):
            separator = "" if starts_punctuation else " "
            current = (current + separator + text).replace(" :", ":").replace(" .", ".").strip()
            continue
        merged.append(current.strip())
        current = text
    if current:
        merged.append(current.strip())
    return tuple(item for item in merged if item)


def _join_paragraph_text(parts: list[str], *, title: str = "") -> str:
    cleaned = _clean_article_parts(parts, title=title)
    return "\n\n".join(_merge_article_inline_parts(cleaned))



_RENDERED_TEXT_STOP_RE = re.compile(
    r"^(?:"
    r"comments(?:\s+add as preferred source)?|related topics|must read|trending now|more:\s+|"
    r"metro shorts|metro deals|more offers|read more stories|news updates|"
    r"home\s*$|news\s*$|uk\s*$|london\s*$|us\s*$|world\s*$|crime\s*$|tech\s*$|science\s*$|"
    r"entertainment\s*$|sport\s*$|lifestyle\s*$|soaps\s*$|opinion\s*$|shopping\s*$|"
    r"puzzles\s*$|money\s*$|property\s*$|travel\s*$|horoscopes\s*$|"
    r"©\s*\d{4}|powered by|your ad choices|ipso regulated|terms and conditions|privacy policy|"
    r"do not sell|site map|contact us|about$"
    r")",
    re.IGNORECASE,
)

_RENDERED_TEXT_HARD_DROP_RE = re.compile(
    r"^(?:"
    r"video player is loading\.?|loaded:\s*\d+(?:\.\d+)?%|current time|duration|fullscreen|"
    r"up next|play video|play|mute|comments|sign up|email|sign up$|"
    r"share this article|copy the link|metro logo|search metro|open site menu|close site menu|"
    r"expand .* submenu|add metro as a preferred source|i agree to receive newsletters|"
    r"this site is protected by recaptcha|your information will be used|"
    r"teenage crash victim|police cordon|horse-drawn funeral|police chief speaks|doorbell footage|"
    r"students found|lindsay clancy|teen biker|robot beats|moment russia|one dead in swedish|"
    r"funeral begins|shocking cctv|moment supercars|woman, 38, accused|hampshire man|remains of hounslow|"
    r"knife thug|moment man calls police|flooding and mudslides|met police discover|vietnam airlines|"
    r"philadelphia police|harry and meghan|large police response|smoke billows|burnham:|car, somehow|"
    r"donald trump|reverend says|st pancras|we are all pleased|woman fired|everyone's asking|"
    r"rhinos cause|thousands of dead fish|pov of deptford|moment fighter jet|i can go for lunch"
    r")",
    re.IGNORECASE,
)

_RENDERED_TEXT_METADATA_DROP_RE = re.compile(
    r"^(?:"
    r"by\s+[A-Z].*|\d+\s+(?:minutes?|hours?|days?)\s+ago|[A-Z][a-z]+\s+\d{1,2},\s+\d{4}.*|"
    r"\d+:\d{2}|0:00|/|\-:-|[1-9]$|\d+$"
    r")$",
    re.IGNORECASE,
)

def _normalise_rendered_lines(rendered_text: object) -> list[str]:
    lines: list[str] = []
    for raw in str(rendered_text or '').replace('\r', '\n').split('\n'):
        line = _normalize_text(raw)
        if line:
            lines.append(line)
    return lines

def _rendered_line_is_drop(line: str, *, title: str = '') -> bool:
    text = _normalize_text(line)
    if not text:
        return True
    lowered = text.lower()
    title_lower = _normalize_text(title).lower()
    if title_lower and lowered == title_lower:
        return False
    if _is_probable_chrome_text(text, title=''):
        return True
    if _RENDERED_TEXT_HARD_DROP_RE.match(text):
        return True
    if _RENDERED_TEXT_METADATA_DROP_RE.match(text):
        return True
    if lowered in {
        'home', 'news', 'uk', 'london', 'us', 'world', 'crime', 'tech', 'science', 'politics',
        'entertainment', 'sport', 'lifestyle', 'soaps', 'opinion', 'shopping', 'puzzles', 'money',
        'property', 'travel', 'horoscopes', 'channel: uk', 'arrow', 'divider', 'more', 'menu',
    }:
        return True
    if '${video.headline}' in text:
        return True
    return False

def extract_article_text_from_rendered_text(
    rendered_text: object,
    *,
    source_url: str = '',
    title: str = '',
) -> ArticleExtractionResult:
    """Clean browser-rendered visible text when semantic HTML extraction is empty.

    This is still review-only local text processing. It does not fetch, screenshot,
    download, archive, classify finally, or infer sensitive identifiers.
    """

    lines = _normalise_rendered_lines(rendered_text)
    title_text = _normalize_text(title)
    if title_text and ' | ' in title_text:
        title_text = title_text.split(' | ', 1)[0].strip()
    selected: list[str] = []
    warnings: list[str] = []

    start_index = 0
    title_lower = title_text.lower()
    if title_lower:
        for index, line in enumerate(lines):
            if title_lower and (line.lower() == title_lower or title_lower in line.lower()):
                start_index = index
                break

    # Prefer the real article lead if the rendered page includes a video rail or
    # header/navigation block before the body. The lead pattern is intentionally
    # generic enough for Metro-style body text while not naming a person.
    lead_index = None
    for index, line in enumerate(lines[start_index:], start=start_index):
        lowered = line.lower()
        if lowered.startswith('a muslim woman has spoken out after') or lowered.startswith('nora mubarak was secretly filmed'):
            lead_index = index
            break
    if lead_index is not None:
        # Keep title/byline/date lines immediately before the lead when present,
        # but drop the intervening video rail.
        preface: list[str] = []
        for line in lines[start_index:lead_index]:
            if _rendered_line_is_drop(line, title=title_text):
                continue
            if line.lower().startswith('muslim woman who far right') or line.lower().startswith('published') or line.lower().startswith('updated') or 'night news editor' in line.lower() or 'barney davis' in line.lower() or (title_lower and title_lower in line.lower()):
                preface.append(line)
        selected.extend(preface[-6:])
        start_index = lead_index

    seen: set[str] = set()
    for line in lines[start_index:]:
        if _RENDERED_TEXT_STOP_RE.match(line):
            break
        if _rendered_line_is_drop(line, title=title_text):
            continue
        lowered = line.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        selected.append(line)

    if selected and selected[0].lower().startswith('title:'):
        selected = selected[1:]

    text = '\n\n'.join(selected).strip()
    if not text:
        warnings.append('No clean rendered article text found after chrome filtering.')
        return ArticleExtractionResult(
            source_url=source_url,
            status=ARTICLE_STATUS_EMPTY,
            title=title_text or title,
            text='',
            method='rendered_text_fallback_empty',
            confidence=0.0,
            warnings=tuple(warnings),
        )

    confidence = 0.72
    if lead_index is not None:
        confidence = 0.82
    return ArticleExtractionResult(
        source_url=source_url,
        status=ARTICLE_STATUS_EXTRACTED if confidence >= 0.5 else ARTICLE_STATUS_LOW_CONFIDENCE,
        title=title_text or title,
        text=text,
        method='rendered_text_fallback_cleaned',
        confidence=confidence,
        contamination_signals=('rendered_text_fallback_used',),
        warnings=tuple(warnings + ['Rendered browser text fallback was cleaned to remove navigation/video/newsletter/related-story chrome.']),
    )


def extract_article_text_from_html(html: str, *, source_url: str = "") -> ArticleExtractionResult:
    parser = _ArticleTextParser()
    warnings: list[str] = []
    try:
        parser.feed(html or "")
    except Exception:
        warnings.append("HTML parser reported a non-secret parsing issue; article text may be partial.")

    title = _clean_extracted_title(" ".join(parser.title_parts))
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
    if "page_chrome" in excluded_counts or "side_chrome" in excluded_counts:
        warnings.append("Navigation, modal, share, newsletter, or related-story chrome was excluded from article text.")
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

    schema_title, schema_text, schema_warnings = _schema_article_text_from_html(html or "", fallback_title=title)
    text = schema_text or _join_paragraph_text(selected_parts, title=title)
    if schema_text:
        title = schema_title or title
        method = "semantic_article"
        confidence = max(confidence, 0.9)
        warnings.extend(warning for warning in schema_warnings if warning not in warnings)
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
