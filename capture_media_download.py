from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit
from urllib.request import urlopen

from capture_media_discovery import MEDIA_RESOURCE_KIND_BLOB, MediaResource
from capture_status import (
    CAPTURE_STATUS_FAILED,
    CAPTURE_STATUS_SUCCESS,
    CAPTURE_STATUS_UNSUPPORTED,
)


MEDIA_DOWNLOAD_SCOPE = (
    "explicit localhost media download and mock mux-plan helper only; no external hosts, "
    "browser profiles, archive action, provider calls, credentials, scraping, real FFmpeg, "
    "real yt-dlp, muxing execution, or GUI behavior"
)

MEDIA_MUX_PLAN_STATUS_PLAN_ONLY = "plan_only"
MEDIA_MUX_PLAN_STATUS_READY = "mock_command_ready"


@dataclass(frozen=True)
class MediaDownloadResult:
    status: str
    resource_id: str
    url: str
    selected_resource_id: str = ""
    source_url: str = ""
    media_type: str = ""
    output_path: str = ""
    sha256: str = ""
    size_bytes: int = 0
    warnings: tuple[str, ...] = ()
    scope: str = MEDIA_DOWNLOAD_SCOPE

    def to_dict(self) -> dict[str, Any]:
        return {
            "media_type": self.media_type,
            "output_path": self.output_path,
            "resource_id": self.resource_id,
            "scope": self.scope,
            "selected_resource_id": self.selected_resource_id,
            "sha256": self.sha256,
            "size_bytes": self.size_bytes,
            "source_url": self.source_url,
            "status": self.status,
            "url": self.url,
            "warnings": list(self.warnings),
        }


@dataclass(frozen=True)
class MediaComponentRecord:
    resource_id: str
    role: str
    path: str
    source_url: str = ""
    sha256: str = ""
    media_type: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "media_type": self.media_type,
            "path": self.path,
            "resource_id": self.resource_id,
            "role": self.role,
            "sha256": self.sha256,
            "source_url": self.source_url,
        }


@dataclass(frozen=True)
class MediaMuxPlan:
    video_resource_id: str
    audio_resource_id: str
    output_filename: str
    executable_command: tuple[str, ...] = ()
    component_hashes: tuple[tuple[str, str], ...] = ()
    inputs: tuple[MediaComponentRecord, ...] = ()
    expected_output: str = ""
    safety_status: str = "not_executable_plan_only"
    status: str = MEDIA_MUX_PLAN_STATUS_PLAN_ONLY
    scope: str = MEDIA_DOWNLOAD_SCOPE

    def to_dict(self) -> dict[str, Any]:
        return {
            "audio_resource_id": self.audio_resource_id,
            "component_hashes": [list(item) for item in self.component_hashes],
            "executable_command": list(self.executable_command),
            "expected_output": self.expected_output,
            "inputs": [component.to_dict() for component in self.inputs],
            "output_filename": self.output_filename,
            "safety_status": self.safety_status,
            "scope": self.scope,
            "status": self.status,
            "video_resource_id": self.video_resource_id,
        }


def is_allowed_media_download_url(
    url: str,
    allowed_hostnames: tuple[str, ...] = ("127.0.0.1", "localhost", "::1"),
) -> bool:
    parsed = urlsplit(str(url or "").strip())
    if parsed.scheme not in {"http", "https"}:
        return False
    return (parsed.hostname or "").lower() in {host.lower() for host in allowed_hostnames}


def safe_media_filename(resource: MediaResource) -> str:
    parsed = urlsplit(resource.url)
    name = Path(parsed.path).name or f"{resource.resource_id}.bin"
    safe = "".join(ch if ch.isalnum() or ch in {".", "-", "_"} else "_" for ch in name)
    return safe or f"{resource.resource_id}.bin"


def download_media_resource(
    resource: MediaResource,
    *,
    output_folder: str,
    selected_resource_ids: tuple[str, ...] = (),
    source_url: str = "",
    allowed_hostnames: tuple[str, ...] = ("127.0.0.1", "localhost", "::1"),
) -> MediaDownloadResult:
    if resource.resource_id not in selected_resource_ids:
        return MediaDownloadResult(
            status=CAPTURE_STATUS_UNSUPPORTED,
            resource_id=resource.resource_id,
            selected_resource_id="",
            source_url=source_url,
            media_type=resource.kind,
            url=resource.url,
            warnings=("Media download requires explicit selected resource ID.",),
        )
    if not resource.downloadable or resource.kind == MEDIA_RESOURCE_KIND_BLOB:
        return MediaDownloadResult(
            status=CAPTURE_STATUS_UNSUPPORTED,
            resource_id=resource.resource_id,
            selected_resource_id=resource.resource_id,
            source_url=source_url,
            media_type=resource.kind,
            url=resource.url,
            warnings=("Media resource is not directly downloadable by this helper.",),
        )
    if not is_allowed_media_download_url(resource.url, allowed_hostnames):
        return MediaDownloadResult(
            status=CAPTURE_STATUS_UNSUPPORTED,
            resource_id=resource.resource_id,
            selected_resource_id=resource.resource_id,
            source_url=source_url,
            media_type=resource.kind,
            url=resource.url,
            warnings=("Media download helper is restricted to allowed localhost fixture hosts.",),
        )

    output_dir = Path(output_folder)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / safe_media_filename(resource)
    part_path = output_path.with_name(output_path.name + ".part")
    try:
        with urlopen(resource.url, timeout=10) as response:
            payload = response.read()
        part_path.write_bytes(payload)
        part_path.replace(output_path)
    except (KeyboardInterrupt, SystemExit, GeneratorExit):
        raise
    except Exception:
        try:
            part_path.unlink()
        except OSError:
            pass
        return MediaDownloadResult(
            status=CAPTURE_STATUS_FAILED,
            resource_id=resource.resource_id,
            selected_resource_id=resource.resource_id,
            source_url=source_url,
            media_type=resource.kind,
            url=resource.url,
            warnings=("Media download failed with a non-secret exception.",),
        )

    return MediaDownloadResult(
        status=CAPTURE_STATUS_SUCCESS,
        resource_id=resource.resource_id,
        selected_resource_id=resource.resource_id,
        source_url=source_url,
        media_type=resource.kind,
        url=resource.url,
        output_path=str(output_path),
        sha256=hashlib.sha256(payload).hexdigest(),
        size_bytes=len(payload),
    )


def build_media_component_record(
    *,
    resource_id: str,
    role: str,
    path: str,
    source_url: str = "",
    media_type: str = "",
) -> MediaComponentRecord:
    sha256 = ""
    if path:
        candidate = Path(path)
        if candidate.is_file():
            sha256 = hashlib.sha256(candidate.read_bytes()).hexdigest()
    return MediaComponentRecord(
        resource_id=resource_id,
        role=role,
        path=path,
        source_url=source_url,
        sha256=sha256,
        media_type=media_type,
    )


def build_separate_av_mux_plan(
    *,
    video_component: MediaComponentRecord,
    audio_component: MediaComponentRecord,
    output_path: str,
    ffmpeg_executable: str = "ffmpeg",
) -> MediaMuxPlan:
    command = (
        ffmpeg_executable,
        "-y",
        "-i",
        video_component.path,
        "-i",
        audio_component.path,
        "-c",
        "copy",
        output_path,
    )
    component_hashes = tuple(
        (component.resource_id, component.sha256)
        for component in (video_component, audio_component)
        if component.sha256
    )
    return MediaMuxPlan(
        video_resource_id=video_component.resource_id,
        audio_resource_id=audio_component.resource_id,
        output_filename=Path(output_path).name,
        executable_command=command,
        component_hashes=component_hashes,
        inputs=(video_component, audio_component),
        expected_output=output_path,
        safety_status="mock_command_plan_only_not_executed",
        status=MEDIA_MUX_PLAN_STATUS_READY,
    )


def build_yt_dlp_mux_plan(
    *,
    resource: MediaResource,
    output_path: str,
    yt_dlp_executable: str = "yt-dlp",
) -> MediaMuxPlan:
    command = (
        yt_dlp_executable,
        "--no-call-home",
        "--no-progress",
        "--merge-output-format",
        "mp4",
        "-o",
        output_path,
        resource.url,
    )
    return MediaMuxPlan(
        video_resource_id=resource.resource_id,
        audio_resource_id="",
        output_filename=Path(output_path).name,
        executable_command=command,
        expected_output=output_path,
        safety_status="mock_yt_dlp_command_plan_only_not_executed",
        status=MEDIA_MUX_PLAN_STATUS_READY,
    )


def build_media_mux_plan(
    *,
    video_resource_id: str,
    audio_resource_id: str,
    output_filename: str,
) -> MediaMuxPlan:
    return MediaMuxPlan(
        video_resource_id=video_resource_id,
        audio_resource_id=audio_resource_id,
        output_filename=output_filename,
    )
