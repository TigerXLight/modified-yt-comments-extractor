from __future__ import annotations

import hashlib
import json
import mimetypes
from dataclasses import asdict, dataclass, field, is_dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from rendered_citation_recording_metadata_v77d import (
    BLOCKED_REASONS,
    CAPTURE_KINDS,
    CAPTURE_METHODS,
    USER_DECLARED_PURPOSES,
    build_rendered_citation_recording_metadata,
)


RENDERED_CITATION_MEDIA_INTAKE_SCHEMA_VERSION = "rendered-citation-media-intake-v77e"
WRITE_RENDERED_CITATION_MEDIA_INTAKE_V77E = "WRITE_RENDERED_CITATION_MEDIA_INTAKE_V77E"

LOCAL_FILE_ROLES = {
    "screenshot",
    "still_frame",
    "video_excerpt",
    "audio_excerpt",
    "subtitle_caption",
    "transcript",
    "livestream_excerpt",
    "source_reference_only",
    "blocked_capture_placeholder",
    "review_required",
}

ATTACHMENT_SCOPES = {
    "article_source_unit",
    "social_video_source_unit",
    "twitter_x_source_unit",
    "internal_media",
    "reference_extant",
    "review_required",
}


@dataclass(frozen=True)
class SourceUnitAttachment:
    attached_to_source_unit: bool
    source_unit_path: str
    attachment_scope: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RenderedCitationMediaIntakeSafetyFlags:
    browser_launch_performed: bool = False
    web_download_performed: bool = False
    media_download_performed: bool = False
    recording_performed: bool = False
    drm_circumvention_performed: bool = False
    hidden_protected_stream_extraction_performed: bool = False
    captcha_solver_used: bool = False
    credential_automation_performed: bool = False
    proxy_or_evasion_performed: bool = False
    forced_rate_limit_bypass_performed: bool = False
    write_actions_performed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RenderedCitationMediaIntakeManifest:
    source_url: str
    page_url: str
    media_url: str
    source_unit_path: str
    user_declared_purpose: str
    capture_kind: str
    capture_method: str
    media_position_start: str
    media_position_end: str
    local_file_path: str
    local_file_name: str
    local_file_extension: str
    local_file_mime_type: str
    local_file_size: int | None
    local_file_sha256: str
    local_file_present: bool
    local_file_role: str
    source_unit_attachment: SourceUnitAttachment
    rendered_citation_metadata: Mapping[str, Any]
    human_mediated_access: Mapping[str, Any]
    blocked_capture: Mapping[str, Any]
    safety_flags: RenderedCitationMediaIntakeSafetyFlags
    warnings: tuple[str, ...] = ()
    schema_version: str = RENDERED_CITATION_MEDIA_INTAKE_SCHEMA_VERSION
    created_at_utc: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"))

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


def _value_for_dict(value: Any) -> Any:
    if is_dataclass(value):
        return {key: _value_for_dict(item) for key, item in asdict(value).items()}
    if isinstance(value, tuple):
        return [_value_for_dict(item) for item in value]
    if isinstance(value, list):
        return [_value_for_dict(item) for item in value]
    if isinstance(value, Mapping):
        return {str(key): _value_for_dict(item) for key, item in value.items()}
    return value


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _validate_choice(name: str, value: str, allowed: set[str]) -> str:
    text = str(value or "").strip()
    if text not in allowed:
        raise ValueError(f"{name} must be one of: {', '.join(sorted(item for item in allowed if item))}")
    return text


def infer_attachment_scope(source_unit_path: str) -> str:
    text = str(source_unit_path or "").replace("\\", "/").lower()
    if not text:
        return "review_required"
    if "internal media" in text or "/internal_media/" in text:
        return "internal_media"
    if "reference extants" in text or "reference_extants" in text:
        return "reference_extant"
    if "twitter" in text or "/x/" in text or "x.com" in text:
        return "twitter_x_source_unit"
    if "social media" in text or "youtube" in text or "tiktok" in text or "instagram" in text or "facebook" in text:
        return "social_video_source_unit"
    if "article" in text or "articles" in text:
        return "article_source_unit"
    return "review_required"


def build_source_unit_attachment(source_unit_path: str, attachment_scope: str = "") -> SourceUnitAttachment:
    scope = _validate_choice("attachment_scope", attachment_scope or infer_attachment_scope(source_unit_path), ATTACHMENT_SCOPES)
    return SourceUnitAttachment(
        attached_to_source_unit=bool(str(source_unit_path or "").strip()),
        source_unit_path=str(source_unit_path or ""),
        attachment_scope=scope,
    )


def _file_metadata(local_file_path: str) -> tuple[str, str, str, int | None, str, bool, tuple[str, ...]]:
    path_text = str(local_file_path or "")
    if not path_text:
        return "", "", "", None, "", False, ()
    path = Path(path_text)
    suffix = path.suffix.lower()
    mime = mimetypes.guess_type(path.name)[0] or ""
    if not path.is_file():
        return path.name, suffix, mime, None, "", False, ("local_file_missing_not_hashed",)
    return path.name, suffix, mime, path.stat().st_size, _sha256_file(path), True, ()


def build_rendered_citation_media_intake_manifest(
    *,
    source_url: str,
    page_url: str = "",
    media_url: str = "",
    source_unit_path: str = "",
    user_declared_purpose: str,
    capture_kind: str,
    capture_method: str,
    media_position_start: str = "",
    media_position_end: str = "",
    local_file_path: str = "",
    local_file_role: str = "review_required",
    capture_blocked: bool = False,
    blocked_reason: str = "",
    human_mediated_access_required: bool = False,
    human_mediated_access_completed_by_user: bool = False,
    attachment_scope: str = "",
    created_at_utc: str | None = None,
) -> RenderedCitationMediaIntakeManifest:
    kind = _validate_choice("capture_kind", capture_kind, CAPTURE_KINDS)
    method = _validate_choice("capture_method", capture_method, CAPTURE_METHODS)
    purpose = _validate_choice("user_declared_purpose", user_declared_purpose, USER_DECLARED_PURPOSES)
    reason = _validate_choice("blocked_reason", blocked_reason if capture_blocked or blocked_reason else "", BLOCKED_REASONS)
    role = _validate_choice("local_file_role", local_file_role, LOCAL_FILE_ROLES)
    warnings: list[str] = []
    name, extension, mime, size, sha256, present, file_warnings = _file_metadata(local_file_path)
    warnings.extend(file_warnings)
    if capture_blocked and not reason:
        reason = "unknown"
        warnings.append("capture_blocked_reason_defaulted_unknown")
    if capture_blocked and role not in {"blocked_capture_placeholder", "review_required"} and not present:
        warnings.append("blocked_capture_without_local_file_should_use_placeholder_role")
    if role == "blocked_capture_placeholder" and present:
        warnings.append("blocked_capture_placeholder_has_local_file")
    attachment = build_source_unit_attachment(source_unit_path, attachment_scope)
    v77d_metadata = build_rendered_citation_recording_metadata(
        source_url=source_url,
        page_url=page_url,
        media_url=media_url,
        capture_kind=kind,
        capture_method=method,
        user_declared_purpose=purpose,
        media_position_start=media_position_start,
        media_position_end=media_position_end,
        local_file_path=local_file_path,
        source_unit_path=source_unit_path,
        capture_blocked=capture_blocked,
        blocked_reason=reason,
        human_mediated_access_required=human_mediated_access_required,
        human_mediated_access_completed_by_user=human_mediated_access_completed_by_user,
        created_at_utc=created_at_utc,
    ).to_dict()
    warnings.extend(str(item) for item in v77d_metadata.get("warnings", []) if item not in warnings)
    human = dict(v77d_metadata["human_mediated_access"])
    human["program_solved_challenge"] = False
    human["solver_service_used"] = False
    human["anti_detection_used"] = False
    return RenderedCitationMediaIntakeManifest(
        source_url=str(source_url or ""),
        page_url=str(page_url or source_url or ""),
        media_url=str(media_url or ""),
        source_unit_path=str(source_unit_path or ""),
        user_declared_purpose=purpose,
        capture_kind=kind,
        capture_method=method,
        media_position_start=str(media_position_start or ""),
        media_position_end=str(media_position_end or ""),
        local_file_path=str(local_file_path or ""),
        local_file_name=name,
        local_file_extension=extension,
        local_file_mime_type=mime,
        local_file_size=size,
        local_file_sha256=sha256,
        local_file_present=present,
        local_file_role=role,
        source_unit_attachment=attachment,
        rendered_citation_metadata=v77d_metadata,
        human_mediated_access=human,
        blocked_capture={"blocked": bool(capture_blocked), "reason": reason},
        safety_flags=RenderedCitationMediaIntakeSafetyFlags(),
        warnings=tuple(dict.fromkeys(warnings)),
        created_at_utc=created_at_utc or utc_now_iso(),
    )


def manifest_to_json_text(manifest: RenderedCitationMediaIntakeManifest) -> str:
    return json.dumps(manifest.to_dict(), indent=2, ensure_ascii=False, sort_keys=True) + "\n"


def write_rendered_citation_media_intake_manifest(
    manifest: RenderedCitationMediaIntakeManifest,
    output_json: str | Path,
    *,
    confirm_write: str = "",
) -> Path:
    if confirm_write != WRITE_RENDERED_CITATION_MEDIA_INTAKE_V77E:
        raise PermissionError("Writing rendered citation media intake manifest requires confirmation token WRITE_RENDERED_CITATION_MEDIA_INTAKE_V77E")
    output = Path(output_json)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(manifest_to_json_text(manifest), encoding="utf-8")
    return output


def render_rendered_citation_media_intake_summary(manifest: RenderedCitationMediaIntakeManifest) -> str:
    lines = [
        "RENDERED CITATION MEDIA INTAKE V77E",
        f"schema_version: {manifest.schema_version}",
        f"source_url: {manifest.source_url}",
        f"page_url: {manifest.page_url}",
        f"media_url: {manifest.media_url}",
        f"source_unit_path: {manifest.source_unit_path}",
        f"user_declared_purpose: {manifest.user_declared_purpose}",
        f"capture_kind: {manifest.capture_kind}",
        f"capture_method: {manifest.capture_method}",
        f"media_position_start: {manifest.media_position_start}",
        f"media_position_end: {manifest.media_position_end}",
        f"local_file_path: {manifest.local_file_path}",
        f"local_file_present: {manifest.local_file_present}",
        f"local_file_name: {manifest.local_file_name}",
        f"local_file_extension: {manifest.local_file_extension}",
        f"local_file_size: {manifest.local_file_size}",
        f"local_file_sha256: {manifest.local_file_sha256}",
        f"local_file_role: {manifest.local_file_role}",
        f"source_unit_attachment.attached_to_source_unit: {manifest.source_unit_attachment.attached_to_source_unit}",
        f"source_unit_attachment.attachment_scope: {manifest.source_unit_attachment.attachment_scope}",
        f"human_mediated_access.required: {manifest.human_mediated_access['required']}",
        f"human_mediated_access.completed_by_user: {manifest.human_mediated_access['completed_by_user']}",
        f"human_mediated_access.program_solved_challenge: {manifest.human_mediated_access['program_solved_challenge']}",
        f"safety_flags.browser_launch_performed: {manifest.safety_flags.browser_launch_performed}",
        f"safety_flags.web_download_performed: {manifest.safety_flags.web_download_performed}",
        f"safety_flags.media_download_performed: {manifest.safety_flags.media_download_performed}",
        f"safety_flags.recording_performed: {manifest.safety_flags.recording_performed}",
        f"safety_flags.drm_circumvention_performed: {manifest.safety_flags.drm_circumvention_performed}",
        f"safety_flags.proxy_or_evasion_performed: {manifest.safety_flags.proxy_or_evasion_performed}",
    ]
    lines.append("warnings: " + (", ".join(manifest.warnings) if manifest.warnings else "NONE"))
    return "\n".join(lines)
