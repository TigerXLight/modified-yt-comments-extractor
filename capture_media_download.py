from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit
from urllib.request import urlopen

from capture_media_discovery import MediaResource
from capture_status import (
    CAPTURE_STATUS_FAILED,
    CAPTURE_STATUS_SUCCESS,
    CAPTURE_STATUS_UNSUPPORTED,
)


MEDIA_DOWNLOAD_SCOPE = (
    "explicit localhost media download helper only; no external hosts, browser profiles, "
    "archive action, provider calls, credentials, scraping, muxing execution, or GUI behavior"
)


@dataclass(frozen=True)
class MediaDownloadResult:
    status: str
    resource_id: str
    url: str
    output_path: str = ""
    sha256: str = ""
    size_bytes: int = 0
    warnings: tuple[str, ...] = ()
    scope: str = MEDIA_DOWNLOAD_SCOPE

    def to_dict(self) -> dict[str, Any]:
        return {
            "output_path": self.output_path,
            "resource_id": self.resource_id,
            "scope": self.scope,
            "sha256": self.sha256,
            "size_bytes": self.size_bytes,
            "status": self.status,
            "url": self.url,
            "warnings": list(self.warnings),
        }


@dataclass(frozen=True)
class MediaMuxPlan:
    video_resource_id: str
    audio_resource_id: str
    output_filename: str
    executable_command: tuple[str, ...] = ()
    status: str = "plan_only"
    scope: str = MEDIA_DOWNLOAD_SCOPE

    def to_dict(self) -> dict[str, Any]:
        return {
            "audio_resource_id": self.audio_resource_id,
            "executable_command": list(self.executable_command),
            "output_filename": self.output_filename,
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
    allowed_hostnames: tuple[str, ...] = ("127.0.0.1", "localhost", "::1"),
) -> MediaDownloadResult:
    if not resource.downloadable:
        return MediaDownloadResult(
            status=CAPTURE_STATUS_UNSUPPORTED,
            resource_id=resource.resource_id,
            url=resource.url,
            warnings=("Media resource is not directly downloadable by this helper.",),
        )
    if not is_allowed_media_download_url(resource.url, allowed_hostnames):
        return MediaDownloadResult(
            status=CAPTURE_STATUS_UNSUPPORTED,
            resource_id=resource.resource_id,
            url=resource.url,
            warnings=("Media download helper is restricted to allowed localhost fixture hosts.",),
        )

    output_dir = Path(output_folder)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / safe_media_filename(resource)
    try:
        with urlopen(resource.url, timeout=10) as response:
            payload = response.read()
        output_path.write_bytes(payload)
    except (KeyboardInterrupt, SystemExit, GeneratorExit):
        raise
    except Exception:
        return MediaDownloadResult(
            status=CAPTURE_STATUS_FAILED,
            resource_id=resource.resource_id,
            url=resource.url,
            warnings=("Media download failed with a non-secret exception.",),
        )

    return MediaDownloadResult(
        status=CAPTURE_STATUS_SUCCESS,
        resource_id=resource.resource_id,
        url=resource.url,
        output_path=str(output_path),
        sha256=hashlib.sha256(payload).hexdigest(),
        size_bytes=len(payload),
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
