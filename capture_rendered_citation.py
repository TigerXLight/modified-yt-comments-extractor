from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Mapping

from capture_contracts import (
    ARTIFACT_TYPE_RENDERED_RECORDING,
    CaptureArtifact,
    build_capture_artifact,
    stable_capture_id,
)
from capture_status import COMPLETENESS_COMPLETE, COMPLETENESS_PARTIAL_UNKNOWN, FIDELITY_RAW


RENDERED_CITATION_STATUS_PLANNED = "planned"
RENDERED_CITATION_STATUS_USER_AUTHORIZATION_REQUIRED = "user_authorization_required"
RENDERED_CITATION_STATUS_RECORDING_FIXTURE_RECEIVED = "recording_fixture_received"
RENDERED_CITATION_STATUS_PROTECTED_OR_BLACK_OUTPUT = "protected_or_black_output"
RENDERED_CITATION_STATUS_COMPLETED = "completed"
RENDERED_CITATION_STATUS_FAILED = "failed"

RENDERED_CITATION_STATUSES = (
    RENDERED_CITATION_STATUS_PLANNED,
    RENDERED_CITATION_STATUS_USER_AUTHORIZATION_REQUIRED,
    RENDERED_CITATION_STATUS_RECORDING_FIXTURE_RECEIVED,
    RENDERED_CITATION_STATUS_PROTECTED_OR_BLACK_OUTPUT,
    RENDERED_CITATION_STATUS_COMPLETED,
    RENDERED_CITATION_STATUS_FAILED,
)

RENDERED_CITATION_METHOD_GET_DISPLAY_MEDIA = "browser_get_display_media"
RENDERED_CITATION_METHOD_OS_WINDOW_CAPTURE = "os_window_capture"

RENDERED_CITATION_METHODS = (
    RENDERED_CITATION_METHOD_GET_DISPLAY_MEDIA,
    RENDERED_CITATION_METHOD_OS_WINDOW_CAPTURE,
)

RENDERED_CITATION_SCOPE = (
    "rendered citation metadata and local fixture segment manifests only; no real "
    "screen recording, browser automation, protected-buffer access, external network, "
    "download, archive, provider, credential, external process, file move, or GUI behavior"
)


@dataclass(frozen=True)
class RenderedCitationSegment:
    segment_id: str
    relative_path: str
    start_seconds: float
    end_seconds: float
    sha256: str = ""
    size_bytes: int = 0
    frame_marker_count: int = 0
    audio_marker_count: int = 0
    warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "audio_marker_count": self.audio_marker_count,
            "end_seconds": self.end_seconds,
            "frame_marker_count": self.frame_marker_count,
            "relative_path": self.relative_path,
            "segment_id": self.segment_id,
            "sha256": self.sha256,
            "size_bytes": self.size_bytes,
            "start_seconds": self.start_seconds,
            "warnings": list(self.warnings),
        }


@dataclass(frozen=True)
class RenderedCitationSession:
    session_id: str
    source_url: str
    source_label: str
    purpose: str
    time_range_start_seconds: float
    time_range_end_seconds: float
    capture_method: str = RENDERED_CITATION_METHOD_GET_DISPLAY_MEDIA
    status: str = RENDERED_CITATION_STATUS_PLANNED
    user_mediated: bool = True
    user_authorization_required: bool = True
    selected_display_label: str = ""
    window_or_region_label: str = ""
    observed_media_start_seconds: float = 0.0
    observed_media_end_seconds: float = 0.0
    subtitles_visible: bool = False
    segments: tuple[RenderedCitationSegment, ...] = ()
    failure_reason: str = ""
    warnings: tuple[str, ...] = ()
    scope: str = RENDERED_CITATION_SCOPE

    def to_dict(self) -> dict[str, Any]:
        return {
            "capture_method": self.capture_method,
            "failure_reason": self.failure_reason,
            "observed_media_end_seconds": self.observed_media_end_seconds,
            "observed_media_start_seconds": self.observed_media_start_seconds,
            "purpose": self.purpose,
            "scope": self.scope,
            "segments": [segment.to_dict() for segment in self.segments],
            "selected_display_label": self.selected_display_label,
            "session_id": self.session_id,
            "source_label": self.source_label,
            "source_url": self.source_url,
            "status": self.status,
            "subtitles_visible": self.subtitles_visible,
            "time_range_end_seconds": self.time_range_end_seconds,
            "time_range_start_seconds": self.time_range_start_seconds,
            "user_authorization_required": self.user_authorization_required,
            "user_mediated": self.user_mediated,
            "warnings": list(self.warnings),
            "window_or_region_label": self.window_or_region_label,
        }


def _non_negative_seconds(value: float, field_name: str) -> float:
    numeric = float(value)
    if numeric < 0:
        raise ValueError(f"{field_name} must be non-negative")
    return numeric


def _validate_range(start_seconds: float, end_seconds: float) -> tuple[float, float]:
    start = _non_negative_seconds(start_seconds, "start_seconds")
    end = _non_negative_seconds(end_seconds, "end_seconds")
    if end < start:
        raise ValueError("end_seconds must be greater than or equal to start_seconds")
    return start, end


def _relative_path(value: str) -> str:
    normalized = str(value or "").replace("\\", "/").strip("/")
    if not normalized:
        raise ValueError("relative_path is required")
    if normalized.startswith("../") or "/../" in f"/{normalized}/":
        raise ValueError("relative_path must stay inside the rendered citation artifact folder")
    return normalized


def plan_rendered_citation_session(
    *,
    source_url: str,
    source_label: str,
    purpose: str,
    time_range_start_seconds: float,
    time_range_end_seconds: float,
    capture_method: str = RENDERED_CITATION_METHOD_GET_DISPLAY_MEDIA,
    selected_display_label: str = "",
    window_or_region_label: str = "",
    observed_media_start_seconds: float | None = None,
    observed_media_end_seconds: float | None = None,
    subtitles_visible: bool = False,
    status: str = RENDERED_CITATION_STATUS_PLANNED,
) -> RenderedCitationSession:
    if capture_method not in RENDERED_CITATION_METHODS:
        raise ValueError(f"Unknown rendered citation capture method: {capture_method}")
    if status not in RENDERED_CITATION_STATUSES:
        raise ValueError(f"Unknown rendered citation status: {status}")
    start, end = _validate_range(time_range_start_seconds, time_range_end_seconds)
    observed_start = start if observed_media_start_seconds is None else observed_media_start_seconds
    observed_end = end if observed_media_end_seconds is None else observed_media_end_seconds
    observed_start, observed_end = _validate_range(observed_start, observed_end)
    return RenderedCitationSession(
        session_id=stable_capture_id(
            "rendered_citation",
            source_url,
            source_label,
            purpose,
            start,
            end,
            capture_method,
        ),
        source_url=source_url,
        source_label=source_label,
        purpose=purpose,
        time_range_start_seconds=start,
        time_range_end_seconds=end,
        capture_method=capture_method,
        status=status,
        selected_display_label=selected_display_label,
        window_or_region_label=window_or_region_label,
        observed_media_start_seconds=observed_start,
        observed_media_end_seconds=observed_end,
        subtitles_visible=bool(subtitles_visible),
    )


def require_user_authorization(session: RenderedCitationSession) -> RenderedCitationSession:
    return replace(
        session,
        status=RENDERED_CITATION_STATUS_USER_AUTHORIZATION_REQUIRED,
        user_authorization_required=True,
    )


def build_fixture_rendered_citation_segment(
    *,
    segment_path: str,
    relative_path: str,
    start_seconds: float,
    end_seconds: float,
    frame_marker_count: int = 0,
    audio_marker_count: int = 0,
) -> RenderedCitationSegment:
    start, end = _validate_range(start_seconds, end_seconds)
    path = Path(segment_path)
    sha256 = ""
    size_bytes = 0
    warnings: tuple[str, ...] = ()
    if path.is_file():
        payload = path.read_bytes()
        sha256 = hashlib.sha256(payload).hexdigest()
        size_bytes = len(payload)
    else:
        warnings = ("Fixture segment file was not present; hash was not computed.",)
    normalized_relative_path = _relative_path(relative_path)
    return RenderedCitationSegment(
        segment_id=stable_capture_id("rendered_segment", normalized_relative_path, start, end, sha256),
        relative_path=normalized_relative_path,
        start_seconds=start,
        end_seconds=end,
        sha256=sha256,
        size_bytes=size_bytes,
        frame_marker_count=max(0, int(frame_marker_count)),
        audio_marker_count=max(0, int(audio_marker_count)),
        warnings=warnings,
    )


def receive_fixture_recording_segments(
    session: RenderedCitationSession,
    segments: tuple[RenderedCitationSegment, ...],
) -> RenderedCitationSession:
    return replace(
        session,
        status=RENDERED_CITATION_STATUS_RECORDING_FIXTURE_RECEIVED,
        user_authorization_required=False,
        segments=tuple(segments),
    )


def complete_rendered_citation_session(session: RenderedCitationSession) -> RenderedCitationSession:
    if session.status == RENDERED_CITATION_STATUS_PROTECTED_OR_BLACK_OUTPUT:
        return session
    return replace(session, status=RENDERED_CITATION_STATUS_COMPLETED)


def mark_protected_or_black_output(
    session: RenderedCitationSession,
    *,
    reason: str,
) -> RenderedCitationSession:
    return replace(
        session,
        status=RENDERED_CITATION_STATUS_PROTECTED_OR_BLACK_OUTPUT,
        failure_reason=" ".join(str(reason or "protected or black output").split()),
        warnings=tuple(dict.fromkeys((*session.warnings, "Protected or black output was blocked and not bypassed."))),
    )


def build_rendered_citation_artifacts(
    *,
    session: RenderedCitationSession,
    timestamp_utc: str,
    source_id: str = "",
    adapter_id: str = "",
) -> tuple[CaptureArtifact, ...]:
    common_metadata: Mapping[str, Any] = {
        "capture_execution": "not executed",
        "capture_method": session.capture_method,
        "operator_user_mediated": session.user_mediated,
        "purpose": session.purpose,
        "selected_display_label": session.selected_display_label,
        "source_label": session.source_label,
        "status": session.status,
        "subtitles_visible": session.subtitles_visible,
        "time_range_end_seconds": session.time_range_end_seconds,
        "time_range_start_seconds": session.time_range_start_seconds,
        "user_authorization_required": session.user_authorization_required,
        "window_or_region_label": session.window_or_region_label,
    }
    manifest_payload = json.dumps(
        [segment.to_dict() for segment in session.segments],
        separators=(",", ":"),
        sort_keys=True,
    )
    manifest_hash = hashlib.sha256(manifest_payload.encode("utf-8")).hexdigest()
    completeness = (
        COMPLETENESS_PARTIAL_UNKNOWN
        if session.status == RENDERED_CITATION_STATUS_PROTECTED_OR_BLACK_OUTPUT
        else COMPLETENESS_COMPLETE
    )
    return (
        build_capture_artifact(
            session_id=session.session_id,
            source_url=session.source_url,
            artifact_type=ARTIFACT_TYPE_RENDERED_RECORDING,
            capture_method="rendered_citation_metadata_manifest",
            relative_path="rendered_citation/rendered_citation_metadata.json",
            sha256=manifest_hash,
            completeness=completeness,
            fidelity=FIDELITY_RAW,
            created_at_utc=timestamp_utc,
            source_id=source_id,
            canonical_url=session.source_url,
            adapter_id=adapter_id,
            scope="mock_capture_tested",
            metadata={**common_metadata, "artifact_role": "metadata_manifest"},
        ),
        build_capture_artifact(
            session_id=session.session_id,
            source_url=session.source_url,
            artifact_type=ARTIFACT_TYPE_RENDERED_RECORDING,
            capture_method="rendered_citation_segment_manifest",
            relative_path="rendered_citation/segments.json",
            sha256=manifest_hash,
            completeness=completeness,
            fidelity=FIDELITY_RAW,
            created_at_utc=timestamp_utc,
            source_id=source_id,
            canonical_url=session.source_url,
            adapter_id=adapter_id,
            scope="mock_capture_tested",
            metadata={
                **common_metadata,
                "artifact_role": "segment_manifest",
                "segment_count": len(session.segments),
                "segment_hashes": tuple(
                    (segment.relative_path, segment.sha256) for segment in session.segments if segment.sha256
                ),
            },
        ),
    )
