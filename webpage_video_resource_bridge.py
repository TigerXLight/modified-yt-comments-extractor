from __future__ import annotations

import hashlib
import urllib.request
from dataclasses import dataclass
from typing import Any

from source_resource_state import RESOURCE_KIND_VIDEO_AUDIO, SourceResourceItem, SourceResourceRowState
from webpage_video_candidate_backend import (
    VIDEO_CANDIDATE_KIND_EMBED,
    VIDEO_CANDIDATE_KIND_FILE,
    VIDEO_CANDIDATE_KIND_STREAM,
    WebpageVideoCandidate,
    WebpageVideoDiscoveryResult,
)
from webpage_video_discovery_backend import discover_webpage_video_candidates, summarize_merged_webpage_video_discovery


@dataclass(frozen=True)
class WebpageVideoSourceDiscovery:
    """Source-row friendly video/audio discovery result.

    This is still discovery-only: no JDownloader job is started, no yt-dlp call is
    made, and no media file is downloaded.  The resources are the GUI/state
    projection of V78C-E candidates plus the JD/API3128-first route metadata.
    """

    row_id: str
    source_url: str
    canonical_url: str
    resources: tuple[SourceResourceItem, ...] = ()
    discovery: WebpageVideoDiscoveryResult | None = None
    summary: dict[str, Any] | None = None
    warnings: tuple[str, ...] = ()

    @property
    def resource_count(self) -> int:
        return len(self.resources)


def _stable_video_resource_id(row: SourceResourceRowState, candidate: WebpageVideoCandidate) -> str:
    seed = "\0".join(
        (
            str(getattr(row, "row_id", "") or ""),
            str(candidate.candidate_id or ""),
            str(candidate.url or ""),
            str(candidate.kind or ""),
        )
    )
    digest = hashlib.sha1(seed.encode("utf-8", "replace")).hexdigest()[:18]
    return f"webpage-video-{digest}"


def _media_type_for_candidate(candidate: WebpageVideoCandidate) -> str:
    mime = str(candidate.mime_type or "").lower()
    if mime.startswith("audio/"):
        return "audio"
    if mime.startswith("video/"):
        return "video"
    if candidate.kind == VIDEO_CANDIDATE_KIND_STREAM:
        return "stream"
    if candidate.kind == VIDEO_CANDIDATE_KIND_EMBED:
        return "embedded_player"
    return "video_audio"


def _candidate_display_name(candidate: WebpageVideoCandidate) -> str:
    title = " ".join(str(candidate.title or "").split())
    if title:
        return title[:180]
    label_parts = []
    if candidate.kind:
        label_parts.append(str(candidate.kind).replace("_", " "))
    if candidate.extension:
        label_parts.append(str(candidate.extension).lstrip(".").upper())
    if candidate.source_tag:
        label_parts.append(f"from {candidate.source_tag}")
    return " ".join(label_parts).strip() or "Webpage video/audio candidate"


def _warning_for_candidate(candidate: WebpageVideoCandidate) -> str:
    if candidate.kind == VIDEO_CANDIDATE_KIND_EMBED:
        return "Embedded/player URL; prefer JDownloader crawler/API3128 route before yt-dlp fallback."
    if candidate.kind not in {VIDEO_CANDIDATE_KIND_FILE, VIDEO_CANDIDATE_KIND_STREAM}:
        return "Candidate needs route verification; prefer JDownloader/API3128 before yt-dlp fallback."
    return ""


def webpage_video_resources_from_discovery(
    row: SourceResourceRowState,
    discovery: WebpageVideoDiscoveryResult,
) -> tuple[SourceResourceItem, ...]:
    """Convert merged video candidates into SourceResourceItem rows."""
    resources: list[SourceResourceItem] = []
    for candidate in discovery.candidates or ():
        if not candidate.url:
            continue
        resources.append(
            SourceResourceItem(
                resource_id=_stable_video_resource_id(row, candidate),
                source_row_id=row.row_id,
                resource_kind=RESOURCE_KIND_VIDEO_AUDIO,
                reference_url=candidate.url,
                canonical_url=candidate.url,
                display_name=_candidate_display_name(candidate),
                media_type=_media_type_for_candidate(candidate),
                mime_type=str(candidate.mime_type or ""),
                extension=str(candidate.extension or ""),
                width=int(candidate.width or 0),
                height=int(candidate.height or 0),
                bitrate_or_quality=str(candidate.kind or ""),
                thumbnail_reference="",
                from_link=str(candidate.source_tag or "").lower() in {"a", "link"},
                status="discovered",
                selectable=bool(candidate.selected_by_default or candidate.kind),
                warning=_warning_for_candidate(candidate),
                provenance=(
                    f"webpage_video_discovery:{discovery.discovery_method}; "
                    f"detected_by={candidate.detection_reason or candidate.source_tag or 'unknown'}; "
                    f"route_preference={discovery.route_preference}; "
                    f"recommended_backend={discovery.recommended_backend_id or 'unknown'}"
                ),
            )
        )
    return tuple(resources)


def _fetch_static_html(source_url: str, *, timeout: float = 8.0, max_bytes: int = 2_000_000) -> tuple[str, tuple[str, ...]]:
    warnings: list[str] = []
    if not str(source_url or "").lower().startswith(("http://", "https://")):
        return "", ("Static HTML video fetch skipped: URL is not http/https.",)
    try:
        request = urllib.request.Request(
            str(source_url),
            headers={
                "User-Agent": "Mozilla/5.0 YTCE webpage video discovery",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            },
        )
        with urllib.request.urlopen(request, timeout=timeout) as response:
            content_type = str(response.headers.get("content-type") or "")
            data = response.read(max_bytes)
        charset = "utf-8"
        for part in content_type.split(";"):
            part = part.strip()
            if part.lower().startswith("charset="):
                charset = part.split("=", 1)[1].strip() or "utf-8"
                break
        return data.decode(charset, errors="replace"), tuple(warnings)
    except Exception as exc:
        return "", (f"Static HTML video fetch warning: {type(exc).__name__}: {exc}",)


def discover_webpage_videos_for_row(
    row: SourceResourceRowState,
    *,
    fetch_static_html: bool = True,
    run_rendered_probe: bool = True,
    rendered_probe_timeout_ms: int = 12000,
) -> WebpageVideoSourceDiscovery:
    """Discover webpage video/audio candidates for a source row without downloading.

    This is intended for source-row prefetch and future Video & Audio dialog
    discovery.  It tries JD/API3128 routing metadata first, while the actual
    candidate gathering is static HTML + optional rendered DOM/network probe.
    """
    source_url = str(getattr(row, "canonical_url", "") or getattr(row, "raw_url", "") or "").strip()
    html_text = ""
    warnings: list[str] = []
    if fetch_static_html:
        html_text, fetch_warnings = _fetch_static_html(source_url)
        warnings.extend(fetch_warnings)
    discovery = discover_webpage_video_candidates(
        source_url,
        html_text=html_text,
        run_rendered_probe=run_rendered_probe,
        rendered_probe_timeout_ms=rendered_probe_timeout_ms,
    )
    resources = webpage_video_resources_from_discovery(row, discovery)
    summary = summarize_merged_webpage_video_discovery(discovery)
    return WebpageVideoSourceDiscovery(
        row_id=row.row_id,
        source_url=source_url,
        canonical_url=discovery.canonical_url or source_url,
        resources=resources,
        discovery=discovery,
        summary=summary,
        warnings=tuple([*warnings, *(discovery.warnings or ())]),
    )


__all__ = [
    "WebpageVideoSourceDiscovery",
    "discover_webpage_videos_for_row",
    "webpage_video_resources_from_discovery",
]
