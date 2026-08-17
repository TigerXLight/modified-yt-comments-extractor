"""Nested source-unit recognition for Profile/Media HOME case roots.

V77B adds read-only recognition for a selected case root that contains
``Sources/`` and multiple nested source units.  It does not crawl, download,
open media content, infer sensitive identifiers, or finalize source roles.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import hashlib
import os
from pathlib import Path
import re
from typing import Any, Iterable, Mapping, Sequence
from urllib.parse import urlparse


PROFILE_MEDIA_NESTED_SOURCE_UNITS_SCHEMA_VERSION = "profile-media-nested-source-units-v77b"

URL_PATTERN = re.compile(r"https?://[^\s<>()\"']+", re.IGNORECASE)
RTF_HEX_PATTERN = re.compile(r"\\'([0-9a-fA-F]{2})")
CONTROL_SYMBOL_REPLACEMENTS = {
    r"\lquote": "\u2018",
    r"\rquote": "\u2019",
    r"\ldblquote": "\u201c",
    r"\rdblquote": "\u201d",
    r"\endash": "\u2013",
    r"\emdash": "\u2014",
}

ARTICLE_SUFFIXES = {".rtf", ".html", ".htm", ".txt"}
RTF_SUFFIXES = {".rtf"}
HTML_SUFFIXES = {".html", ".htm"}
TEXT_SUFFIXES = {".txt"}
TRANSCRIPT_NAMES = {"transcript.txt"}
VIDEO_DESCRIPTION_NAMES = {"youtube description.txt", "description.txt", "video description.txt"}
CAPTION_SUFFIXES = {".srt", ".vtt", ".sbv"}
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".tif", ".tiff"}
MEDIA_SUFFIXES = {".mp4", ".m4v", ".mov", ".mkv", ".webm", ".mp3", ".m4a", ".wav", ".flac", ".ogg", ".aac"}


@dataclass(frozen=True)
class NestedFileReference:
    relative_path: str
    path: str
    kind: str
    suffix: str
    size_bytes: int
    sha256: str
    recorded_reference_only: bool = True
    opened_for_text_extraction: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class NestedSourceUnit:
    source_unit_id: str
    source_unit_path: str
    relative_path: str
    source_unit_kind: str
    source_txt_path: str
    source_urls: tuple[str, ...] = ()
    archive_urls: tuple[str, ...] = ()
    source_txt_fields: Mapping[str, Any] = field(default_factory=dict)
    article_files: tuple[NestedFileReference, ...] = ()
    selected_main_article_file: str = ""
    title: str = ""
    deck: str = ""
    uploader_account_candidate: str = ""
    original_programme_source_candidate: str = ""
    transcript_references: tuple[NestedFileReference, ...] = ()
    subtitle_or_caption_references: tuple[NestedFileReference, ...] = ()
    video_description_references: tuple[NestedFileReference, ...] = ()
    screenshot_references: tuple[NestedFileReference, ...] = ()
    media_references: tuple[NestedFileReference, ...] = ()
    linkage_references: tuple[Mapping[str, Any], ...] = ()
    transcript_support_matches: tuple[str, ...] = ()
    role_axes: Mapping[str, Any] = field(default_factory=dict)
    warnings: tuple[str, ...] = ()
    schema_version: str = PROFILE_MEDIA_NESTED_SOURCE_UNITS_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        for key in (
            "article_files",
            "transcript_references",
            "subtitle_or_caption_references",
            "video_description_references",
            "screenshot_references",
            "media_references",
        ):
            payload[key] = [item.to_dict() for item in getattr(self, key)]
        payload["source_urls"] = list(self.source_urls)
        payload["archive_urls"] = list(self.archive_urls)
        payload["linkage_references"] = [dict(item) for item in self.linkage_references]
        payload["transcript_support_matches"] = list(self.transcript_support_matches)
        payload["source_txt_fields"] = dict(self.source_txt_fields)
        payload["role_axes"] = dict(self.role_axes)
        payload["warnings"] = list(self.warnings)
        return payload


@dataclass(frozen=True)
class NestedSourceUnitDiscovery:
    case_root_detected: bool
    case_root: str
    sources_root: str
    source_units: tuple[NestedSourceUnit, ...] = ()
    primary_article_source_unit: Mapping[str, Any] = field(default_factory=dict)
    repost_source_units: tuple[Mapping[str, Any], ...] = ()
    social_video_source_units: tuple[Mapping[str, Any], ...] = ()
    transcript_references: tuple[Mapping[str, Any], ...] = ()
    subtitle_or_caption_references: tuple[Mapping[str, Any], ...] = ()
    video_description_references: tuple[Mapping[str, Any], ...] = ()
    source_unit_media_references: tuple[Mapping[str, Any], ...] = ()
    role_axes: Mapping[str, Any] = field(default_factory=dict)
    warnings: tuple[str, ...] = ()
    schema_version: str = PROFILE_MEDIA_NESTED_SOURCE_UNITS_SCHEMA_VERSION
    folder_scan_performed: bool = True
    home_database_scan_performed: bool = False
    web_download_performed: bool = False
    crawling_performed: bool = False
    media_download_performed: bool = False
    automatic_classification_performed: bool = False
    sensitive_identifier_inference_performed: bool = False
    final_source_role_decision: bool = False

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["source_units"] = [unit.to_dict() for unit in self.source_units]
        for key in (
            "repost_source_units",
            "social_video_source_units",
            "transcript_references",
            "subtitle_or_caption_references",
            "video_description_references",
            "source_unit_media_references",
        ):
            payload[key] = [dict(item) for item in getattr(self, key)]
        payload["primary_article_source_unit"] = dict(self.primary_article_source_unit)
        payload["role_axes"] = dict(self.role_axes)
        payload["warnings"] = list(self.warnings)
        return payload


def _dedupe(values: Iterable[object]) -> tuple[str, ...]:
    seen: set[str] = set()
    output: list[str] = []
    for value in values:
        text = str(value or "").strip()
        if text and text not in seen:
            seen.add(text)
            output.append(text)
    return tuple(output)


def _dedupe_path_key(path: Path) -> str:
    return os.path.normcase(str(path.resolve()))


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _file_reference(path: Path, root: Path, kind: str, *, opened_for_text_extraction: bool = False) -> NestedFileReference:
    stat = path.stat()
    return NestedFileReference(
        relative_path=path.relative_to(root).as_posix(),
        path=str(path),
        kind=kind,
        suffix=path.suffix.lower(),
        size_bytes=int(stat.st_size),
        sha256=_sha256_file(path),
        opened_for_text_extraction=opened_for_text_extraction,
    )


def _read_text(path: Path) -> str:
    data = path.read_bytes()
    text = data.decode("utf-8", errors="replace")
    if path.suffix.lower() == ".rtf" and "\ufffd" in text:
        text = data.decode("cp1252", errors="replace")
    return text


def _decode_rtf_hex(match: re.Match[str]) -> str:
    try:
        return bytes.fromhex(match.group(1)).decode("cp1252", errors="replace")
    except ValueError:
        return ""


def extract_clean_text_from_rtf_v77b(rtf_text: object) -> str:
    text = str(rtf_text or "")
    text = RTF_HEX_PATTERN.sub(_decode_rtf_hex, text)
    for raw, replacement in CONTROL_SYMBOL_REPLACEMENTS.items():
        if raw in {r"\lquote", r"\ldblquote"}:
            text = re.sub(re.escape(raw) + r" ?", replacement, text)
        else:
            text = text.replace(raw, replacement)
    text = re.sub(r"\\par[d]?", "\n", text)
    text = re.sub(r"\\line", "\n", text)
    text = re.sub(r"\{\\(?:fonttbl|colortbl|stylesheet|info|pict)[\s\S]*?\}", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"\\[a-zA-Z]+\d* ?", " ", text)
    text = re.sub(r"\\[-*_~:;!]", " ", text)
    text = text.replace(r"\{", "{").replace(r"\}", "}").replace(r"\\", "\\")
    text = text.replace("{", " ").replace("}", " ")
    lines = [re.sub(r"\s+", " ", line).strip() for line in text.splitlines()]
    meaningful = [
        line
        for line in lines
        if line
        and not re.fullmatch(r"(rtf\d+|ansi|deff\d+|fonttbl|colortbl|generator|viewkind\d+|uc\d+)", line, re.IGNORECASE)
        and len(line) > 2
    ]
    return "\n".join(meaningful)


def meaningful_text_lines(text: object) -> tuple[str, ...]:
    lines = [re.sub(r"\s+", " ", line).strip() for line in str(text or "").splitlines()]
    ignored = re.compile(r"^(source|url|title|channel|date|views|subscribers|description|text|facebook|twitter)\s*:\s*$", re.I)
    metadata = re.compile(r"^(?:calibri|arial|times new roman|riched\d*|microsoft|fonttbl|colortbl|generator)(?:[ ;].*)?$", re.I)
    return tuple(line for line in lines if line and not ignored.match(line) and not metadata.match(line))


def extract_urls_from_text(text: object) -> tuple[str, ...]:
    return _dedupe(match.group(0).rstrip(".,;]") for match in URL_PATTERN.finditer(str(text or "")))


def _is_archive_url(url: str) -> bool:
    host = urlparse(url).netloc.lower()
    return any(part in host for part in ("web.archive.org", "archive.today", "archive.ph", "archive.is"))


def _field_label(line: str) -> str:
    if re.match(r"^\s*https?://", line, re.IGNORECASE):
        return ""
    if ":" not in line:
        return ""
    label = line.split(":", 1)[0].strip().lower()
    if "/" in label or "\\" in label:
        return ""
    return label


def parse_source_txt_fields(text: object) -> dict[str, Any]:
    fields: dict[str, Any] = {}
    current = ""
    for raw_line in str(text or "").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        label = _field_label(line)
        if label:
            current = label
            value = line.split(":", 1)[1].strip()
            if current in fields:
                existing = fields[current]
                if isinstance(existing, list):
                    existing.append(value)
                else:
                    fields[current] = [existing, value]
            else:
                fields[current] = value
            continue
        if current:
            existing = fields.get(current, "")
            if isinstance(existing, list):
                existing[-1] = (str(existing[-1]) + "\n" + line).strip()
            else:
                fields[current] = (str(existing) + "\n" + line).strip()
    return fields


def find_sources_root(case_root: Path) -> Path | None:
    direct = case_root / "Sources"
    if direct.is_dir():
        return direct
    for child in case_root.iterdir() if case_root.exists() else ():
        if child.is_dir() and child.name.lower() == "sources":
            return child
    return None


def is_case_root_folder(path: str | Path) -> bool:
    root = Path(path)
    return bool(root.is_dir() and find_sources_root(root))


def discover_source_unit_paths(case_root: str | Path) -> tuple[Path, ...]:
    root = Path(case_root).resolve()
    sources = find_sources_root(root)
    if not sources:
        return ()
    by_key: dict[str, Path] = {}
    for source_txt in sources.rglob("*"):
        if source_txt.is_file() and source_txt.name.lower() == "source.txt":
            parent = source_txt.parent.resolve()
            by_key.setdefault(_dedupe_path_key(parent), parent)
    return tuple(sorted(by_key.values(), key=lambda item: item.relative_to(root).as_posix().lower()))


def _is_nested_under(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def _unit_child_paths(unit_path: Path, all_unit_paths: Sequence[Path]) -> tuple[Path, ...]:
    return tuple(path for path in all_unit_paths if path != unit_path and _is_nested_under(path, unit_path))


def _parts_lower(path: Path) -> tuple[str, ...]:
    return tuple(part.lower() for part in path.parts)


def classify_source_unit(case_root: Path, unit_path: Path) -> str:
    parts = _parts_lower(unit_path.relative_to(case_root))
    leaf = unit_path.name.lower()
    if "reposts of article" in parts or leaf in {"pressreader", "repost", "reposts"}:
        return "repost_copy_source_unit"
    if "social media" in parts or any(part in {"youtube", "twitter", "x", "facebook", "tiktok", "instagram"} for part in parts):
        return "social_video_source_unit"
    if "articles" in parts or "article" in parts:
        return "article_source_unit"
    return "source_unit_review_required"


def _is_in_named_folder(path: Path, root: Path, names: set[str]) -> bool:
    rel_parts = {part.lower() for part in path.relative_to(root).parts[:-1]}
    return bool(rel_parts & names)


def _is_transcript_file(path: Path) -> bool:
    return path.name.lower() in TRANSCRIPT_NAMES


def _is_video_description_file(path: Path) -> bool:
    return path.name.lower() in VIDEO_DESCRIPTION_NAMES


def _is_caption_file(path: Path) -> bool:
    return path.suffix.lower() in CAPTION_SUFFIXES


def _is_article_file(path: Path) -> bool:
    name = path.name.lower()
    suffix = path.suffix.lower()
    if name == "source.txt" or _is_transcript_file(path) or _is_video_description_file(path) or _is_caption_file(path):
        return False
    if suffix in RTF_SUFFIXES or suffix in HTML_SUFFIXES:
        return True
    if suffix in TEXT_SUFFIXES and "article" in name:
        return True
    return False


def _selected_main_article(article_refs: Sequence[NestedFileReference]) -> NestedFileReference | None:
    if not article_refs:
        return None
    priority = {".rtf": 0, ".html": 1, ".htm": 1, ".txt": 2}
    return min(article_refs, key=lambda item: (priority.get(item.suffix, 99), item.relative_path.lower()))


def _title_deck_from_article(path: Path | None) -> tuple[str, str]:
    if not path:
        return "", ""
    if path.suffix.lower() in RTF_SUFFIXES:
        text = extract_clean_text_from_rtf_v77b(_read_text(path))
    else:
        text = _read_text(path)
    lines = meaningful_text_lines(text)
    title = lines[0] if lines else ""
    deck = lines[1] if len(lines) > 1 else ""
    return title, deck


def _source_url_fields(fields: Mapping[str, Any], source_txt_text: str) -> tuple[str, ...]:
    urls = list(extract_urls_from_text(source_txt_text))
    for key in ("source", "url", "article", "archive"):
        value = fields.get(key)
        if isinstance(value, list):
            for item in value:
                urls.extend(extract_urls_from_text(item))
        else:
            urls.extend(extract_urls_from_text(value))
    return _dedupe(urls)


def _linkage_references(fields: Mapping[str, Any]) -> tuple[Mapping[str, Any], ...]:
    rows: list[Mapping[str, Any]] = []
    for label in ("used as a reference in", "text"):
        value = fields.get(label)
        if value:
            rows.append({"field": label, "value": value, "linkage_type": "source_unit_cross_reference"})
    return tuple(rows)


def _transcript_support_matches(paths: Sequence[NestedFileReference]) -> tuple[str, ...]:
    needles = (
        "Evangelical Christian faith",
        "influenced the way that I interact with others",
        "Faith goes to your very being",
    )
    found: list[str] = []
    for ref in paths:
        text = Path(ref.path).read_text(encoding="utf-8", errors="replace") if Path(ref.path).is_file() else ""
        for needle in needles:
            if needle.lower() in text.lower():
                found.append(needle)
    return _dedupe(found)


def _role_axes_for_unit(kind: str, title: str, fields: Mapping[str, Any]) -> dict[str, Any]:
    if kind == "social_video_source_unit":
        channel = str(fields.get("channel") or "").strip()
        return {
            "case_claim_role_candidate": "TERTIARY_OR_SECONDARY_REFERENCE_REVIEW",
            "personhood_or_witness_verification_role_candidate": "SECONDARY_WITNESS_OR_PERSONHOOD_VERIFICATION_REVIEW",
            "media_source_role_candidate": "PRIMARY_MEDIA_SOURCE_CAPTURED_OR_PUBLISHED_BY_GBNEWS" if channel.lower() == "gbnews" else "MEDIA_SOURCE_ROLE_REVIEW_REQUIRED",
            "speaker_statement_role_candidate": "DIRECT_INTERVIEW_STATEMENT_CAPTURED_IN_BROADCAST_REVIEW",
            "case_claim_role_is_final": False,
            "role_axis_note": "Social video/programme can be primary on media-source axis while remaining review-required for case/personhood claims.",
        }
    if kind == "repost_copy_source_unit":
        return {
            "case_claim_role_candidate": "REPOST_COPY_REPUBLICATION_REVIEW",
            "personhood_or_witness_verification_role_candidate": "NOT_PRIMARY_REPOST_REVIEW",
            "media_source_role_candidate": "REPOSTED_ARTICLE_COPY_REVIEW",
            "speaker_statement_role_candidate": "NOT_APPLICABLE_OR_REVIEW_REQUIRED",
            "case_claim_role_is_final": False,
        }
    return {
        "case_claim_role_candidate": "ARTICLE_SOURCE_ROLE_REVIEW_REQUIRED",
        "personhood_or_witness_verification_role_candidate": "WITNESS_CONNECTIVITY_REVIEW_REQUIRED",
        "media_source_role_candidate": "ARTICLE_LOCAL_MEDIA_REVIEW_REQUIRED",
        "speaker_statement_role_candidate": "QUOTED_STATEMENT_REVIEW_REQUIRED",
        "case_claim_role_is_final": False,
    }


def build_nested_source_unit(case_root: Path, unit_path: Path, all_unit_paths: Sequence[Path], index: int) -> NestedSourceUnit:
    child_units = _unit_child_paths(unit_path, all_unit_paths)
    source_txt = next((path for path in unit_path.iterdir() if path.is_file() and path.name.lower() == "source.txt"), unit_path / "source.txt")
    source_txt_text = _read_text(source_txt) if source_txt.is_file() else ""
    fields = parse_source_txt_fields(source_txt_text)
    urls = _source_url_fields(fields, source_txt_text)
    archive_urls = tuple(url for url in urls if _is_archive_url(url))
    kind = classify_source_unit(case_root, unit_path)

    article_refs: list[NestedFileReference] = []
    transcript_refs: list[NestedFileReference] = []
    caption_refs: list[NestedFileReference] = []
    description_refs: list[NestedFileReference] = []
    screenshot_refs: list[NestedFileReference] = []
    media_refs: list[NestedFileReference] = []

    for path in sorted((item for item in unit_path.rglob("*") if item.is_file()), key=lambda item: item.relative_to(case_root).as_posix().lower()):
        if path == source_txt:
            continue
        if any(_is_nested_under(path, child) for child in child_units):
            continue
        suffix = path.suffix.lower()
        if _is_transcript_file(path):
            transcript_refs.append(_file_reference(path, case_root, "transcript_reference", opened_for_text_extraction=True))
            continue
        if _is_caption_file(path):
            caption_refs.append(_file_reference(path, case_root, "subtitle_or_caption_reference"))
            continue
        if _is_video_description_file(path):
            description_refs.append(_file_reference(path, case_root, "video_description_reference", opened_for_text_extraction=True))
            continue
        if _is_in_named_folder(path, unit_path, {"screenshots", "screenshot", "images", "image"}) or suffix in IMAGE_SUFFIXES:
            screenshot_refs.append(_file_reference(path, case_root, "screenshot_reference"))
            continue
        if _is_in_named_folder(path, unit_path, {"media", "video", "videos", "audio"}) or suffix in MEDIA_SUFFIXES:
            media_refs.append(_file_reference(path, case_root, "media_reference"))
            continue
        if _is_article_file(path):
            article_refs.append(_file_reference(path, case_root, "article_file", opened_for_text_extraction=True))

    selected = _selected_main_article(article_refs)
    title, deck = _title_deck_from_article(Path(selected.path) if selected else None)
    if kind == "social_video_source_unit":
        title = str(fields.get("title") or title).strip()
        deck = str(fields.get("description") or deck).strip()
    uploader = str(fields.get("channel") or fields.get("uploader") or fields.get("account") or "").strip()
    original_programme = " / ".join(part for part in (title, uploader, "YouTube" if "youtube" in unit_path.as_posix().lower() or any("youtube" in url.lower() or "youtu.be" in url.lower() for url in urls) else "") if part)
    all_text_refs = tuple(transcript_refs) + tuple(description_refs)
    return NestedSourceUnit(
        source_unit_id=f"SU{index:04d}",
        source_unit_path=str(unit_path),
        relative_path=unit_path.relative_to(case_root).as_posix(),
        source_unit_kind=kind,
        source_txt_path=str(source_txt) if source_txt.exists() else "",
        source_urls=urls,
        archive_urls=archive_urls,
        source_txt_fields=fields,
        article_files=tuple(article_refs),
        selected_main_article_file=selected.path if selected else "",
        title=title,
        deck=deck,
        uploader_account_candidate=uploader,
        original_programme_source_candidate=original_programme,
        transcript_references=tuple(transcript_refs),
        subtitle_or_caption_references=tuple(caption_refs),
        video_description_references=tuple(description_refs),
        screenshot_references=tuple(screenshot_refs),
        media_references=tuple(media_refs),
        linkage_references=_linkage_references(fields),
        transcript_support_matches=_transcript_support_matches(all_text_refs),
        role_axes=_role_axes_for_unit(kind, title, fields),
        warnings=_dedupe(
            [
                "nested_child_source_units_excluded_from_this_unit" if child_units else "",
                "source_txt_missing" if not source_txt.exists() else "",
                "source_unit_role_axes_review_required",
            ]
        ),
    )


def discover_nested_source_units(case_root: str | Path) -> NestedSourceUnitDiscovery:
    root = Path(os.path.expandvars(str(case_root or ""))).expanduser().resolve()
    sources = find_sources_root(root)
    if not sources:
        return NestedSourceUnitDiscovery(case_root_detected=False, case_root=str(root), sources_root="", warnings=("sources_folder_missing",))
    unit_paths = discover_source_unit_paths(root)
    units = tuple(build_nested_source_unit(root, unit_path, unit_paths, index) for index, unit_path in enumerate(unit_paths, start=1))
    article_units = [unit for unit in units if unit.source_unit_kind == "article_source_unit" and unit.selected_main_article_file]
    primary = article_units[0].to_dict() if article_units else {}
    reposts = tuple(unit.to_dict() for unit in units if unit.source_unit_kind == "repost_copy_source_unit")
    social = tuple(unit.to_dict() for unit in units if unit.source_unit_kind == "social_video_source_unit")
    transcript_refs = tuple(ref.to_dict() | {"source_unit_id": unit.source_unit_id} for unit in units for ref in unit.transcript_references)
    caption_refs = tuple(ref.to_dict() | {"source_unit_id": unit.source_unit_id} for unit in units for ref in unit.subtitle_or_caption_references)
    description_refs = tuple(ref.to_dict() | {"source_unit_id": unit.source_unit_id} for unit in units for ref in unit.video_description_references)
    media_refs = tuple(ref.to_dict() | {"source_unit_id": unit.source_unit_id} for unit in units for ref in (tuple(unit.media_references) + tuple(unit.screenshot_references)))
    role_axes = {unit.source_unit_id: dict(unit.role_axes) for unit in units}
    return NestedSourceUnitDiscovery(
        case_root_detected=True,
        case_root=str(root),
        sources_root=str(sources),
        source_units=units,
        primary_article_source_unit=primary,
        repost_source_units=reposts,
        social_video_source_units=social,
        transcript_references=transcript_refs,
        subtitle_or_caption_references=caption_refs,
        video_description_references=description_refs,
        source_unit_media_references=media_refs,
        role_axes=role_axes,
        warnings=_dedupe(["case_root_sources_folder_detected", "nested_source_units_review_required"]),
    )
