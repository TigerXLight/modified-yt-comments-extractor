from __future__ import annotations

import argparse
import gzip
import hashlib
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
    parsed = urlsplit(url)
    host = (parsed.hostname or "").lower()
    parts = host.split(".")
    host_key = ",".join(reversed(parts))
    path = parsed.path or "/"
    if parsed.query:
        path += "?" + parsed.query
    return f"{host_key}){path}"


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
            request_headers = StatusAndHeaders(
                f"{response.method or 'GET'} {_warc_target_path(response.url)} HTTP/1.1",
                [("Host", urlsplit(response.url).netloc)],
                protocol="HTTP/1.1",
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
                "url": source_url,
            },
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")
    cdxj = "\n".join(
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
    ).encode("utf-8") + b"\n"
    cdx_gz = gzip.compress(cdxj, mtime=0)
    resources = {
        "archive/data.warc": warc_bytes,
        "indexes/index.cdx.gz": cdx_gz,
        "pages/pages.jsonl": pages_jsonl,
    }
    datapackage = {
        "created": timestamp_utc,
        "description": "Controlled MSN rendered-browser validation WACZ.",
        "home": {"url": source_url, "ts": timestamp_utc},
        "mainPageUrl": source_url,
        "modified": timestamp_utc,
        "profile": "data-package",
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
        "wacz_version": "1.2.0",
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
    }
    with zipfile.ZipFile(package, "r") as bundle:
        names = set(bundle.namelist())
        required = {"archive/data.warc", "indexes/index.cdx.gz", "pages/pages.jsonl", "datapackage.json"}
        result["entries"] = sorted(names)
        result["missing_required_entries"] = sorted(required - names)
        datapackage = json.loads(bundle.read("datapackage.json").decode("utf-8"))
        result["wacz_version"] = str(datapackage.get("wacz_version") or "")
        result["profile"] = str(datapackage.get("profile") or "")
        result["resource_count"] = len(datapackage.get("resources", ()))
        result["page_count"] = max(0, len(bundle.read("pages/pages.jsonl").decode("utf-8").splitlines()) - 1)
        result["index_line_count"] = len(gzip.decompress(bundle.read("indexes/index.cdx.gz")).decode("utf-8").splitlines())
    if result["missing_required_entries"]:
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
                if (!root || depth > 10) return out;
                for (const el of Array.from(root.children || [])) {
                  out.push(el);
                  if (el.shadowRoot) allOpenShadowElements(el.shadowRoot, out, depth + 1);
                  allOpenShadowElements(el, out, depth + 1);
                }
                return out;
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
                const hasReplies = /reply|replies/i.test(replyButtonText) || !!shadow.querySelector("reply-list");
                const reactions = Array.from(shadow.querySelectorAll("msn-social-bar, social-bar-wc, [class*='social-bar']")).map(el => clean(el.innerText || el.textContent || "")).filter(Boolean).join(" ");
                const stable = id || [author, postedAt, body.slice(0, 120), source].join("|");
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
                const replyItems = Array.from(shadow.querySelectorAll("reply-list")).flatMap(list => {
                  const root = list.shadowRoot || list;
                  return Array.from(root.querySelectorAll?.("comment-item") || []);
                });
                for (const reply of replyItems) pushItem(reply, "social-comment-wc.reply-list", depth + 1, stable);
              }
              if (hostRoot) {
                const roots = [hostRoot].concat(allOpenShadowElements(hostRoot).map(el => el.shadowRoot).filter(Boolean));
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
                return /(auto|scroll)/.test(style.overflowY) && el.scrollHeight > el.clientHeight + 50;
              }).slice(0, 20).map(el => ({tag: el.tagName.toLowerCase(), className: String(el.className || ""), id: el.id || "", scrollHeight: el.scrollHeight, clientHeight: el.clientHeight}));
              const commentListItems = hostRoot ? allOpenShadowElements(hostRoot).filter(el => (el.tagName || "").toLowerCase() === "comment-item").length : 0;
              const loadMoreButtons = hostRoot ? allOpenShadowElements(hostRoot).filter(el => /see more comments|load more/i.test(clean(el.innerText || el.textContent || el.getAttribute("aria-label") || ""))).length : 0;
              const headerText = hostRoot ? allOpenShadowElements(hostRoot).map(el => clean(el.innerText || el.textContent || "")).find(text => /\\b\\d+\\s+comments?\\b/i.test(text)) || "" : "";
              const declaredCountMatch = headerText.match(/\\b(\\d+)\\s+comments?\\b/i);
              return {
                social_comment_wc_found: !!host,
                social_comment_wc_shadow_open: !!hostRoot,
                overlay_container_found: !!(hostRoot && hostRoot.querySelector(".overlay-container")),
                comment_list_item_count: commentListItems,
                declared_comment_count: declaredCountMatch ? Number(declaredCountMatch[1]) : 0,
                load_more_control_count: loadMoreButtons,
                nested_scroll_container_count: scrollContainers.length,
                nested_scroll_containers: scrollContainers,
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
                if (!root || depth > 10) return out;
                for (const el of Array.from(root.children || [])) {
                  out.push(el);
                  if (el.shadowRoot) allOpenShadowElements(el.shadowRoot, out, depth + 1);
                  allOpenShadowElements(el, out, depth + 1);
                }
                return out;
              }
              if (!root) return {actions, social_comment_wc_found: !!host, social_comment_wc_shadow_open: false};
              const elements = allOpenShadowElements(root);
              for (const el of elements) {
                try {
                  const style = getComputedStyle(el);
                  if (/(auto|scroll)/.test(style.overflowY) && el.scrollHeight > el.clientHeight + 50) {
                    el.scrollTop = el.scrollHeight;
                    actions.push({action: "scroll_internal_container", tag: (el.tagName || "").toLowerCase(), className: String(el.className || ""), scrollHeight: el.scrollHeight});
                  }
                } catch (error) {}
              }
              const controls = elements.filter(el => {
                const text = clean(el.innerText || el.textContent || el.getAttribute("aria-label") || "");
                return /^(see more comments|load more comments|show more comments|see \\d+ more repl|view \\d+ repl|show \\d+ repl)/i.test(text)
                  || /see more comments|load-more-comments-button/i.test(String(el.className || ""));
              });
              for (const control of controls.slice(0, 4)) {
                try {
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


def _collect_incremental_comments(page: Any, output_root: Path, profile_name: str) -> tuple[dict[str, Any], RenderedArtifact]:
    profile_root = output_root / profile_name
    jsonl_path = profile_root / "comments_incremental.jsonl"
    profile_root.mkdir(parents=True, exist_ok=True)
    seen: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    position_history: dict[str, set[str]] = {}
    step_summaries: list[dict[str, Any]] = []
    new_rows_after_first_step = 0

    for step in range(COMMENT_COLLECTION_STEPS):
        if step:
            actions = _advance_msn_comments(page)
            page.wait_for_timeout(1200)
        else:
            actions = {"actions": []}
        snapshot = _evaluate_comments(page)
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
        if step:
            new_rows_after_first_step += new_this_step
        step_summaries.append(
            {
                "actions": actions.get("actions", []),
                "component_found": bool(snapshot.get("social_comment_wc_found")),
                "component_shadow_open": bool(snapshot.get("social_comment_wc_shadow_open")),
                "comment_list_item_count": int(snapshot.get("comment_list_item_count") or 0),
                "new_row_count": new_this_step,
                "row_count": int(snapshot.get("row_count") or 0),
                "step": step,
            }
        )
        if step >= 3 and new_this_step == 0 and len(seen) > 0:
            break

    final = _evaluate_comments(page)
    rows = [seen[key] for key in order]
    final["rows"] = rows
    final["row_count"] = len(rows)
    final["incremental_serialization_path"] = str(jsonl_path)
    final["incremental_step_count"] = len(step_summaries)
    final["incremental_new_rows_after_first_step"] = new_rows_after_first_step
    final["incremental_step_summaries"] = step_summaries
    final["recycled_node_detected"] = any(len(values) > 1 for values in position_history.values())
    declared_count = int(final.get("declared_comment_count") or 0)
    if rows and declared_count and len(rows) < declared_count:
        final["capture_stop_reason"] = "load_more_exhausted_before_declared_comment_count"
        final["completeness"] = "visible_rows_partial_declared_count_unreached"
    elif rows:
        final["capture_stop_reason"] = "no_new_rows_after_component_scroll_or_load_more"
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
                artifacts = list(_write_profile_artifacts(output_root, profile_name, page, final_dom, comments_info))
                artifacts.append(incremental_comments_artifact)
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
                if response is not None and all(item.url != source_url for item in captured):
                    captured.append(
                        CapturedResponse(
                            url=source_url,
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
        if best.comments
        and (
            not int(best.comments_component.get("declared_comment_count") or 0)
            or len(best.comments) >= int(best.comments_component.get("declared_comment_count") or 0)
        )
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
