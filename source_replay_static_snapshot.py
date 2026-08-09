from __future__ import annotations

import hashlib
import html
import re
from dataclasses import asdict, dataclass, is_dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Mapping, Sequence
from urllib.parse import urlsplit, urlunsplit


SOURCE_REPLAY_STATIC_SNAPSHOT_SCHEMA_VERSION = "source_replay_static_snapshot_v1"

STATIC_EVIDENCE_VIEW_READY = "STATIC_EVIDENCE_VIEW_READY"
STATIC_EVIDENCE_HTML_READY = "STATIC_EVIDENCE_HTML_READY"
STATIC_EVIDENCE_WARC_READY = "STATIC_EVIDENCE_WARC_READY"
REPLAYWEB_RUNTIME_PARTIAL_RENDER = "REPLAYWEB_RUNTIME_PARTIAL_RENDER"
STATIC_EVIDENCE_WARNING = (
    "Derived static replay/evidence view generated from local archived evidence. "
    "This is not the original dynamic page runtime."
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


def build_static_evidence_url(source_url: str, *, site_hint: str = "source") -> str:
    parsed = urlsplit(source_url)
    path = parsed.path or "/source"
    article_match = re.search(r"/(ar-[A-Za-z0-9]+)", path)
    if article_match:
        slug = article_match.group(1)
    else:
        digest = hashlib.sha256(source_url.encode("utf-8")).hexdigest()[:16]
        slug = f"source-{digest}"
    safe_site = re.sub(r"[^a-z0-9-]+", "-", site_hint.lower()).strip("-") or "source"
    return f"https://source-evidence.local/replay/{safe_site}/{slug}/static-evidence.html"


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


def build_static_replay_evidence_warc(
    input_data: StaticReplayEvidenceInput,
    *,
    gzip_output: bool = True,
) -> tuple[StaticReplayEvidencePageResult, bytes]:
    try:
        from warcio.statusandheaders import StatusAndHeaders
        from warcio.warcwriter import WARCWriter
    except Exception as error:  # pragma: no cover - exercised in user venv where warcio is available
        raise RuntimeError(f"warcio unavailable for static evidence WARC generation: {error}") from error

    from io import BytesIO

    page = build_static_replay_evidence_page(input_data)
    if page.errors:
        return page, b""
    html_payload = page.html.encode("utf-8")
    timestamp_utc = input_data.capture_timestamp or "2026-08-09T00:00:00Z"
    output = BytesIO()
    writer = WARCWriter(output, gzip=gzip_output)
    request_headers = StatusAndHeaders(
        f"{_warc_request_path(page.static_url)} HTTP/1.1",
        [("Host", urlsplit(page.static_url).netloc)],
        protocol="GET",
    )
    writer.write_record(
        writer.create_warc_record(
            page.static_url,
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
            page.static_url,
            "response",
            payload=BytesIO(html_payload),
            http_headers=response_headers,
            warc_headers_dict={"WARC-Date": timestamp_utc},
        )
    )
    return page, output.getvalue()


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
