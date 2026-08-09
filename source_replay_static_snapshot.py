from __future__ import annotations

import hashlib
import html
import re
import shutil
from dataclasses import asdict, dataclass, is_dataclass, replace
from enum import Enum
from pathlib import Path
from typing import Any, Mapping, Sequence
from urllib.parse import urlsplit, urlunsplit


SOURCE_REPLAY_STATIC_SNAPSHOT_SCHEMA_VERSION = "source_replay_static_snapshot_v1"

STATIC_EVIDENCE_VIEW_READY = "STATIC_EVIDENCE_VIEW_READY"
STATIC_EVIDENCE_HTML_READY = "STATIC_EVIDENCE_HTML_READY"
STATIC_EVIDENCE_WARC_READY = "STATIC_EVIDENCE_WARC_READY"
STATIC_PAGE_VIEW_READY = "STATIC_PAGE_VIEW_READY"
STATIC_PAGE_VIEW_HTML_READY = "STATIC_PAGE_VIEW_HTML_READY"
STATIC_PAGE_VIEW_WARC_READY = "STATIC_PAGE_VIEW_WARC_READY"
STATIC_TEXT_VIEW_READY = "STATIC_TEXT_VIEW_READY"
STATIC_TEXT_VIEW_HTML_READY = "STATIC_TEXT_VIEW_HTML_READY"
STATIC_TEXT_VIEW_WARC_READY = "STATIC_TEXT_VIEW_WARC_READY"
STATIC_ARTICLE_TEXT_EXPORT_READY = "STATIC_ARTICLE_TEXT_EXPORT_READY"
STATIC_COMMENTS_TEXT_EXPORT_READY = "STATIC_COMMENTS_TEXT_EXPORT_READY"
STATIC_PAGE_TEXT_EXPORT_READY = "STATIC_PAGE_TEXT_EXPORT_READY"
STATIC_PAGE_MARKDOWN_EXPORT_READY = "STATIC_PAGE_MARKDOWN_EXPORT_READY"
STATIC_PAGE_VIEW_VISUAL_FIDELITY_PARTIAL = "STATIC_PAGE_VIEW_VISUAL_FIDELITY_PARTIAL"
REPLAYWEB_RUNTIME_PARTIAL_RENDER = "REPLAYWEB_RUNTIME_PARTIAL_RENDER"
STATIC_EVIDENCE_WARNING = (
    "Derived static replay/evidence view generated from local archived evidence. "
    "This is not the original dynamic page runtime."
)
STATIC_PAGE_VIEW_WARNING = (
    "Derived static archived webpage view generated from local captured evidence. "
    "This is not the original dynamic MSN runtime."
)

DEFAULT_REPLAY_RUNTIME_LIMITATION_NOTES = (
    "Original ReplayWeb runtime page has not been visually verified as complete.",
    "This derived view is a stable, no-JavaScript review fallback built from local archived evidence metadata.",
)


def _value_for_dict(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return {key: _value_for_dict(item) for key, item in asdict(value).items()}
    if isinstance(value, tuple):
        return [_value_for_dict(item) for item in value]
    if isinstance(value, list):
        return [_value_for_dict(item) for item in value]
    if isinstance(value, Mapping):
        return {str(key): _value_for_dict(value[key]) for key in sorted(value)}
    if hasattr(value, "to_dict") and callable(value.to_dict):
        return value.to_dict()
    return value


@dataclass(frozen=True)
class StaticReplayEvidenceReference:
    label: str
    name: str
    sha256: str = ""
    source_path: str = ""

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class StaticReplayCommentsEvidence:
    status: str = ""
    comments_json_count: int = 0
    comments_jsonl_count: int = 0
    declared_comment_count: int = 0
    top_level_comment_count: int = 0
    reply_count: int = 0
    comments_complete: bool = False
    faithful_comments_screenshot_name: str = ""
    faithful_comments_screenshot_sha256: str = ""
    derived_comments_visual_name: str = ""
    derived_comments_visual_sha256: str = ""

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class StaticReplayEvidenceInput:
    source_url: str
    title: str = ""
    capture_timestamp: str = ""
    original_wacz_sha256: str = ""
    normalized_wacz_sha256: str = ""
    warc_record_count: int = 0
    replay_runtime_status: str = REPLAYWEB_RUNTIME_PARTIAL_RENDER
    replay_runtime_notes: tuple[str, ...] = DEFAULT_REPLAY_RUNTIME_LIMITATION_NOTES
    comments_evidence: StaticReplayCommentsEvidence | None = None
    captured_text_snippet: str = ""
    screenshot_references: tuple[StaticReplayEvidenceReference, ...] = ()
    manifest_references: tuple[StaticReplayEvidenceReference, ...] = ()
    static_url: str = ""
    schema_version: str = SOURCE_REPLAY_STATIC_SNAPSHOT_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class StaticReplayCommentItem:
    comment_id: str = ""
    parent_id: str = ""
    author: str = ""
    timestamp: str = ""
    text: str = ""
    permalink: str = ""
    depth: int = 0
    status: str = ""
    order: int = 0

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class StaticReplayPageViewInput:
    source_url: str
    title: str = ""
    capture_timestamp: str = ""
    article_text: str = ""
    captured_text_snippet: str = ""
    comments_evidence: StaticReplayCommentsEvidence | None = None
    comment_items: tuple[StaticReplayCommentItem, ...] = ()
    screenshot_references: tuple[StaticReplayEvidenceReference, ...] = ()
    manifest_references: tuple[StaticReplayEvidenceReference, ...] = ()
    evidence_report_path: str = ""
    evidence_report_url: str = ""
    replay_runtime_status: str = REPLAYWEB_RUNTIME_PARTIAL_RENDER
    replay_runtime_notes: tuple[str, ...] = DEFAULT_REPLAY_RUNTIME_LIMITATION_NOTES
    static_url: str = ""
    text_view_url: str = ""
    schema_version: str = SOURCE_REPLAY_STATIC_SNAPSHOT_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class StaticReplayEvidencePageResult:
    status: str
    static_url: str
    html: str
    html_sha256: str
    html_size_bytes: int
    contains_script_tag: bool
    contains_iframe_tag: bool
    contains_remote_runtime_dependency: bool
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()
    schema_version: str = SOURCE_REPLAY_STATIC_SNAPSHOT_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class StaticReplayPageViewResult:
    status: str
    static_url: str
    html: str
    html_sha256: str
    html_size_bytes: int
    contains_script_tag: bool
    contains_iframe_tag: bool
    contains_remote_runtime_dependency: bool
    visual_fidelity_status: str = STATIC_PAGE_VIEW_VISUAL_FIDELITY_PARTIAL
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()
    schema_version: str = SOURCE_REPLAY_STATIC_SNAPSHOT_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class StaticReplayCopiedAsset:
    label: str
    source_name: str
    relative_path: str
    sha256: str

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class StaticReplayStandaloneOutputResult:
    status: str
    static_evidence_url: str
    static_html_path: str = ""
    static_html_sha256: str = ""
    static_warc_gz_path: str = ""
    static_warc_gz_sha256: str = ""
    static_warc_path: str = ""
    static_warc_sha256: str = ""
    errors: tuple[str, ...] = ()
    schema_version: str = SOURCE_REPLAY_STATIC_SNAPSHOT_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class StaticReplayPageViewStandaloneOutputResult:
    status: str
    static_page_view_url: str
    static_page_view_html_path: str = ""
    static_page_view_html_sha256: str = ""
    static_page_view_warc_gz_path: str = ""
    static_page_view_warc_gz_sha256: str = ""
    static_page_view_warc_path: str = ""
    static_page_view_warc_sha256: str = ""
    visual_fidelity_status: str = STATIC_PAGE_VIEW_VISUAL_FIDELITY_PARTIAL
    copied_assets: tuple[StaticReplayCopiedAsset, ...] = ()
    errors: tuple[str, ...] = ()
    schema_version: str = SOURCE_REPLAY_STATIC_SNAPSHOT_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class StaticReplayTextViewStandaloneOutputResult:
    status: str
    static_text_view_url: str
    static_text_view_html_path: str = ""
    static_text_view_html_sha256: str = ""
    static_text_view_warc_gz_path: str = ""
    static_text_view_warc_gz_sha256: str = ""
    static_text_view_warc_path: str = ""
    static_text_view_warc_sha256: str = ""
    static_article_txt_path: str = ""
    static_article_txt_sha256: str = ""
    static_comments_txt_path: str = ""
    static_comments_txt_sha256: str = ""
    static_page_text_txt_path: str = ""
    static_page_text_txt_sha256: str = ""
    static_page_text_md_path: str = ""
    static_page_text_md_sha256: str = ""
    errors: tuple[str, ...] = ()
    schema_version: str = SOURCE_REPLAY_STATIC_SNAPSHOT_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


def build_static_evidence_url(source_url: str, *, site_hint: str = "source") -> str:
    slug = _stable_source_slug(source_url)
    safe_site = re.sub(r"[^a-z0-9-]+", "-", site_hint.lower()).strip("-") or "source"
    return f"https://source-evidence.local/replay/{safe_site}/{slug}/static-evidence.html"


def build_static_page_view_url(source_url: str, *, site_hint: str = "source") -> str:
    slug = _stable_source_slug(source_url)
    safe_site = re.sub(r"[^a-z0-9-]+", "-", site_hint.lower()).strip("-") or "source"
    return f"https://source-evidence.local/replay/{safe_site}/{slug}/static-page-view.html"


def build_static_text_view_url(source_url: str, *, site_hint: str = "source") -> str:
    slug = _stable_source_slug(source_url)
    safe_site = re.sub(r"[^a-z0-9-]+", "-", site_hint.lower()).strip("-") or "source"
    return f"https://source-evidence.local/replay/{safe_site}/{slug}/static-text-view.html"


def _stable_source_slug(source_url: str) -> str:
    parsed = urlsplit(source_url)
    path = parsed.path or "/source"
    article_match = re.search(r"/(ar-[A-Za-z0-9]+)", path)
    if article_match:
        return article_match.group(1)
    digest = hashlib.sha256(source_url.encode("utf-8")).hexdigest()[:16]
    return f"source-{digest}"


def _warc_request_path(url: str) -> str:
    parsed = urlsplit(url)
    path = parsed.path or "/"
    if parsed.query:
        path += "?" + parsed.query
    return urlunsplit(("", "", path, "", ""))


def _escape(value: object) -> str:
    return html.escape(str(value), quote=True)


def _section(title: str, body: str) -> str:
    return f"<section>\n<h2>{_escape(title)}</h2>\n{body}\n</section>"


def _list_items(values: Sequence[str]) -> str:
    if not values:
        return "<p>Not supplied.</p>"
    return "<ul>\n" + "\n".join(f"<li>{_escape(value)}</li>" for value in values) + "\n</ul>"


def _reference_table(references: Sequence[StaticReplayEvidenceReference]) -> str:
    if not references:
        return "<p>Not supplied.</p>"
    rows = [
        "<table><thead><tr><th>Label</th><th>File name</th><th>SHA-256</th></tr></thead><tbody>"
    ]
    for reference in references:
        rows.append(
            "<tr>"
            f"<td>{_escape(reference.label)}</td>"
            f"<td>{_escape(Path(reference.name).name)}</td>"
            f"<td>{_escape(reference.sha256 or 'not supplied')}</td>"
            "</tr>"
        )
    rows.append("</tbody></table>")
    return "\n".join(rows)


def _comments_section(comments: StaticReplayCommentsEvidence | None) -> str:
    if comments is None:
        return ""
    rows = (
        ("Status", comments.status or "not supplied"),
        ("Declared comment count", comments.declared_comment_count),
        ("JSON comment count", comments.comments_json_count),
        ("JSONL comment count", comments.comments_jsonl_count),
        ("Top-level comments", comments.top_level_comment_count),
        ("Replies", comments.reply_count),
        ("Complete", "yes" if comments.comments_complete else "no"),
        ("Faithful comments screenshot", comments.faithful_comments_screenshot_name or "not supplied"),
        ("Derived comments visual", comments.derived_comments_visual_name or "not supplied"),
    )
    body = ["<table><tbody>"]
    for label, value in rows:
        body.append(f"<tr><th>{_escape(label)}</th><td>{_escape(value)}</td></tr>")
    body.append("</tbody></table>")
    return _section("Comments evidence", "\n".join(body))


def _page_view_article_section(input_data: StaticReplayPageViewInput) -> str:
    if input_data.article_text.strip():
        return _article_text_to_html(input_data.article_text)
    if input_data.captured_text_snippet.strip():
        return (
            "<p><strong>Captured snippet:</strong></p>\n"
            f"<p>{_escape(input_data.captured_text_snippet.strip())}</p>"
        )
    return (
        "<p>Captured article body text was not available in the local manifest; "
        "use screenshot/visual references below.</p>"
    )


def _article_text_to_html(article_text: str) -> str:
    output: list[str] = []
    bullet_items: list[str] = []

    def flush_bullets() -> None:
        if bullet_items:
            output.append("<ul class=\"article-bullets\">")
            output.extend(f"<li>{_escape(item)}</li>" for item in bullet_items)
            output.append("</ul>")
            bullet_items.clear()

    for raw_block in re.split(r"\n\s*\n|\r\n\s*\r\n", article_text):
        block = raw_block.strip()
        if not block:
            continue
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        for line in lines:
            bullet_match = re.match(r"^(?:[-*•]\s+)(.+)$", line)
            if bullet_match:
                bullet_items.append(bullet_match.group(1).strip())
                continue
            flush_bullets()
            if line.upper() == "IN FULL":
                output.append("<h2 class=\"in-full\">IN FULL</h2>")
            elif " IN FULL " in line:
                before, after = line.split(" IN FULL ", 1)
                if before.strip():
                    output.append(f"<p>{_escape(before.strip())}</p>")
                output.append("<h2 class=\"in-full\">IN FULL</h2>")
                if after.strip():
                    output.append(f"<p>{_escape(after.strip())}</p>")
            else:
                output.append(f"<p>{_escape(line)}</p>")
    flush_bullets()
    return "\n".join(output) or "<p>Not supplied.</p>"


def _comments_summary_text(comments: StaticReplayCommentsEvidence | None) -> str:
    if comments is None:
        return "Comments evidence - not supplied"
    status = comments.status or "not supplied"
    return (
        f"Comments evidence - {status}, {comments.declared_comment_count} declared, "
        f"{comments.comments_json_count} JSON, {comments.comments_jsonl_count} JSONL, "
        f"{comments.top_level_comment_count} top-level, {comments.reply_count} replies"
    )


def _page_view_comments_section(input_data: StaticReplayPageViewInput) -> str:
    parts: list[str] = [
        _section(
            "Comments section",
            "<p>Comments are rendered only from local captured evidence supplied to this static page view.</p>",
        )
    ]
    if input_data.comments_evidence:
        parts.append(_comments_section(input_data.comments_evidence))
    if input_data.comment_items:
        rows = [
            "<table><thead><tr><th>Order</th><th>Depth</th><th>Author</th><th>Timestamp</th>"
            "<th>Comment text</th><th>IDs</th></tr></thead><tbody>"
        ]
        for item in sorted(input_data.comment_items, key=lambda comment: (comment.order or 0, comment.comment_id)):
            depth = max(0, int(item.depth or 0))
            id_text = " / ".join(
                value
                for value in (
                    f"id={item.comment_id}" if item.comment_id else "",
                    f"parent={item.parent_id}" if item.parent_id else "",
                    item.status or "",
                )
                if value
            )
            rows.append(
                "<tr>"
                f"<td>{_escape(item.order or '')}</td>"
                f"<td>{_escape(depth)}</td>"
                f"<td>{_escape(item.author or 'not supplied')}</td>"
                f"<td>{_escape(item.timestamp or 'not supplied')}</td>"
                f"<td style=\"padding-left:{depth * 18 + 8}px\">{_escape(item.text or 'not supplied')}</td>"
                f"<td>{_escape(id_text or 'not supplied')}</td>"
                "</tr>"
            )
        rows.append("</tbody></table>")
        parts.append(_section("Comment rows", "\n".join(rows)))
    elif input_data.comments_evidence:
        parts.append(
            _section(
                "Comment rows",
                "<p>Structured comment counts were supplied, but full comment text rows were not supplied.</p>",
            )
        )
    else:
        parts.append(_section("Comment rows", "<p>No local comments evidence was supplied.</p>"))
    return "\n".join(parts)


def _image_reference_for_label(
    references: Sequence[StaticReplayEvidenceReference],
    *label_parts: str,
) -> StaticReplayEvidenceReference | None:
    lowered_parts = tuple(part.lower() for part in label_parts)
    for reference in references:
        label = reference.label.lower()
        name = Path(reference.name).name.lower()
        haystack = f"{label} {name}"
        if all(part in haystack for part in lowered_parts):
            return reference
    return None


def _relative_image_or_empty(reference: StaticReplayEvidenceReference | None) -> str:
    if reference is None:
        return ""
    name = reference.name.replace("\\", "/")
    if re.match(r"^[A-Za-z]:/", name) or name.startswith("//"):
        return ""
    if name.startswith("assets/") or "/" not in name:
        return name
    return Path(name).name


def _page_view_hero(input_data: StaticReplayPageViewInput) -> str:
    hero = _image_reference_for_label(input_data.screenshot_references, "article")
    image_src = _relative_image_or_empty(hero)
    if not image_src:
        return (
            "<div class=\"hero-placeholder\">"
            "Local article visual was not available; see visual evidence references below."
            "</div>"
        )
    return (
        "<figure class=\"hero-visual\">"
        f"<img src=\"{_escape(image_src)}\" alt=\"Captured article visual evidence\">"
        f"<figcaption>{_escape(hero.label)} - SHA-256 {_escape(hero.sha256 or 'not supplied')}</figcaption>"
        "</figure>"
    )


def _page_view_evidence_report_reference(input_data: StaticReplayPageViewInput) -> str:
    references = []
    if input_data.evidence_report_path:
        references.append(f"Evidence report file: {Path(input_data.evidence_report_path).name}")
    if input_data.evidence_report_url:
        references.append(f"Evidence report URL: {input_data.evidence_report_url}")
    return _list_items(references)


def build_static_archived_page_view(input_data: StaticReplayPageViewInput) -> StaticReplayPageViewResult:
    static_url = input_data.static_url or build_static_page_view_url(input_data.source_url, site_hint="msn")
    title = input_data.title or "Static archived webpage view"
    source_body = (
        "<p class=\"source-url\">"
        + _escape(input_data.source_url)
        + "</p><p>This is the captured source URL. The current document is a derived static local review page.</p>"
    )
    timestamp_body = f"<p>{_escape(input_data.capture_timestamp or 'not supplied')}</p>"
    replay_body = (
        f"<p><strong>Status:</strong> {_escape(input_data.replay_runtime_status)}</p>"
        + _list_items(input_data.replay_runtime_notes)
    )
    publisher = "The Independent" if "msn.com" in input_data.source_url.lower() else "Captured source"
    read_meta = "Captured local evidence"
    html_text = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{_escape(title)} - derived static archived webpage view</title>
<style>
body {{ color: #f4f6f8; background: #202020; font-family: Arial, sans-serif; line-height: 1.52; margin: 0; }}
.msn-page-shell {{ max-width: 430px; margin: 0 auto; background: #242424; min-height: 100vh; }}
.msn-masthead {{ align-items: center; background: #181818; border-bottom: 1px solid #343434; display: flex; gap: 10px; padding: 10px 14px; position: sticky; top: 0; }}
.msn-logo {{ color: #fff; font-weight: 700; letter-spacing: .02em; }}
.msn-search {{ background: #f5f5f5; border-radius: 16px; color: #555; flex: 1; font-size: 12px; padding: 7px 12px; }}
main {{ padding: 22px 18px 36px; }}
.warning {{ background: #3a2f10; border: 1px solid #b7791f; border-radius: 4px; color: #ffe8a3; font-size: 12px; margin: 0 0 18px; padding: 12px; }}
.publisher-row {{ align-items: center; border-bottom: 1px solid #333; display: flex; gap: 8px; margin-bottom: 22px; padding-bottom: 12px; }}
.publisher-dot {{ background: #e21d2f; border-radius: 50%; height: 18px; width: 18px; }}
.publisher-name {{ font-size: 13px; font-weight: 700; }}
.follow-chip {{ border: 1px solid #575757; border-radius: 10px; color: #eee; font-size: 11px; padding: 3px 8px; }}
.article-title {{ color: #fff; font-size: 23px; line-height: 1.14; margin: 0 0 12px; }}
.byline {{ color: #b8c0c8; font-size: 12px; margin-bottom: 22px; }}
.read-time {{ color: #33c363; }}
.hero-placeholder {{ background: #303030; border: 1px dashed #666; border-radius: 6px; color: #cdd5dc; margin: 20px 0; padding: 24px; text-align: center; }}
.hero-visual {{ margin: 20px 0; }}
.hero-visual img {{ border-radius: 5px; display: block; max-width: 100%; width: 100%; }}
.hero-visual figcaption {{ color: #b8c0c8; font-size: 11px; margin-top: 6px; }}
.article-content p {{ color: #f5f5f5; font-size: 15px; margin: 0 0 14px; }}
.article-bullets {{ margin: 16px 0 16px 18px; padding: 0; }}
.article-bullets li {{ color: #f5f5f5; font-size: 14px; margin-bottom: 8px; }}
.in-full {{ color: #fff; font-size: 13px; letter-spacing: .04em; margin-top: 18px; text-transform: uppercase; }}
section {{ border-top: 1px solid #393939; margin-top: 26px; padding-top: 20px; }}
h2 {{ color: #fff; font-size: 17px; margin: 0 0 10px; }}
table {{ border-collapse: collapse; width: 100%; }}
th, td {{ border: 1px solid #414141; color: #f1f5f9; padding: 7px; text-align: left; vertical-align: top; }}
th {{ background: #303030; color: #dce3ea; }}
.source-url {{ color: #9ecbff; overflow-wrap: anywhere; font-family: Consolas, monospace; }}
.visual-grid {{ display: grid; gap: 12px; grid-template-columns: 1fr; }}
</style>
</head>
<body>
<div class="msn-page-shell static-page-view">
<div class="msn-masthead"><div class="msn-logo">msn</div><div class="msn-search">Search the web</div></div>
<main>
<div class="warning">{_escape(STATIC_PAGE_VIEW_WARNING)}</div>
<div class="publisher-row"><span class="publisher-dot"></span><span class="publisher-name">{_escape(publisher)}</span><span class="follow-chip">Follow</span></div>
<article class="article-content">
<h1 class="article-title">{_escape(title)}</h1>
<div class="byline">Story from local captured evidence · <span class="read-time">{_escape(read_meta)}</span></div>
{_page_view_hero(input_data)}
{_section("Article/content area", _page_view_article_section(input_data))}
</article>
{_page_view_comments_section(input_data)}
{_section("Screenshots/visual evidence", _reference_table(input_data.screenshot_references))}
{_section("Runtime replay limitation notice", replay_body)}
{_section("Evidence report reference", _page_view_evidence_report_reference(input_data))}
{_section("Source URL", source_body)}
{_section("Capture timestamp", timestamp_body)}
{_section("Manifest references", _reference_table(input_data.manifest_references))}
</main>
</div>
</body>
</html>
"""
    errors = tuple(validate_static_page_view_html(html_text))
    payload = html_text.encode("utf-8")
    return StaticReplayPageViewResult(
        status=STATIC_PAGE_VIEW_READY if not errors else "STATIC_PAGE_VIEW_INVALID",
        static_url=static_url,
        html=html_text,
        html_sha256=hashlib.sha256(payload).hexdigest(),
        html_size_bytes=len(payload),
        contains_script_tag=bool(re.search(r"<\s*script\b", html_text, flags=re.IGNORECASE)),
        contains_iframe_tag=bool(re.search(r"<\s*iframe\b", html_text, flags=re.IGNORECASE)),
        contains_remote_runtime_dependency=contains_remote_runtime_dependency(html_text),
        warnings=(STATIC_PAGE_VIEW_WARNING,),
        errors=errors,
    )


def _plain_comment_rows(input_data: StaticReplayPageViewInput) -> str:
    if not input_data.comment_items:
        if input_data.comments_evidence:
            return "Structured comment counts were supplied, but full comment text rows were not supplied."
        return "No local comments evidence was supplied."
    rows = []
    for item in sorted(input_data.comment_items, key=lambda comment: (comment.order or 0, comment.comment_id)):
        indent = "  " * max(0, int(item.depth or 0))
        header = f"{indent}- [{item.order or ''}] {item.author or 'Author not supplied'}"
        if item.timestamp:
            header += f" ({item.timestamp})"
        if item.comment_id:
            header += f" id={item.comment_id}"
        if item.parent_id:
            header += f" parent={item.parent_id}"
        rows.append(header)
        rows.append(f"{indent}  {item.text or 'Comment text not supplied'}")
    return "\n".join(rows)


def _plain_reference_rows(references: Sequence[StaticReplayEvidenceReference]) -> str:
    if not references:
        return "Not supplied."
    rows = []
    for reference in references:
        rows.append(
            f"- {reference.label}: {Path(reference.name).name}"
            + (f" sha256={reference.sha256}" if reference.sha256 else "")
        )
    return "\n".join(rows)


def build_static_article_text_export(input_data: StaticReplayPageViewInput) -> str:
    body = input_data.article_text.strip() or input_data.captured_text_snippet.strip()
    if not body:
        body = "Captured article body text was not available in the local manifest."
    return (
        "Static Article Text\n"
        "===================\n\n"
        f"Title: {input_data.title or 'not supplied'}\n"
        f"Source URL: {input_data.source_url}\n"
        f"Capture timestamp: {input_data.capture_timestamp or 'not supplied'}\n\n"
        "Article Text\n"
        "------------\n"
        f"{body}\n"
    )


def build_static_comments_text_export(input_data: StaticReplayPageViewInput) -> str:
    return (
        "Static Comments Text\n"
        "====================\n\n"
        f"Source URL: {input_data.source_url}\n"
        f"Capture timestamp: {input_data.capture_timestamp or 'not supplied'}\n\n"
        f"{_comments_summary_text(input_data.comments_evidence)}\n\n"
        "Comment Rows\n"
        "------------\n"
        f"{_plain_comment_rows(input_data)}\n"
    )


def build_static_page_text_export(input_data: StaticReplayPageViewInput) -> str:
    return (
        "Static Page Text\n"
        "================\n\n"
        "Source / Capture Metadata\n"
        "-------------------------\n"
        f"Title: {input_data.title or 'not supplied'}\n"
        f"Source URL: {input_data.source_url}\n"
        f"Capture timestamp: {input_data.capture_timestamp or 'not supplied'}\n\n"
        "Article Text\n"
        "------------\n"
        f"{(input_data.article_text.strip() or input_data.captured_text_snippet.strip() or 'Captured article body text was not available in the local manifest.')}\n\n"
        "Comments Evidence\n"
        "-----------------\n"
        f"{_comments_summary_text(input_data.comments_evidence)}\n\n"
        "Comment Rows\n"
        "------------\n"
        f"{_plain_comment_rows(input_data)}\n\n"
        "Runtime Replay Limitation\n"
        "-------------------------\n"
        f"Status: {input_data.replay_runtime_status}\n"
        + "\n".join(f"- {note}" for note in input_data.replay_runtime_notes)
        + "\n"
    )


def build_static_page_markdown_export(input_data: StaticReplayPageViewInput) -> str:
    return (
        "# Static Page Text\n\n"
        "## Source / Capture Metadata\n"
        f"- Title: {input_data.title or 'not supplied'}\n"
        f"- Source URL: {input_data.source_url}\n"
        f"- Capture timestamp: {input_data.capture_timestamp or 'not supplied'}\n\n"
        "<!-- #region Article Text -->\n"
        "## Article Text\n"
        f"{(input_data.article_text.strip() or input_data.captured_text_snippet.strip() or 'Captured article body text was not available in the local manifest.')}\n"
        "<!-- #endregion -->\n\n"
        "## Comments Evidence\n"
        f"{_comments_summary_text(input_data.comments_evidence)}\n\n"
        "<!-- #region Comment Rows -->\n"
        "## Comment Rows\n"
        f"{_plain_comment_rows(input_data)}\n"
        "<!-- #endregion -->\n\n"
        "## Screenshots / Visual Evidence\n"
        f"{_plain_reference_rows(input_data.screenshot_references)}\n\n"
        "## Runtime Replay Limitation\n"
        f"Status: {input_data.replay_runtime_status}\n"
        + "\n".join(f"- {note}" for note in input_data.replay_runtime_notes)
        + "\n\n"
        "## Integrity / Manifest References\n"
        f"{_plain_reference_rows(input_data.manifest_references)}\n"
    )


def _details(title: str, body: str, *, open_by_default: bool = False) -> str:
    open_attr = " open" if open_by_default else ""
    return f"<details{open_attr}>\n<summary>{_escape(title)}</summary>\n{body}\n</details>"


def build_static_text_view(input_data: StaticReplayPageViewInput) -> StaticReplayPageViewResult:
    static_url = input_data.text_view_url or build_static_text_view_url(input_data.source_url, site_hint="msn")
    title = input_data.title or "Static text view"
    source_body = (
        f"<p><strong>Title:</strong> {_escape(title)}</p>"
        f"<p class=\"source-url\">{_escape(input_data.source_url)}</p>"
        f"<p><strong>Capture timestamp:</strong> {_escape(input_data.capture_timestamp or 'not supplied')}</p>"
    )
    article_body = "<pre>" + _escape(
        input_data.article_text.strip()
        or input_data.captured_text_snippet.strip()
        or "Captured article body text was not available in the local manifest."
    ) + "</pre>"
    comments_body = (
        f"<p>{_escape(_comments_summary_text(input_data.comments_evidence))}</p>"
        "<pre>" + _escape(_plain_comment_rows(input_data)) + "</pre>"
    )
    runtime_body = (
        f"<p><strong>Status:</strong> {_escape(input_data.replay_runtime_status)}</p>"
        + _list_items(input_data.replay_runtime_notes)
    )
    html_text = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{_escape(title)} - static text view</title>
<style>
body {{ background: #f8fafc; color: #17202a; font-family: Arial, sans-serif; line-height: 1.5; margin: 0; }}
main {{ max-width: 980px; margin: 0 auto; padding: 24px; }}
.warning {{ background: #fff4ce; border: 2px solid #b7791f; padding: 16px; font-weight: 700; }}
details {{ background: #fff; border: 1px solid #d9e2ec; margin-top: 14px; padding: 12px; }}
summary {{ cursor: pointer; font-weight: 700; }}
pre {{ white-space: pre-wrap; word-wrap: break-word; }}
.source-url {{ overflow-wrap: anywhere; font-family: Consolas, monospace; }}
</style>
</head>
<body>
<main class="static-text-view">
<h1>Static Text View</h1>
<div class="warning">{_escape(STATIC_PAGE_VIEW_WARNING)}</div>
{_details("Source / capture metadata", source_body, open_by_default=True)}
{_details("Article text", article_body, open_by_default=bool(input_data.article_text.strip()))}
{_details(_comments_summary_text(input_data.comments_evidence), comments_body, open_by_default=False)}
{_details("Screenshots and visual evidence", "<pre>" + _escape(_plain_reference_rows(input_data.screenshot_references)) + "</pre>")}
{_details("Runtime replay limitation notice", runtime_body)}
{_details("Integrity / hashes / manifest references", "<pre>" + _escape(_plain_reference_rows(input_data.manifest_references)) + "</pre>")}
{_details("Evidence report reference", _page_view_evidence_report_reference(input_data))}
</main>
</body>
</html>
"""
    errors = tuple(validate_static_text_view_html(html_text))
    payload = html_text.encode("utf-8")
    return StaticReplayPageViewResult(
        status=STATIC_TEXT_VIEW_READY if not errors else "STATIC_TEXT_VIEW_INVALID",
        static_url=static_url,
        html=html_text,
        html_sha256=hashlib.sha256(payload).hexdigest(),
        html_size_bytes=len(payload),
        contains_script_tag=bool(re.search(r"<\s*script\b", html_text, flags=re.IGNORECASE)),
        contains_iframe_tag=bool(re.search(r"<\s*iframe\b", html_text, flags=re.IGNORECASE)),
        contains_remote_runtime_dependency=contains_remote_runtime_dependency(html_text),
        visual_fidelity_status=STATIC_PAGE_VIEW_VISUAL_FIDELITY_PARTIAL,
        warnings=(STATIC_PAGE_VIEW_WARNING,),
        errors=errors,
    )


def build_static_replay_evidence_page(input_data: StaticReplayEvidenceInput) -> StaticReplayEvidencePageResult:
    static_url = input_data.static_url or build_static_evidence_url(input_data.source_url, site_hint="msn")
    title = input_data.title or "Static replay evidence view"
    integrity_rows = (
        ("Original WACZ SHA-256", input_data.original_wacz_sha256 or "not supplied"),
        ("Normalized/package-ready WACZ SHA-256", input_data.normalized_wacz_sha256 or "not supplied"),
        ("WARC record count", input_data.warc_record_count or "not supplied"),
        ("Static evidence URL", static_url),
    )
    integrity_body = ["<table><tbody>"]
    for label, value in integrity_rows:
        integrity_body.append(f"<tr><th>{_escape(label)}</th><td>{_escape(value)}</td></tr>")
    integrity_body.append("</tbody></table>")

    source_body = (
        "<p class=\"source-url\">"
        + _escape(input_data.source_url)
        + "</p><p>This URL is recorded as source metadata only; this derived page is not that live source.</p>"
    )
    replay_body = (
        f"<p><strong>Status:</strong> {_escape(input_data.replay_runtime_status)}</p>"
        + _list_items(input_data.replay_runtime_notes)
    )
    text_body = (
        f"<p>{_escape(input_data.captured_text_snippet)}</p>"
        if input_data.captured_text_snippet
        else "<p>Not supplied.</p>"
    )
    integrity_html = "\n".join(integrity_body)
    html_text = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{_escape(title)} - derived static evidence view</title>
<style>
body {{ color: #1f2933; background: #f8fafc; font-family: Arial, sans-serif; line-height: 1.45; margin: 0; }}
main {{ max-width: 980px; margin: 0 auto; padding: 24px; }}
.warning {{ background: #fff4ce; border: 2px solid #b7791f; padding: 16px; font-weight: 700; }}
section {{ background: #ffffff; border: 1px solid #d9e2ec; margin-top: 16px; padding: 16px; }}
h1, h2 {{ color: #102a43; }}
table {{ border-collapse: collapse; width: 100%; }}
th, td {{ border: 1px solid #d9e2ec; padding: 8px; text-align: left; vertical-align: top; }}
th {{ background: #eef2f7; width: 30%; }}
.source-url {{ overflow-wrap: anywhere; font-family: Consolas, monospace; }}
</style>
</head>
<body>
<main>
<h1>{_escape(title)}</h1>
<div class="warning">{_escape(STATIC_EVIDENCE_WARNING)}</div>
{_section("Source URL", source_body)}
{_section("Original ReplayWeb runtime result", replay_body)}
{_section("Evidence integrity", integrity_html)}
{_comments_section(input_data.comments_evidence)}
{_section("Captured text/snippet", text_body)}
{_section("Screenshot references", _reference_table(input_data.screenshot_references))}
{_section("Manifest references", _reference_table(input_data.manifest_references))}
</main>
</body>
</html>
"""
    errors = tuple(validate_static_replay_evidence_html(html_text))
    payload = html_text.encode("utf-8")
    return StaticReplayEvidencePageResult(
        status=STATIC_EVIDENCE_VIEW_READY if not errors else "STATIC_EVIDENCE_VIEW_INVALID",
        static_url=static_url,
        html=html_text,
        html_sha256=hashlib.sha256(payload).hexdigest(),
        html_size_bytes=len(payload),
        contains_script_tag=bool(re.search(r"<\s*script\b", html_text, flags=re.IGNORECASE)),
        contains_iframe_tag=bool(re.search(r"<\s*iframe\b", html_text, flags=re.IGNORECASE)),
        contains_remote_runtime_dependency=contains_remote_runtime_dependency(html_text),
        warnings=(STATIC_EVIDENCE_WARNING,),
        errors=errors,
    )


def contains_remote_runtime_dependency(html_text: str) -> bool:
    return bool(
        re.search(
            r"<\s*(script|iframe|link|img|video|audio|source)\b[^>]+(?:src|href)\s*=\s*['\"]https?://",
            html_text,
            flags=re.IGNORECASE,
        )
    )


def validate_static_replay_evidence_html(html_text: str) -> list[str]:
    errors: list[str] = []
    if re.search(r"<\s*script\b", html_text, flags=re.IGNORECASE):
        errors.append("Static evidence page must not contain script tags.")
    if re.search(r"<\s*iframe\b", html_text, flags=re.IGNORECASE):
        errors.append("Static evidence page must not contain iframe tags.")
    if contains_remote_runtime_dependency(html_text):
        errors.append("Static evidence page must not contain remote runtime dependencies.")
    if STATIC_EVIDENCE_WARNING not in html_text:
        errors.append("Static evidence warning banner is missing.")
    return errors


def validate_static_page_view_html(html_text: str) -> list[str]:
    errors: list[str] = []
    if re.search(r"<\s*script\b", html_text, flags=re.IGNORECASE):
        errors.append("Static page view must not contain script tags.")
    if re.search(r"<\s*iframe\b", html_text, flags=re.IGNORECASE):
        errors.append("Static page view must not contain iframe tags.")
    if contains_remote_runtime_dependency(html_text):
        errors.append("Static page view must not contain remote runtime dependencies.")
    if STATIC_PAGE_VIEW_WARNING not in html_text:
        errors.append("Static page view warning banner is missing.")
    return errors


def validate_static_text_view_html(html_text: str) -> list[str]:
    errors: list[str] = []
    if re.search(r"<\s*script\b", html_text, flags=re.IGNORECASE):
        errors.append("Static text view must not contain script tags.")
    if re.search(r"<\s*iframe\b", html_text, flags=re.IGNORECASE):
        errors.append("Static text view must not contain iframe tags.")
    if contains_remote_runtime_dependency(html_text):
        errors.append("Static text view must not contain remote runtime dependencies.")
    if STATIC_PAGE_VIEW_WARNING not in html_text:
        errors.append("Static text view warning banner is missing.")
    if "<details" not in html_text or "<summary>" not in html_text:
        errors.append("Static text view must use native details/summary sections.")
    return errors


def _build_static_html_warc(
    *,
    static_url: str,
    html_payload: bytes,
    timestamp_utc: str,
    gzip_output: bool,
) -> bytes:
    try:
        from warcio.statusandheaders import StatusAndHeaders
        from warcio.warcwriter import WARCWriter
    except Exception as error:  # pragma: no cover - exercised in user venv where warcio is available
        raise RuntimeError(f"warcio unavailable for static WARC generation: {error}") from error

    from io import BytesIO

    output = BytesIO()
    writer = WARCWriter(output, gzip=gzip_output)
    request_headers = StatusAndHeaders(
        f"{_warc_request_path(static_url)} HTTP/1.1",
        [("Host", urlsplit(static_url).netloc)],
        protocol="GET",
    )
    writer.write_record(
        writer.create_warc_record(
            static_url,
            "request",
            payload=BytesIO(b""),
            http_headers=request_headers,
            warc_headers_dict={"WARC-Date": timestamp_utc},
        )
    )
    response_headers = StatusAndHeaders(
        "200 OK",
        [
            ("Content-Type", "text/html; charset=utf-8"),
            ("Content-Length", str(len(html_payload))),
        ],
        protocol="HTTP/1.1",
    )
    writer.write_record(
        writer.create_warc_record(
            static_url,
            "response",
            payload=BytesIO(html_payload),
            http_headers=response_headers,
            warc_headers_dict={"WARC-Date": timestamp_utc},
        )
    )
    return output.getvalue()


def build_static_replay_evidence_warc(
    input_data: StaticReplayEvidenceInput,
    *,
    gzip_output: bool = True,
) -> tuple[StaticReplayEvidencePageResult, bytes]:
    page = build_static_replay_evidence_page(input_data)
    if page.errors:
        return page, b""
    html_payload = page.html.encode("utf-8")
    timestamp_utc = input_data.capture_timestamp or "2026-08-09T00:00:00Z"
    return page, _build_static_html_warc(
        static_url=page.static_url,
        html_payload=html_payload,
        timestamp_utc=timestamp_utc,
        gzip_output=gzip_output,
    )


def build_static_page_view_warc(
    input_data: StaticReplayPageViewInput,
    *,
    gzip_output: bool = True,
) -> tuple[StaticReplayPageViewResult, bytes]:
    page = build_static_archived_page_view(input_data)
    if page.errors:
        return page, b""
    html_payload = page.html.encode("utf-8")
    timestamp_utc = input_data.capture_timestamp or "2026-08-09T00:00:00Z"
    return page, _build_static_html_warc(
        static_url=page.static_url,
        html_payload=html_payload,
        timestamp_utc=timestamp_utc,
        gzip_output=gzip_output,
    )


def build_static_text_view_warc(
    input_data: StaticReplayPageViewInput,
    *,
    gzip_output: bool = True,
) -> tuple[StaticReplayPageViewResult, bytes]:
    page = build_static_text_view(input_data)
    if page.errors:
        return page, b""
    html_payload = page.html.encode("utf-8")
    timestamp_utc = input_data.capture_timestamp or "2026-08-09T00:00:00Z"
    return page, _build_static_html_warc(
        static_url=page.static_url,
        html_payload=html_payload,
        timestamp_utc=timestamp_utc,
        gzip_output=gzip_output,
    )


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _write_new_file(path: Path, payload: bytes) -> str:
    if path.exists():
        raise FileExistsError(f"Static evidence output already exists and will not be overwritten: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return _sha256_bytes(payload)


def write_static_replay_evidence_page(path: str | Path, input_data: StaticReplayEvidenceInput) -> StaticReplayEvidencePageResult:
    result = build_static_replay_evidence_page(input_data)
    if result.errors:
        return result
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(result.html, encoding="utf-8", newline="\n")
    return result


def write_static_archived_page_view(path: str | Path, input_data: StaticReplayPageViewInput) -> StaticReplayPageViewResult:
    result = build_static_archived_page_view(input_data)
    if result.errors:
        return result
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(result.html, encoding="utf-8", newline="\n")
    return result


def _safe_asset_name(reference: StaticReplayEvidenceReference, index: int) -> str:
    suffix = Path(reference.name).suffix.lower()
    if suffix not in {".png", ".jpg", ".jpeg", ".webp", ".gif"}:
        suffix = ".png"
    stem = re.sub(r"[^A-Za-z0-9._-]+", "-", Path(reference.name).stem).strip(".-") or f"asset-{index}"
    digest = (reference.sha256 or hashlib.sha256((reference.label + reference.name).encode("utf-8")).hexdigest())[:12]
    return f"{index:02d}-{stem}-{digest}{suffix}"


def _copy_declared_image_assets(
    references: Sequence[StaticReplayEvidenceReference],
    output_html_path: Path,
) -> tuple[tuple[StaticReplayEvidenceReference, ...], tuple[StaticReplayCopiedAsset, ...]]:
    updated: list[StaticReplayEvidenceReference] = []
    copied: list[StaticReplayCopiedAsset] = []
    asset_dir = output_html_path.parent / "assets"
    for index, reference in enumerate(references, start=1):
        source_path = Path(reference.source_path) if reference.source_path else None
        if source_path is None or not source_path.is_file():
            updated.append(reference)
            continue
        if source_path.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp", ".gif"}:
            updated.append(reference)
            continue
        asset_dir.mkdir(parents=True, exist_ok=True)
        asset_name = _safe_asset_name(reference, index)
        destination = asset_dir / asset_name
        if destination.exists():
            raise FileExistsError(f"Static page-view asset already exists and will not be overwritten: {destination}")
        shutil.copyfile(source_path, destination)
        asset_hash = _sha256_bytes(destination.read_bytes())
        relative = f"assets/{asset_name}"
        copied.append(
            StaticReplayCopiedAsset(
                label=reference.label,
                source_name=source_path.name,
                relative_path=relative,
                sha256=asset_hash,
            )
        )
        updated.append(
            StaticReplayEvidenceReference(
                label=reference.label,
                name=relative,
                sha256=asset_hash,
                source_path=reference.source_path,
            )
        )
    return tuple(updated), tuple(copied)


def write_static_replay_standalone_outputs(
    input_data: StaticReplayEvidenceInput,
    *,
    html_path: str | Path | None = None,
    warc_gz_path: str | Path | None = None,
    warc_path: str | Path | None = None,
) -> StaticReplayStandaloneOutputResult:
    if not any((html_path, warc_gz_path, warc_path)):
        return StaticReplayStandaloneOutputResult(
            status="STATIC_EVIDENCE_OUTPUT_NOT_REQUESTED",
            static_evidence_url=input_data.static_url or build_static_evidence_url(input_data.source_url, site_hint="msn"),
        )
    try:
        page = build_static_replay_evidence_page(input_data)
        if page.errors:
            return StaticReplayStandaloneOutputResult(
                status="STATIC_EVIDENCE_OUTPUT_FAILED",
                static_evidence_url=page.static_url,
                errors=page.errors,
            )

        static_html_path = ""
        static_html_sha256 = ""
        if html_path:
            html_payload = page.html.encode("utf-8")
            html_destination = Path(html_path)
            static_html_sha256 = _write_new_file(html_destination, html_payload)
            static_html_path = str(html_destination)

        static_warc_gz_path = ""
        static_warc_gz_sha256 = ""
        if warc_gz_path:
            _page, warc_gz_payload = build_static_replay_evidence_warc(input_data, gzip_output=True)
            warc_gz_destination = Path(warc_gz_path)
            static_warc_gz_sha256 = _write_new_file(warc_gz_destination, warc_gz_payload)
            static_warc_gz_path = str(warc_gz_destination)

        static_warc_path = ""
        static_warc_sha256 = ""
        if warc_path:
            _page, warc_payload = build_static_replay_evidence_warc(input_data, gzip_output=False)
            warc_destination = Path(warc_path)
            static_warc_sha256 = _write_new_file(warc_destination, warc_payload)
            static_warc_path = str(warc_destination)

        statuses = []
        if static_html_path:
            statuses.append(STATIC_EVIDENCE_HTML_READY)
        if static_warc_gz_path or static_warc_path:
            statuses.append(STATIC_EVIDENCE_WARC_READY)
        return StaticReplayStandaloneOutputResult(
            status="+".join(statuses) if statuses else "STATIC_EVIDENCE_OUTPUT_NOT_REQUESTED",
            static_evidence_url=page.static_url,
            static_html_path=static_html_path,
            static_html_sha256=static_html_sha256,
            static_warc_gz_path=static_warc_gz_path,
            static_warc_gz_sha256=static_warc_gz_sha256,
            static_warc_path=static_warc_path,
            static_warc_sha256=static_warc_sha256,
        )
    except Exception as error:
        return StaticReplayStandaloneOutputResult(
            status="STATIC_EVIDENCE_OUTPUT_FAILED",
            static_evidence_url=input_data.static_url or build_static_evidence_url(input_data.source_url, site_hint="msn"),
            errors=(str(error),),
        )


def write_static_page_view_standalone_outputs(
    input_data: StaticReplayPageViewInput,
    *,
    html_path: str | Path | None = None,
    warc_gz_path: str | Path | None = None,
    warc_path: str | Path | None = None,
) -> StaticReplayPageViewStandaloneOutputResult:
    if not any((html_path, warc_gz_path, warc_path)):
        return StaticReplayPageViewStandaloneOutputResult(
            status="STATIC_PAGE_VIEW_OUTPUT_NOT_REQUESTED",
            static_page_view_url=input_data.static_url or build_static_page_view_url(input_data.source_url, site_hint="msn"),
        )
    try:
        copied_assets: tuple[StaticReplayCopiedAsset, ...] = ()
        html_input = input_data
        if html_path:
            updated_refs, copied_assets = _copy_declared_image_assets(
                input_data.screenshot_references,
                Path(html_path),
            )
            html_input = replace(input_data, screenshot_references=updated_refs)

        page = build_static_archived_page_view(html_input)
        if page.errors:
            return StaticReplayPageViewStandaloneOutputResult(
                status="STATIC_PAGE_VIEW_OUTPUT_FAILED",
                static_page_view_url=page.static_url,
                errors=page.errors,
            )

        static_html_path = ""
        static_html_sha256 = ""
        if html_path:
            html_payload = page.html.encode("utf-8")
            html_destination = Path(html_path)
            static_html_sha256 = _write_new_file(html_destination, html_payload)
            static_html_path = str(html_destination)

        static_warc_gz_path = ""
        static_warc_gz_sha256 = ""
        if warc_gz_path:
            _page, warc_gz_payload = build_static_page_view_warc(input_data, gzip_output=True)
            warc_gz_destination = Path(warc_gz_path)
            static_warc_gz_sha256 = _write_new_file(warc_gz_destination, warc_gz_payload)
            static_warc_gz_path = str(warc_gz_destination)

        static_warc_path = ""
        static_warc_sha256 = ""
        if warc_path:
            _page, warc_payload = build_static_page_view_warc(input_data, gzip_output=False)
            warc_destination = Path(warc_path)
            static_warc_sha256 = _write_new_file(warc_destination, warc_payload)
            static_warc_path = str(warc_destination)

        statuses = []
        if static_html_path:
            statuses.append(STATIC_PAGE_VIEW_HTML_READY)
        if static_warc_gz_path or static_warc_path:
            statuses.append(STATIC_PAGE_VIEW_WARC_READY)
        return StaticReplayPageViewStandaloneOutputResult(
            status="+".join(statuses) if statuses else "STATIC_PAGE_VIEW_OUTPUT_NOT_REQUESTED",
            static_page_view_url=page.static_url,
            static_page_view_html_path=static_html_path,
            static_page_view_html_sha256=static_html_sha256,
            static_page_view_warc_gz_path=static_warc_gz_path,
            static_page_view_warc_gz_sha256=static_warc_gz_sha256,
            static_page_view_warc_path=static_warc_path,
            static_page_view_warc_sha256=static_warc_sha256,
            visual_fidelity_status=STATIC_PAGE_VIEW_VISUAL_FIDELITY_PARTIAL,
            copied_assets=copied_assets,
        )
    except Exception as error:
        return StaticReplayPageViewStandaloneOutputResult(
            status="STATIC_PAGE_VIEW_OUTPUT_FAILED",
            static_page_view_url=input_data.static_url or build_static_page_view_url(input_data.source_url, site_hint="msn"),
            errors=(str(error),),
        )


def _write_text_output(path: str | Path | None, payload: str) -> tuple[str, str]:
    if not path:
        return "", ""
    destination = Path(path)
    sha256 = _write_new_file(destination, payload.encode("utf-8"))
    return str(destination), sha256


def write_static_text_view_standalone_outputs(
    input_data: StaticReplayPageViewInput,
    *,
    html_path: str | Path | None = None,
    warc_gz_path: str | Path | None = None,
    warc_path: str | Path | None = None,
    article_txt_path: str | Path | None = None,
    comments_txt_path: str | Path | None = None,
    page_text_txt_path: str | Path | None = None,
    page_text_md_path: str | Path | None = None,
) -> StaticReplayTextViewStandaloneOutputResult:
    if not any((html_path, warc_gz_path, warc_path, article_txt_path, comments_txt_path, page_text_txt_path, page_text_md_path)):
        return StaticReplayTextViewStandaloneOutputResult(
            status="STATIC_TEXT_VIEW_OUTPUT_NOT_REQUESTED",
            static_text_view_url=input_data.text_view_url or build_static_text_view_url(input_data.source_url, site_hint="msn"),
        )
    try:
        page = build_static_text_view(input_data)
        if page.errors:
            return StaticReplayTextViewStandaloneOutputResult(
                status="STATIC_TEXT_VIEW_OUTPUT_FAILED",
                static_text_view_url=page.static_url,
                errors=page.errors,
            )

        statuses: list[str] = []
        html_written_path = ""
        html_sha256 = ""
        if html_path:
            html_written_path, html_sha256 = _write_text_output(html_path, page.html)
            statuses.append(STATIC_TEXT_VIEW_HTML_READY)

        warc_gz_written_path = ""
        warc_gz_sha256 = ""
        if warc_gz_path:
            _page, warc_gz_payload = build_static_text_view_warc(input_data, gzip_output=True)
            destination = Path(warc_gz_path)
            warc_gz_sha256 = _write_new_file(destination, warc_gz_payload)
            warc_gz_written_path = str(destination)
            statuses.append(STATIC_TEXT_VIEW_WARC_READY)

        warc_written_path = ""
        warc_sha256 = ""
        if warc_path:
            _page, warc_payload = build_static_text_view_warc(input_data, gzip_output=False)
            destination = Path(warc_path)
            warc_sha256 = _write_new_file(destination, warc_payload)
            warc_written_path = str(destination)
            if STATIC_TEXT_VIEW_WARC_READY not in statuses:
                statuses.append(STATIC_TEXT_VIEW_WARC_READY)

        article_path, article_sha = _write_text_output(article_txt_path, build_static_article_text_export(input_data))
        if article_path:
            statuses.append(STATIC_ARTICLE_TEXT_EXPORT_READY)
        comments_path, comments_sha = _write_text_output(comments_txt_path, build_static_comments_text_export(input_data))
        if comments_path:
            statuses.append(STATIC_COMMENTS_TEXT_EXPORT_READY)
        page_text_path, page_text_sha = _write_text_output(page_text_txt_path, build_static_page_text_export(input_data))
        if page_text_path:
            statuses.append(STATIC_PAGE_TEXT_EXPORT_READY)
        page_md_path, page_md_sha = _write_text_output(page_text_md_path, build_static_page_markdown_export(input_data))
        if page_md_path:
            statuses.append(STATIC_PAGE_MARKDOWN_EXPORT_READY)

        return StaticReplayTextViewStandaloneOutputResult(
            status="+".join(statuses) if statuses else "STATIC_TEXT_VIEW_OUTPUT_NOT_REQUESTED",
            static_text_view_url=page.static_url,
            static_text_view_html_path=html_written_path,
            static_text_view_html_sha256=html_sha256,
            static_text_view_warc_gz_path=warc_gz_written_path,
            static_text_view_warc_gz_sha256=warc_gz_sha256,
            static_text_view_warc_path=warc_written_path,
            static_text_view_warc_sha256=warc_sha256,
            static_article_txt_path=article_path,
            static_article_txt_sha256=article_sha,
            static_comments_txt_path=comments_path,
            static_comments_txt_sha256=comments_sha,
            static_page_text_txt_path=page_text_path,
            static_page_text_txt_sha256=page_text_sha,
            static_page_text_md_path=page_md_path,
            static_page_text_md_sha256=page_md_sha,
        )
    except Exception as error:
        return StaticReplayTextViewStandaloneOutputResult(
            status="STATIC_TEXT_VIEW_OUTPUT_FAILED",
            static_text_view_url=input_data.text_view_url or build_static_text_view_url(input_data.source_url, site_hint="msn"),
            errors=(str(error),),
        )
