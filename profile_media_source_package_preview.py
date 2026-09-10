"""Profile/Media source-to-Database import package preview.

V82A adds the missing bridge between a real source row / FILES artifacts and the
existing Profile/Media Database import workbench.  It builds a reviewable batch
JSON payload only.  By default it does not create folders, copy files, scan
folders, download media, classify sources, or infer sensitive identifiers.

The output is intentionally compatible with ``profile_media_case_batch`` so the
current Database Import button can load the generated JSON, and the existing
guarded Save-to-HOME workflow can still require its own confirmation phrase.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping
from urllib.parse import urlparse

from profile_media_case_batch import PROFILE_MEDIA_CASE_BATCH_SCHEMA_VERSION
from profile_media_database import ClaimBasis, CurrentnessStatus, ProfileSourceRole, utc_now_iso
from profile_media_claim_role_classifier import (
    canonicalize_duplicate_transcript_stream,
    classify_claim_text,
    classify_transcript_text,
)
from profile_media_claim_role_policy import POLICY_VERSION as CLAIM_ROLE_POLICY_VERSION
from profile_media_link_extractor import extract_link_source_objects
from profile_media_link_source_policy import build_link_source_preview, classify_link_source_objects, resolve_visible_link_source_roles
from profile_media_browser_network_provenance_v83d import enrich_link_source_objects_with_browser_network_provenance
from profile_media_link_source_decisions import (
    apply_link_source_decisions,
    build_link_source_decision_summary,
    load_link_source_decisions,
)
from profile_media_matching_backend import canonical_person_key
from profile_media_source_reference_candidates import extract_source_reference_candidates
from profile_media_source_chain_definition_set import PRIMARY as SOURCE_CHAIN_PRIMARY_ROLE, SECONDARY as SOURCE_CHAIN_SECONDARY_ROLE, TERTIARY as SOURCE_CHAIN_TERTIARY_ROLE, UNKNOWN as SOURCE_CHAIN_UNKNOWN_ROLE
from profile_media_source_role_matching_workflow import build_source_role_matching_preview
from profile_media_source_text_sections import sections_by_type, split_source_text_sections
from profile_media_source_role_policy import canonical_source_role


PROFILE_MEDIA_SOURCE_PACKAGE_PREVIEW_SCHEMA_VERSION = "profile-media-source-package-preview-v82a"
WRITE_PROFILE_MEDIA_SOURCE_PACKAGE_PREVIEW_CONFIRMATION = "WRITE_PROFILE_MEDIA_SOURCE_PACKAGE_PREVIEW"

_SOURCE_DEFAULT_TITLE = "Untitled source"
_CASE_DEFAULT_TITLE = "Source Evidence Review"


@dataclass(frozen=True)
class ProfileMediaSourcePackageArtifact:
    """One selected/captured artifact to be represented in the DB import preview."""

    artifact_kind: str
    display_name: str = ""
    local_path: str = ""
    source_url: str = ""
    canonical_url: str = ""
    reference_url: str = ""
    resource_id: str = ""
    source_row_id: str = ""
    mime_type: str = ""
    extension: str = ""
    width: int = 0
    height: int = 0
    duration_seconds: float = 0.0
    byte_size: int = 0
    temporary: bool = True
    review_required: bool = True
    notes: str = ""
    internal_media: bool = False
    media_personhood_role: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ProfileMediaSourcePackagePreview:
    """Review-only Profile/Media Database import package preview."""

    status: str
    database_root: str
    case_title: str
    source_url: str
    canonical_url: str = ""
    source_title: str = ""
    source_domain: str = ""
    artifacts: tuple[ProfileMediaSourcePackageArtifact, ...] = ()
    batch_payload: Mapping[str, Any] = field(default_factory=dict)
    warnings: tuple[str, ...] = ()
    schema_version: str = PROFILE_MEDIA_SOURCE_PACKAGE_PREVIEW_SCHEMA_VERSION
    created_at_utc: str = field(default_factory=utc_now_iso)
    folder_scan_performed: bool = False
    folder_creation_performed: bool = False
    folder_move_performed: bool = False
    folder_rename_performed: bool = False
    file_copy_performed: bool = False
    file_write_performed: bool = False
    media_download_performed: bool = False
    web_download_performed: bool = False
    screenshot_performed: bool = False
    archive_provider_call_performed: bool = False
    automatic_classification_performed: bool = False
    sensitive_identifier_inference_performed: bool = False

    @property
    def artifact_count(self) -> int:
        return len(self.artifacts)

    @property
    def source_count(self) -> int:
        sources = self.batch_payload.get("sources", ()) if isinstance(self.batch_payload, Mapping) else ()
        return len(sources) if isinstance(sources, list) else 0

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["artifact_count"] = self.artifact_count
        payload["source_count"] = self.source_count
        payload["artifacts"] = [artifact.to_dict() for artifact in self.artifacts]
        payload["batch_payload"] = dict(self.batch_payload)
        payload["warnings"] = list(self.warnings)
        return payload


@dataclass(frozen=True)
class ProfileMediaSourcePackageWriteResult:
    """Confirmation-gated write result for a generated import JSON."""

    status: str
    output_json: str
    written_file: str = ""
    warning_count: int = 0
    warnings: tuple[str, ...] = ()
    schema_version: str = PROFILE_MEDIA_SOURCE_PACKAGE_PREVIEW_SCHEMA_VERSION
    file_write_performed: bool = False
    folder_scan_performed: bool = False
    folder_creation_performed: bool = False
    folder_move_performed: bool = False
    folder_rename_performed: bool = False
    file_copy_performed: bool = False
    media_download_performed: bool = False
    web_download_performed: bool = False
    automatic_classification_performed: bool = False
    sensitive_identifier_inference_performed: bool = False

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["warnings"] = list(self.warnings)
        return payload


def _clean_text(value: object, *, fallback: str = "") -> str:
    text = " ".join(str(value or "").replace("\r", " ").replace("\n", " ").split()).strip()
    return text or fallback


def _domain_from_url(value: object) -> str:
    parsed = urlparse(str(value or "").strip())
    return parsed.netloc.lower().removeprefix("www.")


def _display_name_from_path(path_text: object) -> str:
    text = str(path_text or "").strip()
    if not text:
        return ""
    return Path(text).name


def _coerce_int(value: object) -> int:
    try:
        return int(float(str(value or "0").strip()))
    except Exception:
        return 0


def _coerce_float(value: object) -> float:
    try:
        return float(str(value or "0").strip())
    except Exception:
        return 0.0


def normalise_source_package_artifact_kind(value: object, *, path: object = "") -> str:
    """Normalise app/UI artifact labels to stable import-preview kinds."""

    text = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
    suffix = Path(str(path or "")).suffix.lower()
    if text in {"article", "article_text", "text_article"}:
        return "article_text"
    if text in {"webpage_text", "full_webpage_text", "rendered_page_text", "visible_page_text"}:
        return "webpage_text"
    if text in {"screenshot", "webpage_screenshot", "page_screenshot"}:
        return "screenshot"
    if text in {"image", "picture", "photo"}:
        return "image"
    if text in {"video", "video_audio", "media_video"}:
        return "video"
    if text in {"audio", "media_audio"}:
        return "audio"
    if text in {"transcript", "asr", "caption", "captions"}:
        return "transcript"
    if text in {"archive", "archive_receipt", "wayback", "archive_today", "archive_ph"}:
        return "archive_receipt"
    if suffix in {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".tif", ".tiff", ".svg", ".ico"}:
        return "image"
    if suffix in {".mp4", ".mkv", ".mov", ".avi", ".webm"}:
        return "video"
    if suffix in {".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg"}:
        return "audio"
    if suffix in {".srt", ".vtt"}:
        return "transcript"
    if suffix in {".txt", ".md", ".html", ".htm", ".rtf"}:
        return "article_text"
    return text or "artifact"


def source_bucket_for_package_artifact_kind(kind: object) -> str:
    """Return the existing Profile/Media Database bucket for a preview artifact."""

    normalised = normalise_source_package_artifact_kind(kind)
    if normalised in {"article_text", "webpage_text"}:
        return "Articles"
    if normalised in {"screenshot", "image", "video", "audio", "transcript", "archive_receipt", "archive_check", "warc", "wacz"}:
        return "Reference Extants"
    return "Reference Extants"


def source_role_for_package_artifact_kind(kind: object, *, root_source_record: bool = False) -> str:
    """Return the V76E canonical source-role scaffold for a source-package record.

    This is not a final factual verdict about the underlying event or people.
    It applies the existing Profile/Media source-role policy to the source row
    itself: a publisher webpage, its rendered screenshot, extracted article
    text, archive/WARC/WACZ receipts, and embedded media captured from that
    webpage are treated as propagated source material until a reviewer marks a
    narrower primary/self-authored or secondary/witness-account scope.
    """

    _normalised = normalise_source_package_artifact_kind(kind)
    return canonical_source_role(ProfileSourceRole.TERTIARY_PROPAGATED_SOURCE.value)


def source_role_for_package_artifact(artifact: ProfileMediaSourcePackageArtifact) -> str:
    if _source_text_evidence_profile(artifact):
        return canonical_source_role(ProfileSourceRole.PRIMARY_SELF_AUTHORED_SCOPE.value)
    artifact_kind = normalise_source_package_artifact_kind(artifact.artifact_kind, path=artifact.local_path or artifact.display_name)
    media_kind = artifact_kind in {"video", "audio", "image", "screenshot", "transcript"}
    has_own_link = bool(artifact.source_url or artifact.canonical_url or artifact.reference_url)
    if artifact.internal_media and media_kind:
        return canonical_source_role(ProfileSourceRole.PRIMARY_SELF_AUTHORED_SCOPE.value)
    if media_kind and not has_own_link:
        # Locally added media has no source role until the reviewer assigns one.
        # It belongs in Review only, not Unknown/Tertiary.
        return ""
    return source_role_for_package_artifact_kind(artifact.artifact_kind)


def claim_basis_for_package_artifact(artifact: ProfileMediaSourcePackageArtifact) -> str:
    if _source_text_evidence_profile(artifact):
        return ClaimBasis.SELF_AUTHORED_EXPERIENCE.value
    artifact_kind = normalise_source_package_artifact_kind(artifact.artifact_kind, path=artifact.local_path or artifact.display_name)
    media_kind = artifact_kind in {"video", "audio", "image", "screenshot", "transcript"}
    has_own_link = bool(artifact.source_url or artifact.canonical_url or artifact.reference_url)
    if artifact.internal_media:
        return ClaimBasis.SELF_AUTHORED_EXPERIENCE.value
    if media_kind and not has_own_link:
        return ClaimBasis.UNKNOWN_CLAIM_BASIS.value
    return claim_basis_for_package_artifact_kind(artifact.artifact_kind)


def source_bucket_for_package_artifact(artifact: ProfileMediaSourcePackageArtifact) -> str:
    if artifact.internal_media:
        return "Internal Media"
    if _source_text_evidence_profile(artifact):
        return "Reference Extants"
    return source_bucket_for_package_artifact_kind(artifact.artifact_kind)


def claim_basis_for_package_artifact_kind(kind: object, *, root_source_record: bool = False) -> str:
    """Return the conservative claim-basis scaffold for package-preview records."""

    return ClaimBasis.AGENCY_OR_OUTSIDE_RETELLING.value


def currentness_status_for_package_artifact_kind(kind: object, *, root_source_record: bool = False) -> str:
    """Return the currentness scaffold for package-preview records."""

    return CurrentnessStatus.UNKNOWN.value


def source_role_policy_note_for_package_artifact_kind(kind: object, *, root_source_record: bool = False) -> str:
    normalised = "source_page" if root_source_record else normalise_source_package_artifact_kind(kind)
    return (
        "source_role_policy=profile_media_source_role_policy.v76e; "
        f"source_role_scaffold={normalised}->TERTIARY_PROPAGATED_SOURCE; "
        "final_source_role_decision=False; review lane attached where required; "
        "Primary/Self-authored and Secondary/Witness-account scopes must be marked by reviewer or explicit source-chain evidence."
    )


def package_artifact_from_mapping(value: Mapping[str, Any]) -> ProfileMediaSourcePackageArtifact:
    """Coerce a generic app/resource/session-file mapping into a package artifact."""

    local_path = str(value.get("local_path") or value.get("path") or value.get("file_path") or "").strip()
    display_name = _clean_text(
        value.get("display_name") or value.get("file_name") or value.get("filename") or _display_name_from_path(local_path),
        fallback="Unnamed artifact",
    )
    kind = normalise_source_package_artifact_kind(
        value.get("artifact_kind") or value.get("kind") or value.get("file_kind") or value.get("resource_kind"),
        path=local_path or display_name,
    )
    return ProfileMediaSourcePackageArtifact(
        artifact_kind=kind,
        display_name=display_name,
        local_path=local_path,
        source_url=str(value.get("source_url") or value.get("page_url") or "").strip(),
        canonical_url=str(value.get("canonical_url") or "").strip(),
        reference_url=str(value.get("reference_url") or value.get("media_url") or value.get("url") or "").strip(),
        resource_id=str(value.get("resource_id") or value.get("id") or "").strip(),
        source_row_id=str(value.get("source_row_id") or "").strip(),
        mime_type=str(value.get("mime_type") or "").strip(),
        extension=str(value.get("extension") or Path(display_name).suffix.lstrip(".") or Path(local_path).suffix.lstrip(".")).strip(),
        width=_coerce_int(value.get("width")),
        height=_coerce_int(value.get("height")),
        duration_seconds=_coerce_float(value.get("duration_seconds") or value.get("duration")),
        byte_size=_coerce_int(value.get("byte_size") or value.get("size") or value.get("file_size")),
        temporary=bool(value.get("temporary", True)),
        review_required=bool(value.get("review_required", True)),
        notes=str(value.get("notes") or "").strip(),
        internal_media=bool(value.get("internal_media") or value.get("is_internal_media")),
        media_personhood_role=_clean_text(value.get("media_personhood_role") or value.get("personhood_role") or ""),
    )


def _dedupe_artifacts(artifacts: Iterable[ProfileMediaSourcePackageArtifact]) -> tuple[ProfileMediaSourcePackageArtifact, ...]:
    seen: set[tuple[str, str, str, str]] = set()
    output: list[ProfileMediaSourcePackageArtifact] = []
    for artifact in artifacts:
        key = (
            artifact.artifact_kind,
            artifact.local_path,
            artifact.reference_url,
            artifact.display_name,
        )
        if key in seen:
            continue
        seen.add(key)
        output.append(artifact)
    return tuple(output)


def _artifact_dimension_text(artifact: ProfileMediaSourcePackageArtifact) -> str:
    if artifact.width and artifact.height:
        return f"{artifact.width}x{artifact.height}"
    return ""



def _read_explicit_text_artifact(path_text: object, *, limit: int = 200_000) -> str:
    path = Path(str(path_text or '').strip())
    if not path or path.suffix.lower() not in {'.txt', '.md'}:
        return ''
    try:
        if not path.is_file():
            return ''
        return path.read_text(encoding='utf-8', errors='replace')[:limit]
    except Exception:
        return ''


def _read_explicit_html_artifact(path_text: object, *, limit: int = 300_000) -> str:
    path = Path(str(path_text or '').strip())
    if not path or path.suffix.lower() not in {'.html', '.htm'}:
        return ''
    try:
        if not path.is_file():
            return ''
        return path.read_text(encoding='utf-8', errors='replace')[:limit]
    except Exception:
        return ''



def _source_text_evidence_metadata(text: object) -> dict[str, str]:
    """Extract explicit source/transcript metadata from an operator-supplied text file."""

    full = str(text or "")
    meta: dict[str, str] = {}
    for key in ("Title", "Channel", "Subscribers", "Views", "Date", "Source", "Support"):
        match = re.search(rf"(?im)^\s*{key}\s*:\s*(.+?)\s*$", full)
        if match:
            meta[key.lower()] = _clean_text(match.group(1))
    if "support" not in meta:
        support = re.search(r"(?im)^\s*Support(?:\s+our\s+mission)?\s*[-:]\s*(.+?)\s*$", full)
        if support:
            meta["support"] = _clean_text(support.group(1))
    description = re.search(
        r"(?ims)^\s*Description\s*:\s*(.*?)(?=^\s*(?:Source|Support|Transcript|Comments|Research|Links|References|Title|Channel|Subscribers|Views|Date)\s*:|^\s*Support(?:\s+our\s+mission)?\s*[-:]|^\s*(?:Transcript|Comments|Research|Links|References)\s*$|\Z)",
        full,
    )
    if description:
        meta["description"] = "\n".join(line.rstrip() for line in description.group(1).strip().splitlines()).strip()
    if "source" not in meta:
        link = re.search(r"https?://(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/)[^\s)>'\"]+", full, flags=re.IGNORECASE)
        if link:
            meta["source"] = _clean_text(link.group(0))
    return meta


def _source_text_metadata_summary(meta: Mapping[str, str]) -> str:
    lines: list[str] = []
    for label, key in (
        ("Title", "title"),
        ("Channel", "channel"),
        ("Subscribers", "subscribers"),
        ("Views", "views"),
        ("Date", "date"),
    ):
        value = str(meta.get(key) or "").strip()
        if value:
            lines.append(f"{label}: {value}")
    description = str(meta.get("description") or "").strip()
    if description:
        lines.append(f"Description: {description}")
    support = str(meta.get("support") or "").strip()
    if support:
        lines.append(f"Support: {support}")
    source = str(meta.get("source") or "").strip()
    if source:
        lines.append(f"Source: {source}")
    return "\n".join(lines)


def _url_source_role_status(url: object, *, section: str, display_label: str = "") -> str:
    url_text = _clean_text(url)
    label = _clean_text(display_label).casefold()
    lowered = url_text.casefold()
    if not url_text:
        return "NOT_A_SOURCE_REFERENCE"
    if section == "metadata" and ("source" in label or re.search(r"(?:youtube\.com/watch\?v=|youtu\.be/|x\.com/.+/status/)", lowered)):
        return "RESOLVED_PRIMARY_SOURCE"
    if "support" in label or "donate" in lowered:
        return "NOT_A_SOURCE_REFERENCE"
    if section == "comments":
        return "RESOLVED_SECONDARY_SOURCE"
    if section in {"external_sources", "research_notes", "copied_ai_analysis", "unknown_appendix"}:
        return "UNRESOLVED_SOURCE_REFERENCE"
    return "UNRESOLVED_SOURCE_REFERENCE"


def _source_link_role_candidates_from_artifacts(
    artifacts: Iterable[ProfileMediaSourcePackageArtifact],
    *,
    claim_spans: Iterable[Mapping[str, Any]] = (),
) -> tuple[dict[str, Any], ...]:
    """Prepare URL/source-link role data without adding a heavy editor yet."""

    candidates: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    span_links: dict[str, list[str]] = {}
    url_pattern = re.compile(
        r"https?://[^\s<>()'\"]+|(?<![A-Za-z0-9@._-])(?:www\.)?(?:[A-Za-z0-9-]+\.)+(?:com|org|net|gov|edu|io|ai|info|uk|co\.uk|org\.uk|gov\.uk|ac\.uk)(?:/[^\s<>()'\"]*)?",
        flags=re.IGNORECASE,
    )

    for span in claim_spans:
        if not isinstance(span, Mapping):
            continue
        text = str(span.get("text") or "")
        edit_key = _clean_text(span.get("edit_key"))
        if not edit_key:
            continue
        for match in url_pattern.finditer(text):
            span_links.setdefault(_clean_text(match.group(0).rstrip(".,;:)]}")), []).append(edit_key)

    def add(*, url: object, label: object, section: str, linked_persons: Iterable[str] = ()) -> None:
        url_text = _clean_text(str(url or "").rstrip(".,;:)]}"))
        if not url_text:
            return
        display = _clean_text(label, fallback=url_text)
        key = (url_text.casefold(), display.casefold(), section)
        if key in seen:
            return
        seen.add(key)
        candidates.append(
            {
                "url": url_text,
                "display_label": display,
                "source_role_status": _url_source_role_status(url_text, section=section, display_label=display),
                "section": section,
                "linked_persons": [_clean_text(item) for item in linked_persons if _clean_text(item)],
                "linked_claim_span_ids": list(dict.fromkeys(span_links.get(url_text, ()))),
            }
        )

    for artifact in artifacts:
        profile = _source_text_evidence_profile(artifact)
        if profile:
            source_url = _clean_text(profile.get("source_link") or profile.get("source_page"))
            if source_url:
                add(url=source_url, label="Source", section="metadata")
            source_text = _read_explicit_text_artifact(artifact.local_path)
            meta = _source_text_evidence_metadata(source_text)
            if meta.get("support"):
                add(url=meta.get("support"), label="Support", section="metadata")
            sections = _split_youtube_source_text_sections(source_text)
            for section in ("comments", "research_notes", "external_sources", "copied_ai_analysis", "unknown_appendix"):
                section_text = sections.get(section) or ""
                for match in url_pattern.finditer(section_text):
                    add(url=match.group(0), label=match.group(0), section=section)
        for value, label in (
            (artifact.source_url, "Artifact source URL"),
            (artifact.canonical_url, "Artifact canonical URL"),
            (artifact.reference_url, "Artifact reference URL"),
        ):
            if value:
                add(url=value, label=label, section="metadata")
    return tuple(candidates)


def _link_source_preview_from_artifacts(
    artifacts: Iterable[ProfileMediaSourcePackageArtifact],
    *,
    source_url: str = "",
    canonical_url: str = "",
    source_title: str = "",
) -> dict[str, Any]:
    """Build the V83B link/source-object layer without altering source counts."""

    link_records: list[dict[str, object]] = []
    rendered_html_parts: list[str] = []
    saved_page_text_parts: list[str] = []

    def add_text(text: object, *, label: str, path: str = "") -> None:
        source_text = str(text or "")
        if not source_text.strip():
            return
        saved_page_text_parts.append(source_text[:120_000])
        link_records.extend(
            extract_link_source_objects(
                source_text,
                source_label=label,
                source_path=path,
            )
        )

    root_lines = []
    if source_url:
        root_lines.extend(["Original URL:", source_url])
    if canonical_url and canonical_url != source_url:
        root_lines.extend(["Canonical URL:", canonical_url])
    add_text("\n".join(root_lines), label=source_title or "source")

    for artifact in artifacts:
        artifact_label = artifact.display_name or artifact.artifact_kind or "artifact"
        for label, value in (
            ("Artifact source URL", artifact.source_url),
            ("Artifact canonical URL", artifact.canonical_url),
            ("Artifact reference URL", artifact.reference_url),
        ):
            if value:
                add_text(f"{label}:\n{value}", label=artifact_label, path=artifact.local_path)
        html_text = _read_explicit_html_artifact(artifact.local_path)
        if html_text:
            rendered_html_parts.append(html_text)
        source_text = _read_explicit_text_artifact(artifact.local_path)
        if source_text:
            add_text(source_text, label=artifact_label, path=artifact.local_path)

    classified = classify_link_source_objects([dict(record) for record in link_records])
    enriched = enrich_link_source_objects_with_browser_network_provenance(
        classified,
        rendered_html="\n".join(rendered_html_parts),
        saved_page_text="\n".join(saved_page_text_parts),
        requested_url=source_url,
        final_url=canonical_url or source_url,
        capture_method="offline_source_package_preview",
    )
    return build_link_source_preview(enriched)


def _link_source_decisions_path_for_preview(
    artifacts: Iterable[ProfileMediaSourcePackageArtifact],
    *,
    database_root: str = "",
    source_title: str = "",
) -> str:
    for artifact in artifacts:
        local_path = str(getattr(artifact, "local_path", "") or "").strip()
        if local_path:
            path = Path(local_path)
            return str(path.with_name(path.stem + "_link_source_decisions.jsonl"))
    if database_root:
        safe_title = re.sub(r"[^A-Za-z0-9_.-]+", "_", source_title or "source").strip("_") or "source"
        return str(Path(database_root) / f"{safe_title}_link_source_decisions.jsonl")
    return "profile_media_link_source_decisions.jsonl"


_YOUTUBE_COMMENT_TIME_PATTERN = r"(?:\d+|one|a)\s+(?:second|minute|hour|day|week|month|year)s?\s+ago(?:\s*\(edited\))?|0\s+seconds?\s+ago(?:\s*\(edited\))?"
_YOUTUBE_COMMENT_TIME_RE = re.compile(
    rf"^{_YOUTUBE_COMMENT_TIME_PATTERN}$",
    flags=re.IGNORECASE,
)
_YOUTUBE_COMMENT_INLINE_HEADER_RE = re.compile(
    rf"^\s*(@[A-Za-z0-9_.-]+)(?:\s*\|\s*|\s+)({_YOUTUBE_COMMENT_TIME_PATTERN})\s*(.*)$",
    flags=re.IGNORECASE,
)
_YOUTUBE_COMMENT_HANDLE_RE = re.compile(r"^\s*(@[A-Za-z0-9_.-]+)\s*$")


def _is_youtube_comment_noise_line(value: object) -> bool:
    text = str(value or "").strip()
    lowered = text.casefold()
    if not text:
        return True
    if lowered in {
        "reply",
        "hide replies",
        "show replies",
        "show more",
        "read more",
        "translate",
        "translated",
        "top comments",
    }:
        return True
    if re.fullmatch(r"\d+", text):
        return True
    if re.fullmatch(r"\d+\s+(?:reply|replies)", text, flags=re.IGNORECASE):
        return True
    return False


def _next_non_noise_line(lines: list[str], start: int) -> tuple[int, str] | None:
    for index in range(start, len(lines)):
        text = lines[index].strip()
        if text:
            return index, text
    return None


def _youtube_comment_author_start(lines: list[str], index: int) -> bool:
    text = lines[index].strip() if 0 <= index < len(lines) else ""
    if _YOUTUBE_COMMENT_INLINE_HEADER_RE.match(text):
        return True
    handle = _YOUTUBE_COMMENT_HANDLE_RE.match(text)
    if not handle:
        return False
    next_line = _next_non_noise_line(lines, index + 1)
    return bool(next_line and _YOUTUBE_COMMENT_TIME_RE.match(next_line[1]))


def _clean_youtube_comment_text(lines: Iterable[str]) -> str:
    clean_lines = []
    for line in lines:
        text = str(line or "").strip()
        if _is_youtube_comment_noise_line(text):
            continue
        clean_lines.append(text)
    return _clean_text(" ".join(clean_lines))


def _parse_preserved_youtube_comment_records(comments_text: object) -> tuple[dict[str, object], ...]:
    """Parse preserved YouTube comments from copied text without network access."""

    lines = str(comments_text or "").replace("\r\n", "\n").replace("\r", "\n").split("\n")
    records: list[dict[str, object]] = []
    index = 0
    while index < len(lines):
        raw_line = lines[index]
        line = raw_line.strip()
        inline = _YOUTUBE_COMMENT_INLINE_HEADER_RE.match(line)
        handle = ""
        time_text = ""
        start_line = index + 1
        initial_text = ""
        if inline:
            handle = inline.group(1)
            time_text = _clean_text(inline.group(2))
            initial_text = _clean_text(inline.group(3))
            index += 1
        else:
            handle_match = _YOUTUBE_COMMENT_HANDLE_RE.match(line)
            if not handle_match:
                index += 1
                continue
            next_line = _next_non_noise_line(lines, index + 1)
            if not next_line or not _YOUTUBE_COMMENT_TIME_RE.match(next_line[1]):
                index += 1
                continue
            handle = handle_match.group(1)
            time_text = _clean_text(next_line[1])
            index = next_line[0] + 1

        body_lines = [initial_text] if initial_text else []
        while index < len(lines):
            if _youtube_comment_author_start(lines, index):
                break
            body_lines.append(lines[index])
            index += 1
        body = _clean_youtube_comment_text(body_lines)
        if not body:
            continue
        records.append(
            {
                "author_handle": handle,
                "time": time_text,
                "text": body,
                "start_line": start_line,
            }
        )
    return tuple(records)


def extract_preserved_youtube_comment_threads(
    comments_text: object,
    *,
    author_handle: str = "@RevBrettMurphy",
) -> tuple[dict[str, object], ...]:
    """Extract authored comments/replies with nearest parent context.

    Mentions of the handle inside another user's comment are not considered
    authored comments. Only parsed comment headers/authors match.
    """

    target = "@" + str(author_handle or "").strip().lstrip("@").casefold()
    parsed = _parse_preserved_youtube_comment_records(comments_text)
    threads: list[dict[str, object]] = []
    last_non_target: dict[str, object] | None = None
    for record in parsed:
        handle = str(record.get("author_handle") or "").casefold()
        if handle == target:
            threads.append(
                {
                    "index": len(threads) + 1,
                    "brett": dict(record),
                    "original_context": dict(last_non_target) if last_non_target else None,
                    "context_note": "nearest visible preceding non-Brett comment before Brett-authored comment" if last_non_target else "no clear preceding non-Brett parent comment detected in the preserved source order",
                    "counts_as_person": False,
                    "brett_person_section": "comments",
                    "merged_into_canonical_transcript": False,
                    "affects_transcript_claim_span_counts": False,
                }
            )
        else:
            last_non_target = dict(record)
    return tuple(threads)


def format_youtube_comment_threads_for_review_display(threads: Iterable[Mapping[str, Any]]) -> str:
    """Format matched comment threads for the Review transcript box."""

    lines = ["------", "YouTube Comments", ""]
    wrote_any = False
    for thread in threads:
        if not isinstance(thread, Mapping):
            continue
        parent = thread.get("original_context") if isinstance(thread.get("original_context"), Mapping) else None
        brett = thread.get("brett") if isinstance(thread.get("brett"), Mapping) else None
        if parent:
            parent_handle = _clean_text(parent.get("author_handle"))
            parent_time = _clean_text(parent.get("time"))
            parent_text = _clean_text(parent.get("text"))
            if parent_handle or parent_time:
                lines.append(" | ".join(part for part in (parent_handle, parent_time) if part))
            if parent_text:
                lines.append(parent_text)
            lines.append("")
        if brett:
            brett_handle = _clean_text(brett.get("author_handle"))
            brett_time = _clean_text(brett.get("time"))
            brett_text = _clean_text(brett.get("text"))
            if brett_handle or brett_time:
                lines.append("    " + " | ".join(part for part in (brett_handle, brett_time) if part))
            if brett_text:
                lines.append("    " + brett_text)
            lines.append("")
            wrote_any = True
    return "\n".join(lines).rstrip() if wrote_any else ""


def _looks_like_operator_source_text(text: object) -> bool:
    """Return true for source/transcript dossier TXT files, not app-generated article text."""

    full = str(text or "")
    if not full.strip():
        return False
    meta = _source_text_evidence_metadata(full)
    lowered = full.lower()
    has_source = bool(meta.get("source"))
    has_transcript = "transcript" in lowered or bool(re.search(r"\d{1,2}:\d{2}\s*-\s*\d{1,2}:\d{2}", full))
    has_channel_or_title = bool(meta.get("channel") or meta.get("title"))
    return bool(has_source and has_transcript and has_channel_or_title)


def _is_app_generated_text_artifact_path(path_text: object) -> bool:
    lowered = str(path_text or "").replace("\\", "/").lower()
    return (
        "profile_media_generic_website_live_captures" in lowered
        or "profile_media_database_import_previews" in lowered
        or lowered.endswith("/article_text.txt")
        or lowered.endswith("/full_webpage_text.txt")
        or lowered.endswith("/rendered_page.html")
    )


def _source_text_evidence_profile(artifact: ProfileMediaSourcePackageArtifact) -> dict[str, str] | None:
    """Return source-text evidence metadata when a local TXT/MD carries its own source link/transcript."""

    path_text = artifact.local_path or artifact.display_name
    suffix = Path(str(path_text or "")).suffix.lower()
    if suffix not in {".txt", ".md"}:
        return None
    # App-generated article/body text remains a preservation artifact for the webpage.
    # Operator-added source/transcript TXT files become their own source scopes.
    content = _read_explicit_text_artifact(artifact.local_path)
    if not _looks_like_operator_source_text(content):
        return None
    meta = _source_text_evidence_metadata(content)
    source_link = _clean_text(meta.get("source") or artifact.reference_url or artifact.source_url or artifact.canonical_url or artifact.local_path)
    title = _clean_text(meta.get("title"), fallback=_clean_text(artifact.display_name, fallback=Path(str(artifact.local_path)).name))
    channel = _clean_text(meta.get("channel"))
    date = _clean_text(meta.get("date"))
    display = _clean_text(artifact.display_name, fallback=Path(str(artifact.local_path)).name)
    summary_parts = [part for part in (title, f"Channel: {channel}" if channel else "", f"Date: {date}" if date else "") if part]
    metadata_summary = _source_text_metadata_summary(meta)
    return {
        "source_page": source_link,
        "source_title": f"{display} — media/source provenance summary",
        "source_summary": " | ".join(summary_parts),
        "source_link": source_link,
        "source_excerpt": "",
        "source_metadata_summary": metadata_summary,
        "title": title,
        "channel": channel,
        "date": date,
    }


def _source_evidence_texts_from_artifacts(artifacts: Iterable[ProfileMediaSourcePackageArtifact]) -> tuple[tuple[ProfileMediaSourcePackageArtifact, str, dict[str, str]], ...]:
    output: list[tuple[ProfileMediaSourcePackageArtifact, str, dict[str, str]]] = []
    for artifact in artifacts:
        profile = _source_text_evidence_profile(artifact)
        if not profile:
            continue
        content = _read_explicit_text_artifact(artifact.local_path)
        if content:
            output.append((artifact, content, profile))
    return tuple(output)


def build_claim_role_classification_preview_from_artifacts(
    artifacts: Iterable[ProfileMediaSourcePackageArtifact],
) -> dict[str, Any]:
    """Classify clause-level claim roles for operator source/transcript TXT files.

    This is intentionally separate from media/source role scaffolding.  The TXT
    source itself can be primary source material while individual transcript
    clauses still classify as Primary, Secondary, Tertiary, Unknown, or Blank.
    """

    span_records: list[dict[str, Any]] = []
    transcript_streams: list[dict[str, Any]] = []
    article_streams: list[dict[str, Any]] = []
    for evidence_index, (artifact, source_text, source_profile) in enumerate(_source_evidence_texts_from_artifacts(artifacts), start=1):
        sections = _split_youtube_source_text_sections(source_text)
        transcript_text = sections.get("transcript") or source_text
        canonical = canonicalize_duplicate_transcript_stream(transcript_text)
        # duplicate_raw_transcript_section_flag_guard
        duplicate_raw_transcript_text = str(sections.get("duplicate_raw_transcript") or "").strip()
        if duplicate_raw_transcript_text and not canonical.get("duplicate_transcript_representations_detected"):
            canonical = dict(canonical)
            canonical["duplicate_transcript_representations_detected"] = True
            canonical["duplicate_raw_transcript_text"] = duplicate_raw_transcript_text
            canonical["duplicate_raw_transcript_section_label"] = "duplicate_raw_transcript"
            canonical["parts_seen"] = max(int(canonical.get("parts_seen", 1) or 1), 2)
            canonical["parts_kept"] = int(canonical.get("parts_kept", 1) or 1)
        # duplicate_transcript_marker_from_full_source_text_guard
        # sections_by_type keeps the canonical Transcript body only; preserve the
        # duplicate-representation flag when the original operator TXT contains
        # a second Transcript section after a ---- separator.
        if (
            not canonical.get("duplicate_transcript_representations_detected")
            and sections.get("transcript")
            and re.search(r"(?is)\n\s*-{4,}\s*\n\s*Transcript\s:", str(source_text or ""))
        ):
            duplicate_probe = canonicalize_duplicate_transcript_stream(source_text)
            canonical = dict(canonical)
            canonical["duplicate_transcript_representations_detected"] = True
            canonical["duplicate_raw_transcript_text"] = str(duplicate_probe.get("duplicate_raw_transcript_text") or "")
            canonical["duplicate_raw_transcript_section_label"] = str(duplicate_probe.get("duplicate_raw_transcript_section_label") or "duplicate_raw_transcript")
            canonical["parts_seen"] = max(int(canonical.get("parts_seen", 1) or 1), int(duplicate_probe.get("parts_seen", 2) or 2))
            canonical["parts_kept"] = int(canonical.get("parts_kept", 1) or 1)
        source_id = f"source_text_{evidence_index:02d}"
        media_source_role = "PRIMARY_SOURCE_EVIDENCE"
        spans = classify_transcript_text(
            canonical.get("text", transcript_text),
            source_id=source_id,
            media_source_role=media_source_role,
        )
        source_url = _clean_text(source_profile.get("source_link") or source_profile.get("source_page"))
        source_title = _clean_text(source_profile.get("title") or source_profile.get("source_title") or artifact.display_name, fallback=f"Source text {evidence_index}")
        for span in spans:
            row = span.to_dict()
            row.update(
                {
                    "source_url": source_url,
                    "source_title": source_title,
                    "artifact_display_name": artifact.display_name,
                    "artifact_local_path": artifact.local_path,
                    "section_label": "transcript",
                    "claim_span_role_system": "claim/span",
                    "media_source_role_system": "media/source",
                    "final_source_role_decision": False,
                }
            )
            span_records.append(row)
        transcript_streams.append(
            {
                "source_id": source_id,
                "source_url": source_url,
                "source_title": source_title,
                "artifact_display_name": artifact.display_name,
                "artifact_local_path": artifact.local_path,
                "canonical_transcript_text": canonical.get("text", transcript_text),
                "duplicate_raw_transcript_text": canonical.get("duplicate_raw_transcript_text", ""),
                "duplicate_raw_transcript_section_label": canonical.get("duplicate_raw_transcript_section_label", ""),
                "duplicate_transcript_representations_detected": bool(canonical.get("duplicate_transcript_representations_detected")),
                "parts_seen": int(canonical.get("parts_seen", 1) or 1),
                "parts_kept": int(canonical.get("parts_kept", 1) or 1),
                "span_count": len(spans),
                "media_source_role": media_source_role,
            }
        )
    for article_index, artifact in enumerate(artifacts, start=1):
        kind = normalise_source_package_artifact_kind(artifact.artifact_kind, path=artifact.local_path or artifact.display_name)
        raw_article_text = _read_explicit_text_artifact(artifact.local_path)
        article_text = _article_text_body_after_top_link_preamble(raw_article_text)
        has_top_link_preamble = bool(article_text.strip()) and article_text.strip() != str(raw_article_text or "").strip()
        if kind not in {"article_text", "webpage_text"} and not (
            has_top_link_preamble and Path(str(artifact.local_path or artifact.display_name or "")).suffix.lower() in {".txt", ".md"}
        ):
            continue
        if _source_text_evidence_profile(artifact) and not has_top_link_preamble:
            continue
        if not article_text:
            continue
        source_id = f"article_text_{article_index:02d}"
        source_url = _clean_text(artifact.canonical_url or artifact.source_url or artifact.reference_url)
        source_title = _clean_text(artifact.display_name, fallback=f"Article text {article_index}")
        spans = classify_claim_text(
            article_text,
            source_id=source_id,
            speaker="Article text",
            media_source_role="SECONDARY_MEDIA_COPY",
        )
        article_span_count = 0
        for span in spans:
            row = span.to_dict()
            if not _clean_text(row.get("text")):
                continue
            row.update(
                {
                    "source_url": source_url,
                    "source_title": source_title,
                    "artifact_display_name": artifact.display_name,
                    "artifact_local_path": artifact.local_path,
                    "section_label": "article_text",
                    "source_stream": "article_text",
                    "is_article_text_claim_span": True,
                    "claim_span_role_system": "claim/span",
                    "media_source_role_system": "media/source",
                    "final_source_role_decision": False,
                }
            )
            span_records.append(row)
            article_span_count += 1
        article_streams.append(
            {
                "source_id": source_id,
                "source_url": source_url,
                "source_title": source_title,
                "artifact_display_name": artifact.display_name,
                "artifact_local_path": artifact.local_path,
                "canonical_article_text": article_text[:120000],
                "section_label": "article_text",
                "YTCE_V83C_REPAIR10_INLINE_ARTICLE_STREAM_TEXT": True,
                "article_text_source_roles_enabled": True,
                "span_count": article_span_count,
                "media_source_role": "SECONDARY_MEDIA_COPY",
            }
        )
    tag_plan = {
        "schema_version": "profile-media-full-transcript-role-tags-v1",
        "policy_version": CLAIM_ROLE_POLICY_VERSION,
        "full_transcript_order_preserved": True,
        "clause_level_tags": True,
        "max_visible_height_per_card": True,
        "internal_scrollbar_required": True,
        "spans": span_records,
        "tag_ranges": [
            {
                "tag": f"claim_role_{span.get('role', '').lower()}",
                "source_id": span.get("source_id", ""),
                "timestamp_start": span.get("timestamp_start", ""),
                "timestamp_end": span.get("timestamp_end", ""),
                "char_start": span.get("char_start", 0),
                "char_end": span.get("char_end", 0),
                "edit_key": span.get("edit_key", ""),
            }
            for span in span_records
        ],
    }
    return {
        "schema_version": "profile-media-claim-role-classification-preview-v1",
        "policy_version": CLAIM_ROLE_POLICY_VERSION,
        "classifier_module": "profile_media_claim_role_classifier",
        "claim_span_role_system": "claim/span",
        "media_source_role_system": "media/source",
        "media_source_role_separate_from_claim_span_role": True,
        "unknown_role_is_assigned": True,
        "blank_role_is_assigned": True,
        "review_unassigned_only_for_classifier_failure": True,
        "canonical_transcript_stream_used": True,
        "full_transcript_order_preserved": True,
        "clause_level_spans": True,
        "span_count": len(span_records),
        "transcript_stream_count": len(transcript_streams),
        "transcript_streams": transcript_streams,
        "article_text_stream_count": len(article_streams),
        "article_text_streams": article_streams,
        "article_text_source_roles_enabled": bool(article_streams),
        "spans": span_records,
        "tag_plan": tag_plan,
    }


def build_transcript_provenance_preview_from_artifacts(
    artifacts: Iterable[ProfileMediaSourcePackageArtifact],
) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    for evidence_index, (artifact, source_text, source_profile) in enumerate(_source_evidence_texts_from_artifacts(artifacts), start=1):
        lowered = source_text.casefold()
        source_url = _clean_text(source_profile.get("source_link") or source_profile.get("source_page"))
        if "verified against primary media" in lowered or "checked against the audio" in lowered or "checked against the video" in lowered:
            role = "VERIFIED_SECONDARY_TRANSCRIPT"
            display = "Transcript: Secondary [Verified against Primary media]"
        elif "youtube auto transcript" in lowered or "youtube transcript" in lowered or "auto-generated transcript" in lowered:
            role = "SECONDARY_TRANSCRIPT"
            display = "Transcript: Secondary [YouTube transcript]"
        elif "youtube-transcript.ai" in lowered or "third-party transcript" in lowered or "derived from platform transcript" in lowered:
            role = "TERTIARY_TRANSCRIPT"
            display = "Transcript: Tertiary [Derived from platform transcript]"
        else:
            role = "SECONDARY_TRANSCRIPT_UNSPECIFIED_PROVENANCE"
            display = "Transcript: Secondary [Transcript text file; provenance not recorded]"
        records.append(
            {
                "source_id": f"source_text_{evidence_index:02d}",
                "source_url": source_url,
                "source_title": _clean_text(source_profile.get("title") or source_profile.get("source_title") or artifact.display_name),
                "artifact_local_path": artifact.local_path,
                "media_source_display": "Media source: Primary [Original video/audio URL]" if source_url else "Media source: Unknown [Original video/audio URL not recorded]",
                "media_source_role": "PRIMARY_MEDIA_URL" if source_url else "UNKNOWN_PROVENANCE",
                "transcript_provenance_role": role,
                "transcript_provenance_display": display,
                "transcript_is_primary_media": False,
                "transcript_provenance_detail": "UNKNOWN_OR_UNRECORDED" if role == "SECONDARY_TRANSCRIPT_UNSPECIFIED_PROVENANCE" else role,
                "review_required": False,
            }
        )
    return {
        "schema_version": "profile-media-transcript-provenance-preview-v1",
        "media_source_provenance_layer": True,
        "transcript_provenance_layer": True,
        "record_count": len(records),
        "records": records,
    }


def _split_youtube_source_text_sections(text: object) -> dict[str, str]:
    """Split an operator TXT into metadata/transcript/comments/research/source sections.

    Source TXT files used by the Review window often contain several different
    evidence layers: YouTube metadata, a transcript, comments, and then the
    operator's own research notes. Person extraction and role-span review must
    not treat all of those as one transcript.
    """

    return sections_by_type(split_source_text_sections(text))


def _normalised_match_text(value: object) -> str:
    text = str(value or "").lower()
    text = text.replace("muhammadans", "mohammedans")
    text = text.replace("‘", "'").replace("’", "'").replace("“", '"').replace("”", '"')
    return " ".join(re.sub(r"[^a-z0-9']+", " ", text).split())


def _evidence_contains_phrase(evidence_items: Iterable[tuple[ProfileMediaSourcePackageArtifact, str, dict[str, str]]], *phrases: str) -> bool:
    if not phrases:
        return False
    normalised_evidence = "\n".join(_normalised_match_text(item[1]) for item in evidence_items)
    return all(_normalised_match_text(phrase) in normalised_evidence for phrase in phrases if phrase)


def _source_evidence_excerpt_for_text(text: object) -> str:
    """Return a compact source/transcript excerpt for Review source scopes."""

    full = str(text or "")
    sections = _split_youtube_source_text_sections(full)
    # The visible source excerpt should be transcript/source evidence, not later
    # comments or operator research notes.
    full = sections.get("transcript") or full
    if not full.strip():
        return ""
    chunks: list[str] = []

    def add(pattern: str, *, label: str = "", window: int = 260, limit: int = 900) -> None:
        excerpt = _excerpt_around(full, pattern, window=window)
        if excerpt and excerpt not in chunks:
            chunks.append((label + ": " if label else "") + _trim_to_word_boundary(excerpt, limit=limit))

    # Metro/Brett-Murphy evidence paths.  These are generic phrase anchors: if
    # another transcript has the same relevant statement, the source scope still
    # surfaces the matching passage rather than only the title/source header.
    if re.search(r"practice\s+black\s+magic|Talmudists|Doug\s+Wilson", full, flags=re.IGNORECASE):
        add(r"(Now\s+that\s+doesn['’]t\s+mean.*?practice\s+black\s+magic.*?false\s+religion\.)", label="Judaism / black-magic passage", window=380, limit=1400)
        add(r"(It['’]s\s+likewise\s+undeniable.*?very\s+very\s+bad.*?)", label="Doug Wilson / Jews quote passage", window=180, limit=900)
    if re.search(r"hordes\s+of\s+heathen\s+Moha?mmedans|army\s+of\s+heathens", full, flags=re.IGNORECASE):
        add(r"(Absolutely\.\s+End\s+the\s+homosexual\s+adoption.*?army\s+of\s+heathens\s+who\s+want\s+to\s+kill\s+us\.)", label="Project Britannia / Muslims quote passage", window=180, limit=1200)
    if re.search(r"absolute\s+retards\s+turned?\s+to\s+Islam|Allah\s+is\s+Satan|Muhammad['’]s\s+a\s+false\s+prophet", full, flags=re.IGNORECASE):
        add(r"(It['’]s\s+why\s+you\s+get\s+so\s+many.*?Muhammad['’]s\s+a\s+false\s+prophet.*?)", label="Turned-to-Islam quoted passage", window=300, limit=1500)
    if re.search(r"sodomite\s+parades|homosexual\s+adoption|progress\s+pride\s+flag", full, flags=re.IGNORECASE):
        add(r"(We\s+need\s+to\s+end\s+the\s+sodomite\s+parades.*?homosexual\s+adoption.*?abuse\s+of\s+children\.)", label="Pride/adoption passage", window=180, limit=1000)
        add(r"(So,?\s+uh\s+very\s+early\s+in\s+my\s+time.*?progress\s+pride\s+flag.*?blasphemous\s+affront\s+to\s+God\.)", label="Pride-flag passage", window=180, limit=1000)
    return "\n\n".join(chunks)


def _evidence_contains_any_phrase(evidence_items: Iterable[tuple[ProfileMediaSourcePackageArtifact, str, dict[str, str]]], *phrases: str) -> bool:
    normalised_evidence = "\n".join(_normalised_match_text(item[1]) for item in evidence_items)
    return any(_normalised_match_text(phrase) in normalised_evidence for phrase in phrases if phrase)

def _article_text_from_artifacts(artifacts: Iterable[ProfileMediaSourcePackageArtifact]) -> str:
    """Return explicit article/webpage text from already-selected text artifacts."""

    article_texts: list[str] = []
    fallback_webpage_texts: list[str] = []
    mixed_texts: list[str] = []
    for artifact in artifacts:
        kind = normalise_source_package_artifact_kind(artifact.artifact_kind, path=artifact.local_path or artifact.display_name)
        content = _read_explicit_text_artifact(artifact.local_path)
        if not content:
            continue
        body_after_links = _article_text_body_after_top_link_preamble(content)
        has_top_link_preamble = body_after_links.strip() and body_after_links.strip() != str(content or "").strip()
        if _source_text_evidence_profile(artifact) and not has_top_link_preamble:
            # Source/transcript TXT files are their own evidence scopes; do not
            # mix them into the publisher article body used for article segments.
            continue
        if kind == "article_text":
            article_texts.append(body_after_links)
        elif kind == "webpage_text":
            fallback_webpage_texts.append(body_after_links)
        elif has_top_link_preamble and Path(str(artifact.local_path or artifact.display_name or "")).suffix.lower() in {".txt", ".md"}:
            mixed_texts.append(body_after_links)
    return "\n".join(article_texts or fallback_webpage_texts or mixed_texts)


def _line_is_top_link_preamble(line: str) -> bool:
    # V83C_REPAIR8_TOP_LINK_PREAMBLE_BOM
    # V83C_REPAIR10_TOP_LINK_PREAMBLE_LABEL_WITH_URL
    clean = str(line or "").replace("\ufeff", "").strip()
    if not clean:
        return True
    if re.fullmatch(r"(?i)(?:source\s+url|archive\s+url|wayback|archive(?:\s+today)?|archive\.ph|live|url|links?)\s*:?(?:\s*(?:https?://|www\.)\S+)?", clean):
        return True
    if re.fullmatch(r"(?i)(?:[-*]\s*)?(?:https?://|www\.)\S+", clean):
        return True
    if re.fullmatch(r"(?i)(?:[-*]\s*)?\[[^\]]+\]\(\s*https?://[^)]+\)", clean):
        return True
    return False

def _article_text_body_after_top_link_preamble(text: object) -> str:
    """Return article body when a TXT starts with URL/archive lines.

    V83D mixed source files can begin with a live URL, Wayback URL and archive.ph
    URL, then continue directly into article title/byline/body without a ----
    separator.  Link extraction still reads the original file; this helper only
    prevents the article/source-role span classifier from treating the preamble
    as the article body.
    """

    lines = str(text or "").replace("\r\n", "\n").replace("\r", "\n").split("\n")
    index = 0
    saw_url = False
    while index < len(lines) and _line_is_top_link_preamble(lines[index]):
        if re.search(r"(?i)https?://|www\.", lines[index]):
            saw_url = True
        index += 1
    if not saw_url:
        return str(text or "")
    body = "\n".join(lines[index:]).strip()
    return body or str(text or "")


def _article_media_details_from_text(text: object) -> list[dict[str, Any]]:
    """Extract bounded article-media role hints from already-preserved text."""

    full = str(text or "")
    lowered = full.casefold()
    details: list[dict[str, Any]] = []
    if re.search(r"\b(secretly\s+filmed\s+clip|viral\s+video|shared\s+the\s+video|video\s+clip)\b", full, flags=re.IGNORECASE):
        details.append(
            {
                "label": "Media",
                "role": "Unknown",
                "reason": "article describes a secretly filmed clip / viral video, but no original social-media embed, source URL, full duration, uploader provenance, or edit-status evidence is preserved.",
                "source_object_type": "embedded_or_reported_video",
            }
        )
    if "@activepatriotuk" in lowered or re.search(r"Picture\s*:\s*@\w+", full, flags=re.IGNORECASE):
        details.append(
            {
                "label": "Image 1",
                "role": "Unknown",
                "reason": "source text/caption exists but no linked original source URL is preserved.",
                "potential_role_if_linked_source_found": "Tertiary or inherited, depending on target.",
                "source_object_type": "credited_image_without_source_url",
            }
        )
    supplied_count = len(re.findall(r"Picture\s*:\s*Supplied", full, flags=re.IGNORECASE))
    for supplied_index in range(supplied_count):
        details.append(
            {
                "label": f"Image {supplied_index + 2}" if any(item.get("label") == "Image 1" for item in details) else f"Image {supplied_index + 1}",
                "role": "Secondary",
                "reason": "Picture: Supplied.",
                "source_object_type": "supplied_article_image",
            }
        )
    return details


def _article_has_direct_witness_account(text: object) -> bool:
    """True when the publisher article contains its own direct interview/witness account.

    This is intentionally conservative but not pronoun-only.  Metro often writes
    "Alejandro Sanchez, from the NSS, told Metro" or "A spokesperson said" rather
    than "he/she told Metro".  These patterns mean the article has a direct
    quoted source relationship even if another claim in the same article remains
    Unknown until source-chain evidence is attached.
    """

    full_text = str(text or "")
    return bool(
        re.search(r"\b(?:she|he|they)\s+told\s+Metro\b", full_text, flags=re.IGNORECASE)
        or re.search(r"\b[A-Z][A-Za-z'’.-]+(?:\s+[A-Z][A-Za-z'’.-]+){0,4}[^\n]{0,100}\btold\s+Metro\b", full_text)
        or re.search(r"\b[Aa]\s+[^\n]{0,80}\bspokesperson\s+said\s*[:‘']", full_text)
        or re.search(r"\bOn\s+the\s+rescue,\s+she\s+said\b", full_text, flags=re.IGNORECASE)
        or re.search(r"\b(?:said|told)\s+(?:the\s+paper|the\s+outlet|the\s+publisher)\b", full_text, flags=re.IGNORECASE)
    )


def _article_author_candidate(text: object) -> dict[str, Any] | None:
    """Extract a conservative article-author person candidate from the captured article header."""

    lines = [line.strip() for line in str(text or "").splitlines() if line.strip()]
    excluded_prefixes = (
        "title:",
        "source url:",
        "final url:",
        "article extraction",
        "published ",
        "updated ",
        "exclusive",
    )
    job_title_words = re.compile(r"\b(?:reporter|editor|writer|journalist|correspondent|producer|news|senior|night)\b", re.IGNORECASE)

    def build(name: str, title: str) -> dict[str, Any] | None:
        name = _clean_text(name)
        title = _clean_text(title)
        if not name or any(token.lower() in {"source", "title", "article", "published", "updated", "exclusive"} for token in name.split()):
            return None
        direct = _article_has_direct_witness_account(text)
        return {
            "canonical_name": name,
            "role_in_event": "article author / interviewer" if direct else "article author / reporter",
            "source_role_candidate": ProfileSourceRole.SECONDARY_WITNESS_ACCOUNT.value if direct else ProfileSourceRole.TERTIARY_PROPAGATED_SOURCE.value,
            "claim_basis_candidate": ClaimBasis.WITNESS_ACCOUNT.value if direct else ClaimBasis.AGENCY_OR_OUTSIDE_RETELLING.value,
            "associations": ["Metro"],
            "designation_candidates": [],
            "review_required": False,
            "final_person_decision": False,
            "notes": title,
        }

    for i, line in enumerate(lines[:28]):
        lowered = line.lower()
        if lowered.startswith(excluded_prefixes):
            continue
        match = re.match(r"^([A-Z][A-Za-z'’.-]+(?:\s+[A-Z][A-Za-z'’.-]+){1,4})\s*\|\s*(.{3,80})$", line)
        if match:
            candidate = build(match.group(1), match.group(2))
            if candidate:
                return candidate
            continue
        # Metro JSON/plain text commonly stores the byline and job title on
        # adjacent lines: "Brooke Davies" then "Senior News reporter".
        if not re.match(r"^[A-Z][A-Za-z'’.-]+(?:\s+[A-Z][A-Za-z'’.-]+){1,4}$", line):
            continue
        if i + 1 >= len(lines):
            continue
        next_line = lines[i + 1].strip()
        if job_title_words.search(next_line) and not next_line.lower().startswith(excluded_prefixes):
            candidate = build(line, next_line)
            if candidate:
                return candidate
    return None

def source_role_for_source_page_from_text(text: object) -> str:
    """Return the article/source-page role according to the author's relation to the material."""

    if _article_has_direct_witness_account(text):
        return canonical_source_role(ProfileSourceRole.SECONDARY_WITNESS_ACCOUNT.value)
    return source_role_for_package_artifact_kind("source_page", root_source_record=True)


def claim_basis_for_source_page_from_text(text: object) -> str:
    if _article_has_direct_witness_account(text):
        return ClaimBasis.WITNESS_ACCOUNT.value
    return claim_basis_for_package_artifact_kind("source_page", root_source_record=True)


def _trim_to_word_boundary(text: str, *, limit: int = 720) -> str:
    cleaned = ' '.join(str(text or '').split()).strip()
    if len(cleaned) <= limit:
        return cleaned
    cut = cleaned[:limit].rstrip()
    last_space = cut.rfind(' ')
    if last_space > max(80, limit // 2):
        cut = cut[:last_space].rstrip()
    return cut + ' …'


def _excerpt_around(text: str, pattern: str, *, fallback: str = '', window: int = 260, limit: int = 840) -> str:
    match = re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL)
    if not match:
        return _trim_to_word_boundary(fallback, limit=limit)
    # Prefer whole-line/paragraph starts so excerpts do not begin mid-word
    # (for example: "itional Islamic dress...").
    start = match.start()
    line_start = text.rfind('\n', 0, start)
    if line_start >= 0:
        start = line_start + 1
    else:
        start = max(0, start - 40)
        while start > 0 and text[start - 1].isalnum():
            start -= 1
    end = min(len(text), match.end() + window)
    # Include a few following paragraphs, then trim cleanly.
    newline_count = 0
    cursor = match.end()
    while cursor < len(text) and newline_count < 4:
        if text[cursor] == '\n':
            newline_count += 1
        cursor += 1
    end = max(end, min(cursor, len(text)))
    return _trim_to_word_boundary(text[start:end], limit=limit)


def _matched_excerpt(text: str, pattern: str, *, fallback: str = "", limit: int = 1200) -> str:
    """Return only the exact matched source sentence/quote, not following article context."""

    match = re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL)
    if not match:
        return _trim_to_word_boundary(fallback, limit=limit)
    return _trim_to_word_boundary(match.group(1), limit=limit)

def build_source_role_segment_candidates_from_artifacts(
    *,
    source_title: object = '',
    source_url: object = '',
    artifacts: Iterable[ProfileMediaSourcePackageArtifact] = (),
) -> tuple[dict[str, Any], ...]:
    """Build review-lane candidates from explicit captured article text.

    These are not final source records. They are review options for mixed-role
    article material: direct witness quotes, reported self-authored posts, and
    propagated media/source-chain gaps. The function only reads explicit local
    text artifacts already selected by the operator.
    """

    full_text = _article_text_from_artifacts(artifacts)
    evidence_items = _source_evidence_texts_from_artifacts(artifacts)
    candidates: list[dict[str, Any]] = []

    def add(
        segment_id: str,
        subject: str,
        role: str,
        basis: str,
        reason: str,
        excerpt: str,
        *,
        source_chain_gap: bool = True,
        review_required: bool | None = None,
        source_url_override: str = "",
        source_title_override: str = "",
    ) -> None:
        if any(item.get('segment_id') == segment_id for item in candidates):
            return
        canonical_role = canonical_source_role(role)
        candidate = {
            'segment_id': segment_id,
            'subject': subject,
            'candidate_source_role': canonical_role,
            'candidate_claim_basis': basis,
            'review_reason': reason,
            'source_chain_gap': bool(source_chain_gap),
            'final_source_role_decision': False,
            'review_required': bool(source_chain_gap) if review_required is None else bool(review_required),
            'excerpt': excerpt,
        }
        if source_url_override:
            candidate['source_url'] = _clean_text(source_url_override)
        if source_title_override:
            candidate['source_title'] = _clean_text(source_title_override)
        if source_chain_gap and canonical_role == 'UNKNOWN_SOURCE_ROLE':
            candidate['potential_source_role_after_chain_verification'] = 'PRIMARY_SELF_AUTHORED_SCOPE'
            candidate['role_gap_label'] = 'Gap'
        candidates.append(candidate)


    if full_text:
        if re.search(r'\bShe told\s+Metro\b|\bOn the rescue, she said\b|\bNora Mubarak\b', full_text, flags=re.IGNORECASE):
            add(
                'main_person_direct_account_secondary_candidate',
                'Nora Mubarak / witness account',
                'SECONDARY_WITNESS_ACCOUNT',
                ClaimBasis.WITNESS_ACCOUNT.value,
                'Witness account',
                _excerpt_around(full_text, r'(She told\s+Metro.*?posted it and it went viral\.)', fallback=_excerpt_around(full_text, r'(A Muslim woman.*?Seagull Appreciation Society.*?)')),
                source_chain_gap=False,
                review_required=False,
            )
        if re.search(r'Oliver\s+Freeston.*?caption', full_text, flags=re.IGNORECASE | re.DOTALL):
            add(
                'oliver_freeston_reported_post_primary_gap_candidate',
                'Oliver Freeston / social-media caption | Gap',
                'UNKNOWN_SOURCE_ROLE',
                ClaimBasis.UNKNOWN_CLAIM_BASIS.value,
                'No source',
                _matched_excerpt(
                    full_text,
                    r"(But\s+Oliver\s+Freeston,\s+the\s+Reform\s+UK\s+leader\s+of\s+North\s+East\s+Lincolnshire\s+Council,\s+shared\s+the\s+video\s+on\s+Facebook\s+with\s+the\s+caption:\s*[‘']Grimsby\s+in\s+2026[’']\.?)",
                    fallback=_excerpt_around(full_text, r'(Oliver\s+Freeston.*?caption:?.*?Grimsby in 2026.?)'),
                ),
                source_chain_gap=True,
                review_required=False,
            )
        if re.search(r'Tommy\s+Robinson.*?(He wrote|wrote:|adding his own agenda)', full_text, flags=re.IGNORECASE | re.DOTALL):
            add(
                'tommy_robinson_reported_post_primary_gap_candidate',
                'Tommy Robinson / social-media statement | Gap',
                'UNKNOWN_SOURCE_ROLE',
                ClaimBasis.UNKNOWN_CLAIM_BASIS.value,
                'No source',
                _matched_excerpt(
                    full_text,
                    r"(Far-right\s+leader\s+Tommy\s+Robinson\s+also\s+shared\s+the\s+video,\s+adding\s+his\s+own\s+agenda\.\s+He\s+wrote:\s*[‘'][^’']*?Get\s+these\s+backwards\s+people\s+out![’']\.?)",
                    fallback=_excerpt_around(full_text, r'(Tommy\s+Robinson.*?He wrote.*?Get these backwards people out!?.?)'),
                ),
                source_chain_gap=True,
                review_required=False,
            )
        if re.search(r'\bBrett\s+Murphy\b|Reverend\s+Brett\s+Murphy|Project\s+Britannia', full_text, flags=re.IGNORECASE):
            if not evidence_items:
                add(
                    'brett_murphy_reported_sermon_video_unknown_candidate',
                    'Brett Murphy / reported sermon and online video',
                    'UNKNOWN_SOURCE_ROLE',
                    ClaimBasis.UNKNOWN_CLAIM_BASIS.value,
                    'Reported claims in article text; attach transcript/source evidence for original-sermon verification',
                    _matched_excerpt(
                        full_text,
                        r'(A\s+Christian\s+church\s+has\s+been\s+reported.*?He\s+adds:\s*.*?desperate[.?’’\']*)',
                        fallback=_excerpt_around(full_text, r'(A\s+Christian\s+church\s+has\s+been\s+reported.*?Murphy.*?Muslims.*?)', window=900),
                        limit=3200,
                    ),
                    source_chain_gap=True,
                    review_required=False,
                )
            else:
                # V82X-R16: claim/span model.  When source/transcript TXT evidence
                # is attached, keep the Metro article in article order but count
                # individual claim spans rather than one broad Brett Murphy bucket.
                if re.search(r'Project\s+Britannia\s+YouTube\s+Channel', full_text, flags=re.IGNORECASE) and _evidence_contains_phrase(evidence_items, 'stop these hordes of heathen Mohammedans', 'invaded by an army of heathens'):
                    add(
                        'brett_murphy_project_britannia_youtube_quote_secondary_candidate',
                        'Brett Murphy / Project Britannia YouTube quote',
                        'SECONDARY_WITNESS_ACCOUNT',
                        ClaimBasis.WITNESS_ACCOUNT.value,
                        'Article names Project Britannia YouTube Channel and attached transcript text contains the quoted passage',
                        _matched_excerpt(
                            full_text,
                            r'(Murphy\s+has\s+also\s+made\s+hateful\s+comments\s+towards\s+Muslims\..*?kill\s+us[’\']?\.)',
                            fallback=_excerpt_around(full_text, r'(Murphy\s+has\s+also\s+made\s+hateful\s+comments\s+towards\s+Muslims.*?)', window=650),
                            limit=1600,
                        ),
                        source_chain_gap=False,
                        review_required=False,
                    )

                if _evidence_contains_phrase(evidence_items, 'practice black magic'):
                    add(
                        'brett_murphy_headline_black_magic_tertiary_candidate',
                        'Brett Murphy / headline black-magic and turned-to-Islam article claim',
                        'TERTIARY_PROPAGATED_SOURCE',
                        ClaimBasis.AGENCY_OR_OUTSIDE_RETELLING.value,
                        'Metro headline/deck claim matched to attached transcript material; the article does not name the August sermon source at this point',
                        _matched_excerpt(
                            full_text,
                            r"(Reverend\s+says\s+Jews\s+[‘']practice\s+black\s+magic[’']\s+and\s+[‘']r\*tards\s+turn\s+to\s+Islam[’']\s+in\s+online\s+videos)",
                            fallback="Reverend says Jews 'practice black magic' and 'r*tards turn to Islam' in online videos",
                            limit=700,
                        ),
                        source_chain_gap=False,
                        review_required=False,
                    )
                    add(
                        'brett_murphy_reported_demonic_cult_tertiary_candidate',
                        'Brett Murphy / reported demonic-cult article claim',
                        'TERTIARY_PROPAGATED_SOURCE',
                        ClaimBasis.AGENCY_OR_OUTSIDE_RETELLING.value,
                        'Article reports the sermon allegation; attached source text matches related sermon material but the article does not name the August sermon source at this point',
                        _matched_excerpt(
                            full_text,
                            r'(A\s+Christian\s+church\s+has\s+been\s+reported\s+after\s+an\s+online\s+sermon\s+shows\s+a\s+reverend\s+describing\s+Judaism\s+as\s+a\s+[‘\']demonic\s+cult[’\'],\s+before\s+adding\s+that\s+[‘\']absolute\s+r\*+\w*ds[’\']\s+turn\s+to\s+Islam\.)',
                            fallback=_excerpt_around(full_text, r'(A\s+Christian\s+church\s+has\s+been\s+reported\s+after\s+an\s+online\s+sermon.*?)', window=420),
                            limit=1200,
                        ),
                        source_chain_gap=False,
                        review_required=False,
                    )
                    add(
                        'brett_murphy_false_religion_claim_tertiary_candidate',
                        'Brett Murphy / false-religion article claim',
                        'TERTIARY_PROPAGATED_SOURCE',
                        ClaimBasis.AGENCY_OR_OUTSIDE_RETELLING.value,
                        'Article reports the false-religion claim; attached source text matches related sermon material but the article does not name the August sermon source at this point',
                        _matched_excerpt(
                            full_text,
                            r'(The\s+Emmanuel\s+Free\s+Church\s+of\s+England\s+in\s+Morecambe,\s+which\s+is\s+a\s+registered\s+charity,\s+claimed\s+Judaism\s+was\s+a\s+[‘\']false\s+religion[’\']\s+in\s+a\s+sermon\s+led\s+by\s+Reverend\s+Brett\s+Murphy\.)',
                            fallback=_excerpt_around(full_text, r'(Emmanuel\s+Free\s+Church.*?false\s+religion.*?)', window=420),
                            limit=1200,
                        ),
                        source_chain_gap=False,
                        review_required=False,
                    )
                    add(
                        'brett_murphy_doug_wilson_quote_tertiary_candidate',
                        'Brett Murphy / Doug Wilson Jews quote article claim',
                        'TERTIARY_PROPAGATED_SOURCE',
                        ClaimBasis.AGENCY_OR_OUTSIDE_RETELLING.value,
                        'Attached source/transcript text matches the Doug Wilson formulation, but the article text does not name the August sermon source for this extant',
                        _matched_excerpt(
                            full_text,
                            r'(He\s+even\s+quotes\s+US\s+Christian\s+nationalist\s+Doug\s+Wilson,\s+saying:\s+[‘\']When\s+the\s+jews\s+are\s+bad,\s+they[’\']re\s+very,\s+very\s+bad[.’\']*)',
                            fallback=_excerpt_around(full_text, r'(Doug\s+Wilson.*?very,\s+very\s+bad.*?)', window=420),
                            limit=1000,
                        ),
                        source_chain_gap=False,
                        review_required=False,
                    )

                add(
                    'brett_murphy_conference_event_unknown_candidate',
                    'Brett Murphy / Make Great Britain Christian Again event statement',
                    'UNKNOWN_SOURCE_ROLE',
                    ClaimBasis.UNKNOWN_CLAIM_BASIS.value,
                    'No attached source text currently verifies this event/timing article extant',
                    _matched_excerpt(
                        full_text,
                        r'(Murphy[’\']s\s+church\s+is\s+due\s+to\s+host\s+a\s+[‘\']Make\s+Great\s+Britain\s+Christian\s+Again[’\']\s+conference\s+this\s+month\.)',
                        fallback='Murphy’s church is due to host a ‘Make Great Britain Christian Again’ conference this month.',
                        limit=700,
                    ),
                    source_chain_gap=True,
                    review_required=False,
                )

                if _evidence_contains_any_phrase(evidence_items, 'homosexual adoption', 'sodomite parades', 'progress pride flag'):
                    add(
                        'brett_murphy_pride_adoption_claims_partial_tertiary_candidate',
                        'Brett Murphy / pride-adoption article claim',
                        'TERTIARY_PROPAGATED_SOURCE',
                        ClaimBasis.AGENCY_OR_OUTSIDE_RETELLING.value,
                        'Attached transcript text matches the sodomite/adoption/pride-theme material, but the article itself does not provide the direct source chain here',
                        _matched_excerpt(
                            full_text,
                            r'(He\s+has\s+previously\s+referred\s+to\s+the\s+gay\s+pride\s+flag\s+as\s+the\s+[‘\']sodomite\s+flag[’\']\s+and\s+urged\s+for\s+the\s+end\s+of\s+gay\s+couples\s+being\s+able\s+to\s+adopt\s+children\.)',
                            fallback=_excerpt_around(full_text, r'(He\s+has\s+previously\s+referred\s+to\s+the\s+gay\s+pride\s+flag.*?)', window=260),
                            limit=1100,
                        ),
                        source_chain_gap=False,
                        review_required=False,
                    )

                add(
                    'brett_murphy_2023_date_unknown_candidate',
                    'Brett Murphy / 2023 timing claim',
                    'UNKNOWN_SOURCE_ROLE',
                    ClaimBasis.UNKNOWN_CLAIM_BASIS.value,
                    'Attached transcripts support Church-of-England background in part, but not the exact 2023 timing',
                    _matched_excerpt(
                        full_text,
                        r'(In\s+2023)',
                        fallback='In 2023',
                        limit=120,
                    ),
                    source_chain_gap=True,
                    review_required=False,
                )

                if _evidence_contains_any_phrase(evidence_items, 'trans person', 'trans woman', "that's a bloke", 'resigned myself'):
                    add(
                        'brett_murphy_resignation_trans_claim_tertiary_candidate',
                        'Brett Murphy / Church-of-England resignation and transgender-comments article claim',
                        'TERTIARY_PROPAGATED_SOURCE',
                        ClaimBasis.AGENCY_OR_OUTSIDE_RETELLING.value,
                        'Attached transcript text supports Church-of-England departure/background and later transgender-related remarks, but not the exact 2023 date',
                        _matched_excerpt(
                            full_text,
                            r'(Murphy\s+resigned\s+from\s+the\s+Church\s+of\s+England,\s+who\s+he\s+now\s+calls\s+heretics,\s+after\s+making\s+derogatory\s+comments\s+about\s+a\s+senior\s+leader\s+who\s+came\s+out\s+as\s+transgender\.)',
                            fallback='Murphy resigned from the Church of England, who he now calls heretics, after making derogatory comments about a senior leader who came out as transgender.',
                            limit=1100,
                        ),
                        source_chain_gap=False,
                        review_required=False,
                    )

                if _evidence_contains_any_phrase(evidence_items, 'absolute retards turned to Islam', 'absolute retards turn to Islam'):
                    add(
                        'brett_murphy_caption_and_turned_to_islam_tertiary_candidate',
                        'Brett Murphy / article caption and “turned to Islam” quote',
                        'TERTIARY_PROPAGATED_SOURCE',
                        ClaimBasis.AGENCY_OR_OUTSIDE_RETELLING.value,
                        'Article caption/bridge and quote are matched to attached transcript material, but the article does not name that transcript/source at this point',
                        _matched_excerpt(
                            full_text,
                            r'(Reverend\s+Brett\s+Murphy\s+has\s+said\s+derogatory\s+comments\s+ab[ou]t\s+Jews,\s+Muslims\s+and\s+members\s+of\s+the\s+LGBTQ\s+community\s*\([^)]*\)(?:\s*\([^)]*\))?\s*He\s+adds:\s*[‘\']You\s+get\s+so\s+many\s+of\s+these\s+absolute\s+retards\s+turned?\s+to\s+Islam,\s+because\s+they[’\']re\s+desperate\.[’\']?)',
                            fallback='Reverend Brett Murphy has said derogatory comments abut Jews, Muslims and members of the LGBTQ community (Picture: Facebook / Revd Canon Brett Murphy) (Picture: Facebook/Revd Canon Brett Murphy) He adds: ‘You get so many of these absolute retards turned to Islam, because they’re desperate.’',
                            limit=1400,
                        ),
                        source_chain_gap=False,
                        review_required=False,
                    )


        if re.search(r'\bAlejandro\s+Sanchez\b.*?told\s+Metro', full_text, flags=re.IGNORECASE | re.DOTALL):
            add(
                'alejandro_sanchez_nss_direct_quote_secondary_candidate',
                'Alejandro Sanchez / NSS quote to Metro',
                'SECONDARY_WITNESS_ACCOUNT',
                ClaimBasis.WITNESS_ACCOUNT.value,
                'Direct quote to Metro',
                _matched_excerpt(
                    full_text,
                    r'(Alejandro\s+Sanchez,\s+from\s+the\s+NSS,\s+told\s+Metro:\s*[‘\'].*?hate\s+and\s+division\.[’\']?)',
                    fallback=_excerpt_around(full_text, r'(Alejandro\s+Sanchez.*?told\s+Metro.*?)', window=500),
                    limit=1800,
                ),
                source_chain_gap=False,
                review_required=False,
            )
        if re.search(r'Charity\s+Commission\s+spokesperson\s+said', full_text, flags=re.IGNORECASE):
            add(
                'charity_commission_statement_secondary_candidate',
                'Charity Commission / spokesperson statement',
                'SECONDARY_WITNESS_ACCOUNT',
                ClaimBasis.WITNESS_ACCOUNT.value,
                'Reported official statement',
                _matched_excerpt(
                    full_text,
                    r"(A\s+Charity\s+Commission\s+spokesperson\s+said:\s*[‘'][^’']+?[’']\.?)",
                    fallback=_excerpt_around(full_text, r'(A\s+Charity\s+Commission\s+spokesperson\s+said.*?)'),
                ),
                source_chain_gap=False,
                review_required=False,
            )


    generated_source_text_excerpt_count = 0
    # V82X closeout: source/transcript TXT semantic passages now live in the
    # clause-level claim/span transcript card.  Keep this legacy generator
    # disabled for the main Sourcing card so media provenance is not mixed with
    # broad generated quote excerpts.
    for evidence_index, (_artifact, source_text, source_profile) in enumerate((), start=1):
        source_link = _clean_text(source_profile.get("source_link") or source_profile.get("source_page"))
        source_title_text = _clean_text(source_profile.get("title") or source_profile.get("source_summary") or source_profile.get("source_title"), fallback=f"Source text {evidence_index}")
        source_prefix = f"source_text_{evidence_index:02d}"
        source_sections = _split_youtube_source_text_sections(source_text)
        source_text = source_sections.get("transcript") or source_text

        def add_source_span(span_no: int, slug: str, role: str, reason: str, excerpt: str, *, gap: bool = False) -> None:
            add(
                f"{source_prefix}_span_{span_no:02d}_{slug}",
                f"{source_title_text} / source-text role map",
                role,
                ClaimBasis.SELF_AUTHORED_EXPERIENCE.value if role == 'PRIMARY_SELF_AUTHORED_SCOPE' else ClaimBasis.UNKNOWN_CLAIM_BASIS.value,
                reason,
                excerpt,
                source_chain_gap=gap,
                review_required=False,
                source_url_override=source_link,
                source_title_override=source_title_text,
            )

        span_no = 1
        header_excerpt = "\n".join(part for part in (source_title_text, f"Source: {source_link}" if source_link else "") if part)
        add_source_span(span_no, "metadata_primary", 'PRIMARY_SELF_AUTHORED_SCOPE', 'The TXT file names its own source URL/title; the source scope itself is preserved as primary source evidence.', header_excerpt, gap=False)
        span_no += 1

        if re.search(r"\bI\s+resigned\b|\bI\s+was\b|\bmy\s+time\b|part\s+of\s+the\s+Church\s+of\s+England|depart\s+from\s+the\s+Church\s+of\s+England", source_text, flags=re.IGNORECASE):
            add_source_span(
                span_no,
                "self_history_primary",
                'PRIMARY_SELF_AUTHORED_SCOPE',
                'First-person/self-history material in the transcript is primary for what the speaker says about himself.',
                _excerpt_around(source_text, r"(I\s+resigned.*?YouTube\s+channel\.)", fallback=_excerpt_around(source_text, r"(part\s+of\s+the\s+Church\s+of\s+England.*?Confessing\s+Anglican\s+Church.*?)", window=520), window=460, limit=1400),
                gap=False,
            )
            span_no += 1

        if re.search(r"false\s+(?:antichrist\s+)?religion|demonic\s+cults|black\s+magic|Talmudists|Carbalists|Kabbalists", source_text, flags=re.IGNORECASE):
            add_source_span(
                span_no,
                "judaism_accusation_unknown",
                'UNKNOWN_SOURCE_ROLE',
                'The transcript preserves the speaker making the claim, but the accusation about Judaism/black magic is not independently sourced inside this TXT.',
                _excerpt_around(source_text, r"(Now\s+that\s+doesn['’]t\s+mean.*?practice\s+black\s+magic.*?)", fallback=_excerpt_around(source_text, r"(false\s+(?:antichrist\s+)?religion.*?black\s+magic.*?)", window=520), window=420, limit=1400),
                gap=True,
            )
            span_no += 1

        if re.search(r"Doug\s+Wilson|George\s+Soros|Epstein", source_text, flags=re.IGNORECASE):
            add_source_span(
                span_no,
                "third_party_claim_unknown",
                'UNKNOWN_SOURCE_ROLE',
                'The transcript mentions or quotes third parties, but this TXT is not itself the third-party source.',
                _excerpt_around(source_text, r"(Pastor\s+Doug\s+Wilson.*?very\s+very\s+bad.*?)", fallback=_excerpt_around(source_text, r"(Doug\s+Wilson|George\s+Soros|Epstein)", window=430), window=300, limit=1200),
                gap=True,
            )
            span_no += 1

        if re.search(r"hordes\s+of\s+heathen\s+Moha?mmedans|invaded\s+by\s+an\s+army\s+of\s+heathens|want\s+to\s+kill\s+us", source_text, flags=re.IGNORECASE):
            add_source_span(
                span_no,
                "muslim_accusation_unknown",
                'UNKNOWN_SOURCE_ROLE',
                'The transcript preserves the quoted wording, but the claim about Muslims/heathens invading or wanting to kill is unsupported inside this source TXT.',
                _excerpt_around(source_text, r"(People\s+talk\s+about\s+demographic\s+replacement.*?want\s+to\s+kill\s+us\.)", fallback=_excerpt_around(source_text, r"(hordes\s+of\s+heathen\s+Moha?mmedans.*?)", window=420), window=260, limit=1100),
                gap=True,
            )
            span_no += 1

        if re.search(r"homosexual\s+adoption|abuse\s+of\s+children|sodomite\s+parades|progress\s+pride\s+flag|trans\s+person", source_text, flags=re.IGNORECASE):
            add_source_span(
                span_no,
                "lgbt_claims_mixed_unknown",
                'UNKNOWN_SOURCE_ROLE',
                'The transcript preserves the speaker’s wording, but claims about others/events need their own evidence if treated as factual claims.',
                _excerpt_around(source_text, r"(We\s+need\s+to\s+end\s+the\s+sodomite\s+parades.*?abuse\s+of\s+children\.)", fallback=_excerpt_around(source_text, r"(progress\s+pride\s+flag|trans\s+person|homosexual\s+adoption)", window=460), window=320, limit=1300),
                gap=True,
            )
            span_no += 1

    generated_source_text_excerpt_count += len(evidence_items)
    for candidate in candidates:
        if str(candidate.get("segment_id") or "").startswith("source_text_"):
            candidate["suppress_from_main_sourcing_card"] = True
            candidate["generated_source_text_excerpt"] = True
    # Media artifacts are shown in the Media section. Do not create a second
    # generic Sourcing row such as "Embedded/rehosted video file" because that
    # duplicates the visible media card and inflates the Review count.
    return tuple(candidates)




def _segment_source_spec(
    *,
    source_url: str,
    canonical_url: str,
    source_title: str,
    segment: Mapping[str, Any],
    index: int,
) -> dict[str, Any]:
    subject = _clean_text(segment.get("subject"), fallback=f"Source-role segment {index}")
    role = canonical_source_role(segment.get("candidate_source_role") or ProfileSourceRole.TERTIARY_PROPAGATED_SOURCE.value)
    basis = _clean_text(segment.get("candidate_claim_basis"), fallback=ClaimBasis.UNKNOWN_CLAIM_BASIS.value)
    notes = [
        "V82K mixed-role article segment candidate; review in the protected Review DB import dialog before saving to HOME.",
        f"segment_id={_clean_text(segment.get('segment_id'))}",
        f"review_reason={_clean_text(segment.get('review_reason'))}",
        f"potential_source_role_after_chain_verification={_clean_text(segment.get('potential_source_role_after_chain_verification'))}" if _clean_text(segment.get('potential_source_role_after_chain_verification')) else "",
        f"excerpt={_clean_text(segment.get('excerpt'))}",
        "final_source_role_decision=False",
        f"review_required={bool(segment.get('review_required', True))}",
    ]
    segment_source_page = _clean_text(segment.get("source_url"), fallback=canonical_url or source_url)
    segment_source_title = _clean_text(segment.get("source_title"), fallback=_clean_text(source_title, fallback=_SOURCE_DEFAULT_TITLE))
    return {
        "source_page": segment_source_page,
        "source_title": f"{segment_source_title} — segment: {subject}",
        "source_bucket": "Articles",
        "source_role": role,
        "claim_basis": basis,
        "currentness_status": CurrentnessStatus.UNKNOWN.value,
        "source_chain_gap": bool(segment.get("source_chain_gap", True)),
        "disputed_framing": False,
        "source_role_review_required": bool(segment.get("review_required", True)),
        "final_source_role_decision": False,
        "source_role_segment_candidate": True,
        "segment_id": _clean_text(segment.get("segment_id")),
        "segment_subject": subject,
        "confidence_or_verification_notes": " | ".join(item for item in notes if item),
    }


def build_person_review_candidates_from_artifacts(
    *,
    source_title: object = "",
    source_url: object = "",
    artifacts: Iterable[ProfileMediaSourcePackageArtifact] = (),
) -> tuple[dict[str, Any], ...]:
    """Build source-bound person/designation candidates from captured article text.

    This is not identity enrichment and not sensitive inference. It only records
    explicit text from selected article artifacts for protected review.
    """

    full_text = _article_text_from_artifacts(artifacts)
    candidates: list[dict[str, Any]] = []
    canonical_transcript_person_text = ""
    related_comment_context_by_person: dict[str, str] = {}
    related_comment_threads_by_person: dict[str, tuple[dict[str, object], ...]] = {}

    def add(candidate: dict[str, Any]) -> None:
        key = canonical_person_key(candidate.get("canonical_name"))
        source_key = _clean_text(candidate.get("source_url"))
        if key and any(canonical_person_key(item.get("canonical_name")) == key and _clean_text(item.get("source_url")) == source_key for item in candidates):
            return
        candidates.append(candidate)

    def _remember_related_comment_context(person_name: str, comments_text: str, aliases: Iterable[str]) -> None:
        """Attach preserved-comment context only to people already present in transcript scope.

        This does not create new person rows. It only records that a transcript
        person also appears as a comment user/comment mention, so the Source
        Roles text can show the context without promoting comment-only people.
        """
        if not comments_text:
            return
        clean_aliases = [str(alias or "").strip() for alias in aliases if str(alias or "").strip()]
        if not clean_aliases:
            return
        handle_aliases = [
            "@" + alias.strip().lstrip("@")
            for alias in clean_aliases
            if re.fullmatch(r"@?[A-Za-z0-9_.-]+", alias.strip())
        ]
        found_threads: list[dict[str, object]] = []
        seen_thread_keys: set[tuple[str, str, str]] = set()
        for handle_alias in handle_aliases:
            for thread in extract_preserved_youtube_comment_threads(comments_text, author_handle=handle_alias):
                brett = thread.get("brett") if isinstance(thread, Mapping) else None
                key = (
                    str((brett or {}).get("author_handle") if isinstance(brett, Mapping) else "").casefold(),
                    str((brett or {}).get("time") if isinstance(brett, Mapping) else ""),
                    str((brett or {}).get("text") if isinstance(brett, Mapping) else ""),
                )
                if key in seen_thread_keys:
                    continue
                seen_thread_keys.add(key)
                found_threads.append(dict(thread))
        if not found_threads:
            return
        key = canonical_person_key(person_name)
        related_comment_threads_by_person[key] = tuple(found_threads)
        found: list[str] = []
        for thread in found_threads[:3]:
            brett = thread.get("brett") if isinstance(thread, Mapping) else None
            if not isinstance(brett, Mapping):
                continue
            handle = _clean_text(brett.get("author_handle"), fallback="comment")
            summary = _clean_text(brett.get("text"))
            if len(summary) > 220:
                summary = summary[:217].rstrip() + "..."
            item = f"{handle}: {summary}" if summary else handle
            if item not in found:
                found.append(item)
        existing = related_comment_context_by_person.get(key, "")
        merged = list(existing.split(" || ")) if existing else []
        for item in found:
            if item not in merged:
                merged.append(item)
        related_comment_context_by_person[key] = " || ".join(merged[:3])

    author_candidate = _article_author_candidate(full_text)
    if author_candidate:
        add(author_candidate)

    # Operator-added transcript/source TXT scopes can have their own people.
    # Split the TXT first: comments/research notes must not be treated as the
    # transcript itself.
    for _artifact, source_text_raw, source_profile in _source_evidence_texts_from_artifacts(artifacts):
        source_link = _clean_text(source_profile.get("source_link") or source_profile.get("source_page"))
        channel = _clean_text(source_profile.get("channel"))
        title = _clean_text(source_profile.get("title"))
        sections = _split_youtube_source_text_sections(source_text_raw)
        transcript_text = sections.get("transcript") or ""
        comments_text = sections.get("comments") or ""
        research_text = sections.get("research") or ""
        canonical_transcript_person_text += "\n" + transcript_text

        def _nearby(pattern: str, *, window: int = 180) -> str:
            match = re.search(pattern, transcript_text, flags=re.IGNORECASE | re.DOTALL)
            if not match:
                return ""
            start = max(0, match.start() - window)
            end = min(len(transcript_text), match.end() + window)
            return transcript_text[start:end]

        if re.search(r"\bBrett\s+Murphy\b|Rev[’']?d\s+Canon\s+Brett\s+Murphy|Father\s+Brett\s+Murphy|\[Brett\s+Murphy\]", transcript_text + " " + title, flags=re.IGNORECASE):
            _remember_related_comment_context("Brett Murphy", comments_text, ("RevBrettMurphy", "Brett Murphy", "Father Brett", "Brett"))
            assoc_values = [channel]
            if "Project Britannia" in channel or "Project Britannia" in title:
                assoc_values.append("Project Britannia")
            if "Rev. Brett Murphy" in channel:
                assoc_values.append("Rev. Brett Murphy")
            if re.search(r"\bFCE\b|Free\s+Church\s+of\s+England", transcript_text, flags=re.IGNORECASE):
                assoc_values.append("Free Church of England")
            if re.search(r"\bChurch\s+of\s+England\b|\bC\s+of\s+E\b|\bCofE\b", transcript_text, flags=re.IGNORECASE):
                assoc_values.append("Church of England")
            unique_associations: list[str] = []
            for assoc in assoc_values:
                assoc = _clean_text(assoc)
                if assoc and assoc not in unique_associations:
                    unique_associations.append(assoc)
            add({
                "canonical_name": "Brett Murphy",
                "role_in_event": "source/transcript speaker / sermon or interview subject",
                "source_role_candidate": "PRIMARY_SELF_AUTHORED_SCOPE",
                "claim_basis_candidate": ClaimBasis.SELF_AUTHORED_EXPERIENCE.value,
                "associations": unique_associations,
                "designation_candidates": ["Christian reverend"] if re.search(r"Rev|Father|priest|sermon", transcript_text + " " + title, flags=re.IGNORECASE) else [],
                "review_required": False,
                "final_person_decision": False,
                "source_url": source_link,
                "source_context_sections": ["transcript"],
                "source_context_section_label": "Section: transcript",
                "notes": title,
            })

        if re.search(r"Thomas\s+Gregory\s+Moffitt|Young\s+Bob|\[Young\s+Bob\]", transcript_text + " " + title, flags=re.IGNORECASE):
            _remember_related_comment_context("Thomas Gregory Moffitt (Young Bob)", comments_text, ("Thomas Gregory Moffitt", "Young Bob", "ThomasGregoryMoffitt"))
            add({
                "canonical_name": "Thomas Gregory Moffitt (Young Bob)",
                "role_in_event": "Project Britannia host / interviewer",
                "source_role_candidate": "PRIMARY_SELF_AUTHORED_SCOPE",
                "claim_basis_candidate": ClaimBasis.SELF_AUTHORED_EXPERIENCE.value,
                "associations": ["Project Britannia"] if ("Project Britannia" in channel or "Project Britannia" in title) else [],
                "designation_candidates": [],
                "review_required": False,
                "final_person_decision": False,
                "source_url": source_link,
                "source_context_sections": ["transcript"],
                "source_context_section_label": "Section: transcript",
                "notes": title,
            })

        # Transcript mentions: use transcript only.  Comments and later research
        # are separate contexts and should not create transcript-person rows.
        if re.search(r"\bDoug\s+Wilson\b", transcript_text, flags=re.IGNORECASE):
            add({
                "canonical_name": "Doug Wilson",
                "role_in_event": "person mentioned/quoted in transcript",
                "source_role_candidate": "UNKNOWN_SOURCE_ROLE",
                "claim_basis_candidate": ClaimBasis.UNKNOWN_CLAIM_BASIS.value,
                "associations": [],
                "designation_candidates": ["Christian pastor"] if re.search(r"\bPastor\s+Doug\s+Wilson\b|American\s+pastor\s+Doug", transcript_text, flags=re.IGNORECASE) else [],
                "review_required": False,
                "final_person_decision": False,
                "source_url": source_link,
                "source_context_sections": ["transcript"],
                "source_context_section_label": "Section: transcript",
                "notes": title + " — transcript mention",
            })
        elif re.search(r"\bDoug\s+Wilson\b", comments_text, flags=re.IGNORECASE):
            # Comments are sectionally preserved, but comment-only named people
            # are not promoted into the default source/transcript Persons list.
            # They belong to an explicit comments review scope, or to structured
            # comment-author handling when the commenter is already a transcript person.
            pass

        if re.search(r"\bCalvin\s+Robinson\b", transcript_text, flags=re.IGNORECASE):
            _remember_related_comment_context("Calvin Robinson", comments_text, ("Calvin Robinson", "Father Calvin Robinson"))
            calvin_context = _nearby(r"\bCalvin\s+Robinson\b", window=260)
            associations = []
            if re.search(r"\bFCE\b|Free\s+Church\s+of\s+England", calvin_context, flags=re.IGNORECASE):
                associations.append("FCE / Free Church of England")
            add({
                "canonical_name": "Calvin Robinson",
                "role_in_event": "person mentioned by Brett Murphy in transcript",
                "source_role_candidate": "UNKNOWN_SOURCE_ROLE",
                "claim_basis_candidate": ClaimBasis.UNKNOWN_CLAIM_BASIS.value,
                "associations": associations,
                "designation_candidates": ["Father"] if re.search(r"Father\s+Calvin\s+Robinson", calvin_context, flags=re.IGNORECASE) else [],
                "review_required": False,
                "final_person_decision": False,
                "source_url": source_link,
                "source_context_sections": ["transcript"],
                "source_context_section_label": "Section: transcript",
                "notes": title + " — transcript mention",
            })
        elif re.search(r"\bCalvin\s+Robinson\b", comments_text, flags=re.IGNORECASE):
            # Comments-only mentions are outside the default source/transcript
            # Persons list.  Transcript mentions remain included above.
            pass

        if re.search(r"\bGeorge\s+Soros\b", transcript_text, flags=re.IGNORECASE):
            add({
                "canonical_name": "George Soros",
                "role_in_event": "person mentioned in unsupported transcript claim",
                "source_role_candidate": "UNKNOWN_SOURCE_ROLE",
                "claim_basis_candidate": ClaimBasis.UNKNOWN_CLAIM_BASIS.value,
                "associations": [],
                "designation_candidates": [],
                "review_required": False,
                "final_person_decision": False,
                "source_url": source_link,
                "source_context_sections": ["transcript"],
                "source_context_section_label": "Section: transcript",
                "notes": title + " — transcript claim mention",
            })

        if re.search(r"\bSarah\s+Mullally\b", transcript_text, flags=re.IGNORECASE):
            add({
                "canonical_name": "Sarah Mullally",
                "role_in_event": "person explicitly named in transcript",
                "source_role_candidate": "UNKNOWN_SOURCE_ROLE",
                "claim_basis_candidate": ClaimBasis.UNKNOWN_CLAIM_BASIS.value,
                "associations": [],
                "designation_candidates": [],
                "review_required": False,
                "final_person_decision": False,
                "source_url": source_link,
                "source_context_sections": ["transcript"],
                "source_context_section_label": "Section: transcript",
                "notes": title + " — transcript mention",
            })

    for candidate in candidates:
        comment_context = related_comment_context_by_person.get(canonical_person_key(candidate.get("canonical_name")), "")
        if not comment_context:
            continue
        sections = [_clean_text(item) for item in candidate.get("source_context_sections", ()) if _clean_text(item)] if isinstance(candidate.get("source_context_sections"), list) else []
        if "transcript" not in sections:
            sections.insert(0, "transcript")
        if "comments" not in sections:
            sections.append("comments")
        candidate["source_context_sections"] = sections
        section_label = "Section: " + ", ".join(sections)
        candidate["source_context_section_label"] = section_label
        labelled_comment_context = section_label + " — " + comment_context
        candidate["related_comment_user_context"] = labelled_comment_context
        candidate["related_comment_thread_records"] = list(related_comment_threads_by_person.get(canonical_person_key(candidate.get("canonical_name")), ()))
        notes = _clean_text(candidate.get("notes"))
        suffix = "Related preserved comments for transcript person: " + labelled_comment_context
        if suffix not in notes:
            candidate["notes"] = (notes + " — " + suffix).strip(" —") if notes else suffix

    if re.search(r"\bNora\s+Mubarak\b", full_text, flags=re.IGNORECASE):
        explicit_religion = bool(re.search(r"\bA\s+Muslim\s+woman\b|\bMuslims\b", full_text, flags=re.IGNORECASE))
        add({
            "canonical_name": "Nora Mubarak",
            "role_in_event": "main person / accused subject / witness account",
            "source_role_candidate": "SECONDARY_WITNESS_ACCOUNT",
            "claim_basis_candidate": ClaimBasis.WITNESS_ACCOUNT.value,
            "religion": "Muslim" if explicit_religion else "",
            "religion_basis": "article text" if explicit_religion else "",
            "clothing_or_appearance_context": "traditional Islamic dress; mask mentioned" if re.search(r"traditional\s+Islamic\s+dress|wear\s+a\s+mask", full_text, flags=re.IGNORECASE) else "",
            "associations": ["Seagull Appreciation Society"] if "Seagull Appreciation Society" in full_text else [],
            "places": ["Grimsby"] if "Grimsby" in full_text else [],
            "designation_candidates": [],
            "review_required": True,
            "final_person_decision": False,
            "notes": "",
        })
    if re.search(r"\bOliver\s+Freeston\b", full_text, flags=re.IGNORECASE):
        add({
            "canonical_name": "Oliver Freeston",
            "role_in_event": "reported amplifier / political actor / far-right figure",
            "source_role_candidate": "UNKNOWN_SOURCE_ROLE",
            "claim_basis_candidate": ClaimBasis.UNKNOWN_CLAIM_BASIS.value,
            "potential_source_role_after_chain_verification": "PRIMARY_SELF_AUTHORED_SCOPE",
            "associations": [item for item in ("Reform UK", "North East Lincolnshire Council") if item in full_text],
            "designation_candidates": [],
            "review_required": True,
            "final_person_decision": False,
            "notes": "",
        })
    if re.search(r"\bTommy\s+Robinson\b", full_text, flags=re.IGNORECASE):
        add({
            "canonical_name": "Tommy Robinson",
            "role_in_event": "reported amplifier / far-right leader",
            "source_role_candidate": "UNKNOWN_SOURCE_ROLE",
            "claim_basis_candidate": ClaimBasis.UNKNOWN_CLAIM_BASIS.value,
            "potential_source_role_after_chain_verification": "PRIMARY_SELF_AUTHORED_SCOPE",
            "associations": [],
            "designation_candidates": [],
            "review_required": True,
            "final_person_decision": False,
            "notes": "",
        })
    if re.search(r"\bBrett\s+Murphy\b|Reverend\s+Brett\s+Murphy", full_text, flags=re.IGNORECASE):
        add({
            "canonical_name": "Brett Murphy",
            "role_in_event": "reverend / reported sermon speaker / church leader",
            "source_role_candidate": "UNKNOWN_SOURCE_ROLE",
            "claim_basis_candidate": ClaimBasis.UNKNOWN_CLAIM_BASIS.value,
            "potential_source_role_after_chain_verification": "PRIMARY_SELF_AUTHORED_SCOPE",
            "associations": [item for item in ("Emmanuel Free Church of England", "Project Britannia", "Church of England") if item in full_text],
            "places": [item for item in ("Morecambe", "England") if item in full_text],
            "designation_candidates": ["Christian reverend"] if re.search(r"Reverend|church", full_text, flags=re.IGNORECASE) else [],
            "review_required": True,
            "final_person_decision": False,
            "notes": "Explicitly named in the article text; review only, not final classification.",
        })
    doug_article_source_context = re.search(
        r"(?:article\s+also\s+quotes?|quotes?|quoted|reported|source\s+says|saying)\s+.{0,120}\bDoug\s+Wilson\b|\bDoug\s+Wilson\b.{0,120}(?:quote|quoted|saying|article)",
        full_text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if re.search(r"\bDoug\s+Wilson\b", full_text, flags=re.IGNORECASE) and doug_article_source_context:
        add({
            "canonical_name": "Doug Wilson",
            "role_in_event": "quoted source named in article; described by article as US Christian nationalist",
            "source_role_candidate": "UNKNOWN_SOURCE_ROLE",
            "claim_basis_candidate": ClaimBasis.UNKNOWN_CLAIM_BASIS.value,
            "associations": [],
            "designation_candidates": ["Christian nationalist"] if re.search(r"Christian\s+nationalist", full_text, flags=re.IGNORECASE) else [],
            "review_required": True,
            "final_person_decision": False,
            "notes": "Explicitly named quoted source; review original quote/source-chain separately.",
        })
    if re.search(r"\bAlejandro\s+Sanchez\b", full_text, flags=re.IGNORECASE):
        add({
            "canonical_name": "Alejandro Sanchez",
            "role_in_event": "NSS spokesperson quoted by Metro",
            "source_role_candidate": "SECONDARY_WITNESS_ACCOUNT",
            "claim_basis_candidate": ClaimBasis.WITNESS_ACCOUNT.value,
            "associations": ["National Secular Society", "NSS"] if "NSS" in full_text else ["National Secular Society"],
            "designation_candidates": [],
            "review_required": True,
            "final_person_decision": False,
            "notes": "Quoted by Metro in the captured article text.",
        })
    return tuple(candidates)


def _profile_spec_from_person_candidate(candidate: Mapping[str, Any], *, source_url: str, source_title: str) -> dict[str, Any]:
    name = _clean_text(candidate.get("canonical_name"), fallback="Unnamed person")
    candidate_source_url = _clean_text(candidate.get("source_url"), fallback=source_url)
    lines = [
        f"Name: {name}",
        f"Role in event: {_clean_text(candidate.get('role_in_event'))}",
    ]
    religion = _clean_text(candidate.get("religion"))
    if religion:
        lines.append(f"Religion: {religion}")
    appearance = _clean_text(candidate.get("clothing_or_appearance_context"))
    if appearance:
        lines.append(f"Clothing / appearance context: {appearance}")
    associations = candidate.get("associations") if isinstance(candidate.get("associations"), list) else []
    if associations:
        lines.append("Associations: " + "; ".join(_clean_text(item) for item in associations if _clean_text(item)))
    places = candidate.get("places") if isinstance(candidate.get("places"), list) else []
    if places:
        lines.append("Places: " + "; ".join(_clean_text(item) for item in places if _clean_text(item)))
    designations = candidate.get("designation_candidates") if isinstance(candidate.get("designation_candidates"), list) else []
    if designations:
        lines.append("Designation candidates: " + "; ".join(_clean_text(item) for item in designations if _clean_text(item)))
    section_label = _clean_text(candidate.get("source_context_section_label"))
    if not section_label:
        sections = candidate.get("source_context_sections") if isinstance(candidate.get("source_context_sections"), list) else []
        clean_sections = [_clean_text(item) for item in sections if _clean_text(item)]
        if clean_sections:
            section_label = "Section: " + ", ".join(clean_sections)
    if section_label:
        lines.append(section_label)
    notes = _clean_text(candidate.get("notes"))
    if notes:
        lines.append(f"Notes: {notes}")
    lines.append(f"Source: {source_title}")
    lines.append(f"Source URL: {candidate_source_url}")
    lines.append("Final decision: false; review required")
    return {
        "profile_text": "\n".join(line for line in lines if line.strip()),
        "canonical_name": name,
        "source_bucket": "Articles",
        "source_role": canonical_source_role(candidate.get("source_role_candidate") or ProfileSourceRole.TERTIARY_PROPAGATED_SOURCE.value),
        "claim_basis": _clean_text(candidate.get("claim_basis_candidate"), fallback=ClaimBasis.UNKNOWN_CLAIM_BASIS.value),
        "currentness_status": CurrentnessStatus.UNKNOWN.value,
        "source_context_sections": list(candidate.get("source_context_sections") or ()),
        "source_context_section_label": section_label,
    }


def _related_comment_review_sections_from_person_candidates(candidates: Iterable[Mapping[str, Any]]) -> tuple[dict[str, Any], ...]:
    """Return preserved comments matched to existing transcript/source people.

    These sections are display material for Review only. They are not canonical
    transcript spans and do not alter transcript claim-span counts.
    """

    sections: list[dict[str, Any]] = []
    for candidate in candidates:
        if not isinstance(candidate, Mapping):
            continue
        person_name = _clean_text(candidate.get("canonical_name"))
        context = _clean_text(candidate.get("related_comment_user_context"))
        if not person_name or not context:
            continue
        if "comments" not in {str(item).strip().lower() for item in candidate.get("source_context_sections", ()) or ()}:
            continue
        thread_records = candidate.get("related_comment_thread_records")
        if not isinstance(thread_records, list):
            thread_records = []
        for index, thread in enumerate(thread_records, start=1):
            if not isinstance(thread, Mapping):
                continue
            brett = thread.get("brett") if isinstance(thread.get("brett"), Mapping) else {}
            comment_text = _clean_text(brett.get("text"))
            handle = _clean_text(brett.get("author_handle"))
            time_text = _clean_text(brett.get("time"))
            if not comment_text or not handle:
                continue
            comment_source_id = f"youtube_comment_{canonical_person_key(person_name)}_{index:03d}"
            comment_claim_spans = []
            try:
                for span in classify_claim_text(
                    comment_text,
                    source_id=comment_source_id,
                    speaker=handle,
                    media_source_role="SECONDARY_MEDIA_COPY",
                ):
                    payload = span.to_dict()
                    # YTCE_V83C_REPAIR14_COMMENT_SPANS_MARK_SHARED_CLASSIFIER
                    payload["comment_role_classifier_module"] = "profile_media_claim_role_classifier"
                    payload["comment_role_classifier_policy_version"] = CLAIM_ROLE_POLICY_VERSION
                    payload["comment_semantic_roles_use_claim_role_classifier"] = True
                    payload["semantic_role_is_separate_from_source_role"] = True
                    payload["section"] = "comments"
                    payload["source_stream"] = "preserved_youtube_comments"
                    payload["source_url"] = _clean_text(candidate.get("source_url"))
                    payload["canonical_person"] = person_name
                    payload["author_handle"] = handle
                    payload["time"] = time_text
                    payload["comment_index"] = index
                    payload["affects_transcript_claim_span_counts"] = False
                    comment_claim_spans.append(payload)
            except Exception:
                comment_claim_spans = []
            sections.append(
                {
                    "section_label": "comments",
                    "display_heading": "YouTube Comments",
                    "person": person_name,
                    "author_handle": handle,
                    "time": time_text,
                    "text": comment_text,
                    "source_url": _clean_text(candidate.get("source_url")),
                    "role": "PRIMARY",
                    "designation": "self-authored-comment",
                    "claim_role_spans": comment_claim_spans,
                    "claim_role_spans_classified_by_shared_classifier": bool(comment_claim_spans),
                    "comment_semantic_roles_use_claim_role_classifier": True,
                    "semantic_role_is_separate_from_source_role": True,
                    "YTCE_V83C_REPAIR14_COMMENT_SPANS_MARK_SHARED_CLASSIFIER": True,
                    "source_stream": "preserved_youtube_comments",
                    "original_context": dict(thread.get("original_context") or {}) if isinstance(thread.get("original_context"), Mapping) else None,
                    "thread_record": dict(thread),
                    "merged_into_canonical_transcript": False,
                    "affects_transcript_claim_span_counts": False,
                    "review_text": format_youtube_comment_threads_for_review_display((thread,)),
                    "comment_index": index,
                }
            )
    return tuple(sections)


def _youtube_comment_source_role_records_from_review_sections(
    sections: Iterable[Mapping[str, Any]],
) -> tuple[dict[str, Any], ...]:
    """Build source-role/source-reference rows for preserved YouTube comments.

    These records are resolved secondary source material because the comments are
    preserved in the current source TXT/package. They do not create people,
    become transcript speech, or alter transcript claim-span counts.
    """

    records: list[dict[str, Any]] = []
    for thread_index, section in enumerate(sections, start=1):
        if not isinstance(section, Mapping):
            continue
        source_url = _clean_text(section.get("source_url"))
        reply_handle = _clean_text(section.get("author_handle"))
        reply_time = _clean_text(section.get("time"))
        reply_text = _clean_text(section.get("text"))
        linked_person = _clean_text(section.get("person"))
        parent = section.get("original_context") if isinstance(section.get("original_context"), Mapping) else {}
        parent_handle = _clean_text(parent.get("author_handle")) if isinstance(parent, Mapping) else ""
        parent_time = _clean_text(parent.get("time") or parent.get("time_label")) if isinstance(parent, Mapping) else ""
        parent_text = _clean_text(parent.get("text")) if isinstance(parent, Mapping) else ""
        if parent_handle or parent_text:
            records.append(
                {
                    "record_id": f"youtube_comment_thread_{thread_index:03d}_parent_context",
                    "thread_index": thread_index,
                    "section": "comments",
                    "source_kind": "youtube_comment_context",
                    "source_role_status": "RESOLVED_SECONDARY_SOURCE",
                    "source_role_label": "Secondary — preserved YouTube comment context",
                    "author_handle": parent_handle,
                    "canonical_person": "",
                    "time_label": parent_time,
                    "text": parent_text,
                    "source_url": source_url,
                    "linked_persons": [],
                    "does_not_create_person": True,
                    "does_not_create_new_person": True,
                    "merged_into_canonical_transcript": False,
                    "affects_transcript_claim_span_counts": False,
                }
            )
        if reply_handle or reply_text:
            records.append(
                {
                    "record_id": f"youtube_comment_thread_{thread_index:03d}_brett_murphy_reply",
                    "thread_index": thread_index,
                    "section": "comments",
                    "source_kind": "youtube_comment_reply",
                    "source_role_status": "RESOLVED_SECONDARY_SOURCE",
                    "source_role_label": "Secondary — preserved YouTube comment by transcript/source person",
                    "author_handle": reply_handle,
                    "canonical_person": linked_person,
                    "time_label": reply_time,
                    "text": reply_text,
                    "source_url": source_url,
                    "linked_persons": [linked_person] if linked_person else [],
                    "does_not_create_person": True,
                    "does_not_create_new_person": True,
                    "merged_into_canonical_transcript": False,
                    "affects_transcript_claim_span_counts": False,
                }
            )
    return tuple(records)


def _artifact_source_title(source_title: str, artifact: ProfileMediaSourcePackageArtifact, index: int) -> str:
    evidence_profile = _source_text_evidence_profile(artifact)
    if evidence_profile:
        return evidence_profile["source_title"]
    prefix = _clean_text(source_title, fallback=_SOURCE_DEFAULT_TITLE)
    label = _clean_text(artifact.display_name, fallback=f"{artifact.artifact_kind} {index}")
    kind = artifact.artifact_kind.replace("_", " ")
    artifact_kind = normalise_source_package_artifact_kind(artifact.artifact_kind, path=artifact.local_path or artifact.display_name)
    is_media_kind = artifact_kind in {"video", "audio", "image", "screenshot", "transcript"}
    has_own_link = bool(_clean_text(artifact.source_url) or _clean_text(artifact.canonical_url) or _clean_text(artifact.reference_url))
    if artifact.internal_media and is_media_kind:
        return label
    if is_media_kind and not has_own_link:
        return label
    return f"{prefix} — {kind}: {label}"


def _artifact_notes(artifact: ProfileMediaSourcePackageArtifact) -> str:
    details = [
        "V82A source-package preview artifact; review before saving to HOME.",
        f"artifact_kind={artifact.artifact_kind}",
    ]
    if artifact.local_path:
        details.append(f"temporary_local_path={artifact.local_path}")
    if artifact.reference_url:
        details.append(f"reference_url={artifact.reference_url}")
    dimensions = _artifact_dimension_text(artifact)
    if dimensions:
        details.append(f"dimensions={dimensions}")
    if artifact.byte_size:
        details.append(f"byte_size={artifact.byte_size}")
    if artifact.notes:
        details.append(f"notes={artifact.notes}")
    if artifact.internal_media:
        details.append("internal_media=True")
    evidence_profile = _source_text_evidence_profile(artifact)
    if evidence_profile:
        details.append("source_text_evidence=True")
        if evidence_profile.get("source_summary"):
            details.append(f"source_evidence_summary={evidence_profile['source_summary']}")
        if evidence_profile.get("source_metadata_summary"):
            details.append(f"source_metadata_summary={evidence_profile['source_metadata_summary']}")
        if evidence_profile.get("source_link"):
            details.append(f"source_evidence_link={evidence_profile['source_link']}")
        details.append("source_text_role=PRIMARY_MEDIA_SOURCE_URL")
        details.append("semantic_claim_excerpts_suppressed=True")
    details.append("No file copy, media download, folder scan, automatic classification, or sensitive inference was performed by this preview builder.")
    return " | ".join(details)


def personhood_role_for_package_artifact(artifact: ProfileMediaSourcePackageArtifact) -> str:
    """Default personhood scope for a media artifact.

    V82S keeps personhood blank for local/operator media.  The app cannot know
    whether the operator is the person in the media (Primary), a witness/recorder
    at the event (Secondary), or outside the event (Tertiary).  Blank personhood
    is shown as Review and does not inflate Unknown/Tertiary counters.
    """

    explicit = canonical_source_role(artifact.media_personhood_role) if artifact.media_personhood_role else ""
    if explicit in {
        ProfileSourceRole.PRIMARY_SELF_AUTHORED_SCOPE.value,
        ProfileSourceRole.SECONDARY_WITNESS_ACCOUNT.value,
        ProfileSourceRole.TERTIARY_PROPAGATED_SOURCE.value,
        ProfileSourceRole.UNKNOWN_SOURCE_ROLE.value,
    }:
        return explicit
    artifact_kind = normalise_source_package_artifact_kind(artifact.artifact_kind, path=artifact.local_path or artifact.display_name)
    has_own_link = bool(artifact.source_url or artifact.canonical_url or artifact.reference_url)
    if artifact_kind in {"video", "audio", "image", "screenshot", "transcript"} and (artifact.internal_media or not has_own_link):
        return ""
    return canonical_source_role(ProfileSourceRole.TERTIARY_PROPAGATED_SOURCE.value)


def _source_spec_for_artifact(
    *,
    source_url: str,
    canonical_url: str,
    source_title: str,
    artifact: ProfileMediaSourcePackageArtifact,
    index: int,
) -> dict[str, Any]:
    internal = bool(getattr(artifact, "internal_media", False))
    artifact_kind = normalise_source_package_artifact_kind(artifact.artifact_kind, path=artifact.local_path or artifact.display_name)
    evidence_profile = _source_text_evidence_profile(artifact)
    media_kind = artifact_kind in {"video", "audio", "image", "screenshot"}
    has_own_link = bool(artifact.source_url or artifact.canonical_url or artifact.reference_url)
    if evidence_profile:
        artifact_page = evidence_profile.get("source_page") or artifact.local_path
    elif internal or (media_kind and not has_own_link):
        # Operator-supplied/local media must not silently inherit the active article URL.
        # It remains an unlinked media item until the reviewer connects it by notes/tags/persons.
        artifact_page = ""
    else:
        artifact_page = artifact.source_url or artifact.canonical_url or artifact.reference_url or canonical_url or source_url
    personhood_role = personhood_role_for_package_artifact(artifact) if media_kind else ""
    personhood_note = ("internal_media=primary_media; personhood_scope=review" if internal and media_kind and not personhood_role else f"internal_media=primary_media; personhood_scope={personhood_role}" if internal and media_kind else source_role_policy_note_for_package_artifact_kind(artifact.artifact_kind))
    unlinked_media = bool(media_kind and not artifact_page)
    return {
        "source_page": artifact_page,
        "source_title": _artifact_source_title(source_title, artifact, index),
        "source_bucket": source_bucket_for_package_artifact(artifact),
        "source_role": source_role_for_package_artifact(artifact),
        "claim_basis": claim_basis_for_package_artifact(artifact),
        "currentness_status": currentness_status_for_package_artifact_kind(artifact.artifact_kind),
        "source_chain_gap": False if (internal or evidence_profile) else True,
        "disputed_framing": False,
        "source_role_review_required": False if evidence_profile else True if (media_kind and unlinked_media and not internal) else False if (media_kind and internal) else bool(artifact.review_required),
        "final_source_role_decision": False,
        "internal_media": internal,
        "unlinked_media": unlinked_media,
        "media_personhood_role": personhood_role,
        "media_personhood_review_required": True if (media_kind and (internal or unlinked_media)) else (bool(artifact.review_required) if media_kind else False),
        "confidence_or_verification_notes": _artifact_notes(artifact)
        + " | "
        + personhood_note,
    }


def _source_page_spec(source_url: str, canonical_url: str, source_title: str, article_text: object = "") -> dict[str, Any]:
    source_role = source_role_for_source_page_from_text(article_text)
    claim_basis = claim_basis_for_source_page_from_text(article_text)
    has_direct_witness = source_role == ProfileSourceRole.SECONDARY_WITNESS_ACCOUNT.value
    scaffold_note = (
        "source_role_policy=profile_media_source_role_policy.v76e; "
        + (
            "source_role_scaffold=source_page->SECONDARY_WITNESS_ACCOUNT; article_contains_direct_interview=True; "
            if has_direct_witness
            else "source_role_scaffold=source_page->TERTIARY_PROPAGATED_SOURCE; article_contains_direct_interview=False; "
        )
        + "final_source_role_decision=False; review lane attached where required; Primary/Self-authored and Secondary/Witness-account scopes must be marked by reviewer or explicit source-chain evidence."
    )
    return {
        "source_page": canonical_url or source_url,
        "source_title": _clean_text(source_title, fallback=_SOURCE_DEFAULT_TITLE),
        "source_bucket": "Articles",
        "source_role": source_role,
        "claim_basis": claim_basis,
        "currentness_status": currentness_status_for_package_artifact_kind("source_page", root_source_record=True),
        "source_chain_gap": False if has_direct_witness else True,
        "disputed_framing": False,
        "source_role_review_required": False,
        "final_source_role_decision": False,
        "confidence_or_verification_notes": (
            "V82O source-page relationship record. The article/source page is Secondary only when explicit article text shows the publisher interviewed or directly quoted a witness; otherwise it remains Tertiary. | "
            + scaffold_note
        ),
    }



# SOURCE_CHAIN_DEFINITION_SET_PASS6_20260827
def _source_reference_role_from_chain_candidate(ref: Mapping[str, Any]) -> str:
    role = _clean_text(ref.get("candidate_source_role") or ref.get("media_source_role"))
    if role in {"PRIMARY_SELF_AUTHORED_SCOPE", "SECONDARY_WITNESS_ACCOUNT", "TERTIARY_PROPAGATED_SOURCE", "UNKNOWN_SOURCE_ROLE"}:
        return role
    status = _clean_text(ref.get("source_reference_status"))
    if status in {"MEDIA_SOURCE_TERTIARY", "RESOLVED_TERTIARY_SOURCE"}: return "TERTIARY_PROPAGATED_SOURCE"
    if status in {"MEDIA_SOURCE_SECONDARY", "RESOLVED_SECONDARY_SOURCE"}: return "SECONDARY_WITNESS_ACCOUNT"
    if status in {"MEDIA_SOURCE_PRIMARY", "RESOLVED_PRIMARY_SOURCE"}: return "PRIMARY_SELF_AUTHORED_SCOPE"
    return "UNKNOWN_SOURCE_ROLE"
def _source_reference_review_required_from_chain_candidate(ref: Mapping[str, Any]) -> bool:
    return bool(ref.get("review_required", False)) and str(ref.get("goes_to_review_text", True)).lower() != "false"


def _source_chain_count_key(ref: Mapping[str, Any]) -> str:
    """Stable user-facing source-count key for pass6 media-source records.

    Source TXT imports can contain duplicate transcript streams and near-duplicate
    clause boundaries.  Sidebar/media-source counts should count the distinct
    provenance statements the Review textbox shows, not every raw classifier row.
    """
    def _source_chain_norm_key(value: Any) -> str:
        return re.sub(r"\s+", " ", str(value or "").replace("\r", " ").replace("\n", " ")).strip().casefold()

    template_id = _clean_text(ref.get("source_chain_template_id") or ref.get("source_pointer_type"))
    actor_key = _source_chain_norm_key(ref.get("source_actor"))
    text_key = _source_chain_norm_key(ref.get("text") or ref.get("excerpt") or ref.get("subject"))
    text_key = re.sub(r"\b(so this was the latest push and they)\s+\1\b", r"\1", text_key)
    text_key = text_key.replace("regret rate for abortions", "regret rate for abortion")
    text_key = text_key.replace("university there are two male suicides", "university, there are two male suicides")
    if template_id == "named_intermediary_told_speaker" and actor_key:
        return f"{template_id}|{actor_key}"
    if template_id == "statistical_claim_no_named_source" or _clean_text(ref.get("source_pointer_type")) == "statistical_claim_no_attached_source":
        if "high rates among the sodomite community" in text_key:
            return "statistical_claim_no_named_source|high_rates_sodomite_community"
        if "hundreds of thousands of pounds" in text_key:
            return "statistical_claim_no_named_source|hundreds_thousands_pounds"
        if "250,000" in text_key or "250000" in text_key:
            return "statistical_claim_no_named_source|250000_children"
        if "regret rate for abortion" in text_key:
            return "statistical_claim_no_named_source|abortion_regret_rate"
        if "two male suicides a week" in text_key:
            return "statistical_claim_no_named_source|two_male_suicides_week"
    return f"{template_id}|{actor_key}|{text_key}"

def build_profile_media_source_package_preview(
    *,
    database_root: object = "",
    case_title: object = "",
    source_url: object = "",
    source_title: object = "",
    canonical_url: object = "",
    artifacts: Iterable[Mapping[str, Any] | ProfileMediaSourcePackageArtifact] = (),
    include_source_page_record: bool = True,
) -> ProfileMediaSourcePackagePreview:
    """Build a reviewable Database import package from one source and artifacts."""

    src_url = str(source_url or "").strip()
    canon = str(canonical_url or "").strip()
    title = _clean_text(source_title, fallback=_SOURCE_DEFAULT_TITLE)
    db_root = str(database_root or "").strip()
    case = _clean_text(case_title, fallback=_CASE_DEFAULT_TITLE)

    warnings: list[str] = []
    if not src_url and not canon:
        warnings.append("missing_source_url")
    if not db_root:
        warnings.append("database_root_not_configured_preview_still_loadable")
    coerced = []
    for item in artifacts:
        if isinstance(item, ProfileMediaSourcePackageArtifact):
            coerced.append(item)
        elif isinstance(item, Mapping):
            coerced.append(package_artifact_from_mapping(item))
        else:
            warnings.append(f"skipped_unknown_artifact_type:{type(item).__name__}")
    safe_artifacts = _dedupe_artifacts(coerced)
    article_text_context = _article_text_from_artifacts(safe_artifacts)
    source_evidence_text_context = "\n\n".join(text for _artifact, text, _profile in _source_evidence_texts_from_artifacts(safe_artifacts))
    source_role_matching_preview = (
        build_source_role_matching_preview(article_text_context, source_evidence_text_context)
        if article_text_context and source_evidence_text_context
        else {
            "schema_version": "profile-media-source-role-matching-v1",
            "article_claim_count": 0,
            "transcript_passage_count": 0,
            "match_count": 0,
            "final_source_role_decision": False,
            "claims": [],
            "transcript_passages": [],
            "matches": [],
        }
    )
    source_role_segments = build_source_role_segment_candidates_from_artifacts(
        source_title=title,
        source_url=canon or src_url,
        artifacts=safe_artifacts,
    )
    claim_role_classification_preview = build_claim_role_classification_preview_from_artifacts(safe_artifacts)
    transcript_provenance_preview = build_transcript_provenance_preview_from_artifacts(safe_artifacts)
    source_reference_inputs: list[Mapping[str, Any] | str] = [
        span for span in claim_role_classification_preview.get("spans", ()) if isinstance(span, Mapping)
    ]
    for _artifact, source_text, _source_profile in _source_evidence_texts_from_artifacts(safe_artifacts):
        sections = _split_youtube_source_text_sections(source_text)
        for section_label in ("operator_notes", "research_notes", "external_sources", "copied_ai_analysis", "unknown_appendix"):
            section_text = sections.get(section_label) or ""
            for chunk in re.split(r"\n{2,}|(?<=[.!?])\s+", section_text):
                clean_chunk = _clean_text(chunk)
                if clean_chunk:
                    source_reference_inputs.append({"text": clean_chunk, "section_label": section_label})
    source_reference_candidate_preview = extract_source_reference_candidates(
        source_reference_inputs,
        current_source_name=title,
        attached_source_urls=[
            str(artifact.source_url or artifact.canonical_url or artifact.reference_url or "")
            for artifact in safe_artifacts
            if str(artifact.source_url or artifact.canonical_url or artifact.reference_url or "").strip()
        ],
    )
    source_link_role_candidates = _source_link_role_candidates_from_artifacts(
        safe_artifacts,
        claim_spans=[span for span in claim_role_classification_preview.get("spans", ()) if isinstance(span, Mapping)],
    )
    link_source_preview = _link_source_preview_from_artifacts(
        safe_artifacts,
        source_url=src_url,
        canonical_url=canon,
        source_title=title,
    )
    link_source_decisions_path = _link_source_decisions_path_for_preview(
        safe_artifacts,
        database_root=db_root,
        source_title=title,
    )
    link_source_decisions = load_link_source_decisions(link_source_decisions_path)
    link_source_objects = apply_link_source_decisions(
        [dict(item) for item in link_source_preview.get("objects", ()) if isinstance(item, Mapping)],
        link_source_decisions,
    )
    link_source_objects = resolve_visible_link_source_roles(link_source_objects)
    article_media_details = _article_media_details_from_text(article_text_context)
    if article_media_details:
        link_source_objects = [
            {
                **dict(item),
                "article_media_details": [dict(detail) for detail in article_media_details],
                "article_media_details_derived_from_text": True,
            }
            for item in link_source_objects
        ]
    link_source_preview = build_link_source_preview(link_source_objects)
    link_source_preview["objects"] = list(link_source_objects)
    link_source_preview["link_count"] = len(link_source_objects)
    link_source_preview["decision_summary"] = build_link_source_decision_summary(link_source_objects)
    link_source_preview["link_source_decisions_path"] = link_source_decisions_path
    link_source_preview["link_source_decisions_count"] = len(link_source_decisions)
    link_source_preview["link_source_decisions_applied"] = bool(link_source_decisions)
    claim_span_counts = {role: 0 for role in ("PRIMARY", "SECONDARY", "TERTIARY", "UNKNOWN")}
    for span in claim_role_classification_preview.get("spans", ()):
        if not isinstance(span, Mapping):
            continue
        role = str(span.get("role") or "").strip().upper()
        if role in claim_span_counts:
            claim_span_counts[role] += 1
    # YTCE_REVIEW_COUNT_VISIBLE_FILTER_PASS5F_20260827
    def _review_count_key(value: Any) -> str:
        text_value = str(value or "").replace("\r", " ").replace("\n", " ")
        return re.sub(r"\s+", " ", text_value).strip().casefold()

    claim_span_by_edit_key: dict[str, Mapping[str, Any]] = {}
    claim_span_by_text: dict[str, Mapping[str, Any]] = {}
    for span in claim_role_classification_preview.get("spans", ()):
        if not isinstance(span, Mapping):
            continue
        span_text_key = _review_count_key(span.get("text"))
        if span_text_key:
            claim_span_by_text.setdefault(span_text_key, span)
        span_edit_key = str(span.get("edit_key") or "").strip()
        if span_edit_key:
            claim_span_by_edit_key.setdefault(span_edit_key, span)

    source_reference_segments = []
    visible_source_reference_review_keys: set[str] = set()
    raw_source_reference_review_keys: set[str] = set()
    for ref_index, ref in enumerate(source_reference_candidate_preview.get("main_sourcing_card_candidates", ()), start=1):
        if not isinstance(ref, Mapping):
            continue
        if "unknown_media_requirement_met" in ref and not bool(ref.get("unknown_media_requirement_met")):
            continue
        candidate_review_required = _source_reference_review_required_from_chain_candidate(ref)
        ref_text_key = _review_count_key(ref.get("text") or ref.get("excerpt") or ref.get("subject"))
        if candidate_review_required and ref_text_key:
            raw_source_reference_review_keys.add(ref_text_key)
        linked_edit_key = str(ref.get("linked_claim_span_edit_key") or ref.get("claim_span_edit_key") or "").strip()
        matched_claim_span = claim_span_by_edit_key.get(linked_edit_key) if linked_edit_key else None
        if matched_claim_span is None and ref_text_key:
            matched_claim_span = claim_span_by_text.get(ref_text_key)
        if candidate_review_required and matched_claim_span is not None:
            visible_key = _review_count_key(matched_claim_span.get("text") or ref_text_key)
            if visible_key:
                visible_source_reference_review_keys.add(visible_key)
        candidate_source_role = _source_reference_role_from_chain_candidate(ref)
        source_reference_segments.append(
            {
                "segment_id": f"source_reference_candidate_{ref_index:03d}",
                "subject": f"Source-reference candidate / {_clean_text(ref.get('source_pointer_type'), fallback='unresolved source')}",
                "candidate_source_role": candidate_source_role,
                "candidate_claim_basis": _clean_text(ref.get("candidate_claim_basis"), fallback=ClaimBasis.UNKNOWN_CLAIM_BASIS.value),
                "source_chain_gap": bool(ref.get("source_chain_gap", False)) or candidate_source_role == "UNKNOWN_SOURCE_ROLE" or candidate_review_required,
                "review_required": candidate_review_required,
                "final_source_role_decision": not candidate_review_required,
                "review_reason": _clean_text(ref.get("reason")),
                "excerpt": _clean_text(ref.get("text")),
                "source_url": canon or src_url,
                "source_reference_candidate": True,
                "source_reference_status": _clean_text(ref.get("source_reference_status")),
                "source_pointer_type": _clean_text(ref.get("source_pointer_type")),
                "source_chain_template_id": _clean_text(ref.get("source_chain_template_id")),
                "source_chain_summary": _clean_text(ref.get("source_chain_summary")),
                "media_source_role": candidate_source_role,
                "goes_to_main_sourcing_card": True,
                "goes_to_review_text": bool(ref.get("goes_to_review_text", False)),
                "linked_claim_span_edit_key": _clean_text(ref.get("linked_claim_span_edit_key")),
            }
        )
    source_reference_review_count = len(visible_source_reference_review_keys)
    if source_reference_review_count <= 0 and not claim_span_by_edit_key and not claim_span_by_text:
        source_reference_review_count = len(raw_source_reference_review_keys)
    source_role_segments = tuple(list(source_role_segments) + source_reference_segments)
    generated_excerpts_suppressed = len(_source_evidence_texts_from_artifacts(safe_artifacts))
    source_record_count_breakdown = {
        "primary_media_sources": sum(
            1
            for record in transcript_provenance_preview.get("records", ())
            if isinstance(record, Mapping) and record.get("media_source_role") == "PRIMARY_MEDIA_URL"
        ),
        "transcript_provenance_records": int(transcript_provenance_preview.get("record_count", 0) or 0),
        "secondary_transcript_records": sum(
            1
            for record in transcript_provenance_preview.get("records", ())
            if isinstance(record, Mapping) and str(record.get("transcript_provenance_role") or "").startswith(("SECONDARY_TRANSCRIPT", "VERIFIED_SECONDARY_TRANSCRIPT"))
        ),
        "unknown_transcript_provenance_records": sum(
            1
            for record in transcript_provenance_preview.get("records", ())
            if isinstance(record, Mapping) and record.get("transcript_provenance_role") == "UNKNOWN_TRANSCRIPT_PROVENANCE"
        ),
        "resolved_secondary_references": sum(
            1
            for ref in source_reference_candidate_preview.get("candidates", ())
            if isinstance(ref, Mapping) and ref.get("source_reference_status") == "RESOLVED_SECONDARY_SOURCE"
        ),
        "resolved_tertiary_references": sum(
            1
            for ref in source_reference_candidate_preview.get("candidates", ())
            if isinstance(ref, Mapping) and ref.get("source_reference_status") == "RESOLVED_TERTIARY_SOURCE"
        ),
        # YTCE_REVIEW_COUNT_DISPLAY_SYNC_PASS5D_20260827: count the unique
        # source-reference segments actually promoted to the visible Sourcing/Review
        # lane, not a stale/raw candidate counter.
        "unresolved_source_reference_candidates": source_reference_review_count,
        "generated_excerpts_suppressed": generated_excerpts_suppressed,
        "youtube_comment_source_role_threads": 0,
        "youtube_comment_source_role_records": 0,
        "claim_span_counts_do_not_inflate_source_records": True,
    }

    # SOURCE_CHAIN_DEFINITION_SET_PASS6_20260827
    _source_chain_main_candidates = [ref for ref in source_reference_candidate_preview.get("main_sourcing_card_candidates", ()) if isinstance(ref, Mapping)]
    _source_chain_role_keys = {
        "PRIMARY_SELF_AUTHORED_SCOPE": set(),
        "SECONDARY_WITNESS_ACCOUNT": set(),
        "TERTIARY_PROPAGATED_SOURCE": set(),
        "UNKNOWN_SOURCE_ROLE": set(),
    }
    _source_chain_raw_review_count = 0
    for ref in _source_chain_main_candidates:
        if _source_reference_review_required_from_chain_candidate(ref):
            _source_chain_raw_review_count += 1
            continue
        role = _source_reference_role_from_chain_candidate(ref)
        if role not in _source_chain_role_keys:
            continue
        if "unknown_media_requirement_met" in ref and not bool(ref.get("unknown_media_requirement_met")):
            continue
        key = _source_chain_count_key(ref)
        if key:
            _source_chain_role_keys[role].add(key)
    _source_chain_role_counts = {role: len(keys) for role, keys in _source_chain_role_keys.items()}
    source_record_count_breakdown["resolved_primary_references"] = _source_chain_role_counts["PRIMARY_SELF_AUTHORED_SCOPE"]
    source_record_count_breakdown["resolved_secondary_references"] = _source_chain_role_counts["SECONDARY_WITNESS_ACCOUNT"]
    source_record_count_breakdown["resolved_tertiary_references"] = _source_chain_role_counts["TERTIARY_PROPAGATED_SOURCE"]
    source_record_count_breakdown["unknown_media_source_statements"] = _source_chain_role_counts["UNKNOWN_SOURCE_ROLE"]
    source_record_count_breakdown["raw_review_source_reference_candidates"] = _source_chain_raw_review_count
    source_record_count_breakdown["visible_source_reference_review_count"] = source_reference_review_count
    source_record_count_breakdown["review_source_reference_candidates"] = source_reference_review_count
    source_record_count_breakdown["unresolved_source_reference_candidates"] = source_reference_review_count
    source_record_count_breakdown["source_chain_definition_set_applied"] = True
    person_review_candidates = build_person_review_candidates_from_artifacts(
        source_title=title,
        source_url=canon or src_url,
        artifacts=safe_artifacts,
    )
    related_comment_review_sections = _related_comment_review_sections_from_person_candidates(person_review_candidates)
    youtube_comment_source_role_records = _youtube_comment_source_role_records_from_review_sections(related_comment_review_sections)
    source_record_count_breakdown["youtube_comment_source_role_threads"] = len(related_comment_review_sections)
    source_record_count_breakdown["youtube_comment_source_role_records"] = len(youtube_comment_source_role_records)
    if related_comment_review_sections:
        claim_role_classification_preview = dict(claim_role_classification_preview)
        claim_role_classification_preview["related_comment_review_sections"] = list(related_comment_review_sections)
        claim_role_classification_preview["related_comment_review_section_count"] = len(related_comment_review_sections)
        claim_role_classification_preview["youtube_comment_source_role_records"] = list(youtube_comment_source_role_records)
        claim_role_classification_preview["youtube_comment_source_role_record_count"] = len(youtube_comment_source_role_records)
        claim_role_classification_preview["comments_merged_into_canonical_transcript"] = False
        claim_role_classification_preview["comment_sections_affect_transcript_claim_span_counts"] = False

    sources: list[dict[str, Any]] = []
    if include_source_page_record:
        sources.append(_source_page_spec(src_url, canon, title, article_text_context))
    for index, artifact in enumerate(safe_artifacts, start=1):
        sources.append(
            _source_spec_for_artifact(
                source_url=src_url,
                canonical_url=canon,
                source_title=title,
                artifact=artifact,
                index=index,
            )
        )
    for index, segment in enumerate(source_role_segments, start=1):
        sources.append(
            _segment_source_spec(
                source_url=src_url,
                canonical_url=canon,
                source_title=title,
                segment=segment,
                index=index,
            )
        )
    profiles = [
        _profile_spec_from_person_candidate(candidate, source_url=canon or src_url, source_title=title)
        for candidate in person_review_candidates
    ]

    batch_payload: dict[str, Any] = {
        "schema_version": PROFILE_MEDIA_CASE_BATCH_SCHEMA_VERSION,
        "database_root": db_root,
        "case_title": case,
        "sources": sources,
        "profiles": profiles,
        "source_package_preview": {
            "schema_version": PROFILE_MEDIA_SOURCE_PACKAGE_PREVIEW_SCHEMA_VERSION,
            "source_url": src_url,
            "canonical_url": canon,
            "source_title": title,
            "source_domain": _domain_from_url(canon or src_url),
            "artifact_count": len(safe_artifacts),
            "artifacts": [artifact.to_dict() for artifact in safe_artifacts],
            "source_role_segments": list(source_role_segments),
            "source_role_segment_count": len(source_role_segments),
            "source_role_matching_preview": source_role_matching_preview,
            "claim_role_classification_preview": claim_role_classification_preview,
            "claim_role_span_count": int(claim_role_classification_preview.get("span_count", 0) or 0),
            "related_comment_review_sections": list(related_comment_review_sections),
            "related_comment_review_section_count": len(related_comment_review_sections),
            "youtube_comment_source_role_records": list(youtube_comment_source_role_records),
            "youtube_comment_source_role_record_count": len(youtube_comment_source_role_records),
            "youtube_comment_source_role_thread_count": len(related_comment_review_sections),
            "claim_span_counts": dict(claim_span_counts),
            "claim_span_counts_exclude_blank_visible": True,
            "transcript_provenance_preview": transcript_provenance_preview,
            "source_reference_candidate_preview": source_reference_candidate_preview,
            "source_reference_candidate_count": len(source_reference_segments),
            "source_link_role_candidates": list(source_link_role_candidates),
            "source_link_role_candidate_count": len(source_link_role_candidates),
            "link_source_preview": dict(link_source_preview),
            "link_source_objects": list(link_source_objects),
            "link_source_object_count": int(link_source_preview.get("link_count", 0) or 0),
            "link_source_objects_separate_from_claim_spans": True,
            "article_media_details": [dict(detail) for detail in article_media_details],
            "article_media_details_derived_from_text": bool(article_media_details),
            "link_source_decisions_path": link_source_decisions_path,
            "link_source_decisions_count": len(link_source_decisions),
            "source_record_count_breakdown": dict(source_record_count_breakdown),
            "generated_excerpts_suppressed": generated_excerpts_suppressed,
            "person_review_candidates": list(person_review_candidates),
            "person_review_candidate_count": len({str(person.get("canonical_name") or "").strip().lower() for person in person_review_candidates if str(person.get("canonical_name") or "").strip()}),
            "review_required": True,
            "source_role_policy_applied": True,
            "source_role_policy": {
                "schema_version": "profile-media-source-role-policy-v76e",
                "root_source_role": source_role_for_package_artifact_kind("source_page", root_source_record=True),
                "artifact_source_role": source_role_for_package_artifact_kind("artifact"),
                "claim_basis": claim_basis_for_package_artifact_kind("artifact"),
                "final_source_role_decision": False,
                "review_required": True,
                "note": "Source-package artifact records are scaffolded conservatively; source_role_segments contains mixed-role review candidates such as direct witness quotes and reported self-authored posts with source-chain gaps.",
            },
            "temporary_local_paths_preserved": True,
            "folder_scan_performed": False,
            "folder_creation_performed": False,
            "folder_move_performed": False,
            "folder_rename_performed": False,
            "file_copy_performed": False,
            "file_write_performed": False,
            "media_download_performed": False,
            "web_download_performed": False,
            "screenshot_performed": False,
            "archive_provider_call_performed": False,
            "automatic_classification_performed": False,
            "sensitive_identifier_inference_performed": False,
        },
    }
    status = "preview_ready" if sources else "preview_empty"
    return ProfileMediaSourcePackagePreview(
        status=status,
        database_root=db_root,
        case_title=case,
        source_url=src_url,
        canonical_url=canon,
        source_title=title,
        source_domain=_domain_from_url(canon or src_url),
        artifacts=safe_artifacts,
        batch_payload=batch_payload,
        warnings=tuple(warnings),
    )


def write_profile_media_source_package_preview_json(
    preview: ProfileMediaSourcePackagePreview,
    output_json: object,
    *,
    confirmation_phrase: object = "",
) -> ProfileMediaSourcePackageWriteResult:
    """Write the import JSON only with the exact confirmation phrase."""

    output_path = Path(str(output_json or "")).expanduser()
    warnings: list[str] = []
    if str(confirmation_phrase or "") != WRITE_PROFILE_MEDIA_SOURCE_PACKAGE_PREVIEW_CONFIRMATION:
        warnings.append(f"confirmation_phrase_must_equal:{WRITE_PROFILE_MEDIA_SOURCE_PACKAGE_PREVIEW_CONFIRMATION}")
        return ProfileMediaSourcePackageWriteResult(
            status="blocked_confirmation_required",
            output_json=str(output_path),
            warning_count=len(warnings),
            warnings=tuple(warnings),
        )
    if not str(output_json or "").strip():
        warnings.append("missing_output_json")
        return ProfileMediaSourcePackageWriteResult(
            status="blocked_missing_output_json",
            output_json="",
            warning_count=len(warnings),
            warnings=tuple(warnings),
        )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(preview.batch_payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return ProfileMediaSourcePackageWriteResult(
        status="written",
        output_json=str(output_path),
        written_file=str(output_path),
        file_write_performed=True,
    )


def render_profile_media_source_package_preview_text(preview: ProfileMediaSourcePackagePreview) -> str:
    """Render a compact human review summary for the import package."""

    lines = [
        "Profile/Media source package preview",
        f"Status: {preview.status}",
        f"Database root: {preview.database_root or '(not configured)'}",
        f"Case title: {preview.case_title}",
        f"Source: {preview.source_title}",
        f"Source URL: {preview.source_url or preview.canonical_url or '(missing)'}",
        f"Artifacts: {preview.artifact_count}",
        f"Database source records: {preview.source_count}",
        "Profiles: 0",
        "",
        "Safety:",
        f"- Folder scan performed: {preview.folder_scan_performed}",
        f"- File copy performed: {preview.file_copy_performed}",
        f"- Media download performed: {preview.media_download_performed}",
        f"- Web download performed: {preview.web_download_performed}",
        f"- Automatic classification performed: {preview.automatic_classification_performed}",
        f"- Sensitive identifier inference performed: {preview.sensitive_identifier_inference_performed}",
        "",
        "Artifacts:",
    ]
    if preview.artifacts:
        for index, artifact in enumerate(preview.artifacts, start=1):
            dimensions = _artifact_dimension_text(artifact)
            parts = [f"{index}. {artifact.artifact_kind}", artifact.display_name]
            if dimensions:
                parts.append(dimensions)
            if artifact.byte_size:
                parts.append(f"{artifact.byte_size} bytes")
            if artifact.local_path:
                parts.append(f"temp={artifact.local_path}")
            lines.append(" - " + " · ".join(part for part in parts if part))
    else:
        lines.append(" - none")
    preview_section = preview.batch_payload.get("source_package_preview") if isinstance(preview.batch_payload, Mapping) else {}
    breakdown = preview_section.get("source_record_count_breakdown") if isinstance(preview_section, Mapping) else {}
    if isinstance(breakdown, Mapping):
        lines.extend(
            [
                "",
                "SOURCE RECORD COUNTS:",
                f"Primary media sources: {int(breakdown.get('primary_media_sources') or 0)}",
                f"Transcript provenance records: {int(breakdown.get('transcript_provenance_records') or 0)}",
                f"Secondary transcript records: {int(breakdown.get('secondary_transcript_records') or breakdown.get('transcript_secondary_records') or 0)}",
                f"Resolved secondary references: {int(breakdown.get('resolved_secondary_references') or 0)}",
                f"Resolved tertiary references: {int(breakdown.get('resolved_tertiary_references') or 0)}",
                f"Unresolved source-reference candidates: {int(breakdown.get('unresolved_source_reference_candidates') or 0)}",
                f"Generated excerpts suppressed: {int(breakdown.get('generated_excerpts_suppressed') or 0)}",
                f"YouTube comment source roles: {int(breakdown.get('youtube_comment_source_role_threads') or 0)} threads / {int(breakdown.get('youtube_comment_source_role_records') or 0)} records",
            ]
        )
    link_source_preview = preview_section.get("link_source_preview") if isinstance(preview_section, Mapping) else {}
    if isinstance(link_source_preview, Mapping):
        role_counts = link_source_preview.get("role_counts")
        role_counts = role_counts if isinstance(role_counts, Mapping) else {}
        visible_role_counts = link_source_preview.get("visible_role_counts")
        visible_role_counts = visible_role_counts if isinstance(visible_role_counts, Mapping) else role_counts
        lines.extend(
            [
                "",
                "LINK SOURCE OBJECTS:",
                f"Links: {int(link_source_preview.get('link_count') or 0)}",
                (
                    "Visible roles: "
                    f"Primary {int(visible_role_counts.get('PRIMARY') or 0)} | "
                    f"Secondary {int(visible_role_counts.get('SECONDARY') or 0)} | "
                    f"Tertiary {int(visible_role_counts.get('TERTIARY') or 0)} | "
                    f"Unknown {int(visible_role_counts.get('UNKNOWN') or 0)}"
                ),
                f"Internal locator/preservation records: {int(role_counts.get('LOCATOR') or 0)}",
                f"Separate from claim spans: {bool(link_source_preview.get('link_objects_are_separate_from_claim_role_spans'))}",
            ]
        )
    comment_source_records = preview_section.get("youtube_comment_source_role_records") if isinstance(preview_section, Mapping) else ()
    if isinstance(comment_source_records, list) and comment_source_records:
        lines.extend(["", "YouTube comment source roles"])
        for record in comment_source_records[:8]:
            if not isinstance(record, Mapping):
                continue
            lines.extend(
                [
                    "",
                    _clean_text(record.get("source_role_label"), fallback="Secondary — preserved YouTube comment"),
                    f"Section: {_clean_text(record.get('section'), fallback='comments')}",
                    f"Author: {_clean_text(record.get('author_handle'), fallback='(unknown)')}",
                ]
            )
            linked_people = [str(item).strip() for item in record.get("linked_persons", ()) or () if str(item).strip()] if isinstance(record.get("linked_persons"), list) else []
            if linked_people:
                lines.append("Linked person: " + ", ".join(linked_people))
            if _clean_text(record.get("time_label")):
                lines.append(f"Time: {_clean_text(record.get('time_label'))}")
            if _clean_text(record.get("text")):
                lines.append(f"Text: {_clean_text(record.get('text'))}")
        if len(comment_source_records) > 8:
            lines.append(f"... {len(comment_source_records) - 8} more YouTube comment source-role records")
    claim_counts = preview_section.get("claim_span_counts") if isinstance(preview_section, Mapping) else {}
    if isinstance(claim_counts, Mapping):
        lines.extend(
            [
                "",
                "CLAIM SPAN COUNTS:",
                f"Primary: {int(claim_counts.get('PRIMARY') or 0)} | Secondary: {int(claim_counts.get('SECONDARY') or 0)} | Tertiary: {int(claim_counts.get('TERTIARY') or 0)} | Unknown: {int(claim_counts.get('UNKNOWN') or 0)}",
            ]
        )
    if preview.warnings:
        lines.extend(["", "Warnings:"])
        lines.extend(f"- {warning}" for warning in preview.warnings)
    return "\n".join(lines)


def source_package_preview_payload(preview: ProfileMediaSourcePackagePreview, *, include_text: bool = False) -> dict[str, Any]:
    payload = preview.to_dict()
    if include_text:
        payload["preview_text"] = render_profile_media_source_package_preview_text(preview)
    return payload
