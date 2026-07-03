from __future__ import annotations

import html
import re
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import parse_qs, urlparse

from transcript_tools import TranscriptSegment


def extract_video_id(url_or_id: str) -> str:
    """Extract a YouTube video ID from a URL or return the ID if already provided."""
    value = url_or_id.strip()

    if not value:
        raise ValueError("No YouTube URL or video ID provided.")

    # Already looks like a YouTube video ID.
    if re.fullmatch(r"[A-Za-z0-9_-]{11}", value):
        return value

    parsed = urlparse(value)
    host = parsed.netloc.lower().replace("www.", "")

    if host in {"youtu.be"}:
        video_id = parsed.path.strip("/").split("/")[0]
        if video_id:
            return video_id

    if host.endswith("youtube.com") or host.endswith("youtube-nocookie.com"):
        query = parse_qs(parsed.query)

        if "v" in query and query["v"]:
            return query["v"][0]

        path_parts = [part for part in parsed.path.split("/") if part]

        if path_parts:
            if path_parts[0] in {"shorts", "embed", "live"} and len(path_parts) >= 2:
                return path_parts[1]

    raise ValueError(f"Could not find a YouTube video ID in: {url_or_id}")


def _seconds_to_timestamp(seconds: float) -> str:
    """Convert seconds to HH:MM:SS.mmm."""
    if seconds < 0:
        seconds = 0

    total_ms = int(round(seconds * 1000))
    hours = total_ms // 3_600_000
    total_ms %= 3_600_000
    minutes = total_ms // 60_000
    total_ms %= 60_000
    secs = total_ms // 1000
    ms = total_ms % 1000

    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{ms:03d}"


def _snippet_get(snippet: Any, key: str, default: Any = None) -> Any:
    """Read snippet fields from either dict-like or object-like transcript snippets."""
    if isinstance(snippet, dict):
        return snippet.get(key, default)

    return getattr(snippet, key, default)


def _fetch_with_preference(video_id: str, languages: List[str], prefer_manual: bool):
    """Fetch transcript, preferring manual or generated captions where possible."""
    from youtube_transcript_api import YouTubeTranscriptApi

    ytt_api = YouTubeTranscriptApi()
    transcript_list = ytt_api.list(video_id)

    transcript = None

    if prefer_manual:
        try:
            transcript = transcript_list.find_manually_created_transcript(languages)
        except Exception:
            transcript = transcript_list.find_generated_transcript(languages)
    else:
        try:
            transcript = transcript_list.find_generated_transcript(languages)
        except Exception:
            transcript = transcript_list.find_manually_created_transcript(languages)

    fetched = transcript.fetch()

    info = {
        "video_id": video_id,
        "language": getattr(transcript, "language", ""),
        "language_code": getattr(transcript, "language_code", ""),
        "is_generated": getattr(transcript, "is_generated", None),
        "is_translatable": getattr(transcript, "is_translatable", None),
    }

    return fetched, info


def download_youtube_transcript(
    url_or_id: str,
    languages: Optional[List[str]] = None,
    prefer_manual: bool = True,
) -> Tuple[List[TranscriptSegment], Dict[str, Any]]:
    """
    Download existing YouTube captions/transcript and convert to TranscriptSegment objects.

    This does not transcribe audio. It only fetches captions/transcripts that YouTube already exposes.
    """
    languages = languages or ["en"]
    video_id = extract_video_id(url_or_id)

    fetched, info = _fetch_with_preference(
        video_id=video_id,
        languages=languages,
        prefer_manual=prefer_manual,
    )

    segments: List[TranscriptSegment] = []

    for snippet in fetched:
        text = _snippet_get(snippet, "text", "")
        start = float(_snippet_get(snippet, "start", 0.0) or 0.0)
        duration = float(_snippet_get(snippet, "duration", 0.0) or 0.0)
        end = start + duration

        # YouTube captions sometimes contain HTML entities.
        text = html.unescape(str(text)).replace("\n", " ").strip()

        if not text:
            continue

        segments.append(
            TranscriptSegment(
                speaker="YouTube",
                start=_seconds_to_timestamp(start),
                end=_seconds_to_timestamp(end),
                text=text,
            )
        )

    if not segments:
        raise ValueError("No transcript segments were returned for this video.")

    info["segment_count"] = len(segments)
    info["requested_languages"] = ", ".join(languages)
    info["prefer_manual"] = prefer_manual

    return segments, info

def _timestamp_to_seconds(timestamp: str) -> float:
    """Convert HH:MM:SS.mmm or HH:MM:SS,mmm to seconds."""
    timestamp = (timestamp or "").strip().replace(",", ".")

    try:
        hours, minutes, seconds = timestamp.split(":")
        return int(hours) * 3600 + int(minutes) * 60 + float(seconds)
    except Exception:
        return 0.0


def _clean_word(word: str) -> str:
    return word.lower().strip(".,!?;:\"'()[]{}")


def _join_with_overlap(left: str, right: str) -> str:
    """Join two transcript strings while removing repeated overlapping words."""
    left = left.strip()
    right = right.strip()

    if not left:
        return right
    if not right:
        return left

    left_words = left.split()
    right_words = right.split()

    max_overlap = min(len(left_words), len(right_words), 12)

    for size in range(max_overlap, 0, -1):
        left_tail = [_clean_word(word) for word in left_words[-size:]]
        right_head = [_clean_word(word) for word in right_words[:size]]

        if left_tail == right_head:
            return " ".join(left_words + right_words[size:])

    if left.endswith("-"):
        return left[:-1] + right

    return left + " " + right


def _ends_sentence(text: str) -> bool:
    return text.rstrip().endswith((".", "!", "?", "…", '."', '!"', '?"'))


def merge_transcript_segments(
    segments: List[TranscriptSegment],
    speaker_name: str = "YouTube",
    max_gap_seconds: float = 0.75,
    max_duration_seconds: float = 18.0,
    max_chars: int = 260,
) -> List[TranscriptSegment]:
    """
    Merge overlapping/nearby YouTube caption chunks into more readable transcript blocks.

    Keeps timestamps, but reduces lines like:
    00:00:00-00:00:07 text A
    00:00:04-00:00:10 text B

    into one cleaner block.
    """
    if not segments:
        return []

    merged: List[TranscriptSegment] = []

    current = TranscriptSegment(
        speaker=speaker_name,
        start=segments[0].start,
        end=segments[0].end,
        text=segments[0].text.strip(),
    )

    for segment in segments[1:]:
        current_start = _timestamp_to_seconds(current.start)
        current_end = _timestamp_to_seconds(current.end)

        next_start = _timestamp_to_seconds(segment.start)
        next_end = _timestamp_to_seconds(segment.end)

        gap = next_start - current_end
        merged_duration = next_end - current_start
        merged_text = _join_with_overlap(current.text, segment.text)

        should_merge = (
            gap <= max_gap_seconds
            and merged_duration <= max_duration_seconds
            and len(merged_text) <= max_chars
            and not _ends_sentence(current.text)
        )

        if should_merge:
            current.text = merged_text
            current.end = segment.end
        else:
            merged.append(current)
            current = TranscriptSegment(
                speaker=speaker_name,
                start=segment.start,
                end=segment.end,
                text=segment.text.strip(),
            )

    merged.append(current)
    return merged