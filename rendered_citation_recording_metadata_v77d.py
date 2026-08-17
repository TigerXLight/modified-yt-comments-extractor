from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field, is_dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping


RENDERED_CITATION_RECORDING_SCHEMA_VERSION = "rendered-citation-recording-metadata-v77d"
WRITE_RENDERED_CITATION_RECORDING_METADATA_V77D = "WRITE_RENDERED_CITATION_RECORDING_METADATA_V77D"

CAPTURE_KINDS = {
    "still_frame",
    "window_recording",
    "region_recording",
    "bounded_video_excerpt",
    "bounded_audio_excerpt",
    "subtitle_caption_capture",
    "livestream_excerpt",
    "blocked_capture_state",
}

CAPTURE_METHODS = {
    "ordinary_browser_visible_capture",
    "ordinary_windows_screen_capture",
    "browser_print_or_save",
    "local_file_preservation",
    "source_reference_only",
}

USER_DECLARED_PURPOSES = {
    "quotation",
    "criticism",
    "review",
    "news_reporting",
    "research",
    "source_preservation",
    "other_review_required",
}

BLOCKED_REASONS = {
    "",
    "black_frame",
    "muted_audio",
    "drm_or_platform_restriction",
    "login_required",
    "access_boundary",
    "captcha_or_challenge_required",
    "rate_limit_or_cooldown",
    "unknown",
}


@dataclass(frozen=True)
class HumanMediatedAccess:
    required: bool = False
    completed_by_user: bool = False
    completion_recorded: bool = False
    program_solved_challenge: bool = False
    solver_service_used: bool = False
    anti_detection_used: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RenderedCitationSafetyFlags:
    drm_circumvention_performed: bool = False
    captcha_solver_used: bool = False
    credential_automation_performed: bool = False
    proxy_or_evasion_performed: bool = False
    forced_rate_limit_bypass_performed: bool = False
    hidden_protected_stream_extraction_performed: bool = False
    web_download_performed: bool = False
    media_download_performed: bool = False
    browser_launch_performed: bool = False
    recording_performed: bool = False
    x_twitter_write_actions_performed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RenderedCitationRecordingMetadata:
    source_url: str
    page_url: str
    media_url: str
    capture_kind: str
    capture_method: str
    user_declared_purpose: str
    start_timestamp_utc: str
    end_timestamp_utc: str
    media_position_start: str
    media_position_end: str
    local_file_path: str
    local_file_size: int | None
    local_file_sha256: str
    source_unit_path: str
    capture_blocked: bool
    blocked_reason: str
    human_mediated_access: HumanMediatedAccess
    safety_flags: RenderedCitationSafetyFlags
    warnings: tuple[str, ...] = ()
    schema_version: str = RENDERED_CITATION_RECORDING_SCHEMA_VERSION
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


def build_rendered_citation_recording_metadata(
    *,
    source_url: str,
    page_url: str = "",
    media_url: str = "",
    capture_kind: str,
    capture_method: str,
    user_declared_purpose: str,
    start_timestamp_utc: str = "",
    end_timestamp_utc: str = "",
    media_position_start: str = "",
    media_position_end: str = "",
    local_file_path: str = "",
    source_unit_path: str = "",
    capture_blocked: bool = False,
    blocked_reason: str = "",
    human_mediated_access_required: bool = False,
    human_mediated_access_completed_by_user: bool = False,
    created_at_utc: str | None = None,
) -> RenderedCitationRecordingMetadata:
    kind = _validate_choice("capture_kind", capture_kind, CAPTURE_KINDS)
    method = _validate_choice("capture_method", capture_method, CAPTURE_METHODS)
    purpose = _validate_choice("user_declared_purpose", user_declared_purpose, USER_DECLARED_PURPOSES)
    reason = _validate_choice("blocked_reason", blocked_reason if capture_blocked or blocked_reason else "", BLOCKED_REASONS)
    warnings: list[str] = []
    if not source_url:
        warnings.append("source_url_missing")
    if not page_url:
        warnings.append("page_url_missing")
    if capture_blocked and not reason:
        reason = "unknown"
        warnings.append("capture_blocked_reason_defaulted_unknown")
    if reason and not capture_blocked:
        warnings.append("blocked_reason_recorded_without_capture_blocked")
    local_size: int | None = None
    local_sha = ""
    local_path_text = str(local_file_path or "")
    if local_path_text:
        path = Path(local_path_text)
        if path.is_file():
            local_size = path.stat().st_size
            local_sha = _sha256_file(path)
        else:
            warnings.append("local_file_missing_not_hashed")
    human = HumanMediatedAccess(
        required=bool(human_mediated_access_required),
        completed_by_user=bool(human_mediated_access_completed_by_user),
        completion_recorded=bool(human_mediated_access_required and human_mediated_access_completed_by_user),
        program_solved_challenge=False,
        solver_service_used=False,
        anti_detection_used=False,
    )
    safety = RenderedCitationSafetyFlags()
    return RenderedCitationRecordingMetadata(
        source_url=str(source_url or ""),
        page_url=str(page_url or source_url or ""),
        media_url=str(media_url or ""),
        capture_kind=kind,
        capture_method=method,
        user_declared_purpose=purpose,
        start_timestamp_utc=str(start_timestamp_utc or ""),
        end_timestamp_utc=str(end_timestamp_utc or ""),
        media_position_start=str(media_position_start or ""),
        media_position_end=str(media_position_end or ""),
        local_file_path=local_path_text,
        local_file_size=local_size,
        local_file_sha256=local_sha,
        source_unit_path=str(source_unit_path or ""),
        capture_blocked=bool(capture_blocked),
        blocked_reason=reason,
        human_mediated_access=human,
        safety_flags=safety,
        warnings=tuple(warnings),
        created_at_utc=created_at_utc or utc_now_iso(),
    )


def metadata_to_json_text(metadata: RenderedCitationRecordingMetadata) -> str:
    return json.dumps(metadata.to_dict(), indent=2, ensure_ascii=False, sort_keys=True) + "\n"


def write_rendered_citation_recording_metadata(
    metadata: RenderedCitationRecordingMetadata,
    output_json: str | Path,
    *,
    confirm_write: str = "",
) -> Path:
    if confirm_write != WRITE_RENDERED_CITATION_RECORDING_METADATA_V77D:
        raise PermissionError("Writing rendered citation recording metadata requires confirmation token WRITE_RENDERED_CITATION_RECORDING_METADATA_V77D")
    output = Path(output_json)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(metadata_to_json_text(metadata), encoding="utf-8")
    return output


def render_rendered_citation_recording_summary(metadata: RenderedCitationRecordingMetadata) -> str:
    lines = [
        "RENDERED CITATION RECORDING METADATA V77D",
        f"schema_version: {metadata.schema_version}",
        f"source_url: {metadata.source_url}",
        f"page_url: {metadata.page_url}",
        f"media_url: {metadata.media_url}",
        f"capture_kind: {metadata.capture_kind}",
        f"capture_method: {metadata.capture_method}",
        f"user_declared_purpose: {metadata.user_declared_purpose}",
        f"capture_blocked: {metadata.capture_blocked}",
        f"blocked_reason: {metadata.blocked_reason}",
        f"local_file_path: {metadata.local_file_path}",
        f"local_file_size: {metadata.local_file_size}",
        f"local_file_sha256: {metadata.local_file_sha256}",
        f"human_mediated_access.required: {metadata.human_mediated_access.required}",
        f"human_mediated_access.completed_by_user: {metadata.human_mediated_access.completed_by_user}",
        f"human_mediated_access.program_solved_challenge: {metadata.human_mediated_access.program_solved_challenge}",
        f"human_mediated_access.solver_service_used: {metadata.human_mediated_access.solver_service_used}",
        f"human_mediated_access.anti_detection_used: {metadata.human_mediated_access.anti_detection_used}",
        f"safety_flags.drm_circumvention_performed: {metadata.safety_flags.drm_circumvention_performed}",
        f"safety_flags.proxy_or_evasion_performed: {metadata.safety_flags.proxy_or_evasion_performed}",
        f"safety_flags.forced_rate_limit_bypass_performed: {metadata.safety_flags.forced_rate_limit_bypass_performed}",
        f"safety_flags.hidden_protected_stream_extraction_performed: {metadata.safety_flags.hidden_protected_stream_extraction_performed}",
    ]
    lines.append("warnings: " + (", ".join(metadata.warnings) if metadata.warnings else "NONE"))
    return "\n".join(lines)
