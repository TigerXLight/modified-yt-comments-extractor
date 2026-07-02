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


def _parse_srt_time_line(line: str) -> Optional[tuple[str, str]]:
    if "-->" not in line:
        return None

    left, right = line.split("-->", 1)
    return _normalise_time(left), _normalise_time(right)


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


def import_srt_or_vtt(path: str) -> List[TranscriptSegment]:
    file_path = Path(path)
    content = file_path.read_text(encoding="utf-8-sig", errors="replace")

    if file_path.suffix.lower() == ".vtt":
        content = _clean_vtt(content)

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

        start, end = times
        text_lines = lines[time_index + 1:]

        if not text_lines:
            continue

        text = " ".join(text_lines).strip()
        speaker = "Speaker 1"

        # Optional format: Speaker: text
        if ":" in text:
            possible_speaker, possible_text = text.split(":", 1)
            if 1 <= len(possible_speaker.strip()) <= 40:
                speaker = possible_speaker.strip()
                text = possible_text.strip()

        segments.append(
            TranscriptSegment(
                speaker=speaker,
                start=start,
                end=end,
                text=text,
            )
        )

    return segments


def import_plain_txt(path: str) -> List[TranscriptSegment]:
    file_path = Path(path)
    content = file_path.read_text(encoding="utf-8-sig", errors="replace")

    segments: List[TranscriptSegment] = []
    lines = [line.strip() for line in content.splitlines() if line.strip()]

    for i, line in enumerate(lines, start=1):
        speaker = "Speaker 1"
        text = line

        if ":" in line:
            possible_speaker, possible_text = line.split(":", 1)
            if 1 <= len(possible_speaker.strip()) <= 40:
                speaker = possible_speaker.strip()
                text = possible_text.strip()

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