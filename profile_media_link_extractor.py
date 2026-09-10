"""Local link extraction for Profile/Media link source objects.

The extractor keeps contextual labels/headings so the policy layer can make a
reviewable source-object decision. It is deterministic and performs no network
work.
"""

from __future__ import annotations

import html
import re
import sys
from pathlib import Path
from typing import Iterable

try:
    from profile_media_url_normalizer import normalise_url_record
except ModuleNotFoundError:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from profile_media_url_normalizer import normalise_url_record


_MARKDOWN_LINK_RE = re.compile(
    r"\[([^\]\n]+)\]\(\s*<?((?:https?://|www\.)[^)\s<>]+)>?(?:\s+['\"][^'\"]*['\"])?\s*\)",
    flags=re.IGNORECASE,
)
_AUTOLINK_RE = re.compile(r"<((?:https?://|www\.)[^<>\s]+)>", flags=re.IGNORECASE)
_BARE_URL_RE = re.compile(r"(?<![@\w])(?:https?://|www\.)[^\s<>()\"']+", flags=re.IGNORECASE)
_REFERENCE_DEF_RE = re.compile(
    r"(?m)^\s{0,3}\[([^\]\n]+)\]:\s*<?((?:https?://|www\.)\S+?)>?(?:\s+['\"][^'\"]*['\"])?\s*$",
    flags=re.IGNORECASE,
)
_REFERENCE_USE_RE = re.compile(r"\[([^\]\n]+)\]\[([^\]\n]*)\]", flags=re.IGNORECASE)
_HEADING_RE = re.compile(r"^\s{0,3}#{1,6}\s+(.+?)\s*$")
_LIST_LABEL_RE = re.compile(
    r"^\s*(Live|Archive(?: index)?|Archive URL|Archived copy|PDF|Related resolution text|Original URL|Source URL|Canonical URL|Open URL|Source|Social|Video|Media|Redirect|Wayback(?: capture list)?)\s*:\s*(.*?)\s*$",
    flags=re.IGNORECASE,
)
_LIST_MARKER_RE = re.compile(r"^\s*(?:[-*+]\s+|\d+[.)]\s+)(.*)$")


def _clean_url(url: object) -> str:
    text = html.unescape(str(url or "")).strip().strip("<>\"'")
    text = text.replace("\\/", "/")
    return text.rstrip(".,;:)]}")


def _clean_anchor_text(text: object) -> str:
    return " ".join(html.unescape(str(text or "")).replace("\n", " ").split()).strip()


def _line_offsets(lines: list[str]) -> list[int]:
    offsets: list[int] = []
    cursor = 0
    for line in lines:
        offsets.append(cursor)
        cursor += len(line) + 1
    return offsets


def _line_number_for_pos(offsets: list[int], pos: int) -> int:
    line_number = 1
    for index, start in enumerate(offsets, start=1):
        if start > pos:
            break
        line_number = index
    return line_number


def _nearest_heading(lines: list[str], line_index: int) -> str:
    for idx in range(line_index, -1, -1):
        match = _HEADING_RE.match(lines[idx])
        if match:
            return match.group(1).strip()
    return ""


def _nearby_context(lines: list[str], line_index: int) -> str:
    start = max(0, line_index - 1)
    end = min(len(lines), line_index + 2)
    return "\n".join(line.rstrip() for line in lines[start:end]).strip()


def _label_for_line(lines: list[str], line_index: int) -> tuple[str, str]:
    current = lines[line_index] if 0 <= line_index < len(lines) else ""
    match = _LIST_LABEL_RE.match(current)
    if match:
        return match.group(1).strip(), match.group(2).strip()
    marker = _LIST_MARKER_RE.match(current)
    if marker:
        return "Numbered/list item" if re.match(r"^\s*\d", current) else "Bullet/list item", marker.group(1).strip()
    if line_index > 0:
        previous = lines[line_index - 1]
        prev_match = _LIST_LABEL_RE.match(previous)
        if prev_match:
            return prev_match.group(1).strip(), prev_match.group(2).strip()
    return "", ""


def _make_record(
    *,
    url: str,
    raw_url: str,
    anchor_text: str,
    source_context_text: str,
    nearby_heading: str,
    list_label: str,
    line_number: int,
    source_label: str,
    source_path: str,
    extraction_method: str,
    char_start: int = -1,
    char_end: int = -1,
) -> dict[str, object]:
    normalised = normalise_url_record(url)
    display_url = str(normalised.get("normalised_url") or url)
    return {
        "url": _clean_url(url),
        "raw_url": str(raw_url or "").strip(),
        "normalised_url": display_url,
        "display_url": display_url,
        "anchor_text": _clean_anchor_text(anchor_text),
        "source_context_text": source_context_text.strip(),
        "nearby_heading": nearby_heading.strip(),
        "list_label": list_label.strip(),
        "line_number": line_number,
        "char_start": char_start,
        "char_end": char_end,
        "source_label": str(source_label or ""),
        "source_path": str(source_path or ""),
        "extraction_method": extraction_method,
    }


def _dedupe(records: Iterable[dict[str, object]]) -> list[dict[str, object]]:
    output: list[dict[str, object]] = []
    by_key: dict[tuple[str, str, str, str], dict[str, object]] = {}
    seen: set[tuple[str, str, str, str]] = set()
    for record in records:
        heading = str(record.get("nearby_heading") or "")
        numbered_heading = re.search(r"\[\d+\]|\b\d+[.)]", heading)
        key = (
            str(record.get("normalised_url") or record.get("url") or "").casefold(),
            heading.casefold() if numbered_heading else "",
            str(record.get("list_label") or "").casefold(),
            str(record.get("source_path") or "").casefold(),
        )
        if key in seen:
            existing = by_key.get(key)
            if existing is not None:
                existing_anchor = str(existing.get("anchor_text") or "").strip()
                incoming_anchor = str(record.get("anchor_text") or "").strip()
                if incoming_anchor and (not existing_anchor or re.fullmatch(r"[a-z0-9_-]{1,12}", existing_anchor, flags=re.IGNORECASE)):
                    existing["anchor_text"] = incoming_anchor
                occurrences = existing.setdefault("duplicate_occurrences", [])
                if isinstance(occurrences, list):
                    occurrences.append(
                        {
                            "line_number": record.get("line_number"),
                            "char_start": record.get("char_start"),
                            "char_end": record.get("char_end"),
                            "raw_url": record.get("raw_url"),
                            "extraction_method": record.get("extraction_method"),
                        }
                    )
                existing["occurrence_count"] = int(existing.get("occurrence_count") or 1) + 1
            continue
        seen.add(key)
        record.setdefault("occurrence_count", 1)
        by_key[key] = record
        output.append(record)
    return output


def extract_link_source_objects(text: str, *, source_label: str = "", source_path: str = "") -> list[dict[str, object]]:
    """Extract Markdown and bare URL link source objects with context."""

    source_text = str(text or "")
    lines = source_text.splitlines()
    offsets = _line_offsets(lines)
    records: list[dict[str, object]] = []
    occupied_ranges: list[tuple[int, int]] = []
    reference_defs: dict[str, dict[str, object]] = {}

    for match in _REFERENCE_DEF_RE.finditer(source_text):
        label, url = match.groups()
        clean_label = _clean_anchor_text(label).casefold()
        line_number = _line_number_for_pos(offsets, match.start())
        line_index = max(0, line_number - 1)
        url_start = match.start(2)
        url_end = match.end(2)
        record = _make_record(
            url=url,
            raw_url=match.group(0),
            anchor_text=label,
            source_context_text=_nearby_context(lines, line_index),
            nearby_heading=_nearest_heading(lines, line_index),
            list_label="Reference",
            line_number=line_number,
            source_label=source_label,
            source_path=source_path,
            extraction_method="markdown_reference_definition",
            char_start=url_start,
            char_end=url_end,
        )
        reference_defs[clean_label] = record
        records.append(record)
        occupied_ranges.append((url_start, url_end))

    for match in _REFERENCE_USE_RE.finditer(source_text):
        anchor, label = match.groups()
        lookup = _clean_anchor_text(label or anchor).casefold()
        definition = reference_defs.get(lookup)
        if definition is None:
            continue
        line_number = _line_number_for_pos(offsets, match.start())
        line_index = max(0, line_number - 1)
        records.append(
            _make_record(
                url=str(definition.get("url") or definition.get("normalised_url") or ""),
                raw_url=match.group(0),
                anchor_text=anchor,
                source_context_text=_nearby_context(lines, line_index),
                nearby_heading=_nearest_heading(lines, line_index),
                list_label=str(definition.get("list_label") or "Reference"),
                line_number=line_number,
                source_label=source_label,
                source_path=source_path,
                extraction_method="markdown_reference_link",
                char_start=match.start(),
                char_end=match.end(),
            )
        )
        occupied_ranges.append(match.span())

    for match in _MARKDOWN_LINK_RE.finditer(source_text):
        anchor, url = match.groups()
        line_number = _line_number_for_pos(offsets, match.start())
        line_index = max(0, line_number - 1)
        list_label, _label_tail = _label_for_line(lines, line_index)
        records.append(
            _make_record(
                url=url,
                raw_url=match.group(0),
                anchor_text=anchor,
                source_context_text=_nearby_context(lines, line_index),
                nearby_heading=_nearest_heading(lines, line_index),
                list_label=list_label,
                line_number=line_number,
                source_label=source_label,
                source_path=source_path,
                extraction_method="markdown_inline_link",
                char_start=match.start(2),
                char_end=match.end(2),
            )
        )
        occupied_ranges.append(match.span())

    for match in _AUTOLINK_RE.finditer(source_text):
        url = match.group(1)
        line_number = _line_number_for_pos(offsets, match.start())
        line_index = max(0, line_number - 1)
        list_label, _label_tail = _label_for_line(lines, line_index)
        records.append(
            _make_record(
                url=url,
                raw_url=match.group(0),
                anchor_text="",
                source_context_text=_nearby_context(lines, line_index),
                nearby_heading=_nearest_heading(lines, line_index),
                list_label=list_label,
                line_number=line_number,
                source_label=source_label,
                source_path=source_path,
                extraction_method="markdown_autolink",
                char_start=match.start(1),
                char_end=match.end(1),
            )
        )
        occupied_ranges.append(match.span())

    def _inside_markdown_link(start: int, end: int) -> bool:
        return any(start < hi and end > lo for lo, hi in occupied_ranges)

    for match in _BARE_URL_RE.finditer(source_text):
        if _inside_markdown_link(match.start(), match.end()):
            continue
        raw_url = match.group(0)
        url = _clean_url(raw_url)
        line_number = _line_number_for_pos(offsets, match.start())
        line_index = max(0, line_number - 1)
        list_label, _label_tail = _label_for_line(lines, line_index)
        method = "reference_source_list_url" if list_label else "bare_url"
        records.append(
            _make_record(
                url=url,
                raw_url=raw_url,
                anchor_text="",
                source_context_text=_nearby_context(lines, line_index),
                nearby_heading=_nearest_heading(lines, line_index),
                list_label=list_label,
                line_number=line_number,
                source_label=source_label,
                source_path=source_path,
                extraction_method=method,
                char_start=match.start(),
                char_end=match.end(),
            )
        )

    return _dedupe(records)
