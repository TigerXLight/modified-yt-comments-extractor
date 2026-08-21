from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from typing import Any
from urllib.parse import urljoin

from jdownloader_capability_router import build_jdownloader_capability_decision
from webpage_video_candidate_backend import (
    VIDEO_CANDIDATE_KIND_EMBED,
    VIDEO_CANDIDATE_KIND_FILE,
    VIDEO_CANDIDATE_KIND_STREAM,
    VIDEO_ROUTE_PREFERENCE,
    WebpageVideoCandidate,
    WebpageVideoDiscoveryResult,
    _candidate_id,
    _clean_url,
    _embed_link_is_plausible,
    _looks_like_media_url,
    _safe_int,
    classify_video_candidate_url,
)

VIDEO_DISCOVERY_METHOD_RENDERED_BROWSER = "rendered_browser_dom_network_media_probe"

RENDERED_VIDEO_PROBE_SCRIPT = r"""
(() => {
  const records = [];
  const pageThumbnailUrl = (() => {
    const meta = document.querySelector('meta[property="og:image"],meta[property="og:image:url"],meta[name="twitter:image"],meta[name="twitter:image:src"]');
    return meta ? (meta.getAttribute('content') || '') : '';
  })();
  const push = (tag, attr, url, extra = {}) => {
    if (!url || typeof url !== 'string') return;
    records.push({
      tag,
      attr,
      url,
      mime_type: extra.mime_type || extra.type || '',
      title: extra.title || '',
      thumbnail_url: extra.thumbnail_url || pageThumbnailUrl || '',
      width: Number(extra.width || 0) || 0,
      height: Number(extra.height || 0) || 0,
      detection_reason: extra.detection_reason || `${tag}[${attr}]`,
      initiator_type: extra.initiator_type || '',
    });
  };

  document.querySelectorAll('video,audio').forEach((el) => {
    push(el.tagName.toLowerCase(), 'currentSrc', el.currentSrc || '', {
      mime_type: el.type || '',
      title: el.getAttribute('title') || el.getAttribute('aria-label') || document.title || '',
      thumbnail_url: el.getAttribute('poster') || '',
      width: el.videoWidth || el.clientWidth || el.getAttribute('width') || 0,
      height: el.videoHeight || el.clientHeight || el.getAttribute('height') || 0,
      detection_reason: `${el.tagName.toLowerCase()} currentSrc after render`,
    });
    push(el.tagName.toLowerCase(), 'src', el.getAttribute('src') || '', {
      mime_type: el.getAttribute('type') || '',
      title: el.getAttribute('title') || el.getAttribute('aria-label') || document.title || '',
      thumbnail_url: el.getAttribute('poster') || '',
      width: el.videoWidth || el.clientWidth || el.getAttribute('width') || 0,
      height: el.videoHeight || el.clientHeight || el.getAttribute('height') || 0,
    });
  });

  document.querySelectorAll('source,track,a,link,iframe,embed').forEach((el) => {
    const tag = el.tagName.toLowerCase();
    const parentMedia = el.closest ? el.closest('video,audio') : null;
    const parentPoster = parentMedia ? (parentMedia.getAttribute('poster') || '') : '';
    ['src', 'href', 'data-src', 'data-url'].forEach((attr) => {
      const value = el.getAttribute(attr);
      push(tag, attr, value || '', {
        mime_type: el.getAttribute('type') || '',
        title: el.getAttribute('title') || el.getAttribute('aria-label') || el.textContent || document.title || '',
        thumbnail_url: parentPoster || pageThumbnailUrl || '',
        width: el.getAttribute('width') || el.clientWidth || (parentMedia ? (parentMedia.videoWidth || parentMedia.clientWidth || parentMedia.getAttribute('width') || 0) : 0),
        height: el.getAttribute('height') || el.clientHeight || (parentMedia ? (parentMedia.videoHeight || parentMedia.clientHeight || parentMedia.getAttribute('height') || 0) : 0),
      });
    });
  });

  document.querySelectorAll('meta').forEach((el) => {
    const propertyName = (el.getAttribute('property') || el.getAttribute('name') || '').toLowerCase();
    if (['og:video', 'og:video:url', 'og:video:secure_url', 'twitter:player', 'twitter:player:stream', 'og:image', 'og:image:url', 'twitter:image', 'twitter:image:src'].includes(propertyName)) {
      push('meta', 'content', el.getAttribute('content') || '', {
        mime_type: el.getAttribute('type') || '',
        title: document.title || '',
        detection_reason: `rendered meta ${propertyName}`,
      });
    }
  });

  try {
    performance.getEntriesByType('resource').forEach((entry) => {
      push('performance', 'name', entry.name || '', {
        initiator_type: entry.initiatorType || '',
        detection_reason: `performance resource ${entry.initiatorType || 'unknown'}`,
      });
    });
  } catch (_err) {}

  return {
    location_href: location.href,
    document_title: document.title || '',
    page_thumbnail_url: pageThumbnailUrl || '',
    records,
  };
})()
""".strip()


def _as_mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _iter_payload_records(payload: Any) -> Iterable[Mapping[str, Any]]:
    data = _as_mapping(payload)
    records = data.get("records", [])
    if isinstance(records, list):
        for item in records:
            if isinstance(item, Mapping):
                yield item
    for key, tag, attr in (
        ("network_urls", "network_response", "url"),
        ("response_urls", "network_response", "url"),
        ("performance_urls", "performance", "name"),
    ):
        values = data.get(key, [])
        if isinstance(values, list):
            for item in values:
                if isinstance(item, str):
                    yield {"tag": tag, "attr": attr, "url": item, "detection_reason": key}
                elif isinstance(item, Mapping):
                    record = dict(item)
                    record.setdefault("tag", tag)
                    record.setdefault("attr", attr)
                    record.setdefault("url", item.get("url") or item.get("name") or "")
                    record.setdefault("detection_reason", key)
                    yield record


def _record_url(record: Mapping[str, Any]) -> str:
    return str(record.get("url") or record.get("name") or record.get("src") or record.get("href") or "")


def discover_rendered_webpage_video_candidates_from_probe_payload(
    source_url: str,
    payload: Mapping[str, Any] | str | None,
    *,
    capability_decision: Mapping[str, Any] | None = None,
) -> WebpageVideoDiscoveryResult:
    """Build video candidates from a rendered-page DOM/network probe payload.

    This function is intentionally pure/testable: tests can feed captured browser
    payloads without launching Playwright.  The runtime browser launcher below is
    optional and is not used on app startup.
    """
    warnings: list[str] = []
    if isinstance(payload, str):
        try:
            payload_data: Mapping[str, Any] = json.loads(payload)
        except Exception as exc:
            payload_data = {}
            warnings.append(f"Rendered video probe payload JSON parse warning: {type(exc).__name__}: {exc}")
    else:
        payload_data = _as_mapping(payload)

    canonical_url = str(payload_data.get("location_href") or source_url or "")
    title_fallback = str(payload_data.get("document_title") or "")
    page_thumbnail_url = urljoin(
        canonical_url or source_url,
        _clean_url(payload_data.get("page_thumbnail_url") or ""),
    )
    for meta_record in _iter_payload_records(payload_data):
        meta_tag = str(meta_record.get("tag") or "").lower()
        meta_reason = str(meta_record.get("detection_reason") or "").lower()
        if not page_thumbnail_url and meta_tag == "meta" and any(token in meta_reason for token in ("og:image", "twitter:image")):
            page_thumbnail_url = urljoin(canonical_url or source_url, _clean_url(_record_url(meta_record)))
            break
    decision = dict(capability_decision or build_jdownloader_capability_decision(source_url).to_dict())

    candidates: list[WebpageVideoCandidate] = []
    seen_urls: set[str] = set()
    for record in _iter_payload_records(payload_data):
        cleaned = _clean_url(_record_url(record))
        if not cleaned:
            continue
        absolute = urljoin(canonical_url or source_url, cleaned)
        mime_type = str(record.get("mime_type") or record.get("content_type") or record.get("type") or "")
        if not _looks_like_media_url(absolute, mime_type=mime_type):
            continue
        kind, extension = classify_video_candidate_url(absolute, mime_type=mime_type)
        tag = str(record.get("tag") or "rendered")
        if kind == VIDEO_CANDIDATE_KIND_EMBED and not _embed_link_is_plausible(tag, absolute):
            continue
        if absolute in seen_urls:
            continue
        seen_urls.add(absolute)
        attr = str(record.get("attr") or "url")
        reason = str(record.get("detection_reason") or f"rendered {tag}[{attr}]")
        title = str(record.get("title") or title_fallback or "")[:240]
        candidates.append(
            WebpageVideoCandidate(
                candidate_id=_candidate_id(absolute, tag, attr),
                url=absolute,
                source_url=str(source_url or ""),
                kind=kind,
                mime_type=mime_type,
                extension=extension,
                title=title,
                thumbnail_url=urljoin(canonical_url or source_url, _clean_url(record.get("thumbnail_url") or page_thumbnail_url or "")) if (record.get("thumbnail_url") or page_thumbnail_url) else "",
                width=_safe_int(record.get("width")),
                height=_safe_int(record.get("height")),
                source_tag=tag,
                source_attr=attr,
                detection_reason=reason,
                selected_by_default=kind in {VIDEO_CANDIDATE_KIND_FILE, VIDEO_CANDIDATE_KIND_STREAM},
            )
        )

    return WebpageVideoDiscoveryResult(
        source_url=str(source_url or ""),
        canonical_url=canonical_url,
        discovery_method=VIDEO_DISCOVERY_METHOD_RENDERED_BROWSER,
        candidates=tuple(candidates),
        candidate_count=len(candidates),
        jdownloader_capability_decision=decision,
        recommended_backend_id=str(decision.get("recommended_backend_id") or ""),
        route_preference=VIDEO_ROUTE_PREFERENCE,
        warnings=tuple(warnings),
    )


def discover_rendered_webpage_video_candidates(
    source_url: str,
    *,
    timeout_ms: int = 15000,
    capability_decision: Mapping[str, Any] | None = None,
    headless: bool = True,
    browser_executable_path: str | None = None,
) -> WebpageVideoDiscoveryResult:
    """Launch a short-lived rendered probe for webpage video candidates.

    V78D keeps this as an explicit on-demand backend.  It does not run on app
    startup, does not download anything, and keeps JDownloader/API3128 as the
    preferred download route by attaching the same capability decision metadata.
    """
    network_records: list[dict[str, Any]] = []
    warnings: list[str] = []
    try:
        from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
        from playwright.sync_api import sync_playwright
    except Exception as exc:
        return WebpageVideoDiscoveryResult(
            source_url=str(source_url or ""),
            canonical_url=str(source_url or ""),
            discovery_method=VIDEO_DISCOVERY_METHOD_RENDERED_BROWSER,
            jdownloader_capability_decision=dict(
                capability_decision or build_jdownloader_capability_decision(source_url).to_dict()
            ),
            recommended_backend_id="",
            warnings=(f"Playwright unavailable for rendered video probe: {type(exc).__name__}: {exc}",),
        )

    payload: Mapping[str, Any] = {}
    try:
        with sync_playwright() as playwright:
            launch_kwargs: dict[str, Any] = {"headless": headless}
            if browser_executable_path:
                launch_kwargs["executable_path"] = browser_executable_path
            browser = playwright.chromium.launch(**launch_kwargs)
            context = browser.new_context(ignore_https_errors=True)
            page = context.new_page()

            def _on_response(response: Any) -> None:
                try:
                    url = str(getattr(response, "url", "") or "")
                    headers = response.headers or {}
                    content_type = str(headers.get("content-type") or headers.get("Content-Type") or "")
                    if _looks_like_media_url(url, mime_type=content_type):
                        network_records.append(
                            {
                                "tag": "network_response",
                                "attr": "url",
                                "url": url,
                                "mime_type": content_type,
                                "detection_reason": "browser network response",
                            }
                        )
                except Exception:
                    return

            page.on("response", _on_response)
            try:
                page.goto(str(source_url or ""), wait_until="domcontentloaded", timeout=timeout_ms)
            except PlaywrightTimeoutError as exc:
                warnings.append(f"Rendered video probe navigation timeout: {exc}")
            except Exception as exc:
                warnings.append(f"Rendered video probe navigation warning: {type(exc).__name__}: {exc}")
            try:
                page.wait_for_load_state("networkidle", timeout=min(max(timeout_ms // 3, 1000), 5000))
            except Exception:
                pass
            try:
                payload = page.evaluate(RENDERED_VIDEO_PROBE_SCRIPT) or {}
            except Exception as exc:
                warnings.append(f"Rendered video probe evaluation warning: {type(exc).__name__}: {exc}")
                payload = {}
            try:
                context.close()
                browser.close()
            except Exception:
                pass
    except Exception as exc:
        warnings.append(f"Rendered video probe browser warning: {type(exc).__name__}: {exc}")

    merged_payload = dict(payload or {})
    merged_payload.setdefault("location_href", source_url)
    existing_network = merged_payload.get("network_urls")
    if isinstance(existing_network, list):
        merged_payload["network_urls"] = [*existing_network, *network_records]
    else:
        merged_payload["network_urls"] = network_records
    result = discover_rendered_webpage_video_candidates_from_probe_payload(
        source_url,
        merged_payload,
        capability_decision=capability_decision,
    )
    if warnings:
        return WebpageVideoDiscoveryResult(
            source_url=result.source_url,
            canonical_url=result.canonical_url,
            discovery_method=result.discovery_method,
            candidates=result.candidates,
            candidate_count=result.candidate_count,
            jdownloader_capability_decision=result.jdownloader_capability_decision,
            recommended_backend_id=result.recommended_backend_id,
            route_preference=result.route_preference,
            warnings=(*result.warnings, *warnings),
        )
    return result


def _is_direct_rendered_video_candidate(candidate: WebpageVideoCandidate) -> bool:
    ext = str(candidate.extension or "").lower()
    if candidate.kind != VIDEO_CANDIDATE_KIND_FILE:
        return False
    if ext not in {".mp4", ".m4v", ".webm"}:
        return False
    url_text = str(candidate.url or "").lower()
    return not any(token in url_text for token in (".m3u8", ".mpd", "/manifest"))


def bounded_direct_rendered_video_candidates(
    source_url: str,
    payload: Mapping[str, Any] | str | None,
    *,
    max_candidates: int = 8,
    capability_decision: Mapping[str, Any] | None = None,
) -> WebpageVideoDiscoveryResult:
    """Return a capped direct MP4/WebM subset from a rendered/media payload."""
    result = discover_rendered_webpage_video_candidates_from_probe_payload(
        source_url,
        payload,
        capability_decision=capability_decision,
    )
    capped: list[WebpageVideoCandidate] = []
    seen_urls: set[str] = set()
    for candidate in result.candidates or ():
        if not _is_direct_rendered_video_candidate(candidate):
            continue
        key = str(candidate.url or "")
        if not key or key in seen_urls:
            continue
        seen_urls.add(key)
        capped.append(candidate)
        if len(capped) >= max(1, int(max_candidates)):
            break
    return WebpageVideoDiscoveryResult(
        source_url=result.source_url,
        canonical_url=result.canonical_url,
        discovery_method="fast_bounded_rendered_direct_media_probe",
        candidates=tuple(capped),
        candidate_count=len(capped),
        jdownloader_capability_decision=result.jdownloader_capability_decision,
        recommended_backend_id=result.recommended_backend_id,
        route_preference=result.route_preference,
        warnings=result.warnings,
    )


def discover_fast_rendered_direct_video_candidates(
    source_url: str,
    *,
    timeout_ms: int = 3500,
    max_candidates: int = 8,
    capability_decision: Mapping[str, Any] | None = None,
    headless: bool = True,
    browser_executable_path: str | None = None,
) -> WebpageVideoDiscoveryResult:
    """Short bounded browser/network probe for direct MP4/WebM URLs.

    This does not replace the full rendered probe.  It returns only a capped set
    of clear direct video files so the dialog can update before slower enrichment.
    """
    network_records: list[dict[str, Any]] = []
    warnings: list[str] = []
    payload: Mapping[str, Any] = {"location_href": source_url, "network_urls": network_records}
    try:
        from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
        from playwright.sync_api import sync_playwright
    except Exception as exc:
        return WebpageVideoDiscoveryResult(
            source_url=str(source_url or ""),
            canonical_url=str(source_url or ""),
            discovery_method="fast_bounded_rendered_direct_media_probe",
            jdownloader_capability_decision=dict(
                capability_decision or build_jdownloader_capability_decision(source_url).to_dict()
            ),
            recommended_backend_id="",
            warnings=(f"Playwright unavailable for fast rendered media probe: {type(exc).__name__}: {exc}",),
        )

    try:
        with sync_playwright() as playwright:
            launch_kwargs: dict[str, Any] = {"headless": headless}
            if browser_executable_path:
                launch_kwargs["executable_path"] = browser_executable_path
            browser = playwright.chromium.launch(**launch_kwargs)
            context = browser.new_context(ignore_https_errors=True)
            page = context.new_page()

            def _on_response(response: Any) -> None:
                try:
                    url = str(getattr(response, "url", "") or "")
                    headers = response.headers or {}
                    content_type = str(headers.get("content-type") or headers.get("Content-Type") or "")
                    if not _looks_like_media_url(url, mime_type=content_type):
                        return
                    kind, extension = classify_video_candidate_url(url, mime_type=content_type)
                    if kind != VIDEO_CANDIDATE_KIND_FILE or extension not in {".mp4", ".m4v", ".webm"}:
                        return
                    if any(existing.get("url") == url for existing in network_records):
                        return
                    network_records.append(
                        {
                            "tag": "network_response",
                            "attr": "url",
                            "url": url,
                            "mime_type": content_type,
                            "detection_reason": "fast browser network response",
                        }
                    )
                except Exception:
                    return

            page.on("response", _on_response)
            try:
                page.goto(str(source_url or ""), wait_until="domcontentloaded", timeout=max(1000, int(timeout_ms)))
            except PlaywrightTimeoutError as exc:
                warnings.append(f"Fast rendered media probe navigation timeout: {exc}")
            except Exception as exc:
                warnings.append(f"Fast rendered media probe navigation warning: {type(exc).__name__}: {exc}")
            deadline_ms = max(750, int(timeout_ms))
            waited = 0
            while waited < deadline_ms and len(network_records) < max(1, int(max_candidates)):
                try:
                    page.wait_for_timeout(250)
                except Exception:
                    break
                waited += 250
                try:
                    payload = page.evaluate(RENDERED_VIDEO_PROBE_SCRIPT) or payload
                    quick = bounded_direct_rendered_video_candidates(
                        source_url,
                        payload,
                        max_candidates=max_candidates,
                        capability_decision=capability_decision,
                    )
                    if len(quick.candidates or ()) >= 2:
                        break
                except Exception:
                    pass
            try:
                payload = page.evaluate(RENDERED_VIDEO_PROBE_SCRIPT) or payload
            except Exception as exc:
                warnings.append(f"Fast rendered media probe evaluation warning: {type(exc).__name__}: {exc}")
            try:
                context.close()
                browser.close()
            except Exception:
                pass
    except Exception as exc:
        warnings.append(f"Fast rendered media probe browser warning: {type(exc).__name__}: {exc}")

    merged_payload = dict(payload or {})
    merged_payload.setdefault("location_href", source_url)
    existing_network = merged_payload.get("network_urls")
    if isinstance(existing_network, list):
        merged_payload["network_urls"] = [*existing_network, *network_records]
    else:
        merged_payload["network_urls"] = network_records
    result = bounded_direct_rendered_video_candidates(
        source_url,
        merged_payload,
        max_candidates=max_candidates,
        capability_decision=capability_decision,
    )
    if warnings:
        return WebpageVideoDiscoveryResult(
            source_url=result.source_url,
            canonical_url=result.canonical_url,
            discovery_method=result.discovery_method,
            candidates=result.candidates,
            candidate_count=result.candidate_count,
            jdownloader_capability_decision=result.jdownloader_capability_decision,
            recommended_backend_id=result.recommended_backend_id,
            route_preference=result.route_preference,
            warnings=(*result.warnings, *warnings),
        )
    return result
