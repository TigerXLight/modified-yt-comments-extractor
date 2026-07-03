from __future__ import annotations

from typing import Any, Dict, Optional

from googleapiclient.discovery import build

from youtube_transcript_downloader import extract_video_id


def _safe_int(value: Any) -> Optional[int]:
    try:
        return int(value)
    except Exception:
        return None


def _format_count(value: Optional[int]) -> str:
    if value is None:
        return ""

    return f"{value:,}"


def fetch_youtube_video_metadata(url_or_id: str, api_key: str) -> Dict[str, Any]:
    """Fetch title, channel, upload date, description, and public stats using YouTube Data API."""
    if not api_key:
        raise ValueError("YouTube API key is required to fetch video metadata.")

    video_id = extract_video_id(url_or_id)

    youtube = build(
        "youtube",
        "v3",
        developerKey=api_key,
        cache_discovery=False,
    )

    video_response = youtube.videos().list(
        part="snippet,statistics",
        id=video_id,
    ).execute()

    video_items = video_response.get("items", [])

    if not video_items:
        raise ValueError(f"No video metadata found for video ID: {video_id}")

    video = video_items[0]
    snippet = video.get("snippet", {})
    statistics = video.get("statistics", {})

    channel_id = snippet.get("channelId", "")
    channel_statistics: Dict[str, Any] = {}

    if channel_id:
        channel_response = youtube.channels().list(
            part="snippet,statistics",
            id=channel_id,
        ).execute()

        channel_items = channel_response.get("items", [])
        if channel_items:
            channel_statistics = channel_items[0].get("statistics", {})

    view_count = _safe_int(statistics.get("viewCount"))
    like_count = _safe_int(statistics.get("likeCount"))
    comment_count = _safe_int(statistics.get("commentCount"))
    subscriber_count = _safe_int(channel_statistics.get("subscriberCount"))

    return {
        "video_id": video_id,
        "url": f"https://www.youtube.com/watch?v={video_id}",
        "title": snippet.get("title", ""),
        "channel_title": snippet.get("channelTitle", ""),
        "channel_id": channel_id,
        "published_at": snippet.get("publishedAt", ""),
        "description": snippet.get("description", ""),
        "view_count": view_count,
        "view_count_text": _format_count(view_count),
        "like_count": like_count,
        "like_count_text": _format_count(like_count),
        "comment_count": comment_count,
        "comment_count_text": _format_count(comment_count),
        "subscriber_count": subscriber_count,
        "subscriber_count_text": _format_count(subscriber_count),
    }