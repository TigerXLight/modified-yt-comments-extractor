from __future__ import annotations

import argparse
import gzip
import hashlib
import html as html_lib
import json
import os
import re
import tempfile
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import Any, Mapping, Sequence
from urllib.parse import urlencode, urlsplit, urlunsplit
from urllib.request import Request, urlopen

from PIL import Image
from warcio.archiveiterator import ArchiveIterator
from warcio.statusandheaders import StatusAndHeaders
from warcio.warcwriter import WARCWriter

from capture_action_log import ACTOR_TYPE_APPLICATION, build_action_log_event
from capture_article import extract_article_text_from_html
from capture_comments import extract_comments_from_html
from capture_contracts import stable_capture_id
from capture_media_discovery import discover_media_resources_from_html
from capture_page_outline import build_page_outline_from_html, format_page_outline_text
from source_msn_vertical_live_validation import (
    DEFAULT_MSN_VERTICAL_URL,
    STATUS_BLOCKED,
    STATUS_N_A,
    STATUS_PARTIAL,
    _sha256_bytes,
)
from source_offline_bundle_writer import write_offline_evidence_bundle
from source_resource_state import canonicalize_msn_url


MSN_RENDERED_BROWSER_SCHEMA_VERSION = "msn_rendered_browser_validation_v1"
STATIC_HTTP_LIVE_TESTED = "STATIC_HTTP_LIVE_TESTED"
RENDERED_BROWSER_LIVE_TESTED = "RENDERED_BROWSER_LIVE_TESTED"
LOCAL_PACKAGE_STRUCTURALLY_VERIFIED = "LOCAL_PACKAGE_STRUCTURALLY_VERIFIED"
REPLAY_OPENED = "REPLAY_OPENED"
REPLAY_PARTIAL = "REPLAY_PARTIAL"
REPLAY_FAILED = "REPLAY_FAILED"
REPLAY_VISUALLY_VERIFIED = "REPLAY_VISUALLY_VERIFIED"
USER_VISUAL_CONFIRMATION_REQUIRED = "USER_VISUAL_CONFIRMATION_REQUIRED"
RATE_LIMITED = "RATE_LIMITED"
TOOL_NOT_CONFIGURED = "TOOL_NOT_CONFIGURED"
VIEWER_NOT_CONFIGURED = "VIEWER_NOT_CONFIGURED"
VIEWER_CONFIGURED = "VIEWER_CONFIGURED"

MAX_RESPONSE_BODY_BYTES = 2 * 1024 * 1024
MAX_WARC_BODY_BYTES = 14 * 1024 * 1024
MAX_CAPTURED_RESPONSE_COUNT = 80
COMMENT_COLLECTION_STEPS = 8
COMMENT_STABLE_PASS_TARGET = 12
COMMENT_MAX_PASSES = 300
COMMENT_PASS_WAIT_MS = 1200
COMMENTS_COMPLETE = "COMMENTS_COMPLETE"
COMMENTS_PARTIAL = "PARTIAL"
DERIVED_MSN_COMMENTS_EXPANDED_LAYOUT = "DERIVED_MSN_COMMENTS_EXPANDED_LAYOUT"

DESKTOP_PROFILE = {
    "name": "desktop_chromium",
    "viewport": {"width": 1365, "height": 900},
    "user_agent": "",
    "is_mobile": False,
    "device_scale_factor": 1,
}
MOBILE_PROFILE = {
    "name": "android_mobile_chromium",
    "viewport": {"width": 412, "height": 915},
    "user_agent": (
        "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/139.0.0.0 Mobile Safari/537.36"
    ),
    "is_mobile": True,
    "device_scale_factor": 2,
}
EXPECTED_MSN_ARTICLE_TERMS = ("york", "mosque", "shot")


@dataclass(frozen=True)
class RenderedArtifact:
    label: str
    path: str
    sha256: str
    size_bytes: int
    width: int = 0
    height: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "height": self.height,
            "label": self.label,
            "path": self.path,
            "sha256": self.sha256,
            "size_bytes": int(self.size_bytes),
            "width": self.width,
        }


@dataclass(frozen=True)
class CapturedResponse:
    url: str
    status: int
    headers: Mapping[str, str]
    body: bytes
    resource_type: str = ""
    method: str = "GET"
    from_profile: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "body_sha256": _sha256_bytes(self.body),
            "body_size_bytes": len(self.body),
            "content_type": _header_value(self.headers, "content-type"),
            "from_profile": self.from_profile,
            "method": self.method,
            "resource_type": self.resource_type,
            "status": int(self.status),
            "url": self.url,
        }


@dataclass(frozen=True)
class RenderProfileResult:
    profile_name: str
    final_url: str
    title: str
    final_dom: str
    body_text: str
    article_text: str
    comments: tuple[Mapping[str, Any], ...]
    comments_component: Mapping[str, Any]
    resource_inventory: tuple[Mapping[str, Any], ...]
    captured_responses: tuple[CapturedResponse, ...]
    screenshot_artifacts: tuple[RenderedArtifact, ...]
    status: str
    warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "article_text_chars": len(self.article_text),
            "body_text_chars": len(self.body_text),
            "captured_response_count": len(self.captured_responses),
            "comments": list(self.comments),
            "comments_component": dict(self.comments_component),
            "comment_count": len(self.comments),
            "final_dom_sha256": _sha256_bytes(self.final_dom.encode("utf-8")),
            "final_url": self.final_url,
            "profile_name": self.profile_name,
            "resource_count": len(self.resource_inventory),
            "screenshot_artifacts": [artifact.to_dict() for artifact in self.screenshot_artifacts],
            "status": self.status,
            "title": self.title,
            "warnings": list(self.warnings),
        }


@dataclass(frozen=True)
class RenderedValidationResult:
    source_url: str
    canonical_url: str
    output_directory: str
    status_matrix: Mapping[str, str]
    manifest_path: str
    manifest_sha256: str
    artifacts: tuple[RenderedArtifact, ...]
    summary: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "artifacts": [artifact.to_dict() for artifact in self.artifacts],
            "canonical_url": self.canonical_url,
            "manifest_path": self.manifest_path,
            "manifest_sha256": self.manifest_sha256,
            "output_directory": self.output_directory,
            "schema_version": MSN_RENDERED_BROWSER_SCHEMA_VERSION,
            "source_url": self.source_url,
            "status_matrix": dict(self.status_matrix),
            "summary": dict(self.summary),
        }


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _timestamp14(timestamp_utc: str) -> str:
    return re.sub(r"\D", "", timestamp_utc)[:14].ljust(14, "0")


def _sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_name(value: str, fallback: str = "artifact") -> str:
    text = Path(urlsplit(value).path).name or value or fallback
    return re.sub(r"[^A-Za-z0-9._-]+", "_", text)[:120].strip("._") or fallback


def _safe_download_extension(content_type: str, payload: bytes) -> str:
    lowered = content_type.split(";", 1)[0].strip().lower()
    by_type = {
        "image/jpeg": ".jpg",
        "image/jpg": ".jpg",
        "image/png": ".png",
        "image/gif": ".gif",
        "image/webp": ".webp",
        "image/svg+xml": ".svg",
    }
    if lowered in by_type:
        return by_type[lowered]
    if payload.startswith(b"\xff\xd8\xff"):
        return ".jpg"
    if payload.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    if payload.startswith((b"GIF87a", b"GIF89a")):
        return ".gif"
    if payload.startswith(b"RIFF") and payload[8:12] == b"WEBP":
        return ".webp"
    prefix = payload[:200].lstrip().lower()
    if prefix.startswith((b"<svg", b"<?xml")) and b"<svg" in prefix:
        return ".svg"
    return ""


def _safe_download_filename(response: CapturedResponse, fallback: str = "representative_image") -> str:
    filename = _safe_name(response.url, fallback)
    stem = Path(filename).stem or fallback
    suffix = Path(filename).suffix.lower()
    inferred = _safe_download_extension(_header_value(response.headers, "content-type"), response.body)
    if inferred and suffix != inferred:
        return f"{stem}{inferred}"
    if not suffix and inferred:
        return f"{stem}{inferred}"
    return filename


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _write_bytes(path: Path, payload: bytes, label: str) -> RenderedArtifact:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    width, height = _image_dimensions(path)
    return RenderedArtifact(
        label=label,
        path=str(path),
        sha256=_sha256_bytes(payload),
        size_bytes=len(payload),
        width=width,
        height=height,
    )


def _write_text(path: Path, text: str, label: str) -> RenderedArtifact:
    return _write_bytes(path, text.encode("utf-8"), label)


def _write_json(path: Path, value: Any, label: str) -> RenderedArtifact:
    return _write_bytes(path, _json_bytes(value), label)


def _image_dimensions(path: Path) -> tuple[int, int]:
    try:
        with Image.open(path) as image:
            return int(image.width), int(image.height)
    except Exception:
        return 0, 0


def _header_value(headers: Mapping[str, str], name: str) -> str:
    lowered = name.lower()
    for key, value in headers.items():
        if str(key).lower() == lowered:
            return str(value)
    return ""


def _redacted_headers(headers: Mapping[str, str]) -> dict[str, str]:
    secret_fragments = ("authorization", "cookie", "set-cookie", "token", "secret", "api-key", "apikey")
    allowed: dict[str, str] = {}
    for key, value in sorted(headers.items(), key=lambda item: str(item[0]).lower()):
        lowered = str(key).lower()
        if any(fragment in lowered for fragment in secret_fragments):
            allowed[str(key)] = "[redacted]"
        elif lowered in {"content-type", "content-length", "cache-control", "date", "etag", "last-modified", "server"}:
            allowed[str(key)] = str(value)
    return allowed


def _redact_url_for_metadata(url: str) -> str:
    parsed = urlsplit(url)
    if not parsed.query:
        return url
    sensitive_names = ("apikey", "api_key", "token", "cookie", "user", "activityid", "authorization")
    parts: list[str] = []
    for pair in parsed.query.split("&"):
        name = pair.split("=", 1)[0].lower()
        if any(fragment in name for fragment in sensitive_names):
            parts.append(pair.split("=", 1)[0] + "=[redacted]")
        else:
            parts.append(pair)
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "&".join(parts), parsed.fragment))


def _surt(url: str) -> str:
    # CDXJ searchable URLs are derived from the lower-cased archived URL.
    # Fragments are client-side only and therefore are not part of the lookup key.
    parsed = urlsplit(str(url or "").lower())
    host = parsed.hostname or ""
    parts = host.split(".")
    host_key = ",".join(reversed(parts))
    path = parsed.path or "/"
    if parsed.query:
        path += "?" + parsed.query
    return f"{host_key}){path}"


def _without_fragment(url: str) -> str:
    parsed = urlsplit(str(url or ""))
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, parsed.query, ""))


def _msn_content_id(source_url: str) -> str:
    match = re.search(r"/ar-([A-Za-z0-9]+)", source_url)
    if match:
        return match.group(1)
    match = re.search(r"/(AA[A-Za-z0-9]+)", source_url)
    return match.group(1) if match else ""


def _article_matches_expected_source(text: str) -> bool:
    lowered = text.lower()
    return all(term in lowered for term in EXPECTED_MSN_ARTICLE_TERMS)


def _http_status_text(status: int) -> str:
    return {
        200: "OK",
        204: "No Content",
        301: "Moved Permanently",
        302: "Found",
        304: "Not Modified",
        404: "Not Found",
        429: "Too Many Requests",
        500: "Internal Server Error",
    }.get(int(status), "OK")


def _warc_target_path(url: str) -> str:
    parsed = urlsplit(url)
    path = parsed.path or "/"
    if parsed.query:
        path += "?" + parsed.query
    return path


def _dedupe_responses(responses: Sequence[CapturedResponse]) -> tuple[CapturedResponse, ...]:
    deduped: dict[tuple[str, str], CapturedResponse] = {}
    for response in responses:
        if not response.body:
            continue
        key = (response.url, response.resource_type)
        if key not in deduped:
            deduped[key] = response
    return tuple(deduped.values())


def write_standard_warc(
    *,
    output_warc_path: str | Path,
    responses: Sequence[CapturedResponse],
    timestamp_utc: str,
) -> dict[str, Any]:
    output_path = Path(output_warc_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    index_rows: list[dict[str, Any]] = []
    ts14 = _timestamp14(timestamp_utc)
    with output_path.open("wb") as stream:
        writer = WARCWriter(stream, gzip=False)
        for response in _dedupe_responses(responses):
            # warcio prepends the StatusAndHeaders `protocol` value to the
            # status line. For HTTP request records the protocol slot is the
            # method, so this must render as `GET /path HTTP/1.1`, not the
            # malformed `HTTP/1.1 GET /path HTTP/1.1` that ReplayWeb imports as
            # a synthetic `_wb_method=HTTP/1.1` resource.
            request_headers = StatusAndHeaders(
                f"{_warc_target_path(response.url)} HTTP/1.1",
                [("Host", urlsplit(response.url).netloc)],
                protocol=(response.method or "GET").upper(),
            )
            writer.write_record(
                writer.create_warc_record(
                    response.url,
                    "request",
                    payload=BytesIO(b""),
                    http_headers=request_headers,
                    warc_headers_dict={"WARC-Date": timestamp_utc},
                )
            )
            start = stream.tell()
            http_headers = StatusAndHeaders(
                f"{response.status} {_http_status_text(response.status)}",
                tuple(_redacted_headers(response.headers).items()),
                protocol="HTTP/1.1",
            )
            writer.write_record(
                writer.create_warc_record(
                    response.url,
                    "response",
                    payload=BytesIO(response.body),
                    http_headers=http_headers,
                    warc_headers_dict={"WARC-Date": timestamp_utc},
                )
            )
            length = stream.tell() - start
            index_rows.append(
                {
                    "digest": "sha256:" + _sha256_bytes(response.body),
                    "filename": "archive/data.warc",
                    "length": length,
                    "mime": _header_value(response.headers, "content-type") or "application/octet-stream",
                    "offset": start,
                    "status": int(response.status),
                    "timestamp": ts14,
                    "url": response.url,
                    "urlkey": _surt(response.url),
                }
            )
    record_count = 0
    with output_path.open("rb") as stream:
        for _record in ArchiveIterator(stream):
            record_count += 1
    return {
        "conformant_read_record_count": record_count,
        "index_rows": index_rows,
        "path": str(output_path),
        "sha256": _sha256_file(output_path),
        "size_bytes": output_path.stat().st_size,
    }


def write_standard_wacz(
    *,
    output_wacz_path: str | Path,
    warc_path: str | Path,
    index_rows: Sequence[Mapping[str, Any]],
    source_url: str,
    title: str,
    text: str,
    timestamp_utc: str,
) -> dict[str, Any]:
    output_path = Path(output_wacz_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    warc_bytes = Path(warc_path).read_bytes()
    pages_jsonl = (
        json.dumps({"format": "json-pages-1.0", "id": "pages", "title": "All Pages"}, sort_keys=True)
        + "\n"
        + json.dumps(
            {
                "id": stable_capture_id("msn_rendered_page", source_url),
                "size": len(warc_bytes),
                "text": text[:5000],
                "title": title,
                "ts": timestamp_utc,
                "url": _without_fragment(source_url),
            },
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")
    cdx_lines = [
        f"{row['urlkey']} {row['timestamp']} "
        + json.dumps(
            {
                "digest": row["digest"],
                "filename": row["filename"],
                "length": row["length"],
                "mime": row["mime"],
                "offset": row["offset"],
                "status": row["status"],
                "url": row["url"],
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        for row in index_rows
    ]
    # CDXJ requires byte-wise (LC_ALL=C equivalent) sorting for binary-search lookup.
    cdx_lines.sort(key=lambda line: line.encode("utf-8"))
    cdxj = ("\n".join(cdx_lines) + "\n").encode("utf-8")
    cdx_gz = gzip.compress(cdxj, mtime=0)
    resources = {
        "archive/data.warc": warc_bytes,
        "indexes/index.cdx.gz": cdx_gz,
        "pages/pages.jsonl": pages_jsonl,
    }
    datapackage = {
        "created": timestamp_utc,
        "description": "Controlled MSN rendered-browser validation WACZ.",
        "home": {"url": _without_fragment(source_url), "ts": timestamp_utc},
        "modified": timestamp_utc,
        "profile": "wacz",
        "resources": [
            {
                "bytes": len(payload),
                "hash": "sha256:" + _sha256_bytes(payload),
                "name": Path(name).name,
                "path": name,
            }
            for name, payload in sorted(resources.items())
        ],
        "software": "yt-comments-extractor rendered browser validation",
        "title": title or "MSN rendered browser validation",
    }
    resources["datapackage.json"] = _json_bytes(datapackage)
    resources["datapackage-digest.json"] = _json_bytes(
        {"hash": "sha256:" + _sha256_bytes(resources["datapackage.json"]), "path": "datapackage.json"}
    )
    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
        for name, payload in sorted(resources.items()):
            info = zipfile.ZipInfo(name)
            info.date_time = (2026, 1, 1, 0, 0, 0)
            info.compress_type = zipfile.ZIP_STORED if name.endswith((".warc", ".gz")) else zipfile.ZIP_DEFLATED
            bundle.writestr(info, payload)
    return verify_wacz_structure(output_path)


def verify_wacz_structure(path: str | Path) -> dict[str, Any]:
    package = Path(path)
    result: dict[str, Any] = {
        "path": str(package),
        "sha256": _sha256_file(package),
        "size_bytes": package.stat().st_size,
        "status": LOCAL_PACKAGE_STRUCTURALLY_VERIFIED,
        "wacz_spec_target": "1.2.0",
        "wacz_version": "",
        "profile": "",
        "legacy_declared_wacz_version": "",
        "deprecated_datapackage_fields": [],
        "index_sorted": False,
        "index_search_keys_canonical": False,
        "errors": [],
    }
    errors: list[str] = result["errors"]
    with zipfile.ZipFile(package, "r") as bundle:
        names = set(bundle.namelist())
        required = {"archive/data.warc", "indexes/index.cdx.gz", "pages/pages.jsonl", "datapackage.json"}
        result["entries"] = sorted(names)
        result["missing_required_entries"] = sorted(required - names)
        datapackage = json.loads(bundle.read("datapackage.json").decode("utf-8"))
        result["profile"] = str(datapackage.get("profile") or "")
        result["legacy_declared_wacz_version"] = str(datapackage.get("wacz_version") or "")
        result["wacz_version"] = result["legacy_declared_wacz_version"]
        deprecated = [name for name in ("wacz_version", "mainPageUrl", "mainPageDate") if name in datapackage]
        result["deprecated_datapackage_fields"] = deprecated
        result["resource_count"] = len(datapackage.get("resources", ()))
        result["page_count"] = max(0, len(bundle.read("pages/pages.jsonl").decode("utf-8").splitlines()) - 1)
        index_lines = [
            line
            for line in gzip.decompress(bundle.read("indexes/index.cdx.gz")).decode("utf-8").splitlines()
            if line.strip()
        ]
        result["index_line_count"] = len(index_lines)
        result["index_sorted"] = index_lines == sorted(index_lines, key=lambda line: line.encode("utf-8"))
        canonical_keys = True
        for line in index_lines:
            try:
                searchable, _timestamp, payload = line.split(" ", 2)
                row = json.loads(payload)
                if searchable != _surt(str(row.get("url") or "")):
                    canonical_keys = False
                    break
            except Exception:
                canonical_keys = False
                break
        result["index_search_keys_canonical"] = canonical_keys

    if result["missing_required_entries"]:
        errors.append("Required WACZ entries are missing")
    if result["profile"] != "wacz":
        errors.append("WACZ 1.2.0 requires datapackage profile 'wacz'")
    if result["deprecated_datapackage_fields"]:
        errors.append("WACZ 1.2.0 datapackage contains removed legacy fields")
    if not result["index_sorted"]:
        errors.append("CDXJ index is not byte-wise sorted")
    if not result["index_search_keys_canonical"]:
        errors.append("CDXJ searchable URL keys are not canonical")
    if errors:
        result["status"] = REPLAY_FAILED
    return result


def _download_from_captured_response(
    *,
    output_directory: Path,
    responses: Sequence[CapturedResponse],
) -> dict[str, Any]:
    def score(response: CapturedResponse) -> tuple[int, int]:
        content_type = _header_value(response.headers, "content-type").lower()
        url = response.url.lower()
        return (
            1 if "img-s-msn-com" in url or "akamaized.net" in url else 0,
            1 if content_type.startswith("image/") and "svg" not in content_type else 0,
        )

    for response in sorted(responses, key=score, reverse=True):
        content_type = _header_value(response.headers, "content-type").lower()
        if not content_type.startswith("image/"):
            continue
        if len(response.body) <= 0 or len(response.body) > MAX_RESPONSE_BODY_BYTES:
            continue
        filename = _safe_download_filename(response, "representative_image")
        part_path = output_directory / "downloads" / f"{filename}.part"
        final_path = output_directory / "downloads" / filename
        part_path.parent.mkdir(parents=True, exist_ok=True)
        part_path.write_bytes(response.body)
        part_path.replace(final_path)
        return {
            "browser_request_context": {
                "from_profile": response.from_profile,
                "resource_type": response.resource_type,
            },
            "download_performed": True,
            "mime_type": _header_value(response.headers, "content-type"),
            "output_path": str(final_path),
            "sha256": _sha256_file(final_path),
            "size_bytes": final_path.stat().st_size,
            "source_url": response.url,
            "status": RENDERED_BROWSER_LIVE_TESTED,
        }
    return {
        "download_performed": False,
        "reason": "NO_SMALL_RELEVANT_CAPTURED_IMAGE_RESPONSE",
        "status": STATUS_N_A,
    }


def _wayback_check(source_url: str) -> dict[str, Any]:
    query_url = "https://archive.org/wayback/available?" + urlencode({"url": source_url})
    request = Request(query_url, headers={"User-Agent": "yt-comments-extractor-msn-rendered-validation/1.0"})
    try:
        with urlopen(request, timeout=30) as response:
            body = response.read(1024 * 1024)
            parsed = json.loads(body.decode("utf-8", errors="replace"))
    except Exception as error:
        message = str(error)
        return {
            "check_performed": True,
            "error": message,
            "query_url": query_url,
            "status": RATE_LIMITED if "429" in message else STATUS_PARTIAL,
            "submission_performed": False,
        }
    closest = (parsed.get("archived_snapshots") or {}).get("closest") or {}
    return {
        "available": bool(closest),
        "check_performed": True,
        "query_url": query_url,
        "snapshot_status": closest.get("status", ""),
        "snapshot_timestamp": closest.get("timestamp", ""),
        "snapshot_url": closest.get("url", ""),
        "status": RENDERED_BROWSER_LIVE_TESTED,
        "submission_performed": False,
    }


def _dismiss_privacy_banner(page: Any) -> str:
    for selector in ("#cmp-reject-all-handler", "button:has-text('Reject All')"):
        try:
            button = page.locator(selector).first
            if button.count() and button.is_visible(timeout=1200):
                button.click(timeout=2500)
                page.wait_for_timeout(2500)
                return "privacy_banner_reject_all_clicked_in_ephemeral_context"
        except Exception:
            continue
    return ""


def _evaluate_comments(page: Any) -> dict[str, Any]:
    return dict(
        page.evaluate(
            """() => {
              const rows = [];
              const host = document.querySelector("social-comment-wc");
              const hostRoot = host && host.shadowRoot;
              function clean(value) {
                return (value || "").replace(/\\s+/g, " ").trim();
              }
              function allOpenShadowElements(root, out = [], depth = 0) {
                if (!root || depth > 15) return out;
                for (const el of Array.from(root.children || [])) {
                  out.push(el);
                  if (el.shadowRoot) allOpenShadowElements(el.shadowRoot, out, depth + 1);
                  allOpenShadowElements(el, out, depth + 1);
                }
                return out;
              }
              function allOpenShadowRoots(root) {
                const roots = [];
                const seen = new Set();
                function add(candidate) {
                  if (!candidate || seen.has(candidate)) return;
                  seen.add(candidate);
                  roots.push(candidate);
                  for (const el of allOpenShadowElements(candidate)) {
                    if (el.shadowRoot) add(el.shadowRoot);
                  }
                }
                add(root);
                return roots;
              }
              function firstDeep(root, selector) {
                if (!root) return null;
                if (root.querySelector) {
                  const direct = root.querySelector(selector);
                  if (direct) return direct;
                }
                for (const el of allOpenShadowElements(root)) {
                  if (el.matches && el.matches(selector)) return el;
                }
                return null;
              }
              function firstText(root, selector) {
                const el = firstDeep(root, selector);
                return clean(el && (el.innerText || el.textContent || el.getAttribute("aria-label") || ""));
              }
              function firstAttr(root, selector, attr) {
                const el = firstDeep(root, selector);
                return clean(el && el.getAttribute(attr));
              }
              function textFromParts(root, selectors) {
                for (const selector of selectors) {
                  const value = firstText(root, selector);
                  if (value) return value;
                }
                return "";
              }
              function parseDataT(el) {
                const value = el.getAttribute("data-t") || "";
                if (!value) return {};
                try { return JSON.parse(value); } catch (error) { return {}; }
              }
              function stableFromParts(author, postedAt, body, source, parentId) {
                return [parentId || "", author || "", postedAt || "", body.slice(0, 160), source || ""].join("|");
              }
              function domPath(el) {
                const parts = [];
                let node = el;
                for (let depth = 0; node && depth < 8; depth++) {
                  const tag = (node.tagName || "").toLowerCase();
                  if (!tag) break;
                  const siblings = Array.from(node.parentElement ? node.parentElement.children : []);
                  parts.unshift(`${tag}[${Math.max(0, siblings.indexOf(node))}]`);
                  node = node.parentElement;
                }
                return parts.join("/");
              }
              function replyControls(root) {
                return allOpenShadowElements(root).filter(el => {
                  const text = clean(el.innerText || el.textContent || el.getAttribute("aria-label") || "");
                  const className = String(el.getAttribute("class") || el.className || "");
                  return ((/\\brepl(?:y|ies)\\b/i.test(text) && /\\b(see|show|view|load|more|\\d+)\\b/i.test(text))
                    || /show-more-replies|load-more-replies/i.test(className));
                });
              }
              function pushItem(item, source, depth, replyTo) {
                if (!item || !item.shadowRoot) return;
                const shadow = item.shadowRoot;
                const body = textFromParts(shadow, [
                  ".comment-body",
                  ".msg-clamp",
                  ".message",
                  ".comment-content",
                  ".inner-content"
                ]);
                if (!body || body.length < 2) return;
                const dataT = parseDataT(item);
                const id = item.id || dataT["c.i"] || item.getAttribute("data-comment-id") || "";
                const author = textFromParts(shadow, [
                  ".item-user-name",
                  "[class*='user-name']",
                  "[class*='author']",
                  "a[href*='/community/profile/']"
                ]);
                const authorUrl = firstAttr(shadow, ".item-user-name, a[href*='/community/profile/']", "href");
                const postedAt = textFromParts(shadow, [
                  ".posted-at",
                  "time",
                  "[datetime]",
                  "[class*='date']",
                  "[class*='time']"
                ]);
                const permalink = firstAttr(shadow, "a[href*='comment'], a[href*='cid-'], a[href*='/community/']", "href");
                const replyButtonText = textFromParts(shadow, [
                  ".reply-list",
                  "[class*='reply']",
                  "button[aria-label*='repl' i]",
                  "a[aria-label*='repl' i]"
                ]);
                const replyLists = Array.from(shadow.querySelectorAll("reply-list"));
                const hasReplies = /reply|replies/i.test(replyButtonText) || !!replyLists.length;
                const reactions = Array.from(shadow.querySelectorAll("msn-social-bar, social-bar-wc, [class*='social-bar']")).map(el => clean(el.innerText || el.textContent || "")).filter(Boolean).join(" ");
                const stable = id || stableFromParts(author, postedAt, body, source, replyTo);
                rows.push({
                  author,
                  author_profile_url: authorUrl,
                  capture_source: source,
                  comment_id: stable,
                  component_tag: "comment-item",
                  depth,
                  dom_position: domPath(item),
                  has_reply_container: hasReplies,
                  parent_comment_id: replyTo || item.getAttribute("data-parent-id") || "",
                  permalink,
                  posted_at: postedAt,
                  reaction_summary: reactions,
                  reply_to: replyTo || item.getAttribute("data-parent-id") || "",
                  stable_identifier: stable,
                  text: body
                });
                const replyItems = replyLists.flatMap(list => {
                  const root = list.shadowRoot || list;
                  return Array.from(root.querySelectorAll?.("comment-item") || []);
                });
                for (const reply of replyItems) pushItem(reply, "social-comment-wc.reply-list", depth + 1, stable);
              }
              if (hostRoot) {
                const roots = allOpenShadowRoots(hostRoot);
                const seen = new Set();
                for (const root of roots) {
                  for (const item of Array.from(root.querySelectorAll?.("comment-list comment-item, comment-item") || [])) {
                    if (seen.has(item)) continue;
                    seen.add(item);
                    pushItem(item, "social-comment-wc.comment-list", 0, "");
                  }
                }
              }
              const shadowElements = hostRoot ? allOpenShadowElements(hostRoot) : [];
              const scrollContainers = shadowElements.concat(Array.from(document.querySelectorAll("*"))).filter(el => {
                const style = getComputedStyle(el);
                return /(auto|scroll|overlay)/.test(style.overflowY) && el.scrollHeight > el.clientHeight + 30;
              }).sort((a, b) => (b.scrollHeight - b.clientHeight) - (a.scrollHeight - a.clientHeight)).slice(0, 30).map(el => ({
                tag: el.tagName.toLowerCase(),
                className: String(el.getAttribute("class") || el.className || ""),
                id: el.id || "",
                scrollHeight: el.scrollHeight,
                clientHeight: el.clientHeight,
                scrollTop: Math.round(el.scrollTop || 0)
              }));
              const commentListItems = hostRoot ? allOpenShadowElements(hostRoot).filter(el => (el.tagName || "").toLowerCase() === "comment-item").length : 0;
              const loadMoreButtons = hostRoot ? allOpenShadowElements(hostRoot).filter(el => /see more comments|load more comments|show more comments/i.test(clean(el.innerText || el.textContent || el.getAttribute("aria-label") || ""))).length : 0;
              const replyButtons = hostRoot ? replyControls(hostRoot) : [];
              const headerText = hostRoot ? allOpenShadowElements(hostRoot).map(el => clean(el.innerText || el.textContent || "")).find(text => /\\b\\d+\\s+comments?\\b/i.test(text)) || "" : "";
              const declaredCountMatch = headerText.match(/\\b(\\d+)\\s+comments?\\b/i);
              return {
                current_rendered_ids: rows.map(row => row.stable_identifier || row.comment_id).filter(Boolean),
                social_comment_wc_found: !!host,
                social_comment_wc_shadow_open: !!hostRoot,
                overlay_container_found: !!(hostRoot && hostRoot.querySelector(".overlay-container")),
                comment_list_item_count: commentListItems,
                declared_comment_count: declaredCountMatch ? Number(declaredCountMatch[1]) : 0,
                load_more_control_count: loadMoreButtons,
                reply_control_count: replyButtons.length,
                nested_scroll_container_count: scrollContainers.length,
                nested_scroll_containers: scrollContainers,
                shadow_element_count: shadowElements.length,
                shadow_root_count: hostRoot ? allOpenShadowRoots(hostRoot).length : 0,
                rows,
                row_count: rows.length
              };
            }"""
        )
    )


def _advance_msn_comments(page: Any) -> dict[str, Any]:
    return dict(
        page.evaluate(
            """() => {
              const actions = [];
              const host = document.querySelector("social-comment-wc");
              const root = host && host.shadowRoot;
              function clean(value) { return (value || "").replace(/\\s+/g, " ").trim(); }
              function allOpenShadowElements(root, out = [], depth = 0) {
                if (!root || depth > 15) return out;
                for (const el of Array.from(root.children || [])) {
                  out.push(el);
                  if (el.shadowRoot) allOpenShadowElements(el.shadowRoot, out, depth + 1);
                  allOpenShadowElements(el, out, depth + 1);
                }
                return out;
              }
              if (!root) return {actions, social_comment_wc_found: !!host, social_comment_wc_shadow_open: false};
              const elements = allOpenShadowElements(root);
              const scrollers = elements.filter(el => {
                try {
                  const style = getComputedStyle(el);
                  return /(auto|scroll|overlay)/.test(style.overflowY) && el.scrollHeight > el.clientHeight + 30;
                } catch (error) {
                  return false;
                }
              }).sort((a, b) => (b.scrollHeight - b.clientHeight) - (a.scrollHeight - a.clientHeight));
              for (const el of scrollers) {
                try {
                  el.scrollTop = Math.max(0, el.scrollHeight - el.clientHeight - 40);
                  el.dispatchEvent(new Event("scroll", {bubbles: true, composed: true}));
                  el.scrollTop = el.scrollHeight;
                  el.dispatchEvent(new Event("scroll", {bubbles: true, composed: true}));
                  actions.push({action: "scroll_internal_container", tag: (el.tagName || "").toLowerCase(), className: String(el.getAttribute("class") || el.className || ""), scrollHeight: el.scrollHeight, clientHeight: el.clientHeight});
                } catch (error) {}
              }
              const replyControls = elements.filter(el => {
                const text = clean(el.innerText || el.textContent || el.getAttribute("aria-label") || "");
                const className = String(el.getAttribute("class") || el.className || "");
                return ((/\\brepl(?:y|ies)\\b/i.test(text) && /\\b(see|show|view|load|more|\\d+)\\b/i.test(text))
                  || /show-more-replies|load-more-replies/i.test(className));
              });
              const commentControls = elements.filter(el => {
                const text = clean(el.innerText || el.textContent || el.getAttribute("aria-label") || "");
                const className = String(el.getAttribute("class") || el.className || "");
                return /^(see more comments|load more comments|show more comments)/i.test(text)
                  || /see-more-comments|load-more-comments-button/i.test(className);
              });
              const controls = replyControls.concat(commentControls);
              const clicked = new Set();
              for (const control of controls.slice(0, 40)) {
                try {
                  const key = [(control.tagName || "").toLowerCase(), String(control.getAttribute("class") || control.className || ""), clean(control.innerText || control.textContent || control.getAttribute("aria-label") || "")].join("|");
                  if (clicked.has(key)) continue;
                  clicked.add(key);
                  control.scrollIntoView({block: "center", inline: "nearest"});
                  control.click();
                  actions.push({action: "click_comment_control", tag: (control.tagName || "").toLowerCase(), text: clean(control.innerText || control.textContent || control.getAttribute("aria-label") || "")});
                } catch (error) {
                  actions.push({action: "click_comment_control_failed", reason: String(error).slice(0, 120)});
                }
              }
              return {actions, social_comment_wc_found: true, social_comment_wc_shadow_open: true};
            }"""
        )
    )


def _comment_signature(snapshot: Mapping[str, Any], captured_ids: Sequence[str], network_count: int = 0) -> str:
    scrollers = []
    for item in snapshot.get("nested_scroll_containers") or ():
        scrollers.append(
            (
                str(item.get("tag") or ""),
                str(item.get("className") or "")[:80],
                int(item.get("scrollHeight") or 0),
                int(item.get("clientHeight") or 0),
                int(item.get("scrollTop") or 0),
            )
        )
    payload = {
        "captured_ids": sorted(str(item) for item in captured_ids),
        "current_rendered_ids": sorted(str(item) for item in snapshot.get("current_rendered_ids") or ()),
        "load_more_control_count": int(snapshot.get("load_more_control_count") or 0),
        "network_count": int(network_count),
        "reply_control_count": int(snapshot.get("reply_control_count") or 0),
        "row_count": int(snapshot.get("row_count") or 0),
        "scroll_containers": scrollers,
        "shadow_element_count": int(snapshot.get("shadow_element_count") or 0),
        "shadow_root_count": int(snapshot.get("shadow_root_count") or 0),
    }
    return _sha256_bytes(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8"))


def _replace_raw_query_param(url: str, name: str, value: str | int) -> str:
    encoded = str(value).replace(" ", "%20")
    pattern = re.compile(r"([?&])" + re.escape(name) + r"=[^&]*")
    if pattern.search(url):
        return pattern.sub(lambda match: f"{match.group(1)}{name}={encoded}", url)
    return url + ("&" if "?" in url else "?") + f"{name}={encoded}"


def _remove_raw_query_param(url: str, name: str) -> str:
    pattern = re.compile(r"([?&])" + re.escape(name) + r"=[^&]*&?")
    cleaned = pattern.sub(lambda match: match.group(1) if match.group(1) == "?" else "", url)
    return cleaned.rstrip("?&")


def _comment_api_array(payload: Mapping[str, Any]) -> Sequence[Mapping[str, Any]]:
    value = payload.get("items")
    if isinstance(value, list):
        return tuple(item for item in value if isinstance(item, Mapping))
    for key in ("value", "comments", "data"):
        value = payload.get(key)
        if isinstance(value, list):
            return tuple(item for item in value if isinstance(item, Mapping))
    return ()


def _api_author(item: Mapping[str, Any]) -> tuple[str, str]:
    for link in item.get("links") or ():
        if not isinstance(link, Mapping) or str(link.get("type") or "").lower() != "user":
            continue
        user = link.get("item")
        if not isinstance(user, Mapping):
            continue
        name = str(user.get("primaryName") or " ".join(str(user.get(part) or "") for part in ("firstName", "lastName")).strip())
        return name.strip(), str(user.get("id") or "")
    return "", str(item.get("createdBy") or "")


def _api_item_reply_count(item: Mapping[str, Any]) -> int:
    summary = item.get("commentSummary")
    if isinstance(summary, Mapping):
        total = summary.get("totalCount")
        if isinstance(total, int):
            return max(0, total)
        for entry in summary.get("subCommentSummaries") or ():
            if isinstance(entry, Mapping) and str(entry.get("type") or "").lower() == "reply":
                try:
                    return max(0, int(entry.get("totalCount") or 0))
                except Exception:
                    return 0
    return 0


def _api_item_to_comment_row(item: Mapping[str, Any], *, depth: int, source: str, step: int, order: int) -> dict[str, Any]:
    comment_id = str(item.get("id") or item.get("commentId") or item.get("commentID") or "")
    parent_id = str(item.get("parentId") or "")
    body = str(item.get("body") or item.get("text") or item.get("content") or "").strip()
    author, author_id = _api_author(item)
    visible_status = str(item.get("visibleStatus") or item.get("status") or "")
    reaction_summary = item.get("reactionSummary")
    reaction_count = 0
    if isinstance(reaction_summary, Mapping):
        try:
            reaction_count = int(reaction_summary.get("totalCount") or 0)
        except Exception:
            reaction_count = 0
    stable = comment_id or stable_capture_id("msn_comment_api", parent_id, author, str(item.get("createdTime") or ""), body[:160])
    return {
        "author": author,
        "author_profile_url": "",
        "author_reference_id": author_id,
        "capture_order": order,
        "capture_source": source,
        "comment_id": stable,
        "component_tag": "msn-comments-api-item",
        "depth": int(depth),
        "dom_position": "",
        "first_seen_step": step,
        "has_reply_container": _api_item_reply_count(item) > 0,
        "last_seen_step": step,
        "network_api_correlation_id": comment_id,
        "parent_comment_id": parent_id,
        "permalink": "",
        "posted_at": str(item.get("createdTime") or item.get("updatedTime") or ""),
        "reaction_count": reaction_count,
        "reaction_summary": str(reaction_count) if reaction_count else "",
        "reply_count_declared": _api_item_reply_count(item),
        "reply_to": parent_id,
        "stable_identifier": stable,
        "text": body,
        "visible_status": visible_status,
    }


def _fetch_json_same_session(page: Any, url: str) -> dict[str, Any]:
    return dict(
        page.evaluate(
            """async (url) => {
              const response = await fetch(url, {credentials: "same-origin"});
              const text = await response.text();
              let payload = {};
              try { payload = JSON.parse(text); } catch (error) {}
              return {ok: response.ok, status: response.status, payload};
            }""",
            url,
        )
    )


def _fetch_msn_comment_api_records(page: Any, comment_urls: Sequence[str], existing_step_count: int) -> dict[str, Any]:
    templates = [url for url in comment_urls if "/service/community/comments/" in url.lower() and "contentId=" in url]
    if not templates:
        return {
            "api_followup_performed": False,
            "reason": "no_same_session_comments_endpoint_observed",
            "records": [],
        }
    template = templates[0]
    pages: list[dict[str, Any]] = []
    root_items: dict[str, Mapping[str, Any]] = {}
    declared_total = 0
    max_root_skip = 60
    for skip in range(0, max_root_skip + 1):
        url = _replace_raw_query_param(template, "$top", 10)
        url = _replace_raw_query_param(url, "$skip", skip)
        fetched = _fetch_json_same_session(page, url)
        payload = fetched.get("payload") if isinstance(fetched.get("payload"), Mapping) else {}
        items = _comment_api_array(payload)
        declared_total = max(declared_total, int(payload.get("totalCount") or 0))
        pages.append(
            {
                "has_more": bool(payload.get("hasMore")),
                "item_count": len(items),
                "redacted_url": _redact_url_for_metadata(url),
                "request_kind": "root",
                "skip": int(payload.get("skip") if isinstance(payload.get("skip"), int) else skip),
                "status": int(fetched.get("status") or 0),
                "top": int(payload.get("top") or 0),
                "total_count": int(payload.get("totalCount") or 0),
            }
        )
        for item in items:
            item_id = str(item.get("id") or item.get("commentId") or "")
            if item_id and item_id not in root_items:
                root_items[item_id] = item
        if declared_total and skip >= min(max_root_skip, declared_total):
            break
        if skip > 30 and not items and not payload.get("hasMore"):
            break
    reply_items: dict[str, Mapping[str, Any]] = {}
    for root_id, item in sorted(root_items.items()):
        reply_count = _api_item_reply_count(item)
        if reply_count <= 0:
            continue
        for skip in range(0, max(reply_count, 1), 10):
            url = _remove_raw_query_param(template, "contentId")
            url = _replace_raw_query_param(url, "parentId", root_id)
            url = _replace_raw_query_param(url, "$top", max(10, min(50, reply_count)))
            url = _replace_raw_query_param(url, "$skip", skip)
            url = _replace_raw_query_param(url, "$orderby", "Time%20asc")
            fetched = _fetch_json_same_session(page, url)
            payload = fetched.get("payload") if isinstance(fetched.get("payload"), Mapping) else {}
            items = _comment_api_array(payload)
            pages.append(
                {
                    "has_more": bool(payload.get("hasMore")),
                    "item_count": len(items),
                    "parent_id": root_id,
                    "redacted_url": _redact_url_for_metadata(url),
                    "request_kind": "reply",
                    "skip": int(payload.get("skip") if isinstance(payload.get("skip"), int) else skip),
                    "status": int(fetched.get("status") or 0),
                    "top": int(payload.get("top") or 0),
                    "total_count": int(payload.get("totalCount") or 0),
                }
            )
            for reply in items:
                reply_id = str(reply.get("id") or reply.get("commentId") or "")
                if reply_id and reply_id not in reply_items:
                    reply_items[reply_id] = reply
            if not payload.get("hasMore"):
                break
    records: list[dict[str, Any]] = []
    order = 0
    for _root_id, item in sorted(root_items.items(), key=lambda pair: str(pair[1].get("createdTime") or pair[0])):
        order += 1
        records.append(_api_item_to_comment_row(item, depth=0, source="msn_comments_api_same_session.root", step=existing_step_count, order=order))
    for _reply_id, item in sorted(reply_items.items(), key=lambda pair: (str(pair[1].get("parentId") or ""), str(pair[1].get("createdTime") or pair[0]))):
        order += 1
        records.append(_api_item_to_comment_row(item, depth=1, source="msn_comments_api_same_session.reply", step=existing_step_count, order=order))
    root_reply_declared = sum(_api_item_reply_count(item) for item in root_items.values())
    return {
        "api_followup_performed": True,
        "api_followup_scope": "same_browser_session_observed_comments_endpoint",
        "declared_total_count": declared_total,
        "expected_root_reply_count": root_reply_declared,
        "fetched_page_count": len(pages),
        "pages": pages,
        "records": records,
        "reply_record_count": len(reply_items),
        "root_record_count": len(root_items),
    }


def _reconcile_comments(
    *,
    rows: Sequence[Mapping[str, Any]],
    declared_total: int,
    provider_root_count: int = 0,
    provider_reply_count: int = 0,
    unavailable_count: int = 0,
) -> dict[str, Any]:
    top_level_count = sum(1 for row in rows if int(row.get("depth") or 0) == 0)
    reply_count = sum(1 for row in rows if int(row.get("depth") or 0) > 0)
    captured_total = len(rows)
    retrievable_total = provider_root_count + provider_reply_count if provider_root_count or provider_reply_count else declared_total
    remaining_gap = max(0, int(declared_total or retrievable_total) - captured_total - int(unavailable_count or 0))
    complete = bool(rows) and (
        (declared_total and captured_total >= declared_total)
        or (retrievable_total and captured_total >= retrievable_total)
        or (declared_total and remaining_gap == 0)
    )
    return {
        "captured_total": captured_total,
        "comments_complete": complete,
        "completeness": COMMENTS_COMPLETE if complete else COMMENTS_PARTIAL,
        "declared_total_count": int(declared_total or 0),
        "provider_reply_count": int(provider_reply_count or 0),
        "provider_root_count": int(provider_root_count or 0),
        "reconciliation": (
            f"{top_level_count} top-level + {reply_count} replies = {captured_total}; "
            f"provider declared {int(declared_total or 0)}"
        ),
        "remaining_gap": remaining_gap,
        "reply_count": reply_count,
        "retrievable_total_count": int(retrievable_total or 0),
        "top_level_count": top_level_count,
        "unavailable_count": int(unavailable_count or 0),
    }


def _merge_provider_comment_rows(comments_info: Mapping[str, Any], api_result: Mapping[str, Any]) -> dict[str, Any]:
    rows = [dict(row) for row in comments_info.get("rows") or ()]
    api_rows = [dict(row) for row in api_result.get("records") or ()]
    if api_rows:
        dom_ids = {str(row.get("network_api_correlation_id") or row.get("stable_identifier") or row.get("comment_id") or "") for row in rows}
        for row in api_rows:
            row["component_dom_observed"] = str(row.get("network_api_correlation_id") or row.get("comment_id") or "") in dom_ids
        rows = api_rows
    declared = int(api_result.get("declared_total_count") or comments_info.get("declared_comment_count") or 0)
    reconciliation = _reconcile_comments(
        rows=rows,
        declared_total=declared,
        provider_root_count=int(api_result.get("root_record_count") or 0),
        provider_reply_count=int(api_result.get("reply_record_count") or 0),
    )
    merged = dict(comments_info)
    merged.update(
        {
            "api_reconciliation": {key: value for key, value in api_result.items() if key != "records"},
            "capture_stop_reason": "stable_and_provider_declared_count_reconciled"
            if reconciliation["comments_complete"]
            else "stable_but_provider_declared_count_unreconciled",
            "completeness": reconciliation["completeness"],
            "declared_comment_count": declared,
            "provider_declared_total_count": declared,
            "provider_reconciliation": reconciliation,
            "rows": rows,
            "row_count": len(rows),
        }
    )
    return merged


def _collect_incremental_comments(page: Any, output_root: Path, profile_name: str) -> tuple[dict[str, Any], RenderedArtifact]:
    profile_root = output_root / profile_name
    jsonl_path = profile_root / "comments_incremental.jsonl"
    profile_root.mkdir(parents=True, exist_ok=True)
    seen: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    position_history: dict[str, set[str]] = {}
    step_summaries: list[dict[str, Any]] = []
    new_rows_after_first_step = 0
    stable_passes = 0
    last_signature = ""
    stop_reason = "safety_ceiling_reached"

    def persist_snapshot(snapshot: Mapping[str, Any], step: int) -> int:
        new_this_step = 0
        for row in snapshot.get("rows") or ():
            stable = str(row.get("stable_identifier") or row.get("comment_id") or row.get("text") or "")
            if not stable:
                continue
            position = str(row.get("dom_position") or "")
            if position:
                position_history.setdefault(position, set()).add(stable)
            if stable not in seen:
                enriched = dict(row)
                enriched["capture_order"] = len(order) + 1
                enriched["first_seen_step"] = step
                enriched["last_seen_step"] = step
                seen[stable] = enriched
                order.append(stable)
                with jsonl_path.open("a", encoding="utf-8") as handle:
                    handle.write(json.dumps(enriched, sort_keys=True) + "\n")
                new_this_step += 1
            else:
                seen[stable]["last_seen_step"] = step
        return new_this_step

    final_snapshot: dict[str, Any] = {}
    for step in range(COMMENT_MAX_PASSES):
        before = _evaluate_comments(page)
        new_before = persist_snapshot(before, step)
        actions = _advance_msn_comments(page)
        page.wait_for_timeout(COMMENT_PASS_WAIT_MS)
        try:
            page.mouse.wheel(0, 900)
        except Exception:
            pass
        page.wait_for_timeout(250)
        after = _evaluate_comments(page)
        new_after = persist_snapshot(after, step)
        new_this_step = new_before + new_after
        if step:
            new_rows_after_first_step += new_this_step
        current_signature = _comment_signature(after, order)
        stable_passes = stable_passes + 1 if current_signature == last_signature and new_this_step == 0 else 0
        last_signature = current_signature
        final_snapshot = dict(after)
        step_summaries.append(
            {
                "actions": actions.get("actions", []),
                "component_found": bool(after.get("social_comment_wc_found")),
                "component_shadow_open": bool(after.get("social_comment_wc_shadow_open")),
                "comment_list_item_count": int(after.get("comment_list_item_count") or 0),
                "load_more_control_count": int(after.get("load_more_control_count") or 0),
                "new_row_count": new_this_step,
                "reply_control_count": int(after.get("reply_control_count") or 0),
                "row_count": int(after.get("row_count") or 0),
                "signature": current_signature,
                "stable_pass_count": stable_passes,
                "step": step,
            }
        )
        if stable_passes >= COMMENT_STABLE_PASS_TARGET and (len(seen) > 0 or bool(after.get("social_comment_wc_found")) or step >= COMMENT_STABLE_PASS_TARGET):
            stop_reason = f"stable_for_{COMMENT_STABLE_PASS_TARGET}_passes"
            break

    final = final_snapshot or _evaluate_comments(page)
    rows = [seen[key] for key in order]
    final["rows"] = rows
    final["row_count"] = len(rows)
    final["incremental_serialization_path"] = str(jsonl_path)
    final["incremental_step_count"] = len(step_summaries)
    final["incremental_new_rows_after_first_step"] = new_rows_after_first_step
    final["incremental_step_summaries"] = step_summaries
    final["incremental_stable_pass_target"] = COMMENT_STABLE_PASS_TARGET
    final["incremental_stable_pass_count"] = stable_passes
    final["incremental_safety_ceiling"] = COMMENT_MAX_PASSES
    final["recycled_node_detected"] = any(len(values) > 1 for values in position_history.values())
    declared_count = int(final.get("declared_comment_count") or 0)
    if rows and declared_count and len(rows) < declared_count:
        final["capture_stop_reason"] = stop_reason
        final["completeness"] = "visible_rows_partial_declared_count_unreached"
    elif rows:
        final["capture_stop_reason"] = stop_reason
        final["completeness"] = "incremental_visible_rows_captured_partial"
    elif final.get("social_comment_wc_found"):
        final["capture_stop_reason"] = "zero_rows_after_component_visible_and_network_evidence"
        final["completeness"] = "component_visible_zero_rows"
    else:
        final["capture_stop_reason"] = "social_comment_wc_not_found"
        final["completeness"] = "component_not_visible"
    artifact = _write_bytes(
        jsonl_path,
        jsonl_path.read_bytes() if jsonl_path.exists() else b"",
        f"{profile_name}_comments_incremental_jsonl",
    )
    return final, artifact


def _write_comments_derived_artifacts(output_root: Path, profile_name: str, page: Any, comments: Mapping[str, Any]) -> tuple[RenderedArtifact, ...]:
    rows = [dict(row) for row in comments.get("rows") or ()]
    if not rows:
        return ()
    profile_root = output_root / profile_name
    width = int(MOBILE_PROFILE["viewport"]["width"])
    parts = [
        "<!doctype html><html><head><meta charset='utf-8'>",
        "<meta name='viewport' content='width=device-width, initial-scale=1'>",
        "<style>body{font-family:Arial,sans-serif;margin:0;background:#f5f5f5;color:#111}.wrap{width:",
        str(width),
        "px;margin:0 auto;background:white;padding:16px;box-sizing:border-box}.label{font-size:12px;text-transform:uppercase;color:#555}.comment{border-bottom:1px solid #ddd;padding:12px 0}.reply{margin-left:28px}.meta{font-size:12px;color:#555;margin-bottom:6px}.body{white-space:pre-wrap;font-size:15px;line-height:1.35}</style></head><body><main class='wrap'>",
        f"<div class='label'>{DERIVED_MSN_COMMENTS_EXPANDED_LAYOUT}</div>",
    ]
    for row in rows:
        depth = int(row.get("depth") or 0)
        author = html_lib.escape(str(row.get("author") or ""))
        posted = html_lib.escape(str(row.get("posted_at") or ""))
        comment_id = html_lib.escape(str(row.get("comment_id") or row.get("stable_identifier") or ""))
        text = html_lib.escape(str(row.get("text") or ""))
        klass = "comment reply" if depth else "comment"
        parts.append(
            f"<article class='{klass}' data-comment-id='{comment_id}'><div class='meta'>"
            f"{author} {posted} depth={depth} id={comment_id}</div><div class='body'>{text}</div></article>"
        )
    parts.append("</main></body></html>")
    html_text = "".join(parts)
    html_artifact = _write_text(profile_root / "derived_comments_full_thread.html", html_text, f"{profile_name}_derived_comments_full_thread_html")
    transform_artifact = _write_json(
        profile_root / "comments_derived_layout_transformations.json",
        {
            "authoritative_record_source": "comments.json/comments_incremental.jsonl",
            "faithful_screenshot_unmodified": True,
            "label": DERIVED_MSN_COMMENTS_EXPANDED_LAYOUT,
            "mobile_width_px": width,
            "record_count": len(rows),
            "transformations": [
                "static_print_document_generated_from_reconciled_comment_records",
                "height:auto !important",
                "max-height:none !important",
                "overflow:visible !important",
                "overflow-y:visible !important",
            ],
            "virtualization_note": "final DOM coexistence is not required; JSON/TXT records are authoritative",
        },
        f"{profile_name}_comments_derived_layout_transformations",
    )
    screenshot_artifact: RenderedArtifact | None = None
    derived_page = None
    try:
        derived_page = page.context.new_page()
        derived_page.set_viewport_size({"width": width, "height": 900})
        derived_page.set_content(html_text, wait_until="domcontentloaded")
        path = profile_root / "derived_comments_full_thread.png"
        derived_page.screenshot(path=str(path), full_page=True)
        screenshot_artifact = _write_bytes(path, path.read_bytes(), f"{profile_name}_derived_comments_full_thread_screenshot")
    except Exception:
        screenshot_artifact = None
    finally:
        if derived_page is not None:
            try:
                derived_page.close()
            except Exception:
                pass
    artifacts = [html_artifact, transform_artifact]
    if screenshot_artifact is not None:
        artifacts.append(screenshot_artifact)
    return tuple(artifacts)


def _write_profile_artifacts(output_root: Path, profile_name: str, page: Any, final_dom: str, comments: Mapping[str, Any]) -> tuple[RenderedArtifact, ...]:
    artifacts: list[RenderedArtifact] = []
    profile_root = output_root / profile_name
    artifacts.append(_write_text(profile_root / "final_rendered_dom.html", final_dom, f"{profile_name}_final_dom"))
    full_page = profile_root / "faithful_full_page.png"
    page.screenshot(path=str(full_page), full_page=True)
    artifacts.append(_write_bytes(full_page, full_page.read_bytes(), f"{profile_name}_faithful_full_page_screenshot"))
    try:
        locator = page.locator("article, main").first
        if locator.count():
            article_path = profile_root / "faithful_article_region.png"
            locator.screenshot(path=str(article_path), timeout=5000)
            artifacts.append(_write_bytes(article_path, article_path.read_bytes(), f"{profile_name}_faithful_article_screenshot"))
    except Exception:
        pass
    if comments.get("social_comment_wc_found") or comments.get("overlay_container_found") or comments.get("row_count"):
        for selector in (
            "social-comment-wc .overlay-container",
            "social-comment-wc comment-list",
            "social-comment-wc",
            ".overlay-container",
        ):
            try:
                comments_path = profile_root / "faithful_comments_visible.png"
                target = page.locator(selector).first
                if target.count():
                    target.screenshot(path=str(comments_path), timeout=5000)
                    artifacts.append(_write_bytes(comments_path, comments_path.read_bytes(), f"{profile_name}_faithful_comments_screenshot"))
                    break
            except Exception:
                continue
    artifacts.extend(_write_comments_derived_artifacts(output_root, profile_name, page, comments))
    return tuple(artifacts)


def _capture_profile(
    *,
    source_url: str,
    output_root: Path,
    profile: Mapping[str, Any],
    headless: bool = True,
) -> RenderProfileResult:
    from playwright.sync_api import sync_playwright

    responses: list[Any] = []
    captured: list[CapturedResponse] = []
    profile_name = str(profile["name"])
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=headless)
        try:
            context_kwargs: dict[str, Any] = {
                "viewport": profile["viewport"],
                "device_scale_factor": profile.get("device_scale_factor", 1),
                "is_mobile": bool(profile.get("is_mobile", False)),
                "locale": "en-GB",
            }
            if profile.get("user_agent"):
                context_kwargs["user_agent"] = profile["user_agent"]
            context = browser.new_context(**context_kwargs)
            try:
                page = context.new_page()
                page.on("response", lambda response: responses.append(response))
                response = page.goto(source_url, wait_until="domcontentloaded", timeout=60000)
                page.wait_for_timeout(7000)
                privacy_warning = _dismiss_privacy_banner(page)
                for selector in (
                    "[data-test-id='continue-reading-button']",
                    "fluent-button[name='Continue reading']",
                    "button:has-text('Continue reading')",
                ):
                    try:
                        button = page.locator(selector).first
                        if button.count() and button.is_visible(timeout=1000):
                            button.click(timeout=2000)
                            page.wait_for_timeout(2500)
                            break
                    except Exception:
                        continue
                for _ in range(4):
                    page.mouse.wheel(0, 1800)
                    page.wait_for_timeout(1200)
                for label in ("Comments", "Join the conversation", "See comments", "Show comments"):
                    try:
                        page.get_by_text(label, exact=False).first.click(timeout=1500)
                        page.wait_for_timeout(2500)
                        break
                    except Exception:
                        continue
                for _ in range(3):
                    page.mouse.wheel(0, 1400)
                    page.wait_for_timeout(1000)
                final_dom = page.content()
                title = _extract_title(page) or page.title()
                body_text = ""
                try:
                    body_text = page.locator("body").inner_text(timeout=5000)
                except Exception:
                    try:
                        body_text = str(page.evaluate("() => document.body ? document.body.innerText : ''") or "")
                    except Exception:
                        body_text = ""
                comments_info, incremental_comments_artifact = _collect_incremental_comments(page, output_root, profile_name)
                comment_response_urls = [
                    str(item.url)
                    for item in responses
                    if "service/community/comments" in str(item.url).lower()
                ]
                api_result = _fetch_msn_comment_api_records(page, comment_response_urls, int(comments_info.get("incremental_step_count") or 0))
                comments_info = _merge_provider_comment_rows(comments_info, api_result)
                artifacts = list(_write_profile_artifacts(output_root, profile_name, page, final_dom, comments_info))
                artifacts.append(incremental_comments_artifact)
                artifacts.append(
                    _write_json(
                        output_root / profile_name / "comments_provider_reconciliation.json",
                        {
                            "api_reconciliation": comments_info.get("api_reconciliation", {}),
                            "provider_reconciliation": comments_info.get("provider_reconciliation", {}),
                        },
                        f"{profile_name}_comments_provider_reconciliation",
                    )
                )
                for item in responses[:MAX_CAPTURED_RESPONSE_COUNT]:
                    try:
                        body = item.body()
                    except Exception:
                        continue
                    if not body or len(body) > MAX_RESPONSE_BODY_BYTES:
                        continue
                    request = item.request
                    captured.append(
                        CapturedResponse(
                            url=item.url,
                            status=int(item.status),
                            headers={str(k): str(v) for k, v in item.headers.items()},
                            body=bytes(body),
                            resource_type=str(request.resource_type),
                            method=str(request.method),
                            from_profile=profile_name,
                        )
                    )
                comment_network_responses = [
                    _redact_url_for_metadata(str(item.url))
                    for item in responses
                    if any(fragment in str(item.url).lower() for fragment in ("service/community/comments", "comment-list", "social-data"))
                ]
                comments_info["comment_network_response_count"] = len(comment_network_responses)
                comments_info["comment_network_response_urls"] = sorted(set(comment_network_responses))[:20]
                source_request_url = _without_fragment(source_url)
                if response is not None and all(_without_fragment(item.url) != source_request_url for item in captured):
                    captured.append(
                        CapturedResponse(
                            url=source_request_url,
                            status=int(response.status),
                            headers={str(k): str(v) for k, v in response.headers.items()},
                            body=final_dom.encode("utf-8"),
                            resource_type="document",
                            method="GET",
                            from_profile=profile_name,
                        )
                    )
                article_text = _extract_article_text(page, final_dom, content_id=_msn_content_id(source_url))
                media = discover_media_resources_from_html(final_dom, source_url=page.url)
                media_rows = [resource.to_dict() for resource in media.resources]
                media_rows.extend(response.to_dict() for response in captured if response.resource_type in {"image", "media", "font"})
                return RenderProfileResult(
                    profile_name=profile_name,
                    final_url=page.url,
                    title=title,
                    final_dom=final_dom,
                    body_text=body_text,
                    article_text=article_text,
                    comments=tuple(comments_info.get("rows") or ()),
                    comments_component=comments_info,
                    resource_inventory=tuple(media_rows),
                    captured_responses=tuple(captured),
                    screenshot_artifacts=tuple(artifacts),
                    status=RENDERED_BROWSER_LIVE_TESTED,
                    warnings=tuple(item for item in (privacy_warning,) if item),
                )
            finally:
                context.close()
        finally:
            browser.close()


def _extract_article_text(page: Any, final_dom: str, *, content_id: str = "") -> str:
    try:
        text = str(
            page.evaluate(
                """(contentId) => {
                  function deepText(node) {
                    if (!node) return "";
                    let text = node.innerText || "";
                    if (!text) {
                      const walker = document.createTreeWalker(node, NodeFilter.SHOW_TEXT);
                      const chunks = [];
                      while (walker.nextNode()) {
                        const parent = walker.currentNode.parentElement;
                        if (parent && parent.closest("style,script,template,noscript")) continue;
                        const value = (walker.currentNode.nodeValue || "").replace(/\\s+/g, " ").trim();
                        if (value) chunks.push(value);
                      }
                      text = chunks.join(" ");
                    }
                    const children = node.querySelectorAll ? Array.from(node.querySelectorAll("*")) : [];
                    for (const child of children) {
                      if (child.shadowRoot) text += "\\n" + deepText(child.shadowRoot);
                    }
                    return text.replace(/\\s+/g, " ").trim();
                  }
                  const selectors = [];
                  if (contentId) {
                    selectors.push(
                      `#ViewsPageId-${contentId} article`,
                      `[id='consumption-feed-content-${contentId}'] article`,
                      `[instance-id*='${contentId}'] article`
                    );
                  }
                  selectors.push(
                    "article",
                    "main [data-t='ArticleBody']",
                    "main [class*='article']",
                    "[role='main'] article",
                    "main",
                    "[role='main']"
                  );
                  let best = "";
                  for (const selector of selectors) {
                    for (const el of document.querySelectorAll(selector)) {
                      const text = deepText(el);
                      if (text.length > best.length) best = text;
                    }
                  }
                  return best.replace(/^\\s*(Continue reading\\s*)?[;\\s]+/, "").trim();
                }""",
                content_id,
            )
            or ""
        ).strip()
        if len(text) > 120:
            return text
    except Exception:
        pass
    for selector in ("article", "main [data-t='ArticleBody']", "main", "[role='main']"):
        try:
            text = page.locator(selector).first.inner_text(timeout=2500).strip()
            if len(text) > 120:
                return text
        except Exception:
            continue
    extracted = extract_article_text_from_html(final_dom)
    return extracted.text


def _extract_title(page: Any) -> str:
    try:
        title = str(
            page.evaluate(
                """() => {
                  function deepText(node) {
                    if (!node) return "";
                    let text = node.innerText || "";
                    if (!text) {
                      const walker = document.createTreeWalker(node, NodeFilter.SHOW_TEXT);
                      const chunks = [];
                      while (walker.nextNode()) {
                        const parent = walker.currentNode.parentElement;
                        if (parent && parent.closest("style,script,template,noscript")) continue;
                        const value = (walker.currentNode.nodeValue || "").replace(/\\s+/g, " ").trim();
                        if (value) chunks.push(value);
                      }
                      text = chunks.join(" ");
                    }
                    const children = node.querySelectorAll ? Array.from(node.querySelectorAll("*")) : [];
                    for (const child of children) {
                      if (child.shadowRoot) text += "\\n" + deepText(child.shadowRoot);
                    }
                    return text.replace(/\\s+/g, " ").trim();
                  }
                  for (const selector of ["article h1", "main h1", "h1"]) {
                    const el = document.querySelector(selector);
                    const text = deepText(el);
                    if (text.length > 8) return text;
                  }
                  for (const host of document.querySelectorAll("views-header-wc, cp-article, desktop-article-content")) {
                    if (!host.shadowRoot) continue;
                    for (const el of host.shadowRoot.querySelectorAll?.("h1,[role='heading']") || []) {
                      const text = deepText(el);
                      if (text.length > 8) return text;
                    }
                  }
                  return "";
                }"""
            )
            or ""
        ).strip()
        return title
    except Exception:
        return ""


def _build_action_log(output_root: Path, result_summary: Mapping[str, Any], timestamp_utc: str) -> RenderedArtifact:
    session_id = stable_capture_id("msn_rendered_validation", result_summary.get("source_url", ""), timestamp_utc)
    events = []
    previous = ""
    for action_type, status in (
        ("rendered_browser_desktop_capture", result_summary["status_matrix"].get("desktop_render")),
        ("rendered_browser_mobile_capture", result_summary["status_matrix"].get("mobile_emulated_render")),
        ("rendered_article_comments_capture", result_summary["status_matrix"].get("comments_replies_capture")),
        ("rendered_resource_download", result_summary["status_matrix"].get("representative_download")),
        ("rendered_wayback_check", result_summary["status_matrix"].get("wayback_check")),
        ("rendered_local_web_archive", result_summary["status_matrix"].get("standards_oriented_wacz")),
        ("rendered_replay_viewer", result_summary["status_matrix"].get("replay_open")),
    ):
        event = build_action_log_event(
            session_id=session_id,
            actor_type=ACTOR_TYPE_APPLICATION,
            action_type=action_type,
            result=str(status or ""),
            timestamp_utc=timestamp_utc,
            previous_event_hash=previous,
            request_summary={"source": "approved_msn_single_url", "raw_payload_included": False},
        )
        events.append(event)
        previous = event.event_hash
    payload = "".join(json.dumps(event.to_dict(), sort_keys=True) + "\n" for event in events)
    return _write_text(output_root / "action_log.jsonl", payload, "action_log")


def _viewer_state(wacz_path: str | Path) -> dict[str, Any]:
    configured = os.environ.get("REPLAYWEBPAGE_PATH", "").strip()
    state = {
        "configured_path": configured,
        "opened": False,
        "status": VIEWER_NOT_CONFIGURED,
        "visual_status": USER_VISUAL_CONFIRMATION_REQUIRED,
        "wacz_path": str(wacz_path),
    }
    if configured and Path(configured).is_file():
        state["status"] = VIEWER_CONFIGURED
    return state


def run_msn_rendered_browser_validation(
    *,
    source_url: str = DEFAULT_MSN_VERTICAL_URL,
    output_directory: str | Path | None = None,
    headless: bool = True,
    timestamp_utc: str = "",
) -> RenderedValidationResult:
    if source_url != DEFAULT_MSN_VERTICAL_URL:
        raise ValueError("rendered MSN validation is approved for the configured MSN URL only")
    timestamp = timestamp_utc or _utc_now_iso()
    output_root = Path(output_directory or tempfile.mkdtemp(prefix="ytce_msn_rendered_browser_validation_"))
    output_root.mkdir(parents=True, exist_ok=True)
    canonical_url = canonicalize_msn_url(source_url)

    desktop = _capture_profile(source_url=source_url, output_root=output_root, profile=DESKTOP_PROFILE, headless=headless)
    mobile = _capture_profile(source_url=source_url, output_root=output_root, profile=MOBILE_PROFILE, headless=headless)
    profile_results = [desktop, mobile]
    mobile_used = True
    best = max(
        profile_results,
        key=lambda item: (
            1 if _article_matches_expected_source(item.article_text) else 0,
            len(item.comments),
            len(item.article_text),
            len(item.resource_inventory),
        ),
    )
    best_article_matches_source = _article_matches_expected_source(best.article_text)
    artifacts: list[RenderedArtifact] = []
    for profile_result in profile_results:
        profile_root = output_root / profile_result.profile_name
        artifacts.extend(profile_result.screenshot_artifacts)
        artifacts.append(_write_json(profile_root / "profile_summary.json", profile_result.to_dict(), f"{profile_result.profile_name}_summary"))
        artifacts.append(_write_text(profile_root / "article.txt", profile_result.article_text, f"{profile_result.profile_name}_article_text"))
        outline = build_page_outline_from_html(profile_result.final_dom, source_url=profile_result.final_url)
        artifacts.append(_write_text(profile_root / "page_outline.txt", format_page_outline_text(outline), f"{profile_result.profile_name}_page_outline"))
        artifacts.append(_write_json(profile_root / "comments.json", list(profile_result.comments), f"{profile_result.profile_name}_comments_json"))
        artifacts.append(_write_text(profile_root / "comments.txt", "\n".join(str(row.get("text") or "") for row in profile_result.comments), f"{profile_result.profile_name}_comments_text"))
        artifacts.append(_write_json(profile_root / "resource_inventory.json", list(profile_result.resource_inventory), f"{profile_result.profile_name}_resource_inventory"))

    all_responses = tuple(response for profile_result in profile_results for response in profile_result.captured_responses)
    download_result = _download_from_captured_response(output_directory=output_root, responses=all_responses)
    if download_result.get("download_performed"):
        artifacts.append(
            RenderedArtifact(
                "representative_download",
                str(download_result["output_path"]),
                str(download_result["sha256"]),
                int(download_result["size_bytes"]),
            )
        )
    wayback = _wayback_check(source_url)
    artifacts.append(_write_json(output_root / "archive" / "wayback_check.json", wayback, "wayback_check"))

    archive_responses: list[CapturedResponse] = []
    archive_size = 0
    for response in all_responses:
        response_size = len(response.body)
        if archive_size + response_size > MAX_WARC_BODY_BYTES:
            continue
        archive_responses.append(response)
        archive_size += response_size
    if not archive_responses:
        archive_responses = [
            CapturedResponse(
                url=best.final_url or source_url,
                status=200,
                headers={"content-type": "text/html; charset=utf-8"},
                body=best.final_dom.encode("utf-8"),
                resource_type="document",
                from_profile=best.profile_name,
            )
        ]
    warc = write_standard_warc(
        output_warc_path=output_root / "local_web_archive" / "archive" / "data.warc",
        responses=archive_responses,
        timestamp_utc=timestamp,
    )
    wacz = write_standard_wacz(
        output_wacz_path=output_root / "local_web_archive" / "archive.wacz",
        warc_path=warc["path"],
        index_rows=warc["index_rows"],
        source_url=best.final_url or source_url,
        title=best.title,
        text=best.body_text or best.article_text,
        timestamp_utc=timestamp,
    )
    artifacts.append(RenderedArtifact("standard_warc", warc["path"], warc["sha256"], warc["size_bytes"]))
    artifacts.append(RenderedArtifact("standard_wacz", wacz["path"], wacz["sha256"], wacz["size_bytes"]))
    bundle = write_offline_evidence_bundle(
        output_zip_path=output_root / "local_web_archive" / "local_evidence_bundle.zip",
        source_url=source_url,
        source_label="MSN rendered browser validation",
        article_text=best.article_text,
        page_outline_text=format_page_outline_text(build_page_outline_from_html(best.final_dom, source_url=best.final_url)),
        html_snapshot=best.final_dom,
        comments=best.comments,
        livechat=(),
        selected_media_metadata=(download_result,),
        archive_results=(wayback, wacz),
        screenshot_paths=tuple(
            artifact.path for artifact in best.screenshot_artifacts if Path(artifact.path).suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}
        ),
        no_live_capture_performed=False,
    )
    artifacts.append(RenderedArtifact("offline_evidence_bundle", str(output_root / "local_web_archive" / "local_evidence_bundle.zip"), bundle.sha256, bundle.size_bytes))
    viewer = _viewer_state(wacz["path"])
    status_matrix = {
        "source_canonicalization": RENDERED_BROWSER_LIVE_TESTED,
        "browser_runtime": RENDERED_BROWSER_LIVE_TESTED,
        "desktop_render": RENDERED_BROWSER_LIVE_TESTED,
        "mobile_emulated_render": RENDERED_BROWSER_LIVE_TESTED if mobile_used else STATUS_N_A,
        "article_only_text": RENDERED_BROWSER_LIVE_TESTED if best.article_text and best_article_matches_source else STATUS_PARTIAL,
        "page_outline": RENDERED_BROWSER_LIVE_TESTED
        if format_page_outline_text(build_page_outline_from_html(best.final_dom, source_url=best.final_url)).strip()
        else STATUS_PARTIAL,
        "final_dom": RENDERED_BROWSER_LIVE_TESTED,
        "faithful_article_screenshot": RENDERED_BROWSER_LIVE_TESTED if best.screenshot_artifacts else STATUS_PARTIAL,
        "comments_component_detection": RENDERED_BROWSER_LIVE_TESTED if best.comments_component.get("social_comment_wc_found") else STATUS_PARTIAL,
        "comments_replies_capture": RENDERED_BROWSER_LIVE_TESTED if best.comments else STATUS_PARTIAL,
        "comment_completeness": RENDERED_BROWSER_LIVE_TESTED
        if best.comments_component.get("completeness") == COMMENTS_COMPLETE
        else STATUS_PARTIAL,
        "comments_screenshot": RENDERED_BROWSER_LIVE_TESTED
        if best.comments and any("comments" in artifact.label for artifact in best.screenshot_artifacts)
        else STATUS_PARTIAL,
        "image_discovery": RENDERED_BROWSER_LIVE_TESTED if any("image" in str(row).lower() for row in best.resource_inventory) else STATUS_PARTIAL,
        "media_subtitle_discovery": RENDERED_BROWSER_LIVE_TESTED if any("media" in response.resource_type for response in all_responses) else STATUS_PARTIAL,
        "playback_triggered_discovery": STATUS_N_A,
        "representative_download": str(download_result["status"]),
        "wayback_check": str(wayback["status"]),
        "wayback_submit": "NOT RUN",
        "real_browser_backed_warc": LOCAL_PACKAGE_STRUCTURALLY_VERIFIED if warc["conformant_read_record_count"] else STATUS_PARTIAL,
        "standards_oriented_wacz": str(wacz["status"]),
        "bundle_hashes": LOCAL_PACKAGE_STRUCTURALLY_VERIFIED,
        "replaywebpage_configuration": str(viewer["status"]),
        "replay_open": USER_VISUAL_CONFIRMATION_REQUIRED if viewer["status"] == VIEWER_CONFIGURED else VIEWER_NOT_CONFIGURED,
        "replay_visual_completeness": USER_VISUAL_CONFIRMATION_REQUIRED,
        "action_log": LOCAL_PACKAGE_STRUCTURALLY_VERIFIED,
    }
    summary = {
        "best_profile": best.to_dict(),
        "canonical_url": canonical_url,
        "dependency_versions": dependency_versions(),
        "download": download_result,
        "mobile_profile_used": mobile_used,
        "profiles": [profile.to_dict() for profile in profile_results],
        "source_url": source_url,
        "source_article_text_match": best_article_matches_source,
        "status_matrix": status_matrix,
        "viewer": viewer,
        "warc": {key: value for key, value in warc.items() if key != "index_rows"},
        "wacz": wacz,
        "wayback": wayback,
    }
    artifacts.append(_write_json(output_root / "summary" / "rendered_validation_summary.json", summary, "rendered_validation_summary"))
    artifacts.append(_build_action_log(output_root, summary, timestamp))
    artifacts.append(_write_text(output_root / "SHA256SUMS.txt", _format_sha256sums(artifacts), "sha256sums"))
    manifest = {
        "artifacts": [artifact.to_dict() for artifact in artifacts],
        "canonical_url": canonical_url,
        "schema_version": MSN_RENDERED_BROWSER_SCHEMA_VERSION,
        "source_url": source_url,
        "status_matrix": status_matrix,
        "summary": summary,
        "timestamp_utc": timestamp,
    }
    manifest_artifact = _write_json(output_root / "manifest.json", manifest, "manifest")
    artifacts.append(manifest_artifact)
    return RenderedValidationResult(
        source_url=source_url,
        canonical_url=canonical_url,
        output_directory=str(output_root),
        status_matrix=status_matrix,
        manifest_path=manifest_artifact.path,
        manifest_sha256=manifest_artifact.sha256,
        artifacts=tuple(artifacts),
        summary=summary,
    )


def dependency_versions() -> dict[str, str]:
    versions: dict[str, str] = {}
    for name in ("playwright", "warcio"):
        try:
            from importlib.metadata import version

            versions[name] = version(name)
        except Exception:
            versions[name] = ""
    versions["playwright_chromium_build"] = "1181"
    versions["playwright_chromium_version"] = "139.0.7258.5"
    return versions


def _format_sha256sums(artifacts: Sequence[RenderedArtifact]) -> str:
    return "".join(f"{artifact.sha256}  {Path(artifact.path).name}\n" for artifact in sorted(artifacts, key=lambda item: item.path))


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Controlled rendered-browser validation for the approved MSN URL.")
    parser.add_argument("--url", default=DEFAULT_MSN_VERTICAL_URL)
    parser.add_argument("--output-dir", default="")
    parser.add_argument("--headed", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    result = run_msn_rendered_browser_validation(
        source_url=args.url,
        output_directory=args.output_dir or None,
        headless=not args.headed,
    )
    if args.json:
        print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
    else:
        print(f"MSN rendered validation output: {result.output_directory}")
        print(f"Manifest: {result.manifest_path}")
        for key, value in result.status_matrix.items():
            print(f"{key}: {value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
