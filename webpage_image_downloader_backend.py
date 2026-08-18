from __future__ import annotations

import atexit
import hashlib
import html
import json
import mimetypes
import os
import queue
import re
import threading
import time
from dataclasses import asdict, dataclass, field, is_dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qsl, unquote, urljoin, urlsplit, urlunsplit
from urllib.request import Request, urlopen

from source_resource_state import (
    MEDIA_INTAKE_SCHEMA_VERSION,
    RESOURCE_KIND_IMAGE,
    MediaResourceFilterState,
    ResourceSelectionDialogState,
    SourceResourceItem,
    SourceResourceRowState,
)

WEBPAGE_IMAGE_DISCOVERY_SCHEMA_VERSION = "webpage-image-discovery-v77g"
WEBPAGE_IMAGE_DOWNLOAD_SCHEMA_VERSION = "webpage-image-download-v77g"

WEBPAGE_IMAGE_DOWNLOAD_STATUS_READY = "ready"
WEBPAGE_IMAGE_DOWNLOAD_STATUS_NO_RESOURCES = "no_resources"
WEBPAGE_IMAGE_DOWNLOAD_STATUS_NO_SELECTION = "no_selection"
WEBPAGE_IMAGE_DOWNLOAD_STATUS_FAILED = "failed"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0 Safari/537.36 YTCE-Source-Preservation/1.0"
)
IMAGE_EXTENSIONS = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".gif": "image/gif",
    ".bmp": "image/bmp",
    ".tif": "image/tiff",
    ".tiff": "image/tiff",
    ".svg": "image/svg+xml",
    ".avif": "image/avif",
}
PROXY_URL_KEYS = (
    "url",
    "u",
    "uri",
    "href",
    "img",
    "imgurl",
    "image",
    "media",
    "src",
    "source",
    "original",
)
CSS_URL_RE = re.compile(r"url\((?P<quote>['\"]?)(?P<url>.*?)(?P=quote)\)", re.IGNORECASE | re.S)
META_IMAGE_KEYS = {
    "og:image",
    "og:image:url",
    "og:image:secure_url",
    "twitter:image",
    "twitter:image:src",
    "image",
    "thumbnail",
}


@dataclass(frozen=True)
class DiscoveredWebpageImage:
    url: str
    source_type: str
    display_name: str = ""
    width: int = 0
    height: int = 0
    alt_text: str = ""
    from_link: bool = False
    page_url: str = ""


@dataclass(frozen=True)
class WebpageImageDiscoveryResult:
    source_url: str
    final_url: str = ""
    resources: tuple[SourceResourceItem, ...] = ()
    candidate_count: int = 0
    deduplicated_count: int = 0
    warnings: tuple[str, ...] = ()
    fetched_html_bytes: int = 0
    network_actions_performed: str = "one page HTML fetch only"
    downloads_performed: str = "none"
    safety_flags: dict[str, bool] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class WebpageImageDownloadResult:
    status: str
    message: str
    source_row_id: str = ""
    resources_selected: int = 0
    resources_downloaded: int = 0
    resources_failed: int = 0
    downloaded_files: tuple[str, ...] = ()
    failed_urls: tuple[str, ...] = ()
    manifest_json: str = ""
    manifest_jsonl: str = ""
    output_dir: str = ""
    network_actions_performed: str = "selected image HTTP GET only"
    downloads_performed: str = "selected accessible images only"
    safety_flags: dict[str, bool] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


def _value_for_dict(value: Any) -> Any:
    if is_dataclass(value):
        return {key: _value_for_dict(item) for key, item in asdict(value).items()}
    if isinstance(value, Mapping):
        return {str(key): _value_for_dict(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_value_for_dict(item) for item in value]
    return value


def webpage_image_safety_flags() -> dict[str, bool]:
    return {
        "browser_launch_performed": False,
        "webpage_html_fetch_performed": True,
        "media_download_performed": True,
        "recording_performed": False,
        "drm_circumvention_performed": False,
        "hidden_protected_stream_extraction_performed": False,
        "captcha_solver_used": False,
        "credential_automation_performed": False,
        "proxy_or_evasion_performed": False,
        "forced_rate_limit_bypass_performed": False,
        "write_actions_performed": False,
    }


def _discovery_safety_flags() -> dict[str, bool]:
    flags = webpage_image_safety_flags()
    flags["media_download_performed"] = False
    flags["write_actions_performed"] = False
    return flags


def _is_http_url(value: str) -> bool:
    try:
        parsed = urlsplit(value)
    except Exception:
        return False
    return parsed.scheme.lower() in {"http", "https"} and bool(parsed.netloc)


def _strip_fragment(value: str) -> str:
    parsed = urlsplit(value)
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, parsed.query, ""))


def _looks_like_data_or_unsafe(value: str) -> bool:
    lowered = (value or "").strip().lower()
    return (
        not lowered
        or lowered.startswith("data:")
        or lowered.startswith("blob:")
        or lowered.startswith("javascript:")
        or lowered.startswith("mailto:")
        or lowered.startswith("tel:")
        or lowered.startswith("#")
    )


def _extension_from_url(value: str) -> str:
    try:
        path = unquote(urlsplit(value).path)
    except Exception:
        return ""
    suffix = Path(path).suffix.lower()
    return suffix if suffix in IMAGE_EXTENSIONS else ""


def _mime_from_extension(extension: str) -> str:
    if extension in IMAGE_EXTENSIONS:
        return IMAGE_EXTENSIONS[extension]
    guessed, _encoding = mimetypes.guess_type("file" + extension)
    return guessed or ""


def _safe_int(value: object) -> int:
    try:
        text = str(value or "").strip().lower().replace("px", "")
        if not text or "%" in text:
            return 0
        return max(0, int(float(text)))
    except Exception:
        return 0


def _split_srcset(value: str) -> tuple[str, ...]:
    # Good enough for normal srcset entries: "url 640w, url2 2x".
    # URLs containing literal commas are uncommon and still remain harmless if skipped later.
    urls: list[str] = []
    for part in str(value or "").split(","):
        token = part.strip().split()
        if token:
            urls.append(token[0].strip())
    return tuple(url for url in urls if url)


def _normalize_candidate_url(page_url: str, candidate_url: str) -> str:
    value = html.unescape(str(candidate_url or "").strip().strip("'\""))
    if _looks_like_data_or_unsafe(value):
        return ""
    value = urljoin(page_url, value)
    value = _strip_fragment(value)
    if not _is_http_url(value):
        return ""
    return _unwrap_proxy_image_url(value)


def _unwrap_proxy_image_url(value: str, *, depth: int = 0) -> str:
    if depth > 2 or not _is_http_url(value):
        return value
    parsed = urlsplit(value)
    for key, raw in parse_qsl(parsed.query, keep_blank_values=True):
        if key.lower() not in PROXY_URL_KEYS:
            continue
        candidate = unquote(raw or "").strip()
        if candidate.lower().startswith(("http://", "https://")):
            return _unwrap_proxy_image_url(_strip_fragment(candidate), depth=depth + 1)
    return value


def _image_dedupe_key(value: str) -> str:
    parsed = urlsplit(value)
    host = parsed.netloc.lower()
    path = unquote(parsed.path or "/")
    query_pairs = []
    for key, val in parse_qsl(parsed.query, keep_blank_values=True):
        lowered = key.lower()
        if lowered.startswith("utm_") or lowered in {"width", "height", "w", "h", "resize", "quality"}:
            continue
        query_pairs.append((key, val))
    return urlunsplit((parsed.scheme.lower(), host, path, "&".join(f"{k}={v}" for k, v in query_pairs), ""))


def _filename_from_url(url: str, fallback: str) -> str:
    try:
        name = Path(unquote(urlsplit(url).path)).name
    except Exception:
        name = ""
    name = re.sub(r"[\\/:*?\"<>|]+", "_", name).strip(" .")
    if not name:
        name = fallback
    suffix = Path(name).suffix.lower()
    if suffix not in IMAGE_EXTENSIONS:
        ext = _extension_from_url(url) or ".jpg"
        name = f"{Path(name).stem or fallback}{ext}"
    return name[:160]


class _ImageCandidateParser(HTMLParser):
    def __init__(self, page_url: str) -> None:
        super().__init__(convert_charrefs=True)
        self.page_url = page_url
        self.candidates: list[DiscoveredWebpageImage] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr = {str(key).lower(): value or "" for key, value in attrs}
        tag = tag.lower()

        def add(raw_url: str, source_type: str, *, from_link: bool = False) -> None:
            normalized = _normalize_candidate_url(self.page_url, raw_url)
            if not normalized:
                return
            self.candidates.append(
                DiscoveredWebpageImage(
                    url=normalized,
                    source_type=source_type,
                    display_name=(attr.get("alt") or attr.get("title") or "").strip(),
                    width=_safe_int(attr.get("width")),
                    height=_safe_int(attr.get("height")),
                    alt_text=(attr.get("alt") or "").strip(),
                    from_link=from_link,
                    page_url=self.page_url,
                )
            )

        if tag == "img":
            for key in (
                "src",
                "data-src",
                "data-original",
                "data-lazy-src",
                "data-full",
                "data-url",
                "data-image",
            ):
                if attr.get(key):
                    add(attr[key], f"img:{key}")
            for key in ("srcset", "data-srcset"):
                for srcset_url in _split_srcset(attr.get(key, "")):
                    add(srcset_url, f"img:{key}")
        elif tag == "source":
            for key in ("srcset", "data-srcset", "src"):
                for srcset_url in _split_srcset(attr.get(key, "")):
                    add(srcset_url, f"picture:{key}")
        elif tag == "a" and attr.get("href"):
            href = attr["href"]
            normalized = _normalize_candidate_url(self.page_url, href)
            if normalized and _extension_from_url(normalized):
                self.candidates.append(
                    DiscoveredWebpageImage(
                        url=normalized,
                        source_type="link:href",
                        display_name=(attr.get("title") or "").strip(),
                        width=0,
                        height=0,
                        alt_text="",
                        from_link=True,
                        page_url=self.page_url,
                    )
                )
        elif tag == "meta":
            key = (attr.get("property") or attr.get("name") or attr.get("itemprop") or "").lower()
            if key in META_IMAGE_KEYS and attr.get("content"):
                add(attr["content"], f"meta:{key}")
        elif tag == "link":
            rel = (attr.get("rel") or "").lower()
            as_value = (attr.get("as") or "").lower()
            if attr.get("href") and ("image" in rel or as_value == "image"):
                add(attr["href"], f"link:{rel or as_value}")

        style = attr.get("style", "")
        if style:
            for match in CSS_URL_RE.finditer(style):
                add(match.group("url"), f"{tag}:style")


def _extract_css_urls(page_url: str, html_text: str) -> tuple[DiscoveredWebpageImage, ...]:
    out: list[DiscoveredWebpageImage] = []
    for match in CSS_URL_RE.finditer(html_text or ""):
        normalized = _normalize_candidate_url(page_url, match.group("url"))
        if not normalized:
            continue
        if not _extension_from_url(normalized):
            continue
        out.append(
            DiscoveredWebpageImage(
                url=normalized,
                source_type="css:url",
                display_name="",
                from_link=False,
                page_url=page_url,
            )
        )
    return tuple(out)


def _fetch_html(url: str, *, timeout: float = 20.0) -> tuple[str, str, int]:
    request = Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        },
    )
    with urlopen(request, timeout=timeout) as response:  # nosec - user supplied visible source URL
        final_url = getattr(response, "url", url)
        raw = response.read(5_000_000)
        content_type = response.headers.get_content_charset() or "utf-8"
    return raw.decode(content_type, errors="replace"), final_url, len(raw)


def _source_resource_items_from_candidates(
    candidates: Sequence[DiscoveredWebpageImage],
    *,
    row_id: str = "",
    max_images: int = 250,
    provenance: str = "webpage image discovery",
    status: str = "discovered",
) -> tuple[tuple[SourceResourceItem, ...], tuple[str, ...]]:
    '''Convert discovered browser/static candidates into source resource items.'''

    warnings: list[str] = []
    seen: set[str] = set()
    resources: list[SourceResourceItem] = []
    for candidate in candidates:
        key = _image_dedupe_key(candidate.url)
        if key in seen:
            continue
        seen.add(key)
        ext = _extension_from_url(candidate.url) or ".jpg"
        mime = _mime_from_extension(ext)
        digest = hashlib.sha1(candidate.url.encode("utf-8", errors="ignore")).hexdigest()[:14]
        display_name = candidate.display_name or _filename_from_url(candidate.url, f"image_{len(resources)+1:03d}{ext}")
        resources.append(
            SourceResourceItem(
                resource_id=f"{row_id or 'webpage'}:image:{digest}",
                source_row_id=row_id,
                resource_kind=RESOURCE_KIND_IMAGE,
                reference_url=candidate.url,
                canonical_url=candidate.url,
                display_name=display_name,
                media_type=candidate.source_type,
                mime_type=mime,
                extension=ext,
                width=candidate.width,
                height=candidate.height,
                duration_seconds=0.0,
                bitrate_or_quality="",
                animated=ext == ".gif",
                thumbnail_reference=candidate.url,
                from_link=candidate.from_link,
                status=status,
                selectable=True,
                warning="",
                provenance=provenance,
            )
        )
        if len(resources) >= max_images:
            warnings.append(f"Image discovery stopped after max_images={max_images}.")
            break
    return tuple(resources), tuple(warnings)


def discover_webpage_images(
    source_url: str,
    *,
    row_id: str = "",
    html_text: str = "",
    fetcher: Callable[[str], tuple[str, str, int]] | None = None,
    max_images: int = 250,
) -> WebpageImageDiscoveryResult:
    '''Discover image candidates from a normal accessible webpage.

    This static path fetches only the source page HTML unless ``html_text`` is supplied
    by a test/caller. Browser-rendered fallback lives in ``discover_webpage_images_for_row``.
    '''

    if not _is_http_url(source_url):
        return WebpageImageDiscoveryResult(
            source_url=source_url,
            warnings=("Source URL is not an http/https webpage URL.",),
            safety_flags=_discovery_safety_flags(),
        )

    warnings: list[str] = []
    final_url = source_url
    fetched_bytes = 0
    if not html_text:
        try:
            if fetcher is not None:
                html_text, final_url, fetched_bytes = fetcher(source_url)
            else:
                html_text, final_url, fetched_bytes = _fetch_html(source_url)
        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            return WebpageImageDiscoveryResult(
                source_url=source_url,
                final_url=final_url,
                warnings=(f"Could not fetch webpage HTML for image discovery: {exc}",),
                safety_flags=_discovery_safety_flags(),
            )

    parser = _ImageCandidateParser(final_url or source_url)
    try:
        parser.feed(html_text or "")
    except Exception as exc:
        warnings.append(f"HTML parser warning: {exc}")
    candidates = list(parser.candidates)
    candidates.extend(_extract_css_urls(final_url or source_url, html_text or ""))
    resources, resource_warnings = _source_resource_items_from_candidates(
        candidates,
        row_id=row_id,
        max_images=max_images,
        provenance="static HTML webpage image discovery",
        status="discovered_static_html",
    )
    warnings.extend(resource_warnings)

    return WebpageImageDiscoveryResult(
        source_url=source_url,
        final_url=final_url,
        resources=resources,
        candidate_count=len(candidates),
        deduplicated_count=len(resources),
        warnings=tuple(warnings),
        fetched_html_bytes=fetched_bytes,
        network_actions_performed="one page static HTML fetch only",
        safety_flags=_discovery_safety_flags(),
    )


_RENDERED_IMAGE_DISCOVERY_SCRIPT = r'''
async (options) => {
  const waitForIdleDOM = Number.isFinite(options?.waitForIdleDOM) ? options.waitForIdleDOM : 450;
  const maxCandidates = Number.isFinite(options?.maxCandidates) ? options.maxCandidates : 900;
  const out = [];
  const seen = new Set();
  const imageUrlRegex = /(?:([^:\/\?#]+):)?(?:\/\/([^\/\?#]*))?([^?#]*\.(?:bmp|gif|ico|jfif|jpe?g|png|svg|tiff?|webp|avif))(?:\?([^#]*))?(?:#(.*))?/i;

  function stripHash(value) {
    const hashIndex = String(value || '').indexOf('#');
    return hashIndex >= 0 ? String(value || '').slice(0, hashIndex) : String(value || '');
  }

  function absoluteUrl(raw) {
    if (!raw) return '';
    const text = stripHash(String(raw).trim().replace(/^url\(["']?|["']?\)$/g, ''));
    if (!text || /^(?:data|blob|javascript|mailto|tel):/i.test(text) || text === '#') return '';
    try {
      const parsed = new URL(text, document.baseURI || window.location.href);
      if (!/^https?:$/i.test(parsed.protocol)) return '';
      parsed.hash = '';
      return parsed.href;
    } catch (_error) {
      return '';
    }
  }

  function textForElement(element) {
    try {
      return (
        element.getAttribute?.('alt') ||
        element.getAttribute?.('title') ||
        element.getAttribute?.('aria-label') ||
        element.getAttribute?.('data-title') ||
        ''
      ).trim();
    } catch (_error) {
      return '';
    }
  }

  function dimsForElement(element) {
    let width = 0;
    let height = 0;
    try {
      width = Number(element.naturalWidth || element.videoWidth || element.width || element.getAttribute?.('width') || 0) || 0;
      height = Number(element.naturalHeight || element.videoHeight || element.height || element.getAttribute?.('height') || 0) || 0;
      if ((!width || !height) && element.getBoundingClientRect) {
        const rect = element.getBoundingClientRect();
        width = width || Math.round(rect.width || 0);
        height = height || Math.round(rect.height || 0);
      }
    } catch (_error) {}
    return { width: Math.max(0, Math.round(width)), height: Math.max(0, Math.round(height)) };
  }

  function push(rawUrl, sourceType, element, fromLink = false) {
    const url = absoluteUrl(rawUrl);
    if (!url || seen.has(url) || out.length >= maxCandidates) return;
    seen.add(url);
    const dims = element ? dimsForElement(element) : { width: 0, height: 0 };
    out.push({
      url,
      sourceType: sourceType || 'rendered',
      displayName: element ? textForElement(element) : '',
      width: dims.width,
      height: dims.height,
      altText: element?.getAttribute?.('alt') || '',
      fromLink: !!fromLink,
      pageUrl: window.location.href,
    });
  }

  function splitSrcset(value) {
    return String(value || '')
      .split(',')
      .map((part) => part.trim().split(/\s+/)[0])
      .filter(Boolean)
      .map(stripHash);
  }

  function extractStyleUrls(value) {
    const urls = [];
    const regex = /url\(["']?([^"')]+)["']?\)/g;
    let match;
    while ((match = regex.exec(String(value || ''))) !== null) urls.push(match[1]);
    return urls;
  }

  function collectRoots(rootDocument) {
    const roots = [rootDocument];
    for (let index = 0; index < roots.length; index++) {
      const root = roots[index];
      try {
        root.querySelectorAll('*').forEach((element) => {
          if (element.shadowRoot) roots.push(element.shadowRoot);
        });
      } catch (_error) {}
    }
    return roots;
  }

  function collectFromElement(element) {
    const tag = String(element.tagName || '').toLowerCase();
    if (tag === 'img') {
      push(element.currentSrc || element.src, 'rendered:img:currentSrc', element, false);
      ['src', 'data-src', 'data-original', 'data-lazy-src', 'data-full', 'data-url', 'data-image', 'data-thumb', 'data-thumbnail'].forEach((name) => push(element.getAttribute?.(name), `rendered:img:${name}`, element, false));
      ['srcset', 'data-srcset'].forEach((name) => splitSrcset(element.getAttribute?.(name)).forEach((url) => push(url, `rendered:img:${name}`, element, false)));
      return;
    }
    if (tag === 'source') {
      ['srcset', 'data-srcset', 'src'].forEach((name) => splitSrcset(element.getAttribute?.(name)).forEach((url) => push(url, `rendered:picture:${name}`, element, false)));
      return;
    }
    if (tag === 'image' || tag === 'use') {
      ['href', 'xlink:href'].forEach((name) => push(element.getAttribute?.(name), `rendered:svg:${name}`, element, false));
      return;
    }
    if (tag === 'a') {
      const href = element.href || element.getAttribute?.('href');
      if (imageUrlRegex.test(String(href || ''))) push(href, 'rendered:link:href', element, true);
    }
    try {
      const backgroundImage = window.getComputedStyle(element).backgroundImage;
      if (backgroundImage && backgroundImage !== 'none') {
        extractStyleUrls(backgroundImage).forEach((url) => push(url, 'rendered:css:background-image', element, false));
      }
    } catch (_error) {}
  }

  if (document.readyState !== 'complete') {
    await new Promise((resolve) => {
      window.addEventListener('load', resolve, { once: true });
      setTimeout(resolve, 1400);
    });
  }
  if (waitForIdleDOM >= 0) {
    await new Promise((resolve) => {
      let timer;
      const finish = () => {
        try { observer.disconnect(); } catch (_error) {}
        resolve();
      };
      const reset = () => {
        clearTimeout(timer);
        timer = setTimeout(finish, waitForIdleDOM);
      };
      const observer = new MutationObserver(reset);
      try { observer.observe(document.documentElement, { childList: true, subtree: true, attributes: false }); } catch (_error) {}
      reset();
    });
  }

  for (const root of collectRoots(document)) {
    try {
      root.querySelectorAll('img, picture source, svg image, svg use, a, [style], [class]').forEach(collectFromElement);
      root.querySelectorAll('meta[property], meta[name], meta[itemprop]').forEach((element) => {
        const key = String(element.getAttribute('property') || element.getAttribute('name') || element.getAttribute('itemprop') || '').toLowerCase();
        if (/image|thumbnail/.test(key)) push(element.getAttribute('content'), `rendered:meta:${key}`, element, false);
      });
      root.querySelectorAll('link[href]').forEach((element) => {
        const rel = String(element.getAttribute('rel') || '').toLowerCase();
        const asValue = String(element.getAttribute('as') || '').toLowerCase();
        if (rel.includes('image') || asValue === 'image' || rel.includes('preload')) push(element.getAttribute('href'), `rendered:link:${rel || asValue}`, element, false);
      });
    } catch (_error) {}
  }

  try {
    performance.getEntriesByType('resource').forEach((entry) => {
      const initiator = String(entry.initiatorType || '').toLowerCase();
      const name = String(entry.name || '');
      if (initiator === 'img' || initiator === 'image' || imageUrlRegex.test(name)) {
        push(name, `rendered:performance:${initiator || 'resource'}`, null, false);
      }
    });
  } catch (_error) {}

  return out;
}
'''


def _rendered_discovery_safety_flags() -> dict[str, bool]:
    flags = _discovery_safety_flags()
    flags["browser_launch_performed"] = True
    flags["webpage_html_fetch_performed"] = True
    flags["media_download_performed"] = False
    flags["write_actions_performed"] = False
    return flags


class _RenderedBrowserDiscoveryWorker:
    """Own a warm Playwright browser on one daemon thread.

    The browser extension is fast because discovery runs inside an already-loaded
    browser context. This worker mirrors that architecture for the desktop app:
    Playwright/Edge is launched once per app session, then each rendered image
    scan creates only a short-lived isolated context/page. Keeping all Playwright
    calls on this worker thread also avoids sync-Playwright thread-affinity issues.
    """

    def __init__(self) -> None:
        self._jobs: "queue.Queue[Any]" = queue.Queue()
        self._thread = threading.Thread(target=self._run, name="YTCEWebpageImageRenderedDiscovery", daemon=True)
        self._thread.start()

    def submit(
        self,
        source_url: str,
        *,
        timeout_ms: int,
        idle_ms: int,
        scroll_steps: int,
        max_candidates_per_frame: int,
    ) -> tuple[str, tuple[dict[str, Any], ...], tuple[str, ...]]:
        result_queue: "queue.Queue[tuple[str, tuple[dict[str, Any], ...], tuple[str, ...]]]" = queue.Queue(maxsize=1)
        self._jobs.put(
            {
                "source_url": source_url,
                "timeout_ms": timeout_ms,
                "idle_ms": idle_ms,
                "scroll_steps": scroll_steps,
                "max_candidates_per_frame": max_candidates_per_frame,
                "result_queue": result_queue,
            }
        )
        try:
            return result_queue.get(timeout=max(8.0, (timeout_ms / 1000.0) + 12.0))
        except queue.Empty:
            return source_url, (), ("Rendered browser discovery timed out waiting for the warm browser worker.",)

    def close(self) -> None:
        try:
            self._jobs.put_nowait(None)
        except Exception:
            pass

    def _open_warm_browser(self) -> tuple[Any, Any, tuple[str, ...]]:
        try:
            from playwright.sync_api import sync_playwright  # type: ignore
        except Exception as exc:
            return None, None, (f"Rendered browser discovery unavailable: Playwright is not importable ({exc}).",)

        playwright = sync_playwright().start()
        launch_errors: list[str] = []
        for launch_kwargs in (
            {"channel": "msedge", "headless": True},
            {"channel": "chrome", "headless": True},
            {"headless": True},
        ):
            try:
                browser = playwright.chromium.launch(**launch_kwargs)
                return playwright, browser, ()
            except Exception as exc:
                launch_errors.append(f"{launch_kwargs}: {exc}")
        try:
            playwright.stop()
        except Exception:
            pass
        return None, None, ("Rendered browser discovery could not launch Chromium/Edge: " + " | ".join(launch_errors[-2:]),)

    def _run(self) -> None:
        playwright = None
        browser = None
        launch_warnings: tuple[str, ...] = ()
        try:
            playwright, browser, launch_warnings = self._open_warm_browser()
            while True:
                job = self._jobs.get()
                if job is None:
                    break
                result_queue = job.get("result_queue")
                try:
                    if browser is None:
                        result = (str(job.get("source_url") or ""), (), launch_warnings)
                    else:
                        result = _rendered_browser_candidate_dicts_with_browser(
                            browser,
                            str(job.get("source_url") or ""),
                            timeout_ms=int(job.get("timeout_ms") or 14_000),
                            idle_ms=int(job.get("idle_ms") or 450),
                            scroll_steps=int(job.get("scroll_steps") or 4),
                            max_candidates_per_frame=int(job.get("max_candidates_per_frame") or 900),
                        )
                        if launch_warnings:
                            result = (result[0], result[1], launch_warnings + tuple(result[2]))
                except Exception as exc:
                    relaunch_warning = f"Rendered browser warm session was restarted after an error: {exc}"
                    try:
                        if browser is not None:
                            browser.close()
                    except Exception:
                        pass
                    browser = None
                    new_playwright, browser, relaunch_warnings = self._open_warm_browser()
                    if new_playwright is not None:
                        try:
                            if playwright is not None:
                                playwright.stop()
                        except Exception:
                            pass
                        playwright = new_playwright
                    if browser is None:
                        result = (str(job.get("source_url") or ""), (), (relaunch_warning,) + tuple(relaunch_warnings))
                    else:
                        try:
                            retry_result = _rendered_browser_candidate_dicts_with_browser(
                                browser,
                                str(job.get("source_url") or ""),
                                timeout_ms=int(job.get("timeout_ms") or 14_000),
                                idle_ms=int(job.get("idle_ms") or 450),
                                scroll_steps=int(job.get("scroll_steps") or 4),
                                max_candidates_per_frame=int(job.get("max_candidates_per_frame") or 900),
                            )
                            result = (retry_result[0], retry_result[1], (relaunch_warning,) + tuple(retry_result[2]))
                        except Exception as retry_exc:
                            result = (str(job.get("source_url") or ""), (), (relaunch_warning, f"Rendered browser retry failed: {retry_exc}"))
                try:
                    result_queue.put_nowait(result)
                except Exception:
                    pass
        finally:
            try:
                if browser is not None:
                    browser.close()
            except Exception:
                pass
            try:
                if playwright is not None:
                    playwright.stop()
            except Exception:
                pass


_RENDERED_DISCOVERY_WORKER_LOCK = threading.Lock()
_RENDERED_DISCOVERY_WORKER: _RenderedBrowserDiscoveryWorker | None = None


def _get_rendered_discovery_worker() -> _RenderedBrowserDiscoveryWorker:
    global _RENDERED_DISCOVERY_WORKER
    with _RENDERED_DISCOVERY_WORKER_LOCK:
        if _RENDERED_DISCOVERY_WORKER is None:
            _RENDERED_DISCOVERY_WORKER = _RenderedBrowserDiscoveryWorker()
        return _RENDERED_DISCOVERY_WORKER


def close_rendered_browser_discovery_worker() -> None:
    global _RENDERED_DISCOVERY_WORKER
    with _RENDERED_DISCOVERY_WORKER_LOCK:
        worker = _RENDERED_DISCOVERY_WORKER
        _RENDERED_DISCOVERY_WORKER = None
    if worker is not None:
        worker.close()


def prewarm_rendered_browser_discovery_worker() -> None:
    """Start the rendered discovery worker/browser before the first JS-heavy scan."""

    _get_rendered_discovery_worker()


atexit.register(close_rendered_browser_discovery_worker)


def _rendered_browser_candidate_dicts_with_browser(
    browser: Any,
    source_url: str,
    *,
    timeout_ms: int = 14_000,
    idle_ms: int = 450,
    scroll_steps: int = 4,
    max_candidates_per_frame: int = 900,
) -> tuple[str, tuple[dict[str, Any], ...], tuple[str, ...]]:
    warnings: list[str] = []
    final_url = source_url
    raw_candidates: list[dict[str, Any]] = []
    context = None
    try:
        context = browser.new_context(
            user_agent=USER_AGENT,
            viewport={"width": 1366, "height": 1400},
            locale="en-GB",
            ignore_https_errors=True,
        )
        page = context.new_page()
        try:
            page.goto(source_url, wait_until="domcontentloaded", timeout=timeout_ms)
        except Exception as exc:
            warnings.append(f"Rendered browser navigation warning: {exc}")
        try:
            page.wait_for_load_state("networkidle", timeout=min(3200, timeout_ms))
        except Exception:
            pass
        # Immediate scan gives extension-like first results; short scroll pass then catches lazy images.
        for frame in list(page.frames):
            try:
                frame_candidates = frame.evaluate(
                    _RENDERED_IMAGE_DISCOVERY_SCRIPT,
                    {"waitForIdleDOM": 60, "maxCandidates": max_candidates_per_frame},
                )
                if isinstance(frame_candidates, list):
                    raw_candidates.extend(item for item in frame_candidates if isinstance(item, dict))
            except Exception:
                pass
        for _step in range(max(0, scroll_steps)):
            try:
                page.evaluate("window.scrollBy(0, Math.max(window.innerHeight || 900, 900));")
                page.wait_for_timeout(180)
            except Exception:
                break
        try:
            page.evaluate("window.scrollTo(0, 0);")
            page.wait_for_timeout(80)
        except Exception:
            pass
        final_url = page.url or source_url
        for frame in list(page.frames):
            try:
                frame_candidates = frame.evaluate(
                    _RENDERED_IMAGE_DISCOVERY_SCRIPT,
                    {"waitForIdleDOM": idle_ms, "maxCandidates": max_candidates_per_frame},
                )
                if isinstance(frame_candidates, list):
                    raw_candidates.extend(item for item in frame_candidates if isinstance(item, dict))
            except Exception as exc:
                frame_url = ""
                try:
                    frame_url = frame.url
                except Exception:
                    frame_url = "frame"
                warnings.append(f"Rendered frame image scan skipped for {frame_url}: {exc}")
    finally:
        try:
            if context is not None:
                context.close()
        except Exception:
            pass
    return final_url, tuple(raw_candidates), tuple(warnings)


def _rendered_browser_candidate_dicts(
    source_url: str,
    *,
    timeout_ms: int = 14_000,
    idle_ms: int = 450,
    scroll_steps: int = 4,
    max_candidates_per_frame: int = 900,
) -> tuple[str, tuple[dict[str, Any], ...], tuple[str, ...]]:
    """Collect image URLs from a warm rendered browser DOM/resource table when available."""

    worker = _get_rendered_discovery_worker()
    return worker.submit(
        source_url,
        timeout_ms=timeout_ms,
        idle_ms=idle_ms,
        scroll_steps=scroll_steps,
        max_candidates_per_frame=max_candidates_per_frame,
    )

def discover_webpage_images_rendered(
    source_url: str,
    *,
    row_id: str = "",
    max_images: int = 250,
    timeout_ms: int = 14_000,
) -> WebpageImageDiscoveryResult:
    '''Discover image candidates from a rendered browser DOM/resource view.

    This mirrors the useful Image Downloader behaviour: execute image discovery inside a
    browser-loaded page so JS/lazy/MSN-style image candidates can be visible. It does not
    select/download images, solve challenges, use credentials, or bypass access controls.
    '''

    if not _is_http_url(source_url):
        return WebpageImageDiscoveryResult(
            source_url=source_url,
            warnings=("Source URL is not an http/https webpage URL.",),
            network_actions_performed="rendered browser discovery skipped",
            safety_flags=_rendered_discovery_safety_flags(),
        )

    final_url, raw_candidates, warnings = _rendered_browser_candidate_dicts(
        source_url,
        timeout_ms=timeout_ms,
    )
    candidates: list[DiscoveredWebpageImage] = []
    for raw in raw_candidates:
        normalized = _normalize_candidate_url(final_url or source_url, str(raw.get("url") or ""))
        if not normalized:
            continue
        candidates.append(
            DiscoveredWebpageImage(
                url=normalized,
                source_type=str(raw.get("sourceType") or "rendered:dom"),
                display_name=str(raw.get("displayName") or "").strip(),
                width=_safe_int(raw.get("width")),
                height=_safe_int(raw.get("height")),
                alt_text=str(raw.get("altText") or "").strip(),
                from_link=bool(raw.get("fromLink")),
                page_url=str(raw.get("pageUrl") or final_url or source_url),
            )
        )
    resources, resource_warnings = _source_resource_items_from_candidates(
        candidates,
        row_id=row_id,
        max_images=max_images,
        provenance="rendered browser webpage image discovery",
        status="discovered_rendered_browser",
    )
    all_warnings = tuple(warnings) + tuple(resource_warnings)
    return WebpageImageDiscoveryResult(
        source_url=source_url,
        final_url=final_url,
        resources=resources,
        candidate_count=len(candidates),
        deduplicated_count=len(resources),
        warnings=all_warnings,
        fetched_html_bytes=0,
        network_actions_performed="headless browser page load plus rendered DOM/resource image scan; no selected image download",
        safety_flags=_rendered_discovery_safety_flags(),
    )


def _merge_discovery_results(
    static_result: WebpageImageDiscoveryResult,
    rendered_result: WebpageImageDiscoveryResult,
    *,
    max_images: int = 250,
) -> WebpageImageDiscoveryResult:
    seen: set[str] = set()
    merged_resources: list[SourceResourceItem] = []
    for item in tuple(rendered_result.resources) + tuple(static_result.resources):
        key = _image_dedupe_key(item.reference_url or item.canonical_url)
        if key in seen:
            continue
        seen.add(key)
        merged_resources.append(item)
        if len(merged_resources) >= max_images:
            break
    warnings = tuple(static_result.warnings) + tuple(rendered_result.warnings)
    if len(merged_resources) >= max_images and len(tuple(rendered_result.resources) + tuple(static_result.resources)) > max_images:
        warnings += (f"Combined image discovery stopped after max_images={max_images}.",)
    flags = dict(static_result.safety_flags)
    flags.update(rendered_result.safety_flags)
    return WebpageImageDiscoveryResult(
        source_url=static_result.source_url,
        final_url=rendered_result.final_url or static_result.final_url,
        resources=tuple(merged_resources),
        candidate_count=static_result.candidate_count + rendered_result.candidate_count,
        deduplicated_count=len(merged_resources),
        warnings=warnings,
        fetched_html_bytes=static_result.fetched_html_bytes,
        network_actions_performed="static HTML fetch plus rendered browser DOM/resource scan; no selected image download",
        downloads_performed="none",
        safety_flags=flags,
    )


def _should_try_rendered_image_discovery(row: SourceResourceRowState, result: WebpageImageDiscoveryResult, *, html_text: str = "") -> bool:
    if html_text:
        return False
    url_text = " ".join(str(part or "").lower() for part in (row.raw_url, row.canonical_url, row.domain, result.final_url))
    js_heavy_markers = ("msn.com", "x.com", "twitter.com", "facebook.com", "instagram.com")
    return not result.resources or any(marker in url_text for marker in js_heavy_markers)


def discover_webpage_images_for_row(
    row: SourceResourceRowState,
    *,
    html_text: str = "",
    max_images: int = 250,
    rendered_fallback: bool = True,
) -> WebpageImageDiscoveryResult:
    static_result = discover_webpage_images(
        row.canonical_url or row.raw_url,
        row_id=row.row_id,
        html_text=html_text,
        max_images=max_images,
    )
    if not rendered_fallback or not _should_try_rendered_image_discovery(row, static_result, html_text=html_text):
        return static_result
    rendered_result = discover_webpage_images_rendered(
        row.canonical_url or row.raw_url,
        row_id=row.row_id,
        max_images=max_images,
    )
    if rendered_result.resources:
        return _merge_discovery_results(static_result, rendered_result, max_images=max_images)
    if not static_result.resources:
        return WebpageImageDiscoveryResult(
            source_url=static_result.source_url,
            final_url=rendered_result.final_url or static_result.final_url,
            resources=(),
            candidate_count=static_result.candidate_count + rendered_result.candidate_count,
            deduplicated_count=0,
            warnings=tuple(static_result.warnings) + tuple(rendered_result.warnings or ("Rendered browser image discovery found no candidates.",)),
            fetched_html_bytes=static_result.fetched_html_bytes,
            network_actions_performed="static HTML fetch plus attempted rendered browser DOM/resource scan; no selected image download",
            downloads_performed="none",
            safety_flags={**static_result.safety_flags, **rendered_result.safety_flags},
        )
    warnings = tuple(static_result.warnings) + tuple(rendered_result.warnings)
    if not warnings:
        warnings = ("Rendered browser image discovery found no additional candidates; using static HTML candidates.",)
    return WebpageImageDiscoveryResult(
        source_url=static_result.source_url,
        final_url=rendered_result.final_url or static_result.final_url,
        resources=static_result.resources,
        candidate_count=static_result.candidate_count + rendered_result.candidate_count,
        deduplicated_count=static_result.deduplicated_count,
        warnings=warnings,
        fetched_html_bytes=static_result.fetched_html_bytes,
        network_actions_performed="static HTML fetch plus attempted rendered browser DOM/resource scan; no selected image download",
        downloads_performed="none",
        safety_flags={**static_result.safety_flags, **rendered_result.safety_flags},
    )


def _safe_filename_stem(value: str) -> str:
    text = re.sub(r"[\\/:*?\"<>|]+", "_", str(value or "")).strip(" ._")
    text = re.sub(r"\s+", " ", text)
    return (text or "source").strip()[:80]


def _unique_path(directory: Path, filename: str) -> Path:
    candidate = directory / filename
    if not candidate.exists():
        return candidate
    stem = candidate.stem
    suffix = candidate.suffix
    for index in range(2, 10000):
        alt = directory / f"{stem}_{index}{suffix}"
        if not alt.exists():
            return alt
    raise FileExistsError(f"Could not allocate unique filename for {filename}")


def _filename_for_resource(
    row: SourceResourceRowState,
    item: SourceResourceItem,
    *,
    rename_files: bool,
    index: int,
) -> str:
    ext = item.extension if item.extension in IMAGE_EXTENSIONS else (_extension_from_url(item.reference_url) or ".jpg")
    if rename_files:
        source_stem = _safe_filename_stem(row.display_title or row.title or row.domain)
        return f"{source_stem}_image_{index:03d}{ext}"
    return _filename_from_url(item.reference_url or item.canonical_url, f"image_{index:03d}{ext}")


def _read_image_bytes(url: str, *, timeout: float = 30.0, max_bytes: int = 80_000_000) -> tuple[bytes, str, str]:
    request = Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
            "Referer": url,
        },
    )
    with urlopen(request, timeout=timeout) as response:  # nosec - selected user-visible image URL
        content_type = response.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
        final_url = getattr(response, "url", url)
        data = response.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise ValueError(f"Image exceeds max download size of {max_bytes} bytes.")
    return data, content_type, final_url


def _image_dimensions(path: Path) -> tuple[int, int]:
    try:
        from PIL import Image  # type: ignore

        with Image.open(path) as image:
            return int(image.width), int(image.height)
    except Exception:
        return 0, 0


def _selected_items(state: ResourceSelectionDialogState) -> tuple[SourceResourceItem, ...]:
    selected_ids = set(state.selected_resource_ids)
    return tuple(
        item
        for item in state.resources
        if item.resource_id in selected_ids and item.resource_kind == RESOURCE_KIND_IMAGE
    )


def _manifest_record(
    *,
    row: SourceResourceRowState,
    item: SourceResourceItem,
    local_path: Path,
    sha256: str,
    size: int,
    width: int,
    height: int,
    content_type: str,
    final_url: str,
) -> dict[str, Any]:
    media_url = item.reference_url or item.canonical_url
    return {
        "schema_version": MEDIA_INTAKE_SCHEMA_VERSION,
        "download_schema_version": WEBPAGE_IMAGE_DOWNLOAD_SCHEMA_VERSION,
        "source_url": row.raw_url,
        "page_url": row.canonical_url or row.raw_url,
        "media_url": media_url,
        "final_media_url": final_url or media_url,
        "source_unit_path": "",
        "user_declared_purpose": "source_preservation",
        "capture_kind": "downloaded_webpage_image",
        "capture_method": "selected_accessible_webpage_image_download",
        "media_position_start": "",
        "media_position_end": "",
        "local_file_path": str(local_path),
        "local_file_name": local_path.name,
        "local_file_extension": local_path.suffix.lower(),
        "local_file_size": size,
        "local_file_sha256": sha256,
        "local_file_present": True,
        "local_file_role": "downloaded_accessible_webpage_media",
        "content_type": content_type,
        "width": width,
        "height": height,
        "source_resource": _value_for_dict(item),
        "source_unit_attachment": {
            "attached_to_source_unit": False,
            "source_unit_path": "",
            "attachment_scope": "session_files_review_required",
        },
        "rendered_citation_metadata": {
            "source_url": row.raw_url,
            "page_url": row.canonical_url or row.raw_url,
            "media_url": media_url,
            "capture_kind": "downloaded_webpage_image",
            "capture_method": "selected_accessible_webpage_image_download",
            "user_declared_purpose": "source_preservation",
        },
        "human_mediated_access": {
            "required": False,
            "completed_by_user": False,
            "program_solved_challenge": False,
            "solver_service_used": False,
            "anti_detection_used": False,
        },
        "blocked_capture": {
            "blocked": False,
            "reason": "",
        },
        "safety_flags": webpage_image_safety_flags(),
    }


def download_selected_webpage_images(
    *,
    row: SourceResourceRowState,
    state: ResourceSelectionDialogState,
    output_dir: str | os.PathLike[str],
    filters: MediaResourceFilterState | None = None,
    max_bytes_per_file: int = 80_000_000,
) -> WebpageImageDownloadResult:
    """Download only explicitly selected accessible image resources.

    No browser automation, credential handling, CAPTCHA solving, proxy/evasion, DRM handling,
    or hidden stream extraction is performed.
    """

    items = _selected_items(state)
    if not items:
        return WebpageImageDownloadResult(
            status=WEBPAGE_IMAGE_DOWNLOAD_STATUS_NO_SELECTION,
            message="No webpage image resources were selected.",
            source_row_id=row.row_id,
            safety_flags=webpage_image_safety_flags(),
        )

    base_output = Path(output_dir).expanduser().resolve()
    target_dir = base_output
    filters = filters or MediaResourceFilterState()
    if filters.save_to_subfolder:
        target_dir = base_output / _safe_filename_stem(row.display_title or row.title or row.domain) / "Images"
    target_dir.mkdir(parents=True, exist_ok=True)

    records: list[dict[str, Any]] = []
    downloaded_files: list[str] = []
    failed_urls: list[str] = []

    for index, item in enumerate(items, start=1):
        url = item.reference_url or item.canonical_url
        if not _is_http_url(url):
            failed_urls.append(url)
            continue
        try:
            data, content_type, final_url = _read_image_bytes(
                url,
                max_bytes=max_bytes_per_file,
            )
            if content_type and not content_type.startswith("image/"):
                # Some CDNs omit/lie about content type; allow known image extension, reject obvious HTML.
                if not _extension_from_url(final_url or url):
                    raise ValueError(f"Downloaded resource is not an image: {content_type}")
            filename = _filename_for_resource(row, item, rename_files=filters.rename_files, index=index)
            ext = Path(filename).suffix.lower()
            if content_type and ext not in IMAGE_EXTENSIONS:
                guessed = mimetypes.guess_extension(content_type) or ext or ".jpg"
                if guessed == ".jpe":
                    guessed = ".jpg"
                filename = f"{Path(filename).stem}{guessed}"
            local_path = _unique_path(target_dir, filename)
            local_path.write_bytes(data)
            digest = hashlib.sha256(data).hexdigest()
            width, height = _image_dimensions(local_path)
            records.append(
                _manifest_record(
                    row=row,
                    item=item,
                    local_path=local_path,
                    sha256=digest,
                    size=len(data),
                    width=width or item.width,
                    height=height or item.height,
                    content_type=content_type,
                    final_url=final_url,
                )
            )
            downloaded_files.append(str(local_path))
            time.sleep(0.2)
        except Exception as exc:
            failed_urls.append(f"{url} :: {exc}")

    manifest_json = ""
    manifest_jsonl = ""
    if records:
        manifest_json_path = target_dir / "selected_webpage_image_download_manifest.json"
        manifest_jsonl_path = target_dir / "selected_webpage_image_download_manifest.jsonl"
        manifest_json_path.write_text(
            json.dumps(
                {
                    "schema_version": WEBPAGE_IMAGE_DOWNLOAD_SCHEMA_VERSION,
                    "source_url": row.raw_url,
                    "page_url": row.canonical_url or row.raw_url,
                    "downloaded": len(records),
                    "failed": len(failed_urls),
                    "records": records,
                    "safety_flags": webpage_image_safety_flags(),
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        manifest_jsonl_path.write_text(
            "\n".join(json.dumps(record, ensure_ascii=False) for record in records) + "\n",
            encoding="utf-8",
        )
        manifest_json = str(manifest_json_path)
        manifest_jsonl = str(manifest_jsonl_path)

    status = WEBPAGE_IMAGE_DOWNLOAD_STATUS_READY if records else WEBPAGE_IMAGE_DOWNLOAD_STATUS_FAILED
    message = (
        f"Downloaded {len(records)} selected webpage image(s)."
        if records
        else "No selected webpage images could be downloaded."
    )
    if failed_urls:
        message += f" Failed/skipped: {len(failed_urls)}."

    return WebpageImageDownloadResult(
        status=status,
        message=message,
        source_row_id=row.row_id,
        resources_selected=len(items),
        resources_downloaded=len(records),
        resources_failed=len(failed_urls),
        downloaded_files=tuple(downloaded_files),
        failed_urls=tuple(failed_urls),
        manifest_json=manifest_json,
        manifest_jsonl=manifest_jsonl,
        output_dir=str(target_dir),
        safety_flags=webpage_image_safety_flags(),
    )


if __name__ == "__main__":
    sample_html = """
    <html><head>
      <meta property="og:image" content="/og.jpg">
      <style>.hero{background-image:url('/hero.webp')}</style>
    </head><body>
      <picture><source srcset="/wide-800.jpg 800w, /wide-1600.jpg 1600w"></picture>
      <a href="/linked.png">image</a>
      <img src="/photo.jpg" width="640" height="480" alt="Photo">
    </body></html>
    """
    result = discover_webpage_images("https://example.com/article", row_id="row1", html_text=sample_html)
    assert result.deduplicated_count >= 5, result
    assert all(item.resource_kind == RESOURCE_KIND_IMAGE for item in result.resources)
    print("webpage_image_downloader_backend_test: PASS")
