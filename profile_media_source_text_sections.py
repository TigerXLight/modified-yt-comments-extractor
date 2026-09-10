"""Section-aware parsing for Profile/Media source TXT bundles.

Operator source TXT files are often mixed bundles: metadata, transcript,
comments, research notes, and source links.  This module keeps those scopes
separate before person extraction or source-role span generation.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable


SECTION_TYPES = (
    "metadata",
    "transcript",
    "comments",
    "operator_notes",
    "research_notes",
    "external_sources",
    "copied_ai_analysis",
    "duplicate_raw_transcript",
    "unknown_appendix",
    # Compatibility aliases used by older preview/review code.
    "research",
    "sources",
    "unknown",
)


@dataclass(frozen=True)
class SourceTextSection:
    section_id: str
    section_type: str
    title: str
    start_line: int | None
    end_line: int | None
    text: str


_TIMESTAMP_SPEAKER_RE = re.compile(
    r"^\s*(?:\d{1,2}:)?\d{1,2}:\d{2}\s*(?:-|–|—|to)\s*(?:\d{1,2}:)?\d{1,2}:\d{2}\s*(?:\[[^\]]+\]|[A-Z][^:]{1,80}:)?",
    re.IGNORECASE,
)
_URL_ONLY_RE = re.compile(r"^\s*(?:https?://|web\.archive\.org/|archive\.)", re.IGNORECASE)


def _clean_heading(line: str) -> str:
    return " ".join(line.strip().strip("#:-— ").split())


def _heading_type(line: str) -> str | None:
    raw = line.strip()
    if ":" in raw and raw.split(":", 1)[1].strip():
        return None
    text = _clean_heading(line).lower()
    if not text:
        return None
    if not raw.lstrip().startswith("#") and (len(text) > 60 or raw.rstrip().endswith((".", "!", "?"))):
        return None
    if text in {"transcript", "transcription", "captions", "subtitle", "subtitles"}:
        return "transcript"
    if re.search(r"\b(comments?|replies|youtube comments?|top comments?)\b", text):
        return "comments"
    if re.search(r"\b(copied\s+ai\s+analysis|ai\s+analysis|chatgpt|claude|llm)\b", text):
        return "copied_ai_analysis"
    if re.search(r"\b(operator\s+notes?|notes?|checking|source review)\b", text):
        return "operator_notes"
    if re.search(r"\b(research|analysis|context|background|article analysis)\b", text):
        return "research_notes"
    if re.search(r"\b(sources?|references?|links?|citations?|archives?)\b", text):
        return "external_sources"
    return None


def _infer_line_type(line: str) -> str | None:
    if _heading_type(line):
        return _heading_type(line)
    if _TIMESTAMP_SPEAKER_RE.search(line):
        return "transcript"
    if re.search(r"^\s*(?:Source|URL|Channel|Title|Date|Video|Archive)\s*:", line, re.IGNORECASE):
        return "metadata"
    if _URL_ONLY_RE.search(line):
        return "external_sources"
    if re.search(r"^\s*(?:@\w+|Reply\b|Likes?\s*:|👍|👎)", line, re.IGNORECASE):
        return "comments"
    return None



def _is_delimiter_line(line: str) -> bool:
    return bool(re.match(r"^\s*-{4,}\s*$", str(line or "")))


def _strip_boundary_delimiters(lines: list[str]) -> list[str]:
    output = list(lines)
    while output and _is_delimiter_line(output[0]):
        output.pop(0)
    while output and _is_delimiter_line(output[-1]):
        output.pop()
    return output


def _previous_nonempty_is_delimiter(lines: list[str], index: int) -> bool:
    for probe in range(index - 1, -1, -1):
        if not str(lines[probe]).strip():
            continue
        return _is_delimiter_line(lines[probe])
    return False


def split_source_text_sections(text: object) -> tuple[SourceTextSection, ...]:
    """Return ordered, non-overlapping sections for one source TXT bundle.

    Important boundary rule: a ``----`` line before the first Transcript heading is
    only a metadata/transcript separator. A ``----`` inside or after a transcript
    stream is a duplicate/raw-transcript boundary and must not feed canonical
    claim-span classification.
    """

    full = str(text or "").replace("\r\n", "\n").replace("\r", "\n")
    if not full.strip():
        return tuple(
            SourceTextSection(f"{kind}_0", kind, kind.title(), None, None, "")
            for kind in SECTION_TYPES
            if kind not in {"unknown", "research", "sources"}
        )

    lines = full.split("\n")
    starts: list[tuple[int, str, str]] = []
    transcript_seen = False

    for idx, line in enumerate(lines):
        if _is_delimiter_line(line):
            continue
        heading = _heading_type(line)
        if heading:
            kind = heading
            title = _clean_heading(line) or kind.title()
            if kind == "transcript":
                if transcript_seen and _previous_nonempty_is_delimiter(lines, idx):
                    kind = "duplicate_raw_transcript"
                    title = "Duplicate/raw transcript"
                else:
                    transcript_seen = True
            starts.append((idx, kind, title))
            continue
        inferred = _infer_line_type(line)
        if inferred == "transcript" and not transcript_seen:
            starts.append((idx, "transcript", "Transcript"))
            transcript_seen = True

    if not starts:
        metadata_text = full.strip()
        return (
            SourceTextSection("metadata_0", "metadata", "Metadata", 1, len(lines), metadata_text),
            SourceTextSection("transcript_0", "transcript", "Transcript", None, None, ""),
            SourceTextSection("comments_0", "comments", "Comments", None, None, ""),
            SourceTextSection("operator_notes_0", "operator_notes", "Operator notes", None, None, ""),
            SourceTextSection("research_notes_0", "research_notes", "Research notes", None, None, ""),
            SourceTextSection("external_sources_0", "external_sources", "External sources", None, None, ""),
            SourceTextSection("copied_ai_analysis_0", "copied_ai_analysis", "Copied ai analysis", None, None, ""),
            SourceTextSection("duplicate_raw_transcript_0", "duplicate_raw_transcript", "Duplicate/raw transcript", None, None, ""),
            SourceTextSection("unknown_appendix_0", "unknown_appendix", "Unknown appendix", None, None, ""),
        )

    starts = sorted(dict.fromkeys(starts), key=lambda item: item[0])
    sections: list[SourceTextSection] = []
    first_start = starts[0][0]
    if first_start > 0:
        metadata_lines = _strip_boundary_delimiters(lines[:first_start])
        sections.append(
            SourceTextSection("metadata_0", "metadata", "Metadata", 1, first_start, "\n".join(metadata_lines).strip())
        )

    counters = {kind: 0 for kind in SECTION_TYPES}
    if sections:
        counters["metadata"] = 1

    def add_section(kind: str, title: str, start_line: int | None, end_line: int | None, body_lines: list[str]) -> None:
        cleaned_lines = _strip_boundary_delimiters(body_lines)
        body = "\n".join(cleaned_lines).strip()
        section_index = counters.get(kind, 0)
        counters[kind] = section_index + 1
        sections.append(SourceTextSection(f"{kind}_{section_index}", kind, title or kind.title(), start_line, end_line, body))

    for pos, (start, kind, title) in enumerate(starts):
        end = starts[pos + 1][0] if pos + 1 < len(starts) else len(lines)
        content_start = start + 1 if _heading_type(lines[start]) else start
        body_lines = lines[content_start:end]
        if kind == "transcript":
            delimiter_at = next((offset for offset, line in enumerate(body_lines) if _is_delimiter_line(line)), None)
            if delimiter_at is not None:
                add_section(kind, title, start + 1, content_start + delimiter_at, body_lines[:delimiter_at])
                tail_lines = body_lines[delimiter_at + 1:]
                if tail_lines:
                    while tail_lines and not tail_lines[0].strip():
                        tail_lines = tail_lines[1:]
                    if tail_lines and _heading_type(tail_lines[0]) == "transcript":
                        tail_lines = tail_lines[1:]
                    add_section("duplicate_raw_transcript", "Duplicate/raw transcript", None, None, tail_lines)
                continue
        add_section(kind, title, start + 1, end, body_lines)

    present = {section.section_type for section in sections}
    for kind in ("metadata", "transcript", "comments", "operator_notes", "research_notes", "external_sources", "copied_ai_analysis", "duplicate_raw_transcript", "unknown_appendix"):
        if kind not in present:
            sections.append(SourceTextSection(f"{kind}_0", kind, kind.title(), None, None, ""))
    return tuple(sections)

def sections_by_type(sections: Iterable[SourceTextSection]) -> dict[str, str]:
    grouped = {kind: [] for kind in SECTION_TYPES if kind != "unknown"}
    for section in sections:
        if section.section_type in grouped and section.text.strip():
            grouped[section.section_type].append(section.text.strip())
    result = {kind: "\n\n".join(parts) for kind, parts in grouped.items()}
    # Legacy callers still ask for "research" and "sources"; keep those aliases
    # while exposing the sharper section labels to new Review/source-card logic.
    if not result.get("research"):
        result["research"] = "\n\n".join(
            part
            for part in (
                result.get("operator_notes", ""),
                result.get("research_notes", ""),
                result.get("copied_ai_analysis", ""),
                result.get("unknown_appendix", ""),
            )
            if part
        )
    if not result.get("sources"):
        result["sources"] = result.get("external_sources", "")
    return result
