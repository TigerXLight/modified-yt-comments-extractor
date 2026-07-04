from __future__ import annotations

import csv
import re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Optional


@dataclass
class TranscriptSegment:
    speaker: str
    start: str
    end: str
    text: str


def _normalise_time(value: str) -> str:
    value = value.strip().replace(",", ".")
    return value


def _parse_srt_time_line(line: str) -> Optional[tuple[str, str, Optional[str]]]:
    """Parse an SRT/VTT timestamp line and optional speaker label.

    Supported examples:
    00:00:00,579 --> 00:00:02,079
    00:00:00,579 --> 00:00:02,079 [Kingman]
    00:00:00.579 --> 00:00:02.079 [Kingman]
    """
    if "-->" not in line:
        return None

    left, right = line.split("-->", 1)
    left = left.strip()
    right = right.strip()

    speaker = None

    speaker_match = re.search(r"\[([^\]]{1,80})\]\s*$", right)
    if speaker_match:
        speaker = speaker_match.group(1).strip()
        right = right[:speaker_match.start()].strip()

    # Remove common VTT cue settings after the end timestamp, while keeping
    # only the actual end time.
    end_match = re.match(
        r"^(\d{1,2}:\d{2}:\d{2}[,.]\d{1,3}|\d{1,2}:\d{2}[,.]\d{1,3})",
        right
    )
    if end_match:
        right = end_match.group(1)

    return _normalise_time(left), _normalise_time(right), speaker


def _clean_vtt(content: str) -> str:
    lines = content.splitlines()
    cleaned = []

    for line in lines:
        stripped = line.strip()

        if stripped.upper() == "WEBVTT":
            continue
        if stripped.startswith("NOTE"):
            continue
        if stripped.startswith("STYLE"):
            continue
        if stripped.startswith("REGION"):
            continue

        cleaned.append(line)

    return "\n".join(cleaned)


def _extract_speaker_from_text(text: str) -> tuple[str, str]:
    """Extract optional speaker labels from transcript text."""
    text = text.strip()
    speaker = "Speaker 1"

    bracket_match = re.match(r"^\[([^\]]{1,80})\]\s*(.*)$", text)
    if bracket_match:
        speaker = bracket_match.group(1).strip()
        text = bracket_match.group(2).strip()
        return speaker, text

    vtt_voice_match = re.match(r"^<v\s+([^>]{1,80})>\s*(.*)$", text)
    if vtt_voice_match:
        speaker = vtt_voice_match.group(1).strip()
        text = vtt_voice_match.group(2).strip()
        return speaker, text

    # Optional format: Speaker: text
    if ":" in text:
        possible_speaker, possible_text = text.split(":", 1)
        possible_speaker = possible_speaker.strip()

        # Avoid treating timestamps such as 00:00:00 as speaker names.
        looks_like_time = bool(re.match(r"^\d{1,2}$|^\d{1,2}:\d{2}", possible_speaker))
        if 1 <= len(possible_speaker) <= 40 and not looks_like_time:
            speaker = possible_speaker
            text = possible_text.strip()

    return speaker, text


def _parse_timed_transcript_content(content: str) -> List[TranscriptSegment]:
    """Parse SRT/VTT-style timed blocks, including .txt files with timestamps."""
    blocks = re.split(r"\n\s*\n", content.strip())
    segments: List[TranscriptSegment] = []

    for block in blocks:
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        if not lines:
            continue

        time_index = None
        for i, line in enumerate(lines):
            if "-->" in line:
                time_index = i
                break

        if time_index is None:
            continue

        times = _parse_srt_time_line(lines[time_index])
        if not times:
            continue

        start, end, speaker_from_time = times
        text_lines = lines[time_index + 1:]

        if not text_lines:
            continue

        text = " ".join(text_lines).strip()
        speaker, text = _extract_speaker_from_text(text)

        if speaker_from_time:
            speaker = speaker_from_time

        segments.append(
            TranscriptSegment(
                speaker=speaker,
                start=start,
                end=end,
                text=text,
            )
        )

    return segments


def import_srt_or_vtt(path: str) -> List[TranscriptSegment]:
    file_path = Path(path)
    content = file_path.read_text(encoding="utf-8-sig", errors="replace")

    if file_path.suffix.lower() == ".vtt":
        content = _clean_vtt(content)

    return _parse_timed_transcript_content(content)


def import_plain_txt(path: str) -> List[TranscriptSegment]:
    file_path = Path(path)
    content = file_path.read_text(encoding="utf-8-sig", errors="replace")

    timed_segments = _parse_timed_transcript_content(content)
    if timed_segments:
        return timed_segments

    segments: List[TranscriptSegment] = []
    lines = [line.strip() for line in content.splitlines() if line.strip()]

    for i, line in enumerate(lines, start=1):
        speaker, text = _extract_speaker_from_text(line)

        segments.append(
            TranscriptSegment(
                speaker=speaker,
                start="",
                end="",
                text=text,
            )
        )

    return segments


def import_transcript(path: str) -> List[TranscriptSegment]:
    suffix = Path(path).suffix.lower()

    if suffix in {".srt", ".vtt"}:
        return import_srt_or_vtt(path)

    if suffix == ".txt":
        return import_plain_txt(path)

    raise ValueError(f"Unsupported transcript file type: {suffix}")


def export_transcript_txt(segments: List[TranscriptSegment], path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write("Transcript Export\n")
        f.write("=" * 80 + "\n\n")

        for segment in segments:
            speaker = segment.speaker or "Speaker"
            time_part = ""

            if segment.start or segment.end:
                time_part = f" [{segment.start} - {segment.end}]"

            f.write(f"{speaker}{time_part}\n")
            f.write(f"{segment.text}\n\n")


def export_transcript_csv(segments: List[TranscriptSegment], path: str) -> None:
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["speaker", "start", "end", "text"]
        )
        writer.writeheader()

        for segment in segments:
            writer.writerow(asdict(segment))


def export_transcript_srt(segments: List[TranscriptSegment], path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        for i, segment in enumerate(segments, start=1):
            start = segment.start or "00:00:00.000"
            end = segment.end or "00:00:00.000"

            # SRT convention uses commas
            start = start.replace(".", ",")
            end = end.replace(".", ",")

            text = segment.text
            if segment.speaker:
                text = f"{segment.speaker}: {text}"

            f.write(f"{i}\n")
            f.write(f"{start} --> {end}\n")
            f.write(f"{text}\n\n")


def export_transcript_vtt(segments: List[TranscriptSegment], path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write("WEBVTT\n\n")

        for segment in segments:
            start = segment.start or "00:00:00.000"
            end = segment.end or "00:00:00.000"

            text = segment.text
            if segment.speaker:
                text = f"{segment.speaker}: {text}"

            f.write(f"{start} --> {end}\n")
            f.write(f"{text}\n\n")