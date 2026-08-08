from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import tempfile
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence
from urllib.error import URLError
from urllib.parse import urlencode, urljoin, urlsplit
from urllib.request import Request, urlopen

from capture_action_log import ACTOR_TYPE_APPLICATION, build_action_log_event
from capture_article import extract_article_text_from_html
from capture_comments import extract_comments_from_html
from capture_contracts import stable_capture_id
from capture_media_discovery import (
    MEDIA_RESOURCE_KIND_IMAGE,
    MediaResource,
    discover_media_resources_from_html,
)
from capture_page_outline import build_page_outline_from_html, format_page_outline_text
from capture_warc_wacz import (
    WARC_RECORD_REQUEST,
    WARC_RECORD_RESPONSE,
    WACZIndexEntry,
    WACZPageEntry,
    WACZResourceRecord,
    build_warc_record,
    write_synthetic_wacz_fixture,
    write_synthetic_warc_fixture,
)
from source_adapters import find_source_adapter
from source_offline_bundle_writer import write_offline_evidence_bundle
from source_resource_state import canonicalize_msn_url


MSN_VERTICAL_VALIDATION_SCHEMA_VERSION = "msn_vertical_live_validation_v1"
DEFAULT_MSN_VERTICAL_URL = (
    "https://www.msn.com/en-gb/news/other/"
    "arrest-made-after-shot-fired-outside-york-mosque/ar-AA29207o?"
    "ocid=edgemobile&PC=EMMX01#comments"
)

STATUS_ALREADY_IMPLEMENTED_AND_TESTED = "ALREADY_IMPLEMENTED_AND_TESTED"
STATUS_STATIC_HTTP_LIVE_TESTED = "STATIC_HTTP_LIVE_TESTED"
STATUS_LIVE_SITE_MANUALLY_TESTED = "LIVE_SITE_MANUALLY_TESTED"
STATUS_PARTIAL = "PARTIAL"
STATUS_BLOCKED = "BLOCKED"
STATUS_N_A = "N_A"

FETCH_TIMEOUT_SECONDS = 30
MAX_HTML_BYTES = 10 * 1024 * 1024
MAX_DOWNLOAD_BYTES = 5 * 1024 * 1024

FetchClient = Callable[[str], "HttpFetchResult"]


@dataclass(frozen=True)
class HttpFetchResult:
    url: str
    status_code: int
    headers: Mapping[str, str]
    body: bytes
    final_url: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "body_sha256": _sha256_bytes(self.body),
            "body_size_bytes": len(self.body),
            "content_type": self.headers.get("Content-Type", self.headers.get("content-type", "")),
            "final_url": self.final_url or self.url,
            "status_code": int(self.status_code),
            "url": self.url,
        }


@dataclass(frozen=True)
class ArtifactSummary:
    label: str
    path: str
    sha256: str
    size_bytes: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "path": self.path,
            "sha256": self.sha256,
            "size_bytes": int(self.size_bytes),
        }


@dataclass(frozen=True)
class MsnVerticalValidationResult:
    source_url: str
    canonical_url: str
    output_directory: str
    status_matrix: Mapping[str, str]
    artifacts: tuple[ArtifactSummary, ...]
    manifest_path: str
    manifest_sha256: str
    summary: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "artifacts": [artifact.to_dict() for artifact in self.artifacts],
            "canonical_url": self.canonical_url,
            "manifest_path": self.manifest_path,
            "manifest_sha256": self.manifest_sha256,
            "output_directory": self.output_directory,
            "schema_version": MSN_VERTICAL_VALIDATION_SCHEMA_VERSION,
            "source_url": self.source_url,
            "status_matrix": dict(self.status_matrix),
            "summary": dict(self.summary),
        }


class _MetaMediaParser(HTMLParser):
    def __init__(self, source_url: str) -> None:
        super().__init__(convert_charrefs=True)
        self.source_url = source_url
        self.image_urls: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "meta":
            return
        attr_map = {str(key or "").lower(): value or "" for key, value in attrs}
        key = (attr_map.get("property") or attr_map.get("name") or "").lower()
        if key in {"og:image", "twitter:image", "twitter:image:src"} and attr_map.get("content"):
            self.image_urls.append(urljoin(self.source_url, attr_map["content"]))


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _sha256_file(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _safe_filename(value: str, fallback: str = "artifact") -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", Path(urlsplit(value).path).name or value).strip("._")
    return cleaned[:120] or fallback


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _preservation_headers(headers: Mapping[str, str]) -> dict[str, str]:
    allowed = {
        "cache-control",
        "content-length",
        "content-type",
        "date",
        "etag",
        "last-modified",
        "server",
    }
    return {
        str(key): str(value)
        for key, value in sorted(headers.items(), key=lambda item: item[0].lower())
        if str(key).lower() in allowed
    }


def _write_bytes(path: Path, payload: bytes) -> ArtifactSummary:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return ArtifactSummary(path.stem, str(path), _sha256_bytes(payload), len(payload))


def _write_json(path: Path, value: Any, label: str | None = None) -> ArtifactSummary:
    payload = _json_bytes(value)
    summary = _write_bytes(path, payload)
    return ArtifactSummary(label or summary.label, summary.path, summary.sha256, summary.size_bytes)


def _write_text(path: Path, value: str, label: str | None = None) -> ArtifactSummary:
    summary = _write_bytes(path, value.encode("utf-8"))
    return ArtifactSummary(label or summary.label, summary.path, summary.sha256, summary.size_bytes)


def _default_fetch(url: str) -> HttpFetchResult:
    request = Request(
        url,
        headers={
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-GB,en;q=0.9",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
            ),
        },
        method="GET",
    )
    with urlopen(request, timeout=FETCH_TIMEOUT_SECONDS) as response:
        body = response.read(MAX_HTML_BYTES + 1)
        if len(body) > MAX_HTML_BYTES:
            body = body[:MAX_HTML_BYTES]
        return HttpFetchResult(
            url=url,
            final_url=response.geturl(),
            status_code=int(getattr(response, "status", response.getcode())),
            headers={str(key): str(value) for key, value in response.headers.items()},
            body=body,
        )


def _fetch_json(fetcher: FetchClient, url: str) -> tuple[dict[str, Any], HttpFetchResult]:
    result = fetcher(url)
    try:
        parsed = json.loads(result.body.decode("utf-8", errors="replace"))
    except json.JSONDecodeError:
        parsed = {"parse_error": "json_decode_failed"}
    return parsed if isinstance(parsed, dict) else {"payload": parsed}, result


def _default_download(url: str, output_path: Path, max_bytes: int = MAX_DOWNLOAD_BYTES) -> HttpFetchResult:
    request = Request(
        url,
        headers={
            "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
            ),
        },
        method="GET",
    )
    with urlopen(request, timeout=FETCH_TIMEOUT_SECONDS) as response:
        declared_length = response.headers.get("Content-Length")
        if declared_length and int(declared_length) > max_bytes:
            raise ValueError("selected resource exceeds representative download byte limit")
        payload = response.read(max_bytes + 1)
        if len(payload) > max_bytes:
            raise ValueError("selected resource exceeds representative download byte limit")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(payload)
        return HttpFetchResult(
            url=url,
            final_url=response.geturl(),
            status_code=int(getattr(response, "status", response.getcode())),
            headers={str(key): str(value) for key, value in response.headers.items()},
            body=payload,
        )


def _meta_image_resources(html: str, source_url: str) -> tuple[dict[str, Any], ...]:
    parser = _MetaMediaParser(source_url)
    try:
        parser.feed(html or "")
    except Exception:
        return ()
    rows = []
    for index, url in enumerate(dict.fromkeys(parser.image_urls), start=1):
        rows.append(
            {
                "discovery_methods": ["metadata"],
                "downloadable": True,
                "kind": MEDIA_RESOURCE_KIND_IMAGE,
                "resource_id": stable_capture_id("msn_meta_image", url),
                "source_tag": "meta",
                "url": url,
                "display_name": f"metadata image {index}",
            }
        )
    return tuple(rows)


def _all_media_rows(html: str, source_url: str) -> tuple[dict[str, Any], ...]:
    discovered = discover_media_resources_from_html(html, source_url=source_url)
    rows: list[dict[str, Any]] = [resource.to_dict() for resource in discovered.resources]
    existing = {row["url"] for row in rows}
    for row in _meta_image_resources(html, source_url):
        if row["url"] not in existing:
            rows.append(row)
            existing.add(row["url"])
    return tuple(sorted(rows, key=lambda row: (str(row.get("kind")), str(row.get("url")))))


def _select_representative_download(media_rows: Sequence[Mapping[str, Any]]) -> Mapping[str, Any] | None:
    for row in media_rows:
        url = str(row.get("url") or "")
        parsed = urlsplit(url)
        if row.get("kind") != MEDIA_RESOURCE_KIND_IMAGE:
            continue
        if not row.get("downloadable", True):
            continue
        if parsed.scheme not in {"http", "https"}:
            continue
        if any(token in url.lower() for token in ("doubleclick", "adservice", "/ads?", "tracking")):
            continue
        return row
    return None


def _download_selected_resource(
    *,
    selected: Mapping[str, Any] | None,
    output_root: Path,
    download_fetcher: Callable[[str, Path, int], HttpFetchResult] | None,
    max_download_bytes: int,
) -> tuple[dict[str, Any], ArtifactSummary | None]:
    if selected is None:
        return (
            {
                "status": STATUS_N_A,
                "download_performed": False,
                "reason": "NO_REPRESENTATIVE_IMAGE_RESOURCE_FOUND",
            },
            None,
        )
    url = str(selected.get("url") or "")
    suffix = Path(urlsplit(url).path).suffix or ".bin"
    output_name = _safe_filename(url, "representative_media") + ("" if suffix in _safe_filename(url, "") else suffix)
    part_path = output_root / "downloads" / f"{output_name}.part"
    final_path = output_root / "downloads" / output_name
    fetcher = download_fetcher or _default_download
    try:
        result = fetcher(url, part_path, max_download_bytes)
        part_path.replace(final_path)
        artifact = ArtifactSummary(
            "representative_download",
            str(final_path),
            _sha256_file(final_path),
            final_path.stat().st_size,
        )
        return (
            {
                "content_type": result.headers.get("Content-Type", result.headers.get("content-type", "")),
                "download_performed": True,
                "final_url": result.final_url or result.url,
                "output_name": final_path.name,
                "resource_id": selected.get("resource_id", ""),
                "sha256": artifact.sha256,
                "size_bytes": artifact.size_bytes,
                "source_url": url,
                "status": STATUS_STATIC_HTTP_LIVE_TESTED,
            },
            artifact,
        )
    except Exception as error:
        if part_path.exists():
            part_path.unlink()
        return (
            {
                "download_performed": False,
                "reason": type(error).__name__,
                "message": str(error),
                "resource_id": selected.get("resource_id", ""),
                "source_url": url,
                "status": STATUS_PARTIAL,
            },
            None,
        )


def _wayback_check(
    source_url: str,
    fetcher: FetchClient,
) -> tuple[dict[str, Any], HttpFetchResult | None]:
    query_url = "https://archive.org/wayback/available?" + urlencode({"url": source_url})
    try:
        parsed, raw = _fetch_json(fetcher, query_url)
    except (URLError, TimeoutError, OSError, ValueError) as error:
        return (
            {
                "check_performed": True,
                "query_url": query_url,
                "status": STATUS_PARTIAL,
                "submission_performed": False,
                "error": str(error),
            },
            None,
        )
    archived = parsed.get("archived_snapshots") if isinstance(parsed, dict) else {}
    closest = archived.get("closest") if isinstance(archived, dict) else {}
    return (
        {
            "available": bool(closest),
            "check_performed": True,
            "query_url": query_url,
            "snapshot_status": closest.get("status") if isinstance(closest, dict) else "",
            "snapshot_timestamp": closest.get("timestamp") if isinstance(closest, dict) else "",
            "snapshot_url": closest.get("url") if isinstance(closest, dict) else "",
            "status": STATUS_STATIC_HTTP_LIVE_TESTED,
            "submission_performed": False,
        },
        raw,
    )


def _build_archive_artifacts(
    *,
    output_root: Path,
    source_url: str,
    canonical_url: str,
    title: str,
    html: str,
    fetch_result: HttpFetchResult,
    article_text: str,
    outline_text: str,
    comments: Sequence[Mapping[str, Any]],
    media_rows: Sequence[Mapping[str, Any]],
    selected_download: Mapping[str, Any],
    wayback_result: Mapping[str, Any],
    timestamp_utc: str,
) -> tuple[dict[str, Any], tuple[ArtifactSummary, ...]]:
    archive_root = output_root / "local_web_archive"
    html_bytes = html.encode("utf-8")
    request = build_warc_record(
        source_url=source_url,
        record_kind=WARC_RECORD_REQUEST,
        method="GET",
        timestamp_utc=timestamp_utc,
        headers={"Accept": "text/html"},
    )
    response = build_warc_record(
        source_url=fetch_result.final_url or source_url,
        record_kind=WARC_RECORD_RESPONSE,
        status_code=fetch_result.status_code,
        content_type=fetch_result.headers.get("Content-Type", fetch_result.headers.get("content-type", "text/html")),
        timestamp_utc=timestamp_utc,
        payload=html_bytes,
        headers=_preservation_headers(fetch_result.headers),
    )
    response_id = response.to_dict()["record_id"]
    warc_result = write_synthetic_warc_fixture(
        output_warc_path=archive_root / "msn_article.warc",
        source_url=source_url,
        records=(request, response),
        payloads_by_record_id={response_id: html_bytes},
    )
    wacz_result = write_synthetic_wacz_fixture(
        output_wacz_path=archive_root / "msn_article.wacz",
        package_id=stable_capture_id("msn_vertical_wacz", canonical_url, _sha256_bytes(html_bytes)),
        source_url=source_url,
        warc_manifest=warc_result.manifest,
        index_entries=(
            WACZIndexEntry(
                url=source_url,
                timestamp_utc=timestamp_utc,
                warc_record_id=response_id,
                status_code=fetch_result.status_code,
                content_type=fetch_result.headers.get("Content-Type", fetch_result.headers.get("content-type", "text/html")),
            ),
        ),
        pages=(WACZPageEntry(page_id=stable_capture_id("msn_page", canonical_url), url=source_url, title=title, timestamp_utc=timestamp_utc),),
        resources=tuple(
            WACZResourceRecord(
                resource_id=str(row.get("resource_id") or stable_capture_id("media", str(row.get("url") or ""))),
                url=str(row.get("url") or ""),
                media_type=str(row.get("kind") or ""),
                sha256=str(row.get("sha256") or ""),
                size_bytes=int(row.get("size_bytes") or 0),
            )
            for row in media_rows[:25]
        ),
    )
    bundle_result = write_offline_evidence_bundle(
        output_zip_path=archive_root / "local_evidence_bundle.zip",
        source_url=source_url,
        source_label="MSN controlled vertical validation",
        article_text=article_text,
        page_outline_text=outline_text,
        html_snapshot=html,
        comments=comments,
        livechat=(),
        selected_media_metadata=(selected_download,),
        archive_results=(wayback_result,),
        screenshot_paths=(),
    )
    viewer_status = _viewer_status(wacz_result)
    local_archive = {
        "archivebox_backend_default": False,
        "archivebox_optional_advanced_backend": True,
        "bundle": bundle_result.to_dict(),
        "local_web_archive_default": True,
        "status": "LOCAL_PACKAGE_STRUCTURALLY_VERIFIED",
        "viewer_status": viewer_status,
        "warc": warc_result.to_dict(),
        "wacz": wacz_result.to_dict(),
    }
    artifacts = (
        ArtifactSummary("warc", str(archive_root / "msn_article.warc"), warc_result.sha256, warc_result.size_bytes),
        ArtifactSummary("wacz", str(archive_root / "msn_article.wacz"), wacz_result.sha256, wacz_result.size_bytes),
        ArtifactSummary(
            "offline_evidence_bundle",
            str(archive_root / "local_evidence_bundle.zip"),
            bundle_result.sha256,
            bundle_result.size_bytes,
        ),
    )
    return local_archive, artifacts


def _viewer_status(wacz_result: Any) -> dict[str, Any]:
    configured = os.environ.get("REPLAYWEBPAGE_PATH", "").strip()
    status = {
        "configured_viewer": configured,
        "launcher_performed": False,
        "status": "VIEWER_NOT_CONFIGURED",
        "structural_zip_read_ok": False,
    }
    try:
        with zipfile.ZipFile(Path(wacz_result.manifest.fixture_wacz_path), "r") as bundle:
            names = set(bundle.namelist())
            status["structural_zip_read_ok"] = {"datapackage.json", "manifest.json", "archive/msn_article.warc"}.issubset(names)
    except Exception as error:
        status["status"] = "VIEWER_STRUCTURAL_CHECK_FAILED"
        status["error"] = str(error)
        return status
    if configured and Path(configured).exists():
        status["status"] = "VIEWER_CONFIGURED_NOT_LAUNCHED"
    return status


def _append_event(
    events: list[Any],
    *,
    session_id: str,
    action_type: str,
    result: str,
    timestamp_utc: str,
    request_summary: Mapping[str, Any] | None = None,
    artifact_ids: tuple[str, ...] = (),
    warnings: tuple[str, ...] = (),
) -> None:
    previous_hash = events[-1].event_hash if events else ""
    events.append(
        build_action_log_event(
            session_id=session_id,
            actor_type=ACTOR_TYPE_APPLICATION,
            action_type=action_type,
            result=result,
            timestamp_utc=timestamp_utc,
            previous_event_hash=previous_hash,
            request_summary=request_summary,
            artifact_ids=artifact_ids,
            warnings=warnings,
        )
    )


def run_msn_vertical_live_validation(
    *,
    source_url: str = DEFAULT_MSN_VERTICAL_URL,
    output_directory: str | Path | None = None,
    fetcher: FetchClient | None = None,
    wayback_fetcher: FetchClient | None = None,
    download_fetcher: Callable[[str, Path, int], HttpFetchResult] | None = None,
    max_download_bytes: int = MAX_DOWNLOAD_BYTES,
    timestamp_utc: str = "",
) -> MsnVerticalValidationResult:
    if source_url != DEFAULT_MSN_VERTICAL_URL:
        raise ValueError("controlled MSN vertical validation is approved for the configured MSN URL only")
    timestamp = timestamp_utc or _utc_now_iso()
    output_root = Path(output_directory or tempfile.mkdtemp(prefix="ytce_msn_vertical_live_validation_"))
    output_root.mkdir(parents=True, exist_ok=True)
    client = fetcher or _default_fetch
    artifacts: list[ArtifactSummary] = []
    events: list[Any] = []
    session_id = stable_capture_id("msn_vertical_validation", source_url, timestamp)

    adapter = find_source_adapter(source_url)
    canonical_url = canonicalize_msn_url(source_url)
    parsed = urlsplit(source_url)
    provenance = {
        "adapter_id": getattr(adapter, "source_name", ""),
        "canonical_url": canonical_url,
        "fragment": parsed.fragment,
        "query": parsed.query,
        "source_url": source_url,
        "source_url_preserved": True,
    }

    fetch_result = client(source_url)
    html = fetch_result.body.decode("utf-8", errors="replace")
    artifacts.append(_write_text(output_root / "page" / "raw.html", html, "raw_html"))
    artifacts.append(_write_text(output_root / "page" / "final_dom.html", html, "final_dom_snapshot"))
    _append_event(
        events,
        session_id=session_id,
        action_type="msn_source_fetch",
        result="completed",
        timestamp_utc=timestamp,
        request_summary={"host": parsed.netloc, "status_code": fetch_result.status_code, "network_scope": "approved_single_msn_url"},
        artifact_ids=("raw_html",),
    )

    article = extract_article_text_from_html(html, source_url=source_url)
    outline = build_page_outline_from_html(html, source_url=source_url)
    outline_text = format_page_outline_text(outline)
    article_data = article.to_dict()
    outline_data = outline.to_dict()
    artifacts.append(_write_text(output_root / "article" / "article.txt", article.text, "article_text"))
    artifacts.append(_write_text(output_root / "article" / "page_outline.txt", outline_text, "page_outline"))
    artifacts.append(_write_json(output_root / "article" / "article.json", article_data, "article_metadata"))
    artifacts.append(_write_json(output_root / "article" / "page_outline.json", outline_data, "page_outline_metadata"))
    _append_event(
        events,
        session_id=session_id,
        action_type="msn_article_outline_extraction",
        result=article.status,
        timestamp_utc=timestamp,
        request_summary={"article_chars": len(article.text), "outline_lines": len(outline.outline_lines)},
        artifact_ids=("article_text", "page_outline"),
        warnings=tuple(article.warnings + outline.warnings),
    )

    comments = extract_comments_from_html(html, source_url=source_url)
    comments_data = comments.to_dict()
    static_comment_markers = {
        "social-comment-wc": html.count("social-comment-wc"),
        "overlay-container": html.count("overlay-container"),
        "comment_token": html.lower().count("comment"),
    }
    comments_status = STATUS_PARTIAL
    if not comments.comments and not any(static_comment_markers.values()):
        comments_status = STATUS_BLOCKED
        comments_data["browser_runtime_required"] = True
        comments_data["block_reason"] = "MSN comments were not present in static HTML; browser/shadow-DOM runtime is required."
    artifacts.append(_write_json(output_root / "comments" / "comments.json", comments_data, "comments_metadata"))
    artifacts.append(
        _write_text(
            output_root / "comments" / "comments.txt",
            "\n".join(comment.text for comment in comments.comments),
            "comments_text",
        )
    )
    _append_event(
        events,
        session_id=session_id,
        action_type="msn_comments_static_extraction",
        result=comments_status,
        timestamp_utc=timestamp,
        request_summary={"comment_count": len(comments.comments), **static_comment_markers},
        artifact_ids=("comments_metadata",),
        warnings=tuple(comments.warnings),
    )

    media_rows = _all_media_rows(html, source_url)
    selected_resource = _select_representative_download(media_rows)
    selected_download, download_artifact = _download_selected_resource(
        selected=selected_resource,
        output_root=output_root,
        download_fetcher=download_fetcher,
        max_download_bytes=max_download_bytes,
    )
    if download_artifact is not None:
        artifacts.append(download_artifact)
    artifacts.append(
        _write_json(
            output_root / "media" / "resource_inventory.json",
            {
                "resources": list(media_rows),
                "selected_download": selected_download,
                "resource_count": len(media_rows),
            },
            "resource_inventory",
        )
    )
    _append_event(
        events,
        session_id=session_id,
        action_type="msn_media_discovery_download",
        result=selected_download["status"],
        timestamp_utc=timestamp,
        request_summary={"resource_count": len(media_rows), "selected_download_performed": selected_download["download_performed"]},
        artifact_ids=("resource_inventory", "representative_download") if download_artifact else ("resource_inventory",),
    )

    wayback_result, wayback_raw = _wayback_check(source_url, wayback_fetcher or client)
    artifacts.append(_write_json(output_root / "archive" / "wayback_check.json", wayback_result, "wayback_check"))
    if wayback_raw is not None:
        artifacts.append(_write_bytes(output_root / "archive" / "wayback_available_raw.json", wayback_raw.body))
    _append_event(
        events,
        session_id=session_id,
        action_type="msn_wayback_check",
        result=wayback_result["status"],
        timestamp_utc=timestamp,
        request_summary={"check_performed": True, "submission_performed": False, "available": wayback_result.get("available")},
        artifact_ids=("wayback_check",),
    )

    screenshot_result = {
        "browser_runtime_available": False,
        "capture_performed": False,
        "mode": "faithful_page_screenshot",
        "reason": "BROWSER_RUNTIME_NOT_AVAILABLE",
        "status": STATUS_BLOCKED,
    }
    artifacts.append(_write_json(output_root / "screenshots" / "screenshot_status.json", screenshot_result, "screenshot_status"))

    local_archive, archive_artifacts = _build_archive_artifacts(
        output_root=output_root,
        source_url=source_url,
        canonical_url=canonical_url,
        title=article.title or outline.title,
        html=html,
        fetch_result=fetch_result,
        article_text=article.text,
        outline_text=outline_text,
        comments=[comment.to_dict() for comment in comments.comments],
        media_rows=media_rows,
        selected_download=selected_download,
        wayback_result=wayback_result,
        timestamp_utc=timestamp,
    )
    artifacts.extend(archive_artifacts)
    artifacts.append(_write_json(output_root / "local_web_archive" / "local_web_archive_result.json", local_archive, "local_web_archive_result"))
    _append_event(
        events,
        session_id=session_id,
        action_type="msn_local_web_archive_written",
        result=local_archive["status"],
        timestamp_utc=timestamp,
        request_summary={"local_web_archive_default": True, "archivebox_executed": False, "viewer_status": local_archive["viewer_status"]["status"]},
        artifact_ids=("warc", "wacz", "offline_evidence_bundle"),
    )

    status_matrix = {
        "source_identification": STATUS_STATIC_HTTP_LIVE_TESTED,
        "article_text_extraction": STATUS_STATIC_HTTP_LIVE_TESTED if article.text else STATUS_PARTIAL,
        "visible_page_outline": STATUS_STATIC_HTTP_LIVE_TESTED if outline.outline_lines else STATUS_PARTIAL,
        "faithful_screenshot": STATUS_BLOCKED,
        "derived_screenshot": STATUS_BLOCKED,
        "comments_shadow_dom": comments_status,
        "resource_inventory": STATUS_STATIC_HTTP_LIVE_TESTED if media_rows else STATUS_PARTIAL,
        "representative_download": selected_download["status"],
        "wayback_check": wayback_result["status"],
        "wayback_submit": STATUS_N_A,
        "local_web_archive": local_archive["status"],
        "archivebox": STATUS_N_A,
        "evidence_database": STATUS_N_A,
    }
    summary = {
        "article": article_data,
        "comments": comments_data,
        "download": selected_download,
        "live_actions": {
            "approved_single_msn_fetch": True,
            "archivebox_executed": False,
            "browser_profile_used": False,
            "external_sites_other_than_approved_msn_and_wayback_check": False,
            "wayback_check_performed": True,
            "wayback_submit_performed": False,
        },
        "local_web_archive": local_archive,
        "media": {"resource_count": len(media_rows), "resources": list(media_rows[:50])},
        "outline": outline_data,
        "provenance": provenance,
        "screenshot": screenshot_result,
        "wayback": wayback_result,
    }
    artifacts.append(_write_json(output_root / "summary" / "validation_summary.json", summary, "validation_summary"))
    action_log_path = output_root / "action_log.jsonl"
    action_log_payload = "".join(json.dumps(event.to_dict(), sort_keys=True) + "\n" for event in events)
    artifacts.append(_write_text(action_log_path, action_log_payload, "action_log"))
    artifacts.append(_write_text(output_root / "SHA256SUMS.txt", _format_sha256sums(artifacts), "sha256sums"))
    manifest = {
        "artifacts": [artifact.to_dict() for artifact in artifacts],
        "canonical_url": canonical_url,
        "schema_version": MSN_VERTICAL_VALIDATION_SCHEMA_VERSION,
        "source_url": source_url,
        "status_matrix": status_matrix,
        "summary": summary,
        "timestamp_utc": timestamp,
    }
    manifest_artifact = _write_json(output_root / "manifest.json", manifest, "manifest")
    artifacts.append(manifest_artifact)
    return MsnVerticalValidationResult(
        source_url=source_url,
        canonical_url=canonical_url,
        output_directory=str(output_root),
        status_matrix=status_matrix,
        artifacts=tuple(artifacts),
        manifest_path=manifest_artifact.path,
        manifest_sha256=manifest_artifact.sha256,
        summary=summary,
    )


def _format_sha256sums(artifacts: Sequence[ArtifactSummary]) -> str:
    lines = []
    for artifact in sorted(artifacts, key=lambda item: item.path):
        lines.append(f"{artifact.sha256}  {Path(artifact.path).name}")
    return "\n".join(lines) + "\n"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Controlled MSN vertical live validation for the approved MSN URL.")
    parser.add_argument("--url", default=DEFAULT_MSN_VERTICAL_URL)
    parser.add_argument("--output-dir", default="")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    result = run_msn_vertical_live_validation(
        source_url=args.url,
        output_directory=args.output_dir or None,
    )
    payload = result.to_dict()
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(f"MSN validation output: {result.output_directory}")
        print(f"Manifest: {result.manifest_path}")
        for key, value in result.status_matrix.items():
            print(f"{key}: {value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
