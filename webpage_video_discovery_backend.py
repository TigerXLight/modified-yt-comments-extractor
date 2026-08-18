from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Iterable
from urllib.parse import urldefrag

from jdownloader_capability_router import build_jdownloader_capability_decision
from webpage_rendered_video_probe_backend import (
    VIDEO_DISCOVERY_METHOD_RENDERED_BROWSER,
    discover_rendered_webpage_video_candidates,
    discover_rendered_webpage_video_candidates_from_probe_payload,
)
from webpage_video_candidate_backend import (
    VIDEO_CANDIDATE_KIND_FILE,
    VIDEO_CANDIDATE_KIND_STREAM,
    VIDEO_ROUTE_PREFERENCE,
    WebpageVideoCandidate,
    WebpageVideoDiscoveryResult,
    discover_webpage_video_candidates_from_html,
    summarize_webpage_video_candidate_kinds,
)

VIDEO_DISCOVERY_METHOD_MERGED = "static_html_plus_rendered_browser_video_probe"


def _candidate_merge_key(candidate: WebpageVideoCandidate) -> str:
    # Treat URL fragments as presentation details for downloadable media.
    # Keep query strings intact because signed/CDN URLs and stream variants often
    # use query parameters as part of the effective resource identity.
    return urldefrag(str(candidate.url or ""))[0]


def _candidate_quality_score(candidate: WebpageVideoCandidate) -> tuple[int, int, int, int, int]:
    """Prefer more actionable/better-evidenced candidates during dedupe."""
    kind_score = 3 if candidate.kind in {VIDEO_CANDIDATE_KIND_FILE, VIDEO_CANDIDATE_KIND_STREAM} else 1
    rendered_score = 1 if str(candidate.detection_reason or "").lower().startswith(("rendered", "browser")) else 0
    network_score = 1 if str(candidate.source_tag or "").lower() in {"network_response", "performance"} else 0
    pixels = int(candidate.width or 0) * int(candidate.height or 0)
    selected_score = 1 if candidate.selected_by_default else 0
    return (kind_score, rendered_score, network_score, pixels, selected_score)


def merge_webpage_video_discovery_results(
    source_url: str,
    results: Iterable[WebpageVideoDiscoveryResult],
    *,
    capability_decision: Mapping[str, Any] | None = None,
) -> WebpageVideoDiscoveryResult:
    """Merge static and rendered video discovery results without downloading.

    This is intentionally a pure aggregation layer.  It does not launch a
    browser, does not call JDownloader, and does not make yt-dlp the primary
    route.  The merged result keeps the same JD/API3128-first capability
    metadata used by V78B-C-D.
    """
    result_list = [item for item in results if item is not None]
    decision = dict(capability_decision or {})
    if not decision:
        for item in result_list:
            if item.jdownloader_capability_decision:
                decision = dict(item.jdownloader_capability_decision)
                break
    if not decision:
        decision = dict(build_jdownloader_capability_decision(source_url).to_dict())

    merged_by_key: dict[str, WebpageVideoCandidate] = {}
    method_names: list[str] = []
    warnings: list[str] = []
    canonical_url = str(source_url or "")
    for result in result_list:
        if result.discovery_method and result.discovery_method not in method_names:
            method_names.append(result.discovery_method)
        if result.canonical_url and canonical_url == str(source_url or ""):
            canonical_url = str(result.canonical_url)
        warnings.extend([str(item) for item in (result.warnings or ()) if str(item)])
        for candidate in result.candidates or ():
            key = _candidate_merge_key(candidate)
            if not key:
                continue
            existing = merged_by_key.get(key)
            if existing is None or _candidate_quality_score(candidate) > _candidate_quality_score(existing):
                merged_by_key[key] = candidate

    candidates = tuple(merged_by_key.values())
    if not method_names:
        method_names = [VIDEO_DISCOVERY_METHOD_MERGED]

    return WebpageVideoDiscoveryResult(
        source_url=str(source_url or ""),
        canonical_url=canonical_url,
        discovery_method=VIDEO_DISCOVERY_METHOD_MERGED,
        candidates=candidates,
        candidate_count=len(candidates),
        jdownloader_capability_decision=decision,
        recommended_backend_id=str(decision.get("recommended_backend_id") or ""),
        route_preference=VIDEO_ROUTE_PREFERENCE,
        warnings=tuple(warnings),
    )


def discover_webpage_video_candidates(
    source_url: str,
    *,
    html_text: str = "",
    rendered_probe_payload: Mapping[str, Any] | str | None = None,
    run_rendered_probe: bool = False,
    capability_decision: Mapping[str, Any] | None = None,
    rendered_probe_timeout_ms: int = 15000,
) -> WebpageVideoDiscoveryResult:
    """Discover webpage video candidates through static and optional rendered probes.

    V78E is still a discovery/metadata layer only:
    - static HTML scanning is always available when HTML text is supplied;
    - rendered payload merging is pure/testable when a captured payload is supplied;
    - launching a rendered probe is explicit via run_rendered_probe=True;
    - downloads remain a later handoff to JD/API3128 first.
    """
    decision = dict(capability_decision or build_jdownloader_capability_decision(source_url).to_dict())
    results: list[WebpageVideoDiscoveryResult] = []

    if html_text:
        results.append(
            discover_webpage_video_candidates_from_html(
                source_url,
                html_text,
                capability_decision=decision,
            )
        )

    if rendered_probe_payload is not None:
        results.append(
            discover_rendered_webpage_video_candidates_from_probe_payload(
                source_url,
                rendered_probe_payload,
                capability_decision=decision,
            )
        )
    elif run_rendered_probe:
        results.append(
            discover_rendered_webpage_video_candidates(
                source_url,
                timeout_ms=rendered_probe_timeout_ms,
                capability_decision=decision,
            )
        )

    if not results:
        return WebpageVideoDiscoveryResult(
            source_url=str(source_url or ""),
            canonical_url=str(source_url or ""),
            discovery_method=VIDEO_DISCOVERY_METHOD_MERGED,
            candidates=(),
            candidate_count=0,
            jdownloader_capability_decision=decision,
            recommended_backend_id=str(decision.get("recommended_backend_id") or ""),
            route_preference=VIDEO_ROUTE_PREFERENCE,
            warnings=("No static HTML or rendered probe input was supplied for webpage video discovery.",),
        )

    return merge_webpage_video_discovery_results(source_url, results, capability_decision=decision)


def summarize_merged_webpage_video_discovery(result: WebpageVideoDiscoveryResult) -> dict[str, Any]:
    """Small serializable summary for Activity Log / future GUI evidence labels."""
    decision = dict(result.jdownloader_capability_decision or {})
    return {
        "source_url": result.source_url,
        "canonical_url": result.canonical_url,
        "discovery_method": result.discovery_method,
        "candidate_count": result.candidate_count,
        "candidate_kinds": summarize_webpage_video_candidate_kinds(result.candidates),
        "recommended_backend_id": result.recommended_backend_id,
        "route_preference": result.route_preference,
        "api3128_preferred": bool(decision.get("api3128_preferred")),
        "yt_dlp_role": str(decision.get("yt_dlp_role") or ""),
        "warning_count": len(result.warnings or ()),
    }


__all__ = [
    "VIDEO_DISCOVERY_METHOD_MERGED",
    "discover_webpage_video_candidates",
    "merge_webpage_video_discovery_results",
    "summarize_merged_webpage_video_discovery",
]
