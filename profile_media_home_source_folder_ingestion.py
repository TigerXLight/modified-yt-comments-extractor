"""Selected HOME source-folder ingestion preview for Profile/Media Database.

V76O reads one explicitly selected source folder and produces a review-first
source evaluation preview.  It does not scan a full HOME database, crawl the
web, download media, move files, infer sensitive identifiers, or finalize
Primary/Secondary/Tertiary roles.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from html import escape, unescape
from html.parser import HTMLParser
import hashlib
import json
import os
from pathlib import Path
import re
from typing import Any, Iterable, Mapping, Sequence
from urllib.parse import urlparse

from profile_media_article_extraction_adapter import (
    DEFAULT_EXTRACTOR_ORDER,
    ArticleExtractionResult,
    extract_article_from_html,
)
from profile_media_database import utc_now_iso
from profile_media_nested_source_units_v77b import discover_nested_source_units
from profile_media_social_video_provenance import build_social_video_provenance_review
from profile_media_source_segment_analysis import analyze_source_segments, source_segments_to_dicts

PROFILE_MEDIA_HOME_SOURCE_FOLDER_INGESTION_SCHEMA_VERSION = "profile-media-home-source-folder-ingestion-v76o"
WRITE_HOME_SOURCE_FOLDER_EVALUATION_PREVIEW = "WRITE_HOME_SOURCE_FOLDER_EVALUATION_PREVIEW"

ARTICLE_SUFFIXES = {".txt", ".html", ".htm", ".rtf"}
HTML_SUFFIXES = {".html", ".htm"}
RTF_SUFFIXES = {".rtf"}
TEXT_SUFFIXES = {".txt"}
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".tif", ".tiff"}
MEDIA_SUFFIXES = {".mp4", ".m4v", ".mov", ".mkv", ".webm", ".mp3", ".m4a", ".wav", ".flac", ".ogg", ".aac"}
OPTIONAL_ARTICLE_BACKENDS = {"metadata_parser", "trafilatura", "newspaper4k"}

URL_PATTERN = re.compile(r"https?://[^\s<>()\"']+", re.IGNORECASE)
FIRST_PERSON_PATTERN = re.compile(r"\b(i|i'm|i've|i’d|i'd|my|mine|me|we|we're|we've|our|ours)\b", re.IGNORECASE)
AUTHORITY_PATTERN = re.compile(
    r"\b(police|court|judge|jury|officer|authority|authorities|official|agency|family|statement|charged|arrested)\b",
    re.IGNORECASE,
)
DIRECT_WITNESS_PATTERN = re.compile(
    r"\b(i saw|i heard|i filmed|i recorded|i witnessed|witnessed first hand|direct witness|interviewed by me|court observer)\b",
    re.IGNORECASE,
)
AFFILIATION_PATTERN = re.compile(r"\b(affiliation|depicts|shows|pictured|claim subject|subject shown|source credit)\b", re.IGNORECASE)


@dataclass(frozen=True)
class HomeSourceFolderFileReference:
    relative_path: str
    path: str
    kind: str
    suffix: str
    size_bytes: int
    sha256: str
    opened_for_text_extraction: bool = False
    recorded_reference_only: bool = True
    schema_version: str = PROFILE_MEDIA_HOME_SOURCE_FOLDER_INGESTION_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class HomeSourceFolderEvaluationPreview:
    source_folder: str
    source_txt_present: bool
    source_urls: tuple[str, ...] = ()
    archive_urls: tuple[str, ...] = ()
    article_files: tuple[HomeSourceFolderFileReference, ...] = ()
    rtf_files: tuple[HomeSourceFolderFileReference, ...] = ()
    html_files: tuple[HomeSourceFolderFileReference, ...] = ()
    text_files: tuple[HomeSourceFolderFileReference, ...] = ()
    screenshot_references: tuple[HomeSourceFolderFileReference, ...] = ()
    media_references: tuple[HomeSourceFolderFileReference, ...] = ()
    extracted_article_preview: Mapping[str, Any] = field(default_factory=dict)
    attribution_markings: tuple[str, ...] = ()
    source_basis_candidates: tuple[str, ...] = ()
    review_lanes: tuple[str, ...] = ()
    claim_subject_affiliation_review: Mapping[str, Any] = field(default_factory=dict)
    witness_connectivity_review: Mapping[str, Any] = field(default_factory=dict)
    first_person_author_self_claim_review: Mapping[str, Any] = field(default_factory=dict)
    social_media_video_provenance_review: Mapping[str, Any] = field(default_factory=dict)
    source_role_segments: tuple[Mapping[str, Any], ...] = ()
    social_video_provenance: Mapping[str, Any] = field(default_factory=dict)
    case_root_detected: bool = False
    source_units: tuple[Mapping[str, Any], ...] = ()
    primary_article_source_unit: Mapping[str, Any] = field(default_factory=dict)
    repost_source_units: tuple[Mapping[str, Any], ...] = ()
    social_video_source_units: tuple[Mapping[str, Any], ...] = ()
    transcript_references: tuple[Mapping[str, Any], ...] = ()
    subtitle_or_caption_references: tuple[Mapping[str, Any], ...] = ()
    video_description_references: tuple[Mapping[str, Any], ...] = ()
    source_unit_media_references: tuple[Mapping[str, Any], ...] = ()
    role_axes: Mapping[str, Any] = field(default_factory=dict)
    source_role_candidate: str = "REVIEW_REQUIRED"
    final_source_role_decision: bool = False
    warnings: tuple[str, ...] = ()
    schema_version: str = PROFILE_MEDIA_HOME_SOURCE_FOLDER_INGESTION_SCHEMA_VERSION
    created_at_utc: str = field(default_factory=utc_now_iso)
    folder_scan_performed: bool = True
    home_database_scan_performed: bool = False
    web_download_performed: bool = False
    crawling_performed: bool = False
    media_download_performed: bool = False
    automatic_classification_performed: bool = False
    sensitive_identifier_inference_performed: bool = False
    file_write_performed: bool = False

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        for key in ("article_files", "rtf_files", "html_files", "text_files", "screenshot_references", "media_references"):
            payload[key] = [item.to_dict() for item in getattr(self, key)]
        payload["source_urls"] = list(self.source_urls)
        payload["archive_urls"] = list(self.archive_urls)
        payload["attribution_markings"] = list(self.attribution_markings)
        payload["source_basis_candidates"] = list(self.source_basis_candidates)
        payload["review_lanes"] = list(self.review_lanes)
        payload["warnings"] = list(self.warnings)
        payload["extracted_article_preview"] = dict(self.extracted_article_preview)
        payload["claim_subject_affiliation_review"] = dict(self.claim_subject_affiliation_review)
        payload["witness_connectivity_review"] = dict(self.witness_connectivity_review)
        payload["first_person_author_self_claim_review"] = dict(self.first_person_author_self_claim_review)
        payload["social_media_video_provenance_review"] = dict(self.social_media_video_provenance_review)
        payload["source_role_segments"] = [dict(item) for item in self.source_role_segments]
        payload["social_video_provenance"] = dict(self.social_video_provenance)
        payload["source_units"] = [dict(item) for item in self.source_units]
        payload["primary_article_source_unit"] = dict(self.primary_article_source_unit)
        payload["repost_source_units"] = [dict(item) for item in self.repost_source_units]
        payload["social_video_source_units"] = [dict(item) for item in self.social_video_source_units]
        payload["transcript_references"] = [dict(item) for item in self.transcript_references]
        payload["subtitle_or_caption_references"] = [dict(item) for item in self.subtitle_or_caption_references]
        payload["video_description_references"] = [dict(item) for item in self.video_description_references]
        payload["source_unit_media_references"] = [dict(item) for item in self.source_unit_media_references]
        payload["role_axes"] = dict(self.role_axes)
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


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _file_reference(path: Path, root: Path, kind: str, *, opened_for_text_extraction: bool = False) -> HomeSourceFolderFileReference:
    stat = path.stat()
    return HomeSourceFolderFileReference(
        relative_path=path.relative_to(root).as_posix(),
        path=str(path),
        kind=kind,
        suffix=path.suffix.lower(),
        size_bytes=int(stat.st_size),
        sha256=_sha256_file(path),
        opened_for_text_extraction=opened_for_text_extraction,
    )


def _read_text_file(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def extract_urls_from_text(text: object) -> tuple[str, ...]:
    urls: list[str] = []
    for match in URL_PATTERN.finditer(str(text or "")):
        url = match.group(0).rstrip(".,;]")
        urls.append(url)
    return _dedupe(urls)


def _is_archive_url(url: str) -> bool:
    host = urlparse(url).netloc.lower()
    return any(part in host for part in ("web.archive.org", "archive.today", "archive.ph", "archive.is"))


def _is_in_named_folder(path: Path, root: Path, names: set[str]) -> bool:
    rel_parts = {part.lower() for part in path.relative_to(root).parts[:-1]}
    return bool(rel_parts & names)


def _decode_rtf_hex(match: re.Match[str]) -> str:
    value = match.group(1)
    try:
        return bytes.fromhex(value).decode("cp1252", errors="replace")
    except ValueError:
        return ""


def extract_plain_text_from_rtf(rtf_text: object) -> str:
    """Return a lightweight readable-text approximation for simple RTF notes."""

    text = str(rtf_text or "")
    text = re.sub(r"\\'([0-9a-fA-F]{2})", _decode_rtf_hex, text)
    replacements = {
        r"\lquote": "\u2018",
        r"\rquote": "\u2019",
        r"\ldblquote": "\u201c",
        r"\rdblquote": "\u201d",
    }
    for raw, replacement in replacements.items():
        if raw in {r"\lquote", r"\ldblquote"}:
            text = re.sub(re.escape(raw) + r" ?", replacement, text)
        else:
            text = text.replace(raw, replacement)
    text = re.sub(r"\\par[d]?", "\n", text)
    text = re.sub(r"\\line", "\n", text)
    text = re.sub(r"\{\\(?:fonttbl|colortbl|stylesheet|info|pict)[\s\S]*?\}", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"\\[a-zA-Z]+-?\d* ?", "", text)
    text = text.replace(r"\{", "{").replace(r"\}", "}").replace(r"\\", "\\")
    text = text.replace("{", " ").replace("}", " ")
    lines = [re.sub(r"\s+", " ", line).strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line)


class _HTMLTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() in {"script", "style", "noscript"}:
            self._skip_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in {"script", "style", "noscript"} and self._skip_depth:
            self._skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if not self._skip_depth:
            text = data.strip()
            if text:
                self.parts.append(text)

    def text(self) -> str:
        return "\n".join(self.parts)


def _html_to_visible_text(html_text: str) -> str:
    parser = _HTMLTextParser()
    parser.feed(html_text)
    return parser.text()


def _text_to_html_document(text: str, *, title: str, source_url: str) -> str:
    paragraphs = [line.strip() for line in text.splitlines() if line.strip()]
    body = "\n".join(f"<p>{escape(line)}</p>" for line in paragraphs)
    source_link = f"<p><a href=\"{escape(source_url, quote=True)}\">{escape(source_url)}</a></p>" if source_url else ""
    return (
        "<!doctype html><html><head>"
        f"<title>{escape(title or 'Local source folder article')}</title>"
        "</head><body><article>"
        f"<h1>{escape(title or 'Local source folder article')}</h1>"
        f"{source_link}{body}</article></body></html>"
    )


def _read_article_as_html(path: Path, source_url: str) -> tuple[str, str]:
    suffix = path.suffix.lower()
    if suffix in HTML_SUFFIXES:
        html = _read_text_file(path)
        visible = _html_to_visible_text(html)
        return html, visible
    if suffix in RTF_SUFFIXES:
        visible = extract_plain_text_from_rtf(_read_text_file(path))
        title = next((line.strip() for line in visible.splitlines() if line.strip()), path.stem)
        return _text_to_html_document(visible, title=title, source_url=source_url), visible
    visible = _read_text_file(path)
    title = next((line.strip() for line in visible.splitlines() if line.strip()), path.stem)
    return _text_to_html_document(visible, title=title, source_url=source_url), visible


def _selected_article_file(article_files: Sequence[HomeSourceFolderFileReference]) -> str:
    if not article_files:
        return ""
    priority = {".html": 0, ".htm": 0, ".txt": 1, ".rtf": 2}
    return min(article_files, key=lambda item: (priority.get(item.suffix, 99), item.relative_path)).path


def _build_article_preview(
    article_file_path: str,
    *,
    source_url: str,
    reference_root: str,
    extractor_order: Sequence[str] | None,
) -> tuple[dict[str, Any], tuple[str, ...], str]:
    if not article_file_path:
        return {}, ("no_article_file_found",), ""
    path = Path(article_file_path)
    html, visible_text = _read_article_as_html(path, source_url)
    result: ArticleExtractionResult = extract_article_from_html(
        html,
        source_url=source_url,
        local_path=str(path),
        reference_root=reference_root,
        extractor_order=extractor_order or DEFAULT_EXTRACTOR_ORDER,
    )
    payload = result.to_dict()
    payload["selected_article_file"] = str(path)
    payload["visible_text_preview"] = visible_text[:2000]
    warnings = list(result.warnings)
    for run in result.extractor_runs:
        if run.extractor_name in OPTIONAL_ARTICLE_BACKENDS and run.status == "skipped_unavailable":
            warnings.append(f"backend_missing:{run.extractor_name}")
    if result.extractor_runs and not any(run.external_tool_loaded for run in result.extractor_runs if run.extractor_name in OPTIONAL_ARTICLE_BACKENDS):
        warnings.append("stdlib_article_extraction_fallback_used")
    return payload, _dedupe(warnings), visible_text


def _build_review_state(
    *,
    combined_text: str,
    source_urls: Sequence[str],
    screenshot_refs: Sequence[HomeSourceFolderFileReference],
    media_refs: Sequence[HomeSourceFolderFileReference],
    article_preview: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], tuple[str, ...], tuple[str, ...], tuple[str, ...], str]:
    review_lanes = list(article_preview.get("review_lanes") or [])
    attribution_markings = list(article_preview.get("attribution_markings") or [])
    source_basis_candidates = list(article_preview.get("source_basis_candidates") or [])
    text = combined_text or ""

    first_person_found = bool(FIRST_PERSON_PATTERN.search(text))
    authority_found = bool(AUTHORITY_PATTERN.search(text))
    direct_witness_found = bool(DIRECT_WITNESS_PATTERN.search(text)) and not bool(
        re.search(r"\b(no|not|without)\s+(direct\s+)?witness", text, re.IGNORECASE)
    )
    social_urls = [url for url in source_urls if any(marker in url.lower() for marker in ("x.com", "twitter.com", "youtube.com", "youtu.be", "web.archive.org", "archive.today", "archive.ph"))]
    has_visual_refs = bool(screenshot_refs or media_refs)
    explicit_affiliation = bool(AFFILIATION_PATTERN.search(text)) and not bool(
        re.search(r"\b(no|not|without)\s+(explicit\s+)?(claim-subject\s+)?affiliation", text, re.IGNORECASE)
    )

    if first_person_found:
        review_lanes.append("first_person_author_self_claim_review")
    if authority_found:
        review_lanes.append("source_chain_basis_review")
        source_basis_candidates.append("authority_or_court_claim_language_present")
    if has_visual_refs and not explicit_affiliation:
        review_lanes.append("claim_subject_affiliation_review")
    if social_urls or media_refs:
        review_lanes.append("social_media_video_provenance_review")
    if not direct_witness_found:
        review_lanes.append("witness_connectivity_review")

    claim_subject_affiliation_review = {
        "status": "review_required_affiliation_gap" if has_visual_refs and not explicit_affiliation else "not_triggered_or_explicit_affiliation_present",
        "has_screenshot_references": bool(screenshot_refs),
        "has_media_references": bool(media_refs),
        "explicit_affiliation_marking_found": explicit_affiliation,
        "note": "Visual/material references are recorded only; logos, filenames, or platform labels do not prove claim-subject affiliation.",
    }
    witness_connectivity_review = {
        "status": "direct_witness_marker_found" if direct_witness_found else "review_required_witness_connectivity_not_established",
        "direct_witness_marker_found": direct_witness_found,
        "note": "Secondary depends on witness/direct holder/interviewer connectivity; repeated authority/publisher wording remains review-required.",
    }
    first_person_review = {
        "status": "review_required_first_person_scope" if first_person_found else "not_triggered",
        "first_person_marker_found": first_person_found,
        "note": "First-person language may be primary only for the author/speaker's own claimed experience, not claims about other people.",
    }
    social_media_video_review = {
        "status": "review_required_social_media_video_provenance" if social_urls or media_refs else "not_triggered",
        "source_or_archive_urls": list(social_urls),
        "media_reference_count": len(media_refs),
        "note": "Separate uploader/account, speaker, source URL, archive URL, clip holder, and transcripted statement before role review.",
    }
    source_role_candidate = "REVIEW_REQUIRED"
    if authority_found:
        source_role_candidate = "TERTIARY_PROPAGATED_SOURCE_REVIEW_REQUIRED"
    return (
        claim_subject_affiliation_review,
        witness_connectivity_review,
        first_person_review,
        social_media_video_review,
        _dedupe(review_lanes),
        _dedupe(attribution_markings),
        _dedupe(source_basis_candidates),
        source_role_candidate,
    )


def build_home_source_folder_evaluation_preview(
    source_folder: object,
    *,
    reference_root: object = "",
    extractor_order: Sequence[str] | None = None,
) -> HomeSourceFolderEvaluationPreview:
    root = Path(os.path.expandvars(str(source_folder or ""))).expanduser().resolve()
    if not root.exists() or not root.is_dir():
        raise FileNotFoundError(f"source folder does not exist or is not a directory: {root}")

    nested_discovery = discover_nested_source_units(root)
    nested_payload = nested_discovery.to_dict()

    source_txt = next((item for item in root.iterdir() if item.is_file() and item.name.lower() == "source.txt"), root / "source.txt")
    source_txt_text = _read_text_file(source_txt) if source_txt.exists() else ""
    source_urls = extract_urls_from_text(source_txt_text)
    archive_urls = tuple(url for url in source_urls if _is_archive_url(url))
    non_archive_urls = tuple(url for url in source_urls if not _is_archive_url(url))
    primary_source_url = non_archive_urls[0] if non_archive_urls else (source_urls[0] if source_urls else "")

    article_refs: list[HomeSourceFolderFileReference] = []
    rtf_refs: list[HomeSourceFolderFileReference] = []
    html_refs: list[HomeSourceFolderFileReference] = []
    text_refs: list[HomeSourceFolderFileReference] = []
    screenshot_refs: list[HomeSourceFolderFileReference] = []
    media_refs: list[HomeSourceFolderFileReference] = []
    warnings: list[str] = ["selected_source_folder_scan_only", "source_folder_may_contain_multiple_role_segments"]
    if not source_txt.exists():
        warnings.append("source_txt_missing")

    for path in sorted((item for item in root.rglob("*") if item.is_file()), key=lambda item: item.relative_to(root).as_posix().lower()):
        if path == source_txt:
            continue
        suffix = path.suffix.lower()
        in_screenshots = _is_in_named_folder(path, root, {"screenshots", "screenshot", "images", "image"})
        in_media = _is_in_named_folder(path, root, {"media", "video", "videos", "audio"})
        if in_screenshots or suffix in IMAGE_SUFFIXES:
            screenshot_refs.append(_file_reference(path, root, "screenshot_reference"))
            continue
        if in_media or suffix in MEDIA_SUFFIXES:
            media_refs.append(_file_reference(path, root, "media_reference"))
            continue
        if suffix in ARTICLE_SUFFIXES:
            ref = _file_reference(path, root, "article_file", opened_for_text_extraction=True)
            article_refs.append(ref)
            if suffix in RTF_SUFFIXES:
                rtf_refs.append(ref)
            elif suffix in HTML_SUFFIXES:
                html_refs.append(ref)
            elif suffix in TEXT_SUFFIXES:
                text_refs.append(ref)

    if screenshot_refs:
        warnings.append("screenshot_references_recorded_not_opened")
    if media_refs:
        warnings.append("media_references_recorded_not_opened")

    article_path = _selected_article_file(article_refs)
    article_preview, article_warnings, visible_article_text = _build_article_preview(
        article_path,
        source_url=primary_source_url,
        reference_root=str(reference_root or ""),
        extractor_order=extractor_order,
    )
    warnings.extend(article_warnings)
    if nested_discovery.case_root_detected:
        warnings.extend(nested_discovery.warnings)
        primary_unit = dict(nested_discovery.primary_article_source_unit)
        if primary_unit:
            article_preview = dict(article_preview)
            article_preview.update(
                {
                    "status": "nested_case_root_primary_article_selected",
                    "title": primary_unit.get("title") or article_preview.get("title", ""),
                    "deck": primary_unit.get("deck") or article_preview.get("deck", ""),
                    "selected_article_file": primary_unit.get("selected_main_article_file") or article_preview.get("selected_article_file", ""),
                    "selected_source_unit_path": primary_unit.get("source_unit_path", ""),
                    "selected_source_unit_relative_path": primary_unit.get("relative_path", ""),
                    "case_root_nested_source_unit_count": len(nested_discovery.source_units),
                }
            )
    combined_text = "\n".join([source_txt_text, visible_article_text])
    segment_reviews = analyze_source_segments(combined_text)
    segment_payloads = tuple(source_segments_to_dicts(segment_reviews))
    social_video_payload = build_social_video_provenance_review(
        combined_text,
        source_urls=source_urls,
        media_reference_count=len(media_refs),
    ).to_dict()
    (
        claim_subject_review,
        witness_review,
        first_person_review,
        social_video_review,
        review_lanes,
        attribution_markings,
        source_basis_candidates,
        source_role_candidate,
    ) = _build_review_state(
        combined_text=combined_text,
        source_urls=source_urls,
        screenshot_refs=screenshot_refs,
        media_refs=media_refs,
        article_preview=article_preview,
    )
    review_lanes = _dedupe(tuple(review_lanes) + tuple(social_video_payload.get("review_lanes") or []))

    return HomeSourceFolderEvaluationPreview(
        source_folder=str(root),
        source_txt_present=source_txt.exists(),
        source_urls=source_urls,
        archive_urls=archive_urls,
        article_files=tuple(article_refs),
        rtf_files=tuple(rtf_refs),
        html_files=tuple(html_refs),
        text_files=tuple(text_refs),
        screenshot_references=tuple(screenshot_refs),
        media_references=tuple(media_refs),
        extracted_article_preview=article_preview,
        attribution_markings=attribution_markings,
        source_basis_candidates=source_basis_candidates,
        review_lanes=review_lanes,
        claim_subject_affiliation_review=claim_subject_review,
        witness_connectivity_review=witness_review,
        first_person_author_self_claim_review=first_person_review,
        social_media_video_provenance_review=social_video_review,
        source_role_segments=segment_payloads,
        social_video_provenance=social_video_payload,
        case_root_detected=nested_discovery.case_root_detected,
        source_units=tuple(nested_payload.get("source_units") or ()),
        primary_article_source_unit=dict(nested_payload.get("primary_article_source_unit") or {}),
        repost_source_units=tuple(nested_payload.get("repost_source_units") or ()),
        social_video_source_units=tuple(nested_payload.get("social_video_source_units") or ()),
        transcript_references=tuple(nested_payload.get("transcript_references") or ()),
        subtitle_or_caption_references=tuple(nested_payload.get("subtitle_or_caption_references") or ()),
        video_description_references=tuple(nested_payload.get("video_description_references") or ()),
        source_unit_media_references=tuple(nested_payload.get("source_unit_media_references") or ()),
        role_axes=dict(nested_payload.get("role_axes") or {}),
        source_role_candidate=source_role_candidate,
        final_source_role_decision=False,
        warnings=_dedupe(warnings),
    )


def write_home_source_folder_evaluation_preview(
    preview: HomeSourceFolderEvaluationPreview | Mapping[str, Any],
    output_json: object,
    *,
    confirm_write: object = "",
) -> dict[str, Any]:
    path = Path(os.path.expandvars(str(output_json or "").strip())).expanduser()
    payload = {
        "schema_version": PROFILE_MEDIA_HOME_SOURCE_FOLDER_INGESTION_SCHEMA_VERSION,
        "status": "blocked_confirmation_required",
        "confirmation_required": WRITE_HOME_SOURCE_FOLDER_EVALUATION_PREVIEW,
        "output_json": str(path),
        "file_write_performed": False,
        "folder_scan_performed": False,
        "home_database_scan_performed": False,
        "web_download_performed": False,
        "crawling_performed": False,
        "media_download_performed": False,
        "automatic_classification_performed": False,
        "sensitive_identifier_inference_performed": False,
        "warnings": ["write_blocked_confirmation_required"],
    }
    if str(confirm_write or "") != WRITE_HOME_SOURCE_FOLDER_EVALUATION_PREVIEW:
        return payload
    if not str(path):
        payload["status"] = "blocked_missing_output_path"
        payload["warnings"] = ["missing_output_json"]
        return payload
    data = preview.to_dict() if isinstance(preview, HomeSourceFolderEvaluationPreview) else dict(preview)
    data["file_write_performed"] = True
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    payload["status"] = "home_source_folder_evaluation_preview_written"
    payload["file_write_performed"] = True
    payload["warnings"] = []
    return payload


def render_home_source_folder_evaluation_text(preview: HomeSourceFolderEvaluationPreview | Mapping[str, Any]) -> str:
    data = preview.to_dict() if isinstance(preview, HomeSourceFolderEvaluationPreview) else dict(preview)
    article_preview = data.get("extracted_article_preview") or {}
    lines = [
        "Profile/Media HOME Source Folder Ingestion Preview V76O",
        f"Schema: {data.get('schema_version')}",
        f"Source folder: {data.get('source_folder')}",
        f"source.txt present: {data.get('source_txt_present')}",
        f"Source URLs: {len(data.get('source_urls') or [])}",
        f"Archive URLs: {len(data.get('archive_urls') or [])}",
        f"Article files: {len(data.get('article_files') or [])}",
        f"RTF files: {len(data.get('rtf_files') or [])}",
        f"HTML files: {len(data.get('html_files') or [])}",
        f"Text files: {len(data.get('text_files') or [])}",
        f"Screenshot references: {len(data.get('screenshot_references') or [])}",
        f"Media references: {len(data.get('media_references') or [])}",
        f"Source-role segments: {len(data.get('source_role_segments') or [])}",
        f"case_root_detected: {data.get('case_root_detected')}",
        f"source_units: {len(data.get('source_units') or [])}",
        f"Article title: {article_preview.get('title') or '(missing)'}",
        f"Article extraction status: {article_preview.get('status') or '(not run)'}",
        f"Source role candidate: {data.get('source_role_candidate')}",
        f"Final source role decision: {data.get('final_source_role_decision')}",
        "",
        "Safety flags:",
        f"- folder_scan_performed: {data.get('folder_scan_performed')} (selected source folder only)",
        f"- home_database_scan_performed: {data.get('home_database_scan_performed')}",
        f"- web_download_performed: {data.get('web_download_performed')}",
        f"- crawling_performed: {data.get('crawling_performed')}",
        f"- media_download_performed: {data.get('media_download_performed')}",
        f"- automatic_classification_performed: {data.get('automatic_classification_performed')}",
        f"- sensitive_identifier_inference_performed: {data.get('sensitive_identifier_inference_performed')}",
        "",
        "Review lanes:",
    ]
    for lane in data.get("review_lanes") or []:
        lines.append(f"- {lane}")
    lines.extend(["", "Segment/source-role preview:"])
    for segment in (data.get("source_role_segments") or [])[:8]:
        if not isinstance(segment, Mapping):
            continue
        lines.append(
            f"- {segment.get('segment_id')}: {segment.get('source_role_candidate')} "
            f"({segment.get('role_scope')})"
        )
    social_video = data.get("social_video_provenance") or {}
    if isinstance(social_video, Mapping) and social_video:
        lines.extend([
            "",
            "Social/video provenance:",
            f"- Uploader/account: {social_video.get('uploader_account') or '(review needed)'}",
            f"- Speaker: {social_video.get('speaker') or '(review needed)'}",
            f"- Original programme/channel/source: {social_video.get('original_programme_channel_source') or '(review needed)'}",
            f"- Claim-subject affiliation gap: {social_video.get('claim_subject_affiliation_gap')}",
        ])
    if data.get("case_root_detected"):
        primary = data.get("primary_article_source_unit") or {}
        lines.extend(
            [
                "",
                "Nested source-unit summary:",
                f"- Primary article source unit: {primary.get('relative_path') or '(missing)'}",
                f"- Primary article title: {primary.get('title') or '(missing)'}",
                f"- Repost source units: {len(data.get('repost_source_units') or [])}",
                f"- Social/video source units: {len(data.get('social_video_source_units') or [])}",
            ]
        )
        for unit in data.get("source_units") or []:
            if not isinstance(unit, Mapping):
                continue
            axes = unit.get("role_axes") if isinstance(unit.get("role_axes"), Mapping) else {}
            lines.append(
                f"- {unit.get('source_unit_id')}: {unit.get('source_unit_kind')} | "
                f"{unit.get('relative_path')} | title={unit.get('title') or '(missing)'}"
            )
            if unit.get("uploader_account_candidate"):
                lines.append(f"  uploader/account candidate: {unit.get('uploader_account_candidate')}")
            if axes:
                lines.append(f"  media_source_role_candidate: {axes.get('media_source_role_candidate')}")
                lines.append(f"  personhood_or_witness_verification_role_candidate: {axes.get('personhood_or_witness_verification_role_candidate')}")
                lines.append(f"  speaker_statement_role_candidate: {axes.get('speaker_statement_role_candidate')}")
                lines.append(f"  case_claim_role_is_final: {axes.get('case_claim_role_is_final')}")
    lines.extend(["", "Warnings:"])
    for warning in data.get("warnings") or []:
        lines.append(f"- {warning}")
    return "\n".join(lines)
