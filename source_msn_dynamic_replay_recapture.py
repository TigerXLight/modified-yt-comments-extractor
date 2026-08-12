from __future__ import annotations

import argparse
import gzip
import hashlib
import html
import json
import re
import uuid
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse


RECAPTURE_ID = "msn_dynamic_replay_recapture_v4_20260812"
SCHEMA_VERSION = "msn_dynamic_replay_recapture_v4"
STATUS_READY = "DYNAMIC_RECAPTURE_V4_NETWORK_MATERIALIZED_GENERATED_MANUAL_REPLAY_REQUIRED"
STATUS_BLOCKED = "DYNAMIC_RECAPTURE_V4_BLOCKED_NO_ARTICLE_DETAIL_JSON"
STATUS_DEPENDENCY_BLOCKED = "DYNAMIC_RECAPTURE_V4_BLOCKED_DEPENDENCY"
STATUS_FAILED = "DYNAMIC_RECAPTURE_V4_FAILED"

MAIN_URL_FALLBACK = (
    "https://www.msn.com/en-gb/news/other/"
    "arrest-made-after-shot-fired-outside-york-mosque/ar-AA29207o?ocid=edgemobile&PC=EMMX01"
)
ARTICLE_REQUIRED_TERMS = ("york", "mosque")
ARTICLE_HELPER_TERMS = ("shot fired", "arrest made", "outside york mosque", "ar-aa29207o")
MAX_CAPTURED_RESPONSES = 260
MAX_RESPONSE_BODY_BYTES = 36 * 1024 * 1024


@dataclass(frozen=True)
class CapturedResponse:
    url: str
    status: int
    content_type: str
    resource_type: str
    body: bytes
    captured_at_utc: str

    @property
    def body_sha256(self) -> str:
        return sha256_bytes(self.body)

    @property
    def is_textual(self) -> bool:
        ct = self.content_type.lower()
        return any(x in ct for x in ("text/", "json", "javascript", "xml", "html"))

    def row(self) -> dict[str, Any]:
        probe = self.body[:2000].decode("utf-8", errors="replace") if self.is_textual else ""
        return {
            "url": self.url,
            "status": self.status,
            "content_type": self.content_type,
            "resource_type": self.resource_type,
            "body_size": len(self.body),
            "body_sha256": self.body_sha256,
            "captured_at_utc": self.captured_at_utc,
            "text_probe": probe,
        }


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def cdx_timestamp_from_iso(value: str) -> str:
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})", value or "")
    if m:
        return "".join(m.groups())
    if re.match(r"^\d{14}$", value or ""):
        return str(value)
    return datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def write_text(path: Path, text: str) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return sha256_file(path)


def write_bytes(path: Path, data: bytes) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return sha256_file(path)


def raw_target_url(url: str) -> str:
    return str(url or "").split("#", 1)[0]


def canonical_article_url(url: str | None) -> str:
    raw = raw_target_url(url or MAIN_URL_FALLBACK)
    parsed = urlparse(raw)
    if not parsed.scheme or not parsed.netloc:
        return MAIN_URL_FALLBACK
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", parsed.query, ""))


def no_query_url(url: str) -> str:
    parsed = urlparse(raw_target_url(url))
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", "", ""))


def url_variants(url: str) -> list[str]:
    base = canonical_article_url(url)
    parsed = urlparse(base)
    pairs = parse_qsl(parsed.query, keep_blank_values=True)
    lower_names = urlencode([(k.lower(), v) for k, v in pairs], doseq=True)
    lower_all = urlencode([(k.lower(), v.lower()) for k, v in pairs], doseq=True)
    candidates = [
        base,
        urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", lower_names, "")),
        urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", lower_all, "")),
        no_query_url(base),
    ]
    out: list[str] = []
    for candidate in candidates:
        if candidate and candidate not in out:
            out.append(candidate)
    return out


def _query_key(query: str) -> str:
    return urlencode([(k.lower(), v.lower()) for k, v in parse_qsl(query, keep_blank_values=True)], doseq=True)


def surt_key(url: str) -> str:
    parsed = urlparse(raw_target_url(url))
    host = parsed.netloc.lower().split("@")[-1]
    if ":" in host and not host.startswith("["):
        host, port = host.rsplit(":", 1)
        port_part = ":" + port
    else:
        port_part = ""
    host_key = ",".join(reversed([p for p in host.split(".") if p])) + ",)" + port_part
    path = (parsed.path or "/").lower()
    query = _query_key(parsed.query)
    return f"{host_key}{path}?{query}" if query else f"{host_key}{path}"


def text_from_html(value: str) -> str:
    no_tags = re.sub(r"<[^>]+>", " ", value or "")
    return html.unescape(re.sub(r"\s+", " ", no_tags)).strip()


def article_terms_verified(text: str) -> bool:
    lower = (text or "").lower()
    return all(term in lower for term in ARTICLE_REQUIRED_TERMS) and any(term in lower for term in ARTICLE_HELPER_TERMS)


def dependency_errors() -> list[str]:
    try:
        import playwright  # type: ignore  # noqa: F401
    except Exception:
        return ["playwright is not importable in this environment"]
    return []


def try_default_msn_url() -> str:
    try:
        from source_msn_vertical_live_validation import DEFAULT_MSN_VERTICAL_URL  # type: ignore
        value = str(DEFAULT_MSN_VERTICAL_URL)
        if value:
            return value
    except Exception:
        pass
    return MAIN_URL_FALLBACK


def parse_json_response(response: CapturedResponse) -> Any | None:
    if "json" not in response.content_type.lower():
        return None
    try:
        return json.loads(response.body.decode("utf-8", errors="replace"))
    except Exception:
        return None


def find_article_detail(responses: Sequence[CapturedResponse]) -> tuple[dict[str, Any] | None, CapturedResponse | None]:
    best: tuple[dict[str, Any], CapturedResponse] | None = None
    for response in responses:
        data = parse_json_response(response)
        if not isinstance(data, dict):
            continue
        title = str(data.get("title") or "")
        body = str(data.get("body") or "")
        sample = " ".join([title, body, str(data.get("abstract") or ""), response.url])
        if "content/view/v2/detail" in response.url.lower() and article_terms_verified(sample):
            return data, response
        if data.get("body") and data.get("title") and article_terms_verified(sample):
            best = (data, response)
    return best if best else (None, None)


def find_social_summary(responses: Sequence[CapturedResponse]) -> tuple[dict[str, Any] | None, CapturedResponse | None]:
    for response in responses:
        if "service/community/urls" not in response.url.lower():
            continue
        data = parse_json_response(response)
        if isinstance(data, dict):
            return data, response
    return None, None


def materialize_body_html(article: Mapping[str, Any]) -> str:
    body = str(article.get("body") or "")
    images = article.get("imageResources")
    if isinstance(images, list):
        for image in images:
            if not isinstance(image, dict):
                continue
            cms_id = str(image.get("cmsId") or image.get("id") or "")
            url = str(image.get("url") or "")
            caption = html.escape(str(image.get("caption") or image.get("title") or ""))
            attribution = html.escape(str(image.get("attribution") or ""))
            if cms_id and url:
                replacement = (
                    f"<figure class='article-image'><img src='{html.escape(url)}' alt='{caption}' />"
                    f"<figcaption>{caption}{' — ' + attribution if attribution else ''}</figcaption></figure>"
                )
                body = re.sub(
                    r"<img\b[^>]*data-document-id=[\"']" + re.escape(cms_id) + r"[\"'][^>]*>",
                    replacement,
                    body,
                    flags=re.I,
                )
    return body


def render_social_summary(summary: Mapping[str, Any] | None) -> str:
    if not summary:
        return "<section class='social-summary'><h2>MSN social/comment summary</h2><p>No community-summary API response was captured.</p></section>"
    comment_summary = summary.get("commentSummary") if isinstance(summary.get("commentSummary"), dict) else {}
    reaction_summary = summary.get("reactionSummary") if isinstance(summary.get("reactionSummary"), dict) else {}
    total_comments = comment_summary.get("totalCount", "Not captured")
    reaction_total = reaction_summary.get("totalCount", "Not captured")
    sub_comments = comment_summary.get("subCommentSummaries") if isinstance(comment_summary.get("subCommentSummaries"), list) else []
    sub_reactions = reaction_summary.get("subReactionSummaries") if isinstance(reaction_summary.get("subReactionSummaries"), list) else []
    def rows(items: Any) -> str:
        out = []
        if isinstance(items, list):
            for item in items:
                if isinstance(item, dict):
                    out.append(f"<li>{html.escape(str(item.get('type')))}: {html.escape(str(item.get('totalCount')))}</li>")
        return "\n".join(out)
    return (
        "<section class='social-summary'>"
        "<h2>MSN captured social/comment summary</h2>"
        f"<p>Total comments/replies reported by captured MSN community API: <strong>{html.escape(str(total_comments))}</strong></p>"
        f"<ul>{rows(sub_comments)}</ul>"
        f"<p>Total reactions reported by captured MSN community API: <strong>{html.escape(str(reaction_total))}</strong></p>"
        f"<ul>{rows(sub_reactions)}</ul>"
        "<p class='note'>Actual comment text was not captured in this dynamic recapture; this section preserves only the captured community-summary counts.</p>"
        "</section>"
    )


def build_materialized_article_html(
    *,
    source_url: str,
    article: Mapping[str, Any],
    article_response: CapturedResponse,
    social_summary: Mapping[str, Any] | None,
    social_response: CapturedResponse | None,
    visible_body_text: str,
    dom_verified: bool,
) -> str:
    title = str(article.get("title") or "MSN captured article")
    abstract = str(article.get("abstract") or "")
    source_href = str(article.get("sourceHref") or "")
    provider = article.get("provider") if isinstance(article.get("provider"), dict) else {}
    provider_name = str(provider.get("name") or "")
    authors = article.get("authors")
    author_names = []
    if isinstance(authors, list):
        for item in authors:
            if isinstance(item, dict) and item.get("name"):
                author_names.append(str(item["name"]))
    body_html = materialize_body_html(article)
    article_text = text_from_html(body_html)
    generated_at = utc_now_iso()
    return f"""<!doctype html>
<html lang="en-GB">
<head>
<meta charset="utf-8" />
<title>{html.escape(title)}</title>
<meta name="viewport" content="width=device-width, initial-scale=1" />
<style>
:root {{ color-scheme: light; }}
body {{ margin:0; background:#f3f4f6; color:#111827; font-family: Arial, Helvetica, sans-serif; line-height:1.55; }}
.page {{ max-width: 860px; margin: 0 auto; background: #fff; min-height:100vh; box-shadow: 0 0 0 1px #e5e7eb; }}
.header {{ padding: 24px 24px 12px; border-bottom: 1px solid #e5e7eb; }}
.kicker {{ color:#6b7280; font-size: 14px; text-transform: uppercase; letter-spacing:.04em; }}
h1 {{ font-size: 34px; line-height:1.12; margin: 10px 0; }}
.meta {{ color:#4b5563; font-size: 15px; }}
.article-body {{ padding: 20px 24px; font-size: 18px; }}
.article-body ul {{ padding-left: 1.3em; }}
.article-body li {{ margin: 0.55em 0; }}
.article-body a {{ color: #0b5cad; }}
.article-image {{ margin: 18px 0; }}
.article-image img {{ max-width: 100%; border-radius: 10px; display:block; }}
.article-image figcaption {{ color:#6b7280; font-size: 13px; margin-top: 6px; }}
.social-summary, .recapture-panel {{ margin: 18px 24px; padding: 14px; border:1px solid #d1d5db; border-radius:10px; background:#f9fafb; }}
.recapture-panel {{ border-color:#f59e0b; background:#fff7ed; }}
.note {{ color:#6b7280; font-size: 14px; }}
pre {{ white-space: pre-wrap; word-break: break-word; }}
</style>
</head>
<body>
<main class="page">
  <section class="header">
    <div class="kicker">MSN dynamic network recapture V4</div>
    <h1>{html.escape(title)}</h1>
    <p class="meta">{html.escape(provider_name)}{(" • " + html.escape(", ".join(author_names))) if author_names else ""}</p>
    <p>{html.escape(abstract)}</p>
  </section>
  <section class="recapture-panel">
    <strong>YTCE MSN dynamic recapture V4 — network-materialized replay candidate</strong>
    <p>This page is generated from article JSON captured during the live MSN browser session, because the replay-visible DOM remained an MSN shell/More-for-You state.</p>
    <ul>
      <li>MSN source URL: {html.escape(raw_target_url(source_url))}</li>
      <li>Article JSON endpoint: {html.escape(article_response.url)}</li>
      <li>Article JSON SHA-256: {article_response.body_sha256}</li>
      <li>Community summary endpoint: {html.escape(social_response.url) if social_response else "Not captured"}</li>
      <li>Generated at UTC: {generated_at}</li>
      <li>Visible DOM body verified: {str(article_terms_verified(visible_body_text))}</li>
      <li>DOM/network article verified: {str(dom_verified)}</li>
      <li>Dynamic replay success claimed: False; manual ReplayWeb review required.</li>
    </ul>
  </section>
  <article class="article-body">
    {body_html}
  </article>
  {render_social_summary(social_summary)}
  <section class="recapture-panel">
    <h2>Article text evidence extracted from captured JSON</h2>
    <pre>{html.escape(article_text)}</pre>
    <p class="note">Original provider link captured in MSN JSON: {html.escape(source_href)}</p>
  </section>
</main>
</body>
</html>
"""


def http_response_payload(body: bytes, content_type: str = "text/html; charset=utf-8", status: int = 200) -> bytes:
    reason = "OK" if status == 200 else "Captured"
    return (
        f"HTTP/1.1 {status} {reason}\r\n"
        f"Content-Type: {content_type}\r\n"
        f"Content-Length: {len(body)}\r\n"
        "Cache-Control: no-store\r\n"
        f"X-YTCE-Dynamic-Recapture: {RECAPTURE_ID}\r\n"
        "\r\n"
    ).encode("utf-8") + body


def warc_record(record_type: str, target_uri: str, payload: bytes, content_type: str, timestamp_utc: str) -> bytes:
    return (
        "WARC/1.0\r\n"
        f"WARC-Type: {record_type}\r\n"
        f"WARC-Date: {timestamp_utc}\r\n"
        f"WARC-Record-ID: <urn:uuid:{uuid.uuid4()}>\r\n"
        f"WARC-Target-URI: {raw_target_url(target_uri)}\r\n"
        f"WARC-Block-Digest: sha256:{hashlib.sha256(payload).hexdigest()}\r\n"
        f"Content-Type: {content_type}\r\n"
        f"Content-Length: {len(payload)}\r\n"
        "\r\n"
    ).encode("utf-8") + payload + b"\r\n\r\n"


def parse_warc_boundaries(warc_bytes: bytes) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    pos = 0
    while pos < len(warc_bytes):
        start = warc_bytes.find(b"WARC/1.0", pos)
        if start < 0:
            break
        header_end = warc_bytes.find(b"\r\n\r\n", start)
        if header_end < 0:
            break
        header = warc_bytes[start:header_end].decode("latin1", errors="replace")
        m_len = re.search(r"^Content-Length:\s*(\d+)\s*$", header, flags=re.I | re.M)
        if not m_len:
            break
        payload_start = header_end + 4
        payload_end = payload_start + int(m_len.group(1))
        end = payload_end
        while end + 2 <= len(warc_bytes) and warc_bytes[end:end+2] == b"\r\n":
            end += 2
        payload = warc_bytes[payload_start:payload_end]
        target = re.search(r"^WARC-Target-URI:\s*(.*?)\s*$", header, flags=re.I | re.M)
        wtype = re.search(r"^WARC-Type:\s*(.*?)\s*$", header, flags=re.I | re.M)
        status = 200
        ctype = "application/octet-stream"
        if payload.startswith(b"HTTP/"):
            http_header_end = payload.find(b"\r\n\r\n")
            http_header = payload[: http_header_end if http_header_end >= 0 else min(len(payload), 4096)].decode("latin1", errors="replace")
            lines = http_header.splitlines()
            if lines:
                sm = re.match(r"HTTP/\S+\s+(\d+)", lines[0])
                if sm:
                    status = int(sm.group(1))
            for line in lines[1:]:
                if line.lower().startswith("content-type:"):
                    ctype = line.split(":", 1)[1].strip()
                    break
        records.append({
            "offset": start,
            "length": end - start,
            "target_uri": target.group(1) if target else "",
            "warc_type": wtype.group(1) if wtype else "",
            "http_status": status,
            "http_content_type": ctype,
            "record_sha256": sha256_bytes(warc_bytes[start:end]),
        })
        pos = end
    return records


def gzip_warc_members(warc_bytes: bytes) -> tuple[bytes, list[dict[str, Any]]]:
    records = parse_warc_boundaries(warc_bytes)
    out = bytearray()
    members: list[dict[str, Any]] = []
    for index, rec in enumerate(records):
        raw = warc_bytes[rec["offset"]: rec["offset"] + rec["length"]]
        member = gzip.compress(raw, compresslevel=9, mtime=0)
        offset = len(out)
        out.extend(member)
        members.append({**rec, "index": index, "gzip_offset": offset, "gzip_length": len(member), "filename": "archive/data.warc.gz"})
    return bytes(out), members


def cdxj_for_members(members: Sequence[Mapping[str, Any]], source_url: str, cdx_timestamp: str) -> str:
    lines: list[str] = []
    seen: set[tuple[str, int]] = set()
    for member in members:
        if str(member.get("warc_type")).lower() != "response":
            continue
        target = str(member.get("target_uri") or "")
        urls = [target]
        if raw_target_url(target) == raw_target_url(source_url):
            urls = url_variants(source_url)
        for url in urls:
            if not url:
                continue
            key = (surt_key(url), int(member.get("gzip_offset") or 0))
            if key in seen:
                continue
            payload = {
                "url": raw_target_url(url),
                "mime": str(member.get("http_content_type") or "application/octet-stream"),
                "status": int(member.get("http_status") or 200),
                "digest": "sha256:" + str(member.get("record_sha256") or "").lower(),
                "length": int(member.get("gzip_length") or 0),
                "offset": int(member.get("gzip_offset") or 0),
                "filename": "archive/data.warc.gz",
            }
            if raw_target_url(url) != raw_target_url(target):
                payload["ytce_dynamic_recapture_lookup_alias"] = True
                payload["ytce_dynamic_recapture_lookup_alias_of"] = raw_target_url(target)
            lines.append(f"{surt_key(url)} {cdx_timestamp} {json.dumps(payload, sort_keys=True, separators=(',', ':'))}")
            seen.add(key)
    lines.sort()
    return "\n".join(lines) + "\n"


def write_wacz(destination: Path, source_url: str, title: str, warc_gz: bytes, members: Sequence[Mapping[str, Any]], timestamp_utc: str) -> dict[str, Any]:
    cdx_timestamp = cdx_timestamp_from_iso(timestamp_utc)
    cdxj = cdxj_for_members(members, source_url, cdx_timestamp).encode("utf-8")
    cdx_gz = gzip.compress(cdxj, compresslevel=9, mtime=0)
    pages = (
        json.dumps({"format": "json-pages-1.0", "id": "pages", "title": "All Pages"}, sort_keys=True)
        + "\n"
        + json.dumps({"id": "msn_dynamic_recapture_v4_main_page", "title": title, "url": raw_target_url(source_url), "ts": timestamp_utc, "size": len(warc_gz), "text": "MSN dynamic network-materialized article replay candidate."}, sort_keys=True)
        + "\n"
    ).encode("utf-8")
    resources = [
        {"name": "data.warc.gz", "path": "archive/data.warc.gz", "bytes": len(warc_gz), "hash": "sha256:" + hashlib.sha256(warc_gz).hexdigest()},
        {"name": "index.cdx", "path": "indexes/index.cdx", "bytes": len(cdxj), "hash": "sha256:" + hashlib.sha256(cdxj).hexdigest()},
        {"name": "index.cdxj", "path": "indexes/index.cdxj", "bytes": len(cdxj), "hash": "sha256:" + hashlib.sha256(cdxj).hexdigest()},
        {"name": "index.cdx.gz", "path": "indexes/index.cdx.gz", "bytes": len(cdx_gz), "hash": "sha256:" + hashlib.sha256(cdx_gz).hexdigest()},
        {"name": "pages.jsonl", "path": "pages/pages.jsonl", "bytes": len(pages), "hash": "sha256:" + hashlib.sha256(pages).hexdigest()},
    ]
    datapackage = {
        "profile": "data-package",
        "wacz_version": "1.1.1",
        "created": timestamp_utc,
        "modified": timestamp_utc,
        "title": title,
        "description": "MSN dynamic recapture V4: article materialized from captured MSN JSON endpoint. Manual ReplayWeb review required.",
        "home": {"url": raw_target_url(source_url), "ts": timestamp_utc},
        "resources": resources,
        "ytce_recapture_note": {
            "recapture_id": RECAPTURE_ID,
            "schema_version": SCHEMA_VERSION,
            "candidate_type": "network_materialized_dynamic_article",
            "dynamic_replay_success_claimed": False,
            "manual_replayweb_visual_review_required": True,
        },
    }
    dp = (json.dumps(datapackage, indent=2, sort_keys=True) + "\n").encode("utf-8")
    digest = (json.dumps({"path": "datapackage.json", "hash": "sha256:" + hashlib.sha256(dp).hexdigest()}, indent=2, sort_keys=True) + "\n").encode("utf-8")
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        destination.unlink()

    def put(z: zipfile.ZipFile, name: str, data: bytes, stored: bool = False) -> None:
        info = zipfile.ZipInfo(name)
        info.compress_type = zipfile.ZIP_STORED if stored else zipfile.ZIP_DEFLATED
        z.writestr(info, data)

    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        put(z, "datapackage.json", dp)
        put(z, "datapackage-digest.json", digest)
        put(z, "archive/data.warc.gz", warc_gz, stored=True)
        put(z, "indexes/index.cdx", cdxj)
        put(z, "indexes/index.cdxj", cdxj)
        put(z, "indexes/index.cdx.gz", cdx_gz)
        put(z, "pages/pages.jsonl", pages)
    return {"path": str(destination), "sha256": sha256_file(destination), "main_surt_key": surt_key(source_url), "cdx_timestamp": cdx_timestamp}


def build_warc(source_url: str, materialized_html: str, responses: Sequence[CapturedResponse], timestamp_utc: str) -> bytes:
    out = bytearray()
    out.extend(warc_record("response", source_url, http_response_payload(materialized_html.encode("utf-8"), "text/html; charset=utf-8", 200), "application/http; msgtype=response", timestamp_utc))
    seen = {raw_target_url(source_url)}
    for response in responses:
        target = raw_target_url(response.url)
        if not target or target in seen or not response.body:
            continue
        seen.add(target)
        ctype = response.content_type or "application/octet-stream"
        out.extend(warc_record("response", response.url, http_response_payload(response.body, ctype, response.status or 200), "application/http; msgtype=response", response.captured_at_utc or timestamp_utc))
    return bytes(out)


def run_browser_capture(source_url: str, output_root: Path, headless: bool, timeout_ms: int, scroll_passes: int) -> tuple[list[CapturedResponse], str, str, bool, str]:
    from playwright.sync_api import sync_playwright  # type: ignore

    responses: list[CapturedResponse] = []
    total_bytes = 0
    final_dom = ""
    final_text = ""
    title = ""
    screenshot_hash = ""

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context(
            viewport={"width": 412, "height": 915},
            device_scale_factor=2,
            is_mobile=True,
            has_touch=True,
            user_agent=("Mozilla/5.0 (Linux; Android 14; Xperia 1 IV) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Mobile Safari/537.36 EdgA/139.0.0.0"),
            locale="en-GB",
        )
        page = context.new_page()

        def on_response(response: Any) -> None:
            nonlocal total_bytes
            if len(responses) >= MAX_CAPTURED_RESPONSES:
                return
            url = str(response.url)
            if not (url.startswith("http://") or url.startswith("https://")):
                return
            try:
                resource_type = str(response.request.resource_type)
            except Exception:
                resource_type = ""
            try:
                headers = response.headers
            except Exception:
                headers = {}
            content_type = str(headers.get("content-type") or headers.get("Content-Type") or "")
            interesting = "msn.com" in url.lower() or "akamaized" in url.lower() or resource_type in {"document", "stylesheet", "script", "image", "font", "xhr", "fetch"}
            if not interesting:
                return
            try:
                body = response.body()
            except Exception:
                return
            if not body or total_bytes + len(body) > MAX_RESPONSE_BODY_BYTES:
                return
            try:
                status = int(response.status)
            except Exception:
                status = 200
            responses.append(CapturedResponse(url=url, status=status, content_type=content_type, resource_type=resource_type, body=body, captured_at_utc=utc_now_iso()))
            total_bytes += len(body)

        page.on("response", on_response)

        # Try variants but retain the first that yields the article JSON endpoint.
        for attempt_url in url_variants(source_url):
            page.goto(attempt_url, wait_until="domcontentloaded", timeout=timeout_ms)
            page.wait_for_timeout(2500)
            try:
                page.wait_for_load_state("networkidle", timeout=8000)
            except Exception:
                pass

            # Remove consent/privacy where possible and trigger expansions, but V4 does not depend on visible DOM.
            for label in ("Reject all", "Reject All", "Accept all", "Accept All", "Agree", "I agree", "Save", "Confirm choices"):
                try:
                    loc = page.get_by_text(label, exact=False)
                    for i in range(min(loc.count(), 3)):
                        try:
                            loc.nth(i).click(timeout=800)
                            page.wait_for_timeout(500)
                        except Exception:
                            pass
                except Exception:
                    pass

            for label in ("Continue reading", "Expand article", "Read more", "Comments", "See comments", "Show comments", "Join the conversation"):
                try:
                    loc = page.get_by_text(label, exact=False)
                    for i in range(min(loc.count(), 4)):
                        try:
                            loc.nth(i).click(timeout=800)
                            page.wait_for_timeout(600)
                        except Exception:
                            pass
                except Exception:
                    pass

            for _ in range(max(1, scroll_passes)):
                try:
                    page.evaluate("window.scrollBy(0, Math.max(700, window.innerHeight * 0.85))")
                except Exception:
                    pass
                page.wait_for_timeout(550)

            article, _resp = find_article_detail(responses)
            if article:
                source_url = attempt_url
                break

        try:
            page.evaluate("window.scrollTo(0, 0)")
        except Exception:
            pass
        page.wait_for_timeout(600)
        try:
            final_dom = page.content()
        except Exception:
            final_dom = ""
        try:
            final_text = str(page.locator("body").inner_text(timeout=3000))
        except Exception:
            final_text = ""
        try:
            title = page.title()
        except Exception:
            title = ""
        try:
            shot = output_root / "screenshots" / "dynamic-recapture-v4-final-full-page.png"
            shot.parent.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(shot), full_page=True, timeout=15000)
            screenshot_hash = sha256_file(shot)
        except Exception:
            screenshot_hash = ""
        browser.close()
    return responses, final_dom, final_text, bool(article_terms_verified(final_text) or article_terms_verified(final_dom)), screenshot_hash


def run_dynamic_replay_recapture_v4(source_url: str | None, output_root: str | Path, headless: bool, timeout_ms: int, scroll_passes: int, dry_run: bool = False) -> dict[str, Any]:
    output_root = Path(output_root)
    source_url = canonical_article_url(source_url or try_default_msn_url())
    errors = dependency_errors()
    if dry_run:
        return {"status": "DYNAMIC_RECAPTURE_V4_DRY_RUN", "source_url": source_url, "output_root": str(output_root), "dependency_errors": errors, "dynamic_replay_success_claimed": False}
    output_root.mkdir(parents=True, exist_ok=True)
    if errors:
        result = {"status": STATUS_DEPENDENCY_BLOCKED, "source_url": source_url, "output_root": str(output_root), "dependency_errors": errors, "dynamic_replay_success_claimed": False, "manual_replayweb_visual_review_required": False}
        write_text(output_root / "dynamic-recapture-v4-manifest.json", json.dumps(result, indent=2, sort_keys=True) + "\n")
        return result

    try:
        responses, final_dom, final_text, visible_dom_verified, screenshot_hash = run_browser_capture(source_url, output_root, headless, timeout_ms, scroll_passes)
    except Exception as exc:
        result = {"status": STATUS_FAILED, "source_url": source_url, "output_root": str(output_root), "error": f"{type(exc).__name__}: {exc}", "dynamic_replay_success_claimed": False, "manual_replayweb_visual_review_required": False}
        write_text(output_root / "dynamic-recapture-v4-manifest.json", json.dumps(result, indent=2, sort_keys=True) + "\n")
        return result

    article, article_response = find_article_detail(responses)
    social_summary, social_response = find_social_summary(responses)
    response_rows = [r.row() for r in responses]
    write_text(output_root / "captured-network-responses-v4.json", json.dumps(response_rows, indent=2, sort_keys=True) + "\n")
    write_text(output_root / "rendered-visible-dom-v4.html", final_dom)
    write_text(output_root / "rendered-visible-text-v4.txt", final_text)

    if not article or not article_response:
        result = {
            "schema_version": SCHEMA_VERSION,
            "recapture_id": RECAPTURE_ID,
            "status": STATUS_BLOCKED,
            "source_url": source_url,
            "output_root": str(output_root),
            "visible_dom_article_verified": visible_dom_verified,
            "captured_network_response_count": len(responses),
            "dynamic_replay_success_claimed": False,
            "manual_replayweb_visual_review_required": False,
        }
        write_text(output_root / "dynamic-recapture-v4-manifest.json", json.dumps(result, indent=2, sort_keys=True) + "\n")
        return result

    materialized_html = build_materialized_article_html(
        source_url=source_url,
        article=article,
        article_response=article_response,
        social_summary=social_summary,
        social_response=social_response,
        visible_body_text=final_text,
        dom_verified=visible_dom_verified,
    )
    article_text = text_from_html(str(article.get("body") or ""))
    materialized_article_verified = article_terms_verified(article_text)
    html_path = output_root / "network-materialized-article-v4.html"
    html_hash = write_text(html_path, materialized_html)
    article_json_path = output_root / "captured-article-detail-v4.json"
    article_json_hash = write_text(article_json_path, json.dumps(article, indent=2, sort_keys=True) + "\n")
    social_json_path = output_root / "captured-community-summary-v4.json"
    social_json_hash = write_text(social_json_path, json.dumps(social_summary or {}, indent=2, sort_keys=True) + "\n")

    ts = utc_now_iso()
    warc_bytes = build_warc(source_url, materialized_html, responses, ts)
    warc_path = output_root / "archive" / "dynamic-network-materialized-v4.warc"
    warc_hash = write_bytes(warc_path, warc_bytes)
    warc_gz, members = gzip_warc_members(warc_bytes)
    warc_gz_path = output_root / "archive" / "dynamic-network-materialized-v4.warc.gz"
    warc_gz_hash = write_bytes(warc_gz_path, warc_gz)
    wacz_path = output_root / "archive" / "dynamic-network-materialized-v4.wacz"
    title = str(article.get("title") or "MSN dynamic network recapture V4")
    wacz = write_wacz(wacz_path, source_url, title, warc_gz, members, ts)

    result = {
        "schema_version": SCHEMA_VERSION,
        "recapture_id": RECAPTURE_ID,
        "status": STATUS_READY,
        "candidate_type": "network_materialized_dynamic_article",
        "source_url": source_url,
        "output_root": str(output_root),
        "title": title,
        "visible_dom_article_verified": visible_dom_verified,
        "network_detail_article_verified": materialized_article_verified,
        "article_json_endpoint": article_response.url,
        "article_json_sha256": article_response.body_sha256,
        "community_summary_endpoint": social_response.url if social_response else "",
        "community_summary_sha256": social_response.body_sha256 if social_response else "",
        "comment_summary_total_count": ((social_summary or {}).get("commentSummary") or {}).get("totalCount") if isinstance((social_summary or {}).get("commentSummary"), dict) else None,
        "actual_comment_text_captured": False,
        "captured_network_response_count": len(responses),
        "warc_record_count": len(members),
        "materialized_html_path": str(html_path),
        "materialized_html_sha256": html_hash,
        "article_json_path": str(article_json_path),
        "article_json_sha256": article_json_hash,
        "social_json_path": str(social_json_path),
        "social_json_sha256": social_json_hash,
        "screenshot_sha256": screenshot_hash,
        "warc_path": str(warc_path),
        "warc_sha256": warc_hash,
        "warc_gz_path": str(warc_gz_path),
        "warc_gz_sha256": warc_gz_hash,
        "wacz_path": str(wacz_path),
        "wacz_sha256": wacz["sha256"],
        "wacz_main_surt_key": wacz["main_surt_key"],
        "wacz_cdx_timestamp": wacz["cdx_timestamp"],
        "dynamic_replay_success_claimed": False,
        "manual_replayweb_visual_review_required": True,
    }
    manifest_path = output_root / "dynamic-recapture-v4-manifest.json"
    result["manifest_path"] = str(manifest_path)
    write_text(manifest_path, json.dumps(result, indent=2, sort_keys=True) + "\n")
    result["manifest_sha256"] = sha256_file(manifest_path)
    write_text(manifest_path, json.dumps(result, indent=2, sort_keys=True) + "\n")
    return result


def render_result_lines(result: Mapping[str, Any]) -> list[str]:
    lines = [
        f"DYNAMIC_RECAPTURE_V4_STATUS={result.get('status')}",
        f"DYNAMIC_RECAPTURE_V4_OUTPUT_ROOT={result.get('output_root')}",
        f"DYNAMIC_RECAPTURE_V4_SOURCE_URL={result.get('source_url')}",
        f"CANDIDATE_TYPE={result.get('candidate_type')}",
        f"VISIBLE_DOM_ARTICLE_VERIFIED={result.get('visible_dom_article_verified')}",
        f"NETWORK_DETAIL_ARTICLE_VERIFIED={result.get('network_detail_article_verified')}",
        f"COMMENT_SUMMARY_TOTAL_COUNT={result.get('comment_summary_total_count')}",
        f"ACTUAL_COMMENT_TEXT_CAPTURED={result.get('actual_comment_text_captured')}",
        f"CAPTURED_NETWORK_RESPONSE_COUNT={result.get('captured_network_response_count')}",
        f"WARC_RECORD_COUNT={result.get('warc_record_count')}",
        f"WACZ_CDX_TIMESTAMP={result.get('wacz_cdx_timestamp')}",
        f"DYNAMIC_REPLAY_SUCCESS_CLAIMED={result.get('dynamic_replay_success_claimed')}",
        f"MANUAL_REPLAYWEB_VISUAL_REVIEW_REQUIRED={result.get('manual_replayweb_visual_review_required')}",
    ]
    for key, label in [
        ("materialized_html_path", "NETWORK_MATERIALIZED_HTML_V4"),
        ("article_json_path", "CAPTURED_ARTICLE_JSON_V4"),
        ("social_json_path", "CAPTURED_COMMUNITY_SUMMARY_V4"),
        ("warc_gz_path", "DYNAMIC_RECAPTURE_V4_WARC_GZ"),
        ("wacz_path", "DYNAMIC_RECAPTURE_V4_WACZ"),
        ("manifest_path", "DYNAMIC_RECAPTURE_V4_MANIFEST"),
    ]:
        if result.get(key):
            lines.append(f"{label}={result.get(key)}")
    if result.get("status") == STATUS_READY:
        lines.append("DYNAMIC_RECAPTURE_V4_READY_FOR_MANUAL_REPLAYWEB_TEST")
    elif result.get("status") == STATUS_BLOCKED:
        lines.append("DYNAMIC_RECAPTURE_V4_BLOCKED_NO_REPLAY_ACCEPTANCE_CLAIM")
    if result.get("error"):
        lines.append("ERROR=" + str(result.get("error")))
    return lines


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-url", default="")
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--timeout-ms", type=int, default=45000)
    parser.add_argument("--scroll-passes", type=int, default=8)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    if args.dry_run:
        result = {"status": "DYNAMIC_RECAPTURE_V4_DRY_RUN", "source_url": canonical_article_url(args.source_url or try_default_msn_url()), "output_root": args.output_root, "dependency_errors": dependency_errors(), "dynamic_replay_success_claimed": False}
    else:
        result = run_dynamic_replay_recapture_v4(args.source_url or None, args.output_root, bool(args.headless), int(args.timeout_ms), int(args.scroll_passes))
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        for line in render_result_lines(result):
            print(line)
    return 0 if result.get("status") != STATUS_FAILED else 2


if __name__ == "__main__":
    raise SystemExit(main())
