from __future__ import annotations

import argparse
import csv
import html
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence
from urllib.parse import parse_qsl, urlencode, unquote, urlsplit, urlunsplit

from evidence_exporter import _write_readable_txt
from profile_media_youtube_proven_capability_registration_r42go import (
    R42GO_PASS_STATUS,
    validate_youtube_proven_capability_registration,
)
from profile_media_universal_source_map_r42gg import sanitize_source_url


R42GP_MARKER = "YTCE_R42GP_YOUTUBE_SEARCHABLE_HTML_PROFILE_URL_EXPORT_SURFACE"
R42GP_PASS_STATUS = "PASS_R42GP_YOUTUBE_SEARCHABLE_HTML_PROFILE_URL_EXPORT_SURFACE"
R42GP_BLOCKED_STATUS = "BLOCKED_R42GP_WITH_EXACT_BLOCKER"
R42GP_SCHEMA_VERSION = "youtube_searchable_html_profile_export.r42gp.v1"

DEFAULT_SAMPLE_VIDEO_URL = "https://www.youtube.com/watch?v=qGNKkvxE61Q"
NO_SIDE_EFFECT_BOUNDARY = (
    "offline export surface only: no live YouTube capture, no browser/WebView2/CDP launch, "
    "no screenshot run, no comment scraping run, no network fetch, no yt-dlp, no JDownloader, "
    "no source-role assignment, no counter/no-jump mutation, no metadata promotion"
)

REMOTE_URL_RE = re.compile(r"https?://", re.IGNORECASE)
MARKDOWN_LINK_RE = re.compile(r"\[[^\]]+\]\((https?://[^)]+)\)")


@dataclass(frozen=True)
class YoutubeCommentRecord:
    comment_id: str
    parent_id: str
    thread_id: str
    root_id: str
    depth: int
    comment_type: str
    author: str
    text: str
    published_at: str = ""
    likes: str = ""
    author_channel_id: str = ""
    author_channel_url: str = ""
    source_video_url: str = ""
    canonical_video_url: str = ""
    replies: tuple["YoutubeCommentRecord", ...] = ()

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["replies"] = [reply.to_dict() for reply in self.replies]
        return payload


@dataclass(frozen=True)
class YoutubeExportOptions:
    include_author_profile_urls: bool = False
    generated_at: str = ""


@dataclass(frozen=True)
class YoutubeProfileSidecarRow:
    comment_id: str
    parent_id: str
    thread_id: str
    root_id: str
    depth: int
    author: str
    author_channel_id: str
    author_channel_url: str
    profile_url: str
    published_at: str
    text_snippet: str
    source_video_url: str
    canonical_video_url: str
    url_source: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class YoutubeExportSurfaceFiles:
    output_dir: str
    manifest_path: str
    report_json_path: str
    report_md_path: str
    searchable_html_path: str
    readable_txt_reference_path: str
    profile_sidecar_json_path: str
    profile_sidecar_csv_path: str
    profile_sidecar_html_path: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class YoutubeExportSurfaceReport:
    marker: str
    schema_version: str
    status: str
    generated_at: str
    source_root: str
    source_video_url: str
    canonical_video_url: str
    include_author_profile_urls_default: bool
    include_author_profile_urls_effective: bool
    parents: int
    items: int
    max_depth: int
    files: Mapping[str, str]
    contrast_table: Mapping[str, str]
    checks: tuple[Mapping[str, str], ...]
    side_effect_boundary: str = NO_SIDE_EFFECT_BOUNDARY

    @property
    def passed(self) -> bool:
        return self.status == R42GP_PASS_STATUS and all(check.get("status") == "pass" for check in self.checks)

    def to_dict(self) -> dict[str, Any]:
        return {
            "marker": self.marker,
            "schema_version": self.schema_version,
            "status": self.status,
            "passed": self.passed,
            "generated_at": self.generated_at,
            "source_root": self.source_root,
            "source_video_url": self.source_video_url,
            "canonical_video_url": self.canonical_video_url,
            "include_author_profile_urls_default": self.include_author_profile_urls_default,
            "include_author_profile_urls_effective": self.include_author_profile_urls_effective,
            "parents": self.parents,
            "items": self.items,
            "max_depth": self.max_depth,
            "files": dict(self.files),
            "contrast_table": dict(self.contrast_table),
            "checks": [dict(item) for item in self.checks],
            "side_effect_boundary": self.side_effect_boundary,
        }


def _check(name: str, condition: bool, detail: str = "") -> dict[str, str]:
    return {"name": name, "status": "pass" if condition else "fail", "detail": detail}


def _clean_text(value: Any) -> str:
    text = str(value or "").replace("\u00a0", " ").replace("\u200b", "")
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n[ \t]+", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _compact_text(value: Any, *, limit: int = 240) -> str:
    text = re.sub(r"\s+", " ", _clean_text(value)).strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "..."


def plain_machine_url(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    match = MARKDOWN_LINK_RE.search(text)
    if match:
        text = match.group(1)
    elif text.startswith("[") and text.endswith("]"):
        text = text[1:-1].strip()
    text = unquote(text).replace("\\_", "_").replace("\\", "")
    sanitized = sanitize_source_url(text)
    text = sanitized or text
    parsed = urlsplit(text)
    if parsed.netloc.lower() in {"youtu.be"}:
        video_id = parsed.path.strip("/").split("/", 1)[0]
        if video_id:
            return f"https://www.youtube.com/watch?v={video_id}"
    if parsed.netloc.lower() in {"youtube.com", "www.youtube.com", "m.youtube.com"}:
        query_pairs = [(key, value) for key, value in parse_qsl(parsed.query, keep_blank_values=True) if key.lower() in {"v", "t", "start"}]
        path = parsed.path or "/watch"
        query = urlencode(query_pairs)
        return urlunsplit(("https", "www.youtube.com", path, query, ""))
    return text


def is_plain_machine_url(value: Any) -> bool:
    text = str(value or "").strip()
    return not text.startswith("[") and "](" not in text and r"]\(" not in text


def _channel_url_from_id(channel_id: str) -> tuple[str, str]:
    value = str(channel_id or "").strip()
    if value.startswith("UC") and len(value) >= 12:
        return f"https://www.youtube.com/channel/{value}", "derived_from_stable_youtube_channel_id"
    return "", "channel_id_preserved_url_not_derived"


def normalize_comment_record(record: Mapping[str, Any], *, source_video_url: str = "", parent_id: str = "", depth: int = 0, root_id: str = "") -> YoutubeCommentRecord:
    comment_id = str(record.get("comment_id") or record.get("id") or record.get("source_comment_id") or "")
    actual_parent = str(record.get("parent_id") or record.get("parentId") or parent_id or "")
    thread_id = str(record.get("thread_id") or record.get("threadId") or root_id or comment_id or actual_parent)
    actual_root = str(record.get("root_id") or record.get("rootId") or root_id or thread_id or comment_id)
    actual_depth = int(record.get("depth") or depth or 0)
    comment_type = str(record.get("type") or record.get("comment_type") or ("Reply" if actual_depth else "Parent Comment"))
    author_channel_id = str(record.get("author_channel_id") or record.get("authorChannelId") or record.get("channelId") or "")
    raw_channel_url = str(
        record.get("author_channel_url")
        or record.get("author_profile_url")
        or record.get("profile_url")
        or record.get("authorChannelUrl")
        or ""
    )
    channel_url = plain_machine_url(raw_channel_url) if raw_channel_url else ""
    canonical_video = plain_machine_url(record.get("canonical_video_url") or source_video_url)
    own_source_url = plain_machine_url(record.get("source_video_url") or source_video_url)
    replies = tuple(
        normalize_comment_record(
            reply,
            source_video_url=own_source_url or canonical_video,
            parent_id=comment_id,
            depth=actual_depth + 1,
            root_id=actual_root or comment_id,
        )
        for reply in record.get("replies") or []
        if isinstance(reply, Mapping)
    )
    return YoutubeCommentRecord(
        comment_id=comment_id,
        parent_id=actual_parent,
        thread_id=thread_id,
        root_id=actual_root,
        depth=actual_depth,
        comment_type=comment_type,
        author=str(record.get("author") or record.get("authorDisplayName") or "Unknown"),
        text=_clean_text(record.get("text") or record.get("textDisplay") or ""),
        published_at=str(record.get("published_at") or record.get("publishedAt") or record.get("created_at") or ""),
        likes=str(record.get("likes") or record.get("likeCount") or ""),
        author_channel_id=author_channel_id,
        author_channel_url=channel_url,
        source_video_url=own_source_url,
        canonical_video_url=canonical_video,
        replies=replies,
    )


def normalize_comment_records(records: Iterable[Mapping[str, Any]], *, source_video_url: str = "") -> tuple[YoutubeCommentRecord, ...]:
    return tuple(normalize_comment_record(record, source_video_url=source_video_url) for record in records)


def walk_comment_records(records: Iterable[YoutubeCommentRecord]) -> Iterable[YoutubeCommentRecord]:
    for record in records:
        yield record
        yield from walk_comment_records(record.replies)


def render_existing_readable_txt_reference(records: Sequence[YoutubeCommentRecord]) -> str:
    """Render through the existing YouTube readable export format."""

    lines = ["YouTube Comments - Readable Evidence Export", "=" * 80, ""]
    if not records:
        return "\n".join(lines + ["No comments found.", ""]) 
    flat = list(walk_comment_records(records))
    for index, record in enumerate(flat, 1):
        prefix = "\u21b3 Reply" if record.depth or record.comment_type.lower() == "reply" else f"[{index}] Parent Comment"
        lines.extend(
            [
                prefix,
                f"Author: {record.author}",
                f"Date: {record.published_at}",
                f"Likes: {record.likes or 0}",
            ]
        )
        if record.parent_id:
            lines.append(f"Parent ID: {record.parent_id}")
        lines.extend(["", "Text:", f"  {record.text}", "", "-" * 80, ""])
    return "\n".join(lines)


def _html_comment_block(record: YoutubeCommentRecord, *, include_author_profile_urls: bool) -> str:
    attrs = {
        "data-comment-id": record.comment_id,
        "data-parent-id": record.parent_id,
        "data-thread-id": record.thread_id,
        "data-depth": str(record.depth),
    }
    attr_text = " ".join(f'{name}="{html.escape(value, quote=True)}"' for name, value in attrs.items())
    indent = min(record.depth, 8)
    profile_line = ""
    if include_author_profile_urls and record.author_channel_url:
        profile_line = f'<div class="profile-url">Author channel: <code>{html.escape(record.author_channel_url)}</code></div>'
    replies = "\n".join(_html_comment_block(reply, include_author_profile_urls=include_author_profile_urls) for reply in record.replies)
    return f"""
<article class="comment depth-{indent}" style="--depth:{indent}" {attr_text}>
  <div class="comment-meta">
    <span class="comment-kind">{html.escape(record.comment_type)}</span>
    <strong>{html.escape(record.author)}</strong>
    <span>{html.escape(record.published_at)}</span>
    <span>{html.escape(str(record.likes))} like(s)</span>
  </div>
  <div class="comment-ids">comment {html.escape(record.comment_id)} · parent {html.escape(record.parent_id or '-')} · thread {html.escape(record.thread_id or '-')}</div>
  {profile_line}
  <p>{html.escape(record.text)}</p>
  {replies}
</article>
""".strip()


def render_searchable_comments_html(
    records: Sequence[YoutubeCommentRecord],
    *,
    source_video_url: str,
    include_author_profile_urls: bool = False,
) -> str:
    source_video_url = plain_machine_url(source_video_url)
    comments_html = "\n".join(_html_comment_block(record, include_author_profile_urls=include_author_profile_urls) for record in records)
    payload = json.dumps([record.to_dict() for record in records], ensure_ascii=False)
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>YouTube comments searchable export</title>
<style>
:root {{ color-scheme: light dark; }}
body {{ margin: 20px; font-family: system-ui, sans-serif; background: #101214; color: #f2f2f2; }}
button, input {{ background: #20242a; color: #f2f2f2; border: 1px solid #68707c; border-radius: 5px; padding: 6px 9px; }}
input[type="search"] {{ width: min(36rem, 86vw); }}
.toolbar {{ display: flex; gap: 8px; align-items: center; flex-wrap: wrap; margin: 12px 0 18px; }}
.comment {{ margin: 10px 0 10px calc(var(--depth) * 24px); padding: 10px 12px; border-left: 4px solid #7aa2ff; background: #171b20; border-radius: 7px; }}
.depth-1, .depth-2, .depth-3, .depth-4, .depth-5, .depth-6, .depth-7, .depth-8 {{ border-left-color: #95d68b; }}
.comment-meta {{ display: flex; gap: 10px; flex-wrap: wrap; color: #d8dde7; }}
.comment-kind {{ color: #ffd166; font-weight: 700; }}
.comment-ids, .profile-url, .small {{ color: #aeb6c2; font-size: 12px; }}
.hidden {{ display: none; }}
.match {{ outline: 2px solid #ffd166; }}
mark {{ background: #ffd166; color: #111; }}
pre {{ white-space: pre-wrap; background: #080a0d; padding: 10px; border-radius: 6px; }}
</style>
</head>
<body>
<h1>YouTube comments searchable export</h1>
<p class="small">Source video URL: <code>{html.escape(source_video_url)}</code></p>
<p class="small">Offline sibling export. Existing readable TXT/thread indentation remains separate and unchanged.</p>
<section aria-label="Search comments">
  <div class="toolbar">
    <input id="searchBox" type="search" placeholder="Search comments, replies, authors, IDs">
    <button id="searchButton" onclick="runSearch()">Search</button>
    <button id="clearSearch" onclick="clearSearch()">Clear</button>
    <button id="copySearchResults" onclick="copyResults()">Copy search results</button>
    <button id="downloadSearchResults" onclick="downloadResults()">Download search TXT</button>
  </div>
  <div id="searchSummary" class="small">No search run yet.</div>
</section>
<main id="commentsRoot">
{comments_html}
</main>
<section aria-label="Search result text">
  <h2>Search result text</h2>
  <pre id="searchResultText"></pre>
</section>
<script>
const commentsPayload = {payload};
let currentResultsText = "";
function walk(items, callback) {{
  for (const item of items) {{
    callback(item);
    walk(item.replies || [], callback);
  }}
}}
function flatRecords() {{
  const out = [];
  walk(commentsPayload, item => out.push(item));
  return out;
}}
function blockText(item) {{
  const prefix = Number(item.depth || 0) > 0 ? "Reply" : "Parent Comment";
  return [
    prefix + " " + (item.comment_id || ""),
    "Author: " + (item.author || ""),
    "Date: " + (item.published_at || ""),
    "Likes: " + (item.likes || ""),
    "Parent ID: " + (item.parent_id || ""),
    "Thread ID: " + (item.thread_id || ""),
    "",
    item.text || ""
  ].join("\\n").trim();
}}
function runSearch() {{
  const query = document.getElementById("searchBox").value.trim().toLowerCase();
  const articles = Array.from(document.querySelectorAll(".comment"));
  articles.forEach(el => {{ el.classList.remove("hidden", "match"); }});
  if (!query) {{
    currentResultsText = "";
    document.getElementById("searchSummary").textContent = "Showing all comments.";
    document.getElementById("searchResultText").textContent = "";
    return;
  }}
  const hits = [];
  for (const item of flatRecords()) {{
    const haystack = [item.comment_id, item.parent_id, item.thread_id, item.author, item.published_at, item.likes, item.text, item.author_channel_url].join(" ").toLowerCase();
    if (haystack.includes(query)) hits.push(item);
  }}
  const hitIds = new Set(hits.map(item => item.comment_id));
  articles.forEach(el => {{
    if (hitIds.has(el.dataset.commentId)) el.classList.add("match"); else el.classList.add("hidden");
  }});
  currentResultsText = hits.map(blockText).join("\\n\\n" + "-".repeat(60) + "\\n\\n");
  document.getElementById("searchSummary").textContent = hits.length + " result(s) for " + query;
  document.getElementById("searchResultText").textContent = currentResultsText;
}}
function clearSearch() {{
  document.getElementById("searchBox").value = "";
  runSearch();
}}
function copyResults() {{
  if (navigator.clipboard) navigator.clipboard.writeText(currentResultsText);
}}
function downloadResults() {{
  const blob = new Blob([currentResultsText], {{type: "text/plain;charset=utf-8"}});
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url; a.download = "youtube-comments-search-results.txt"; a.click();
  URL.revokeObjectURL(url);
}}
</script>
</body>
</html>
"""


def build_profile_sidecar_rows(
    records: Sequence[YoutubeCommentRecord],
    *,
    include_author_profile_urls: bool = False,
) -> tuple[YoutubeProfileSidecarRow, ...]:
    if not include_author_profile_urls:
        return ()
    rows: list[YoutubeProfileSidecarRow] = []
    for record in walk_comment_records(records):
        channel_url = record.author_channel_url
        url_source = "existing_metadata"
        if not channel_url and record.author_channel_id:
            channel_url, url_source = _channel_url_from_id(record.author_channel_id)
        if not (record.author_channel_id or channel_url):
            continue
        rows.append(
            YoutubeProfileSidecarRow(
                comment_id=record.comment_id,
                parent_id=record.parent_id,
                thread_id=record.thread_id,
                root_id=record.root_id,
                depth=record.depth,
                author=record.author,
                author_channel_id=record.author_channel_id,
                author_channel_url=channel_url,
                profile_url=channel_url,
                published_at=record.published_at,
                text_snippet=_compact_text(record.text),
                source_video_url=record.source_video_url,
                canonical_video_url=record.canonical_video_url,
                url_source=url_source,
            )
        )
    return tuple(rows)


def render_profile_sidecar_html(rows: Sequence[YoutubeProfileSidecarRow]) -> str:
    body = "\n".join(
        "<tr>"
        + "".join(
            f"<td>{html.escape(str(value))}</td>"
            for value in (
                row.comment_id,
                row.parent_id,
                row.thread_id,
                row.depth,
                row.author,
                row.author_channel_id,
                row.author_channel_url,
                row.published_at,
                row.text_snippet,
            )
        )
        + "</tr>"
        for row in rows
    )
    return f"""<!doctype html>
<html lang="en"><meta charset="utf-8">
<title>YouTube author profile/channel URL sidecar</title>
<style>body{{font-family:system-ui,sans-serif;margin:18px}}table{{border-collapse:collapse}}td,th{{border:1px solid #bbb;padding:5px 7px}}</style>
<h1>YouTube author profile/channel URL sidecar</h1>
<p>Optional sidecar generated only when include_author_profile_urls is enabled.</p>
<table><thead><tr><th>comment_id</th><th>parent_id</th><th>thread_id</th><th>depth</th><th>author</th><th>author_channel_id</th><th>author_channel_url</th><th>published_at</th><th>text_snippet</th></tr></thead>
<tbody>{body}</tbody></table>
</html>
"""


def contrast_table() -> dict[str, str]:
    return {
        "youtube_existing_readable_txt": "Protected Notepad-friendly parent/reply TXT output remains the canonical readable text artifact.",
        "youtube_additive_searchable_html": "R42GP adds a sibling local searchable HTML surface generated from already-captured records.",
        "youtube_optional_profile_url_sidecars": "Author/channel URL sidecars are explicit opt-in and default off.",
        "msn_v34_searchable_html_strength": "MSN V34 demonstrated local HTML search, copy results, and download search result ergonomics.",
        "msn_v35_profile_sidecar_strength": "MSN V35 demonstrated profile URL/account sidecars and copied profile URL behavior.",
        "non_replacement_policy": "YouTube output is not converted to MSN format and capture engines are not executed or replaced.",
    }


def sample_youtube_comment_records() -> tuple[YoutubeCommentRecord, ...]:
    return normalize_comment_records(
        (
            {
                "comment_id": "yt-parent-001",
                "thread_id": "yt-parent-001",
                "root_id": "yt-parent-001",
                "type": "Parent Comment",
                "author": "Example Parent",
                "author_channel_id": "UCexampleParent0001",
                "author_channel_url": "https://www.youtube.com/channel/UCexampleParent0001",
                "published_at": "2026-09-13T10:00:00Z",
                "likes": "12",
                "text": "Parent comment text for the preserved YouTube readable export.",
                "replies": (
                    {
                        "comment_id": "yt-reply-001",
                        "parent_id": "yt-parent-001",
                        "thread_id": "yt-parent-001",
                        "root_id": "yt-parent-001",
                        "depth": 1,
                        "type": "Reply",
                        "author": "Example Reply",
                        "author_channel_id": "UCreplyExample0002",
                        "published_at": "2026-09-13T10:05:00Z",
                        "likes": "3",
                        "text": "Indented reply text that remains easy to read in Notepad.",
                    },
                ),
            },
            {
                "comment_id": "yt-parent-002",
                "thread_id": "yt-parent-002",
                "root_id": "yt-parent-002",
                "type": "Parent Comment",
                "author": "Second Parent",
                "published_at": "2026-09-13T11:00:00Z",
                "likes": "4",
                "text": "Another parent comment for local HTML search.",
            },
        ),
        source_video_url=DEFAULT_SAMPLE_VIDEO_URL,
    )


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")


def write_youtube_searchable_export_surface(
    records: Sequence[YoutubeCommentRecord],
    output_root: str | Path,
    *,
    source_video_url: str,
    include_author_profile_urls: bool = False,
    source_root: str | Path = ".",
    generated_at: str = "",
) -> tuple[YoutubeExportSurfaceFiles, YoutubeExportSurfaceReport]:
    out = Path(output_root)
    out.mkdir(parents=True, exist_ok=True)
    generated = generated_at or datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    canonical_video_url = plain_machine_url(source_video_url)

    html_path = out / "youtube-comments-searchable-r42gp.html"
    readable_txt_path = out / "comments_readable_existing_format_reference.txt"
    sidecar_json_path = out / "youtube-author-profile-sidecar.json"
    sidecar_csv_path = out / "youtube-author-profile-sidecar.csv"
    sidecar_html_path = out / "youtube-author-profile-sidecar.html"
    manifest_path = out / "R42GP_YOUTUBE_EXPORT_SURFACE_MANIFEST.json"
    report_json_path = out / "R42GP_YOUTUBE_SEARCHABLE_HTML_PROFILE_EXPORT_REPORT.json"
    report_md_path = out / "R42GP_YOUTUBE_SEARCHABLE_HTML_PROFILE_EXPORT_REPORT.md"

    html_payload = render_searchable_comments_html(
        records,
        source_video_url=canonical_video_url,
        include_author_profile_urls=include_author_profile_urls,
    )
    html_path.write_text(html_payload, encoding="utf-8")

    # Keep a sibling artifact rendered through the existing readable TXT writer.
    existing_style_rows = [
        {
            "type": "Reply" if record.depth else "Parent Comment",
            "author": record.author,
            "published_at": record.published_at,
            "likes": record.likes,
            "text": record.text,
            "parent_id": record.parent_id,
        }
        for record in walk_comment_records(records)
    ]
    _write_readable_txt(readable_txt_path, existing_style_rows)

    sidecars = build_profile_sidecar_rows(records, include_author_profile_urls=include_author_profile_urls)
    _write_json(sidecar_json_path, [row.to_dict() for row in sidecars])
    with sidecar_csv_path.open("w", newline="", encoding="utf-8-sig") as handle:
        columns = (
            "comment_id",
            "parent_id",
            "thread_id",
            "root_id",
            "depth",
            "author",
            "author_channel_id",
            "author_channel_url",
            "profile_url",
            "published_at",
            "text_snippet",
            "source_video_url",
            "canonical_video_url",
            "url_source",
        )
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for row in sidecars:
            writer.writerow(row.to_dict())
    sidecar_html_path.write_text(render_profile_sidecar_html(sidecars), encoding="utf-8")

    files = YoutubeExportSurfaceFiles(
        output_dir=str(out),
        manifest_path=str(manifest_path),
        report_json_path=str(report_json_path),
        report_md_path=str(report_md_path),
        searchable_html_path=str(html_path),
        readable_txt_reference_path=str(readable_txt_path),
        profile_sidecar_json_path=str(sidecar_json_path),
        profile_sidecar_csv_path=str(sidecar_csv_path),
        profile_sidecar_html_path=str(sidecar_html_path),
    )
    r42go = validate_youtube_proven_capability_registration(source_root)
    flat = tuple(walk_comment_records(records))
    checks = (
        _check("searchable_html_written", html_path.is_file() and "id=\"searchBox\"" in html_payload),
        _check("html_has_no_remote_script_or_style_urls", html_has_no_remote_script_or_style_urls(html_payload)),
        _check("readable_txt_sibling_preserved", readable_txt_path.is_file() and "Parent Comment" in readable_txt_path.read_text(encoding="utf-8")),
        _check("profile_sidecar_default_is_optional", include_author_profile_urls is False or bool(sidecars)),
        _check("plain_machine_urls", all_machine_url_fields_plain({"source_video_url": canonical_video_url, "files": files.to_dict(), "sidecars": [row.to_dict() for row in sidecars]})),
        _check("no_capture_side_effects", "no live YouTube capture" in NO_SIDE_EFFECT_BOUNDARY),
        _check("r42go_still_green", r42go.status == R42GO_PASS_STATUS, r42go.status),
    )
    status = R42GP_PASS_STATUS if all(check["status"] == "pass" for check in checks) else R42GP_BLOCKED_STATUS
    report = YoutubeExportSurfaceReport(
        marker=R42GP_MARKER,
        schema_version=R42GP_SCHEMA_VERSION,
        status=status,
        generated_at=generated,
        source_root=str(source_root),
        source_video_url=canonical_video_url,
        canonical_video_url=canonical_video_url,
        include_author_profile_urls_default=False,
        include_author_profile_urls_effective=include_author_profile_urls,
        parents=sum(1 for record in records if record.depth == 0),
        items=len(flat),
        max_depth=max((record.depth for record in flat), default=0),
        files=files.to_dict(),
        contrast_table=contrast_table(),
        checks=checks,
    )
    _write_json(manifest_path, {"schema_version": R42GP_SCHEMA_VERSION, "files": files.to_dict(), "report": report.to_dict()})
    _write_json(report_json_path, report.to_dict())
    report_md_path.write_text(report_to_markdown(report), encoding="utf-8")
    return files, report


def html_has_no_remote_script_or_style_urls(html_text: str) -> bool:
    script_or_link = re.findall(r"<(?:script|link)\b[^>]*(?:src|href)\s*=\s*['\"]([^'\"]+)['\"]", html_text, flags=re.IGNORECASE)
    return all(not REMOTE_URL_RE.search(value) for value in script_or_link)


def all_machine_url_fields_plain(value: Any) -> bool:
    if isinstance(value, Mapping):
        for key, item in value.items():
            lowered = str(key).lower()
            if ("url" in lowered or lowered.endswith("path")) and item:
                if not is_plain_machine_url(item):
                    return False
            if not all_machine_url_fields_plain(item):
                return False
    elif isinstance(value, (list, tuple)):
        return all(all_machine_url_fields_plain(item) for item in value)
    return True


def report_to_markdown(report: YoutubeExportSurfaceReport) -> str:
    lines = [
        "# R42GP YouTube Searchable HTML + Optional Profile URL Export Surface",
        "",
        f"Marker: `{report.marker}`",
        f"Status: `{report.status}`",
        f"Canonical video URL: `{report.canonical_video_url}`",
        f"Profile URL export default: `{report.include_author_profile_urls_default}`",
        f"Profile URL export effective: `{report.include_author_profile_urls_effective}`",
        "",
        "## Contrast Table",
    ]
    for key, value in report.contrast_table.items():
        lines.append(f"- `{key}`: {value}")
    lines.extend(["", "## Checks"])
    for check in report.checks:
        detail = f" - {check['detail']}" if check.get("detail") else ""
        lines.append(f"- {check['name']}: {check['status']}{detail}")
    lines.extend(["", "## Side Effect Boundary", report.side_effect_boundary])
    return "\n".join(lines) + "\n"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build R42GP YouTube searchable HTML/profile sidecar export samples.")
    parser.add_argument("--source-root", default=".")
    parser.add_argument(
        "--output-root",
        default=r"profile_media_live_captures\r42gp_youtube_searchable_html_profile_export",
    )
    parser.add_argument("--include-author-profile-urls", action="store_true")
    args = parser.parse_args(argv)
    records = sample_youtube_comment_records()
    _files, report = write_youtube_searchable_export_surface(
        records,
        Path(args.source_root) / args.output_root,
        source_video_url=DEFAULT_SAMPLE_VIDEO_URL,
        include_author_profile_urls=args.include_author_profile_urls,
        source_root=args.source_root,
    )
    # Also write an opt-in sidecar sample so the audit package contains both modes.
    write_youtube_searchable_export_surface(
        records,
        Path(args.source_root) / args.output_root / "with_profile_urls_enabled_sample",
        source_video_url=DEFAULT_SAMPLE_VIDEO_URL,
        include_author_profile_urls=True,
        source_root=args.source_root,
    )
    print(R42GP_MARKER)
    print(report.status)
    print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
    return 0 if report.status == R42GP_PASS_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())
