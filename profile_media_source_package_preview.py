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
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping
from urllib.parse import urlparse

from profile_media_case_batch import PROFILE_MEDIA_CASE_BATCH_SCHEMA_VERSION
from profile_media_database import utc_now_iso


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
    if text in {"article", "article_text", "webpage_text", "text_article"}:
        return "article_text"
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
    if normalised == "article_text":
        return "Articles"
    if normalised in {"screenshot", "image", "video", "audio", "transcript", "archive_receipt"}:
        return "Reference Extants"
    return "Reference Extants"


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


def _artifact_source_title(source_title: str, artifact: ProfileMediaSourcePackageArtifact, index: int) -> str:
    prefix = _clean_text(source_title, fallback=_SOURCE_DEFAULT_TITLE)
    label = _clean_text(artifact.display_name, fallback=f"{artifact.artifact_kind} {index}")
    kind = artifact.artifact_kind.replace("_", " ")
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
    details.append("No file copy, media download, folder scan, automatic classification, or sensitive inference was performed by this preview builder.")
    return " | ".join(details)


def _source_spec_for_artifact(
    *,
    source_url: str,
    canonical_url: str,
    source_title: str,
    artifact: ProfileMediaSourcePackageArtifact,
    index: int,
) -> dict[str, Any]:
    artifact_page = artifact.source_url or artifact.canonical_url or artifact.reference_url or canonical_url or source_url
    return {
        "source_page": artifact_page,
        "source_title": _artifact_source_title(source_title, artifact, index),
        "source_bucket": source_bucket_for_package_artifact_kind(artifact.artifact_kind),
        "source_role": "UNKNOWN_SOURCE_ROLE",
        "claim_basis": "UNKNOWN_CLAIM_BASIS",
        "currentness_status": "UNKNOWN",
        "source_chain_gap": True,
        "disputed_framing": False,
        "confidence_or_verification_notes": _artifact_notes(artifact),
    }


def _source_page_spec(source_url: str, canonical_url: str, source_title: str) -> dict[str, Any]:
    return {
        "source_page": canonical_url or source_url,
        "source_title": _clean_text(source_title, fallback=_SOURCE_DEFAULT_TITLE),
        "source_bucket": "Articles",
        "source_role": "UNKNOWN_SOURCE_ROLE",
        "claim_basis": "UNKNOWN_CLAIM_BASIS",
        "currentness_status": "UNKNOWN",
        "source_chain_gap": True,
        "disputed_framing": False,
        "confidence_or_verification_notes": (
            "V82A source-package preview root record. Source URL was carried forward for review; "
            "the preview builder did not classify, download, copy, scan folders, or infer sensitive identifiers."
        ),
    }


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

    sources: list[dict[str, Any]] = []
    if include_source_page_record:
        sources.append(_source_page_spec(src_url, canon, title))
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

    batch_payload: dict[str, Any] = {
        "schema_version": PROFILE_MEDIA_CASE_BATCH_SCHEMA_VERSION,
        "database_root": db_root,
        "case_title": case,
        "sources": sources,
        "profiles": [],
        "source_package_preview": {
            "schema_version": PROFILE_MEDIA_SOURCE_PACKAGE_PREVIEW_SCHEMA_VERSION,
            "source_url": src_url,
            "canonical_url": canon,
            "source_title": title,
            "source_domain": _domain_from_url(canon or src_url),
            "artifact_count": len(safe_artifacts),
            "artifacts": [artifact.to_dict() for artifact in safe_artifacts],
            "review_required": True,
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
    if preview.warnings:
        lines.extend(["", "Warnings:"])
        lines.extend(f"- {warning}" for warning in preview.warnings)
    return "\n".join(lines)


def source_package_preview_payload(preview: ProfileMediaSourcePackagePreview, *, include_text: bool = False) -> dict[str, Any]:
    payload = preview.to_dict()
    if include_text:
        payload["preview_text"] = render_profile_media_source_package_preview_text(preview)
    return payload
