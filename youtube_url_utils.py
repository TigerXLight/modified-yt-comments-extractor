from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import parse_qs, urlparse


YOUTUBE_VIDEO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")
CANONICAL_YOUTUBE_URL_TEMPLATE = "https://www.youtube.com/watch?v={video_id}"


@dataclass(frozen=True)
class YouTubeVideoRef:
    video_id: str
    canonical_url: str


def is_valid_youtube_video_id(value: str) -> bool:
    """Return True when value is a canonical 11-character YouTube video ID."""
    return bool(YOUTUBE_VIDEO_ID_RE.fullmatch((value or "").strip()))


def canonical_youtube_url(video_id: str) -> str:
    """Build the canonical watch URL for a validated YouTube video ID."""
    video_id = (video_id or "").strip()
    if not is_valid_youtube_video_id(video_id):
        raise ValueError(f"Invalid YouTube video ID: {video_id!r}")
    return CANONICAL_YOUTUBE_URL_TEMPLATE.format(video_id=video_id)


def _parse_url(value: str):
    parsed = urlparse(value)
    if parsed.scheme:
        return parsed

    # Accept pasted URLs without a scheme while still rejecting arbitrary text.
    if value.lower().startswith(("youtube.com/", "www.youtube.com/", "m.youtube.com/", "youtu.be/")):
        return urlparse("https://" + value)

    return parsed


def _host_matches(host: str, domain: str) -> bool:
    return host == domain or host.endswith("." + domain)


def _extract_candidate_id(value: str) -> str:
    value = value.strip()

    if is_valid_youtube_video_id(value):
        return value

    parsed = _parse_url(value)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError(f"Invalid YouTube URL: {value!r}")
    if parsed.username or parsed.password:
        raise ValueError("YouTube URL must not contain credentials.")

    host = (parsed.hostname or "").lower()
    path_parts = [part for part in parsed.path.split("/") if part]

    if host == "youtu.be":
        if path_parts:
            return path_parts[0]
        raise ValueError(f"Could not find a YouTube video ID in: {value!r}")

    if _host_matches(host, "youtube.com") or _host_matches(host, "youtube-nocookie.com"):
        query = parse_qs(parsed.query or "")
        video_ids = query.get("v") or []
        if video_ids:
            return video_ids[0]

        if len(path_parts) >= 2 and path_parts[0] in {"shorts", "embed", "live", "v"}:
            return path_parts[1]

    raise ValueError(f"Could not find a YouTube video ID in: {value!r}")


def parse_youtube_video_ref(value: str) -> YouTubeVideoRef:
    """Parse a YouTube URL or raw ID into a strict video ID and canonical URL."""
    if not value or not value.strip():
        raise ValueError("No YouTube URL or video ID provided.")

    candidate = _extract_candidate_id(value)
    if not is_valid_youtube_video_id(candidate):
        raise ValueError(f"Invalid YouTube video ID: {candidate!r}")

    return YouTubeVideoRef(
        video_id=candidate,
        canonical_url=canonical_youtube_url(candidate),
    )


def extract_youtube_video_id(value: str) -> str:
    """Extract and validate the canonical 11-character YouTube video ID."""
    return parse_youtube_video_ref(value).video_id


def normalize_youtube_url(value: str) -> str:
    """Return the canonical YouTube watch URL for a URL or raw video ID."""
    return parse_youtube_video_ref(value).canonical_url
