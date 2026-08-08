from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from dataclasses import asdict, dataclass, is_dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence
from urllib.parse import urlsplit

from capture_media_download import MediaComponentRecord, MediaDownloadResult, MediaMuxPlan, is_allowed_media_download_url
from capture_status import CAPTURE_STATUS_FAILED, CAPTURE_STATUS_SUCCESS, CAPTURE_STATUS_UNSUPPORTED


SOURCE_MEDIA_EXECUTION_BRIDGE_SCHEMA_VERSION = "source_media_execution_bridge_v1"
SOURCE_MEDIA_EXECUTION_SCOPE = (
    "explicit selected local/localhost media execution bridge; tests use temp local files "
    "and mocked subprocess runners only; external downloads and real FFmpeg/yt-dlp remain "
    "approval gated"
)


class MediaExecutionStatus(str, Enum):
    SUCCESS = "success"
    DRY_RUN = "dry_run"
    DEPENDENCY_NOT_FOUND = "dependency_not_found"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"
    UNSUPPORTED = "unsupported"
    FAILED = "failed"


class MediaCollisionPolicy(str, Enum):
    FAIL = "fail"
    OVERWRITE = "overwrite"
    KEEP_BOTH = "keep_both"


def _value_for_dict(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return {key: _value_for_dict(item) for key, item in asdict(value).items()}
    if isinstance(value, tuple):
        return [_value_for_dict(item) for item in value]
    if isinstance(value, list):
        return [_value_for_dict(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _value_for_dict(value[key]) for key in sorted(value)}
    if hasattr(value, "to_dict") and callable(value.to_dict):
        return value.to_dict()
    return value


def _stable_json(data: Any) -> str:
    return json.dumps(_value_for_dict(data), sort_keys=True, separators=(",", ":"))


def _sha16(data: Any) -> str:
    return hashlib.sha256(_stable_json(data).encode("utf-8")).hexdigest()[:16]


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_name(value: str) -> str:
    name = Path(urlsplit(value).path).name or Path(value).name or "media.bin"
    return "".join(ch if ch.isalnum() or ch in {".", "-", "_"} else "_" for ch in name) or "media.bin"


def _resolve_collision(path: Path, policy: MediaCollisionPolicy) -> Path:
    if not path.exists() or policy == MediaCollisionPolicy.OVERWRITE:
        return path
    if policy == MediaCollisionPolicy.FAIL:
        raise FileExistsError(f"destination exists: {path.name}")
    stem = path.stem
    suffix = path.suffix
    for index in range(1, 1000):
        candidate = path.with_name(f"{stem}_{index}{suffix}")
        if not candidate.exists():
            return candidate
    raise FileExistsError("could not allocate collision-safe media filename")


@dataclass(frozen=True)
class SelectedMediaCopyReceipt:
    resource_id: str
    source_name: str
    output_name: str
    media_type: str
    sha256: str
    size_bytes: int
    copied: bool
    status: MediaExecutionStatus

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class SelectedMediaExecutionQueue:
    queue_id: str
    selected_resource_ids: tuple[str, ...]
    download_results: tuple[MediaDownloadResult, ...] = ()
    local_copy_receipts: tuple[SelectedMediaCopyReceipt, ...] = ()
    status: MediaExecutionStatus = MediaExecutionStatus.SUCCESS
    scope: str = SOURCE_MEDIA_EXECUTION_SCOPE
    schema_version: str = SOURCE_MEDIA_EXECUTION_BRIDGE_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        data = _value_for_dict(self)
        data["selected_count"] = len(self.selected_resource_ids)
        data["download_result_count"] = len(self.download_results)
        data["local_copy_count"] = len(self.local_copy_receipts)
        return data


@dataclass(frozen=True)
class MediaCommandExecutionResult:
    execution_id: str
    tool: str
    status: MediaExecutionStatus
    command: tuple[str, ...]
    stdout: str = ""
    stderr: str = ""
    returncode: int | None = None
    dry_run: bool = False
    approval_required: bool = True
    approval_granted: bool = False
    timeout_seconds: int = 0
    output_name: str = ""
    warnings: tuple[str, ...] = ()
    scope: str = SOURCE_MEDIA_EXECUTION_SCOPE
    schema_version: str = SOURCE_MEDIA_EXECUTION_BRIDGE_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class MediaHttpDownloadReceipt:
    resource_id: str
    url: str
    output_name: str
    sha256: str
    size_bytes: int
    status: MediaExecutionStatus
    source_url: str = ""
    media_type: str = ""
    warnings: tuple[str, ...] = ()
    schema_version: str = SOURCE_MEDIA_EXECUTION_BRIDGE_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class MediaTrackGrouping:
    grouping_id: str
    video_components: tuple[MediaComponentRecord, ...]
    audio_components: tuple[MediaComponentRecord, ...]
    other_components: tuple[MediaComponentRecord, ...]
    schema_version: str = SOURCE_MEDIA_EXECUTION_BRIDGE_SCHEMA_VERSION

    @property
    def video_count(self) -> int:
        return len(self.video_components)

    @property
    def audio_count(self) -> int:
        return len(self.audio_components)

    def to_dict(self) -> dict[str, Any]:
        data = _value_for_dict(self)
        data["video_count"] = self.video_count
        data["audio_count"] = self.audio_count
        data["other_count"] = len(self.other_components)
        return data


Runner = Callable[..., Any]
HttpDownloader = Callable[[str, int], bytes]


def copy_selected_local_media_files(
    *,
    resources: Sequence[Mapping[str, Any]],
    output_directory: str | Path,
    selected_resource_ids: Sequence[str],
    collision_policy: MediaCollisionPolicy = MediaCollisionPolicy.FAIL,
) -> SelectedMediaExecutionQueue:
    selected = tuple(sorted(set(str(item) for item in selected_resource_ids)))
    selected_set = set(selected)
    output_root = Path(output_directory)
    output_root.mkdir(parents=True, exist_ok=True)
    receipts: list[SelectedMediaCopyReceipt] = []
    for resource in sorted((dict(item) for item in resources), key=lambda item: str(item.get("resource_id") or "")):
        resource_id = str(resource.get("resource_id") or "")
        if resource_id not in selected_set:
            continue
        source_path = Path(str(resource.get("path") or ""))
        if not source_path.is_file():
            receipts.append(
                SelectedMediaCopyReceipt(
                    resource_id=resource_id,
                    source_name=source_path.name,
                    output_name="",
                    media_type=str(resource.get("media_type") or resource.get("kind") or ""),
                    sha256="",
                    size_bytes=0,
                    copied=False,
                    status=MediaExecutionStatus.FAILED,
                )
            )
            continue
        output_path = _resolve_collision(output_root / _safe_name(source_path.name), collision_policy)
        shutil.copy2(source_path, output_path)
        receipts.append(
            SelectedMediaCopyReceipt(
                resource_id=resource_id,
                source_name=source_path.name,
                output_name=output_path.name,
                media_type=str(resource.get("media_type") or resource.get("kind") or ""),
                sha256=_sha256_file(output_path),
                size_bytes=output_path.stat().st_size,
                copied=True,
                status=MediaExecutionStatus.SUCCESS,
            )
        )
    status = MediaExecutionStatus.SUCCESS if all(item.copied for item in receipts) else MediaExecutionStatus.FAILED
    return SelectedMediaExecutionQueue(
        queue_id="selected_media_execution_queue_" + _sha16((selected, [item.to_dict() for item in receipts])),
        selected_resource_ids=selected,
        local_copy_receipts=tuple(receipts),
        status=status,
    )


def download_selected_media_resources_with_http_client(
    *,
    resources: Sequence[Mapping[str, Any]],
    output_directory: str | Path,
    selected_resource_ids: Sequence[str],
    http_downloader: HttpDownloader,
    timeout_seconds: int = 30,
    allowed_hostnames: tuple[str, ...] = ("127.0.0.1", "localhost", "::1"),
    allow_external_network: bool = False,
    cancel_requested: bool = False,
) -> tuple[MediaHttpDownloadReceipt, ...]:
    if cancel_requested:
        return tuple(
            MediaHttpDownloadReceipt(
                resource_id=str(resource.get("resource_id") or ""),
                url=str(resource.get("url") or ""),
                output_name="",
                sha256="",
                size_bytes=0,
                status=MediaExecutionStatus.CANCELLED,
                warnings=("Operator cancellation requested before HTTP media download.",),
            )
            for resource in resources
            if str(resource.get("resource_id") or "") in set(str(item) for item in selected_resource_ids)
        )
    selected = set(str(item) for item in selected_resource_ids)
    output_root = Path(output_directory)
    output_root.mkdir(parents=True, exist_ok=True)
    receipts: list[MediaHttpDownloadReceipt] = []
    for resource in sorted((dict(item) for item in resources), key=lambda item: str(item.get("resource_id") or "")):
        resource_id = str(resource.get("resource_id") or "")
        if resource_id not in selected:
            continue
        url = str(resource.get("url") or "")
        if url.startswith("blob:") or url.startswith("mediasource:"):
            receipts.append(
                MediaHttpDownloadReceipt(
                    resource_id=resource_id,
                    url=url,
                    output_name="",
                    sha256="",
                    size_bytes=0,
                    status=MediaExecutionStatus.UNSUPPORTED,
                    source_url=str(resource.get("source_url") or ""),
                    media_type=str(resource.get("media_type") or resource.get("kind") or ""),
                    warnings=("Blob/MediaSource URLs are not directly downloadable.",),
                )
            )
            continue
        if not allow_external_network and not is_allowed_media_download_url(url, allowed_hostnames):
            receipts.append(
                MediaHttpDownloadReceipt(
                    resource_id=resource_id,
                    url=url,
                    output_name="",
                    sha256="",
                    size_bytes=0,
                    status=MediaExecutionStatus.UNSUPPORTED,
                    source_url=str(resource.get("source_url") or ""),
                    media_type=str(resource.get("media_type") or resource.get("kind") or ""),
                    warnings=("HTTP media download is restricted to local fixture hosts unless explicitly approved.",),
                )
            )
            continue
        try:
            payload = http_downloader(url, timeout_seconds)
        except TimeoutError:
            receipts.append(
                MediaHttpDownloadReceipt(
                    resource_id=resource_id,
                    url=url,
                    output_name="",
                    sha256="",
                    size_bytes=0,
                    status=MediaExecutionStatus.TIMEOUT,
                    warnings=("HTTP media download timed out.",),
                )
            )
            continue
        except Exception as exc:
            receipts.append(
                MediaHttpDownloadReceipt(
                    resource_id=resource_id,
                    url=url,
                    output_name="",
                    sha256="",
                    size_bytes=0,
                    status=MediaExecutionStatus.FAILED,
                    warnings=(f"HTTP media downloader failed: {type(exc).__name__}",),
                )
            )
            continue
        output_name = _safe_name(str(resource.get("filename") or url))
        output_path = _resolve_collision(output_root / output_name, MediaCollisionPolicy.KEEP_BOTH)
        output_path.write_bytes(payload)
        receipts.append(
            MediaHttpDownloadReceipt(
                resource_id=resource_id,
                url=url,
                output_name=output_path.name,
                sha256=hashlib.sha256(payload).hexdigest(),
                size_bytes=len(payload),
                status=MediaExecutionStatus.SUCCESS,
                source_url=str(resource.get("source_url") or ""),
                media_type=str(resource.get("media_type") or resource.get("kind") or ""),
            )
        )
    return tuple(receipts)


def group_media_components_for_mux(
    components: Sequence[MediaComponentRecord],
) -> MediaTrackGrouping:
    video: list[MediaComponentRecord] = []
    audio: list[MediaComponentRecord] = []
    other: list[MediaComponentRecord] = []
    for component in components:
        role = str(component.role or component.media_type or "").lower()
        if role == "video":
            video.append(component)
        elif role == "audio":
            audio.append(component)
        else:
            other.append(component)
    return MediaTrackGrouping(
        grouping_id="media_track_grouping_" + _sha16([component.to_dict() for component in components]),
        video_components=tuple(video),
        audio_components=tuple(audio),
        other_components=tuple(other),
    )


def _redact_process_text(value: object) -> str:
    text = str(value or "")
    for token in ("authorization", "cookie", "password", "api_key", "token", "secret"):
        text = text.replace(token, "[REDACTED]")
        text = text.replace(token.upper(), "[REDACTED]")
    return text[:4000]


def execute_media_command(
    *,
    tool: str,
    command: Sequence[str],
    runner: Runner | None = None,
    approval_granted: bool = False,
    dry_run: bool = False,
    timeout_seconds: int = 120,
    output_name: str = "",
    cancel_requested: bool = False,
) -> MediaCommandExecutionResult:
    command_tuple = tuple(str(part) for part in command)
    if cancel_requested:
        return MediaCommandExecutionResult(
            execution_id=f"media_command_{tool}_" + _sha16((command_tuple, "cancelled")),
            tool=tool,
            status=MediaExecutionStatus.CANCELLED,
            command=command_tuple,
            approval_granted=approval_granted,
            timeout_seconds=timeout_seconds,
            output_name=output_name,
            warnings=("Operator cancellation requested before media subprocess execution.",),
        )
    if dry_run:
        return MediaCommandExecutionResult(
            execution_id=f"media_command_{tool}_" + _sha16((command_tuple, "dry_run")),
            tool=tool,
            status=MediaExecutionStatus.DRY_RUN,
            command=command_tuple,
            dry_run=True,
            approval_granted=approval_granted,
            timeout_seconds=timeout_seconds,
            output_name=output_name,
            warnings=("Dry run: command was not executed.",),
        )
    if not approval_granted:
        return MediaCommandExecutionResult(
            execution_id=f"media_command_{tool}_" + _sha16((command_tuple, "approval_required")),
            tool=tool,
            status=MediaExecutionStatus.UNSUPPORTED,
            command=command_tuple,
            approval_granted=False,
            timeout_seconds=timeout_seconds,
            output_name=output_name,
            warnings=("Operator approval is required before media subprocess execution.",),
        )
    selected_runner = runner or subprocess.run
    try:
        completed = selected_runner(
            list(command_tuple),
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
    except FileNotFoundError:
        return MediaCommandExecutionResult(
            execution_id=f"media_command_{tool}_" + _sha16((command_tuple, "missing")),
            tool=tool,
            status=MediaExecutionStatus.DEPENDENCY_NOT_FOUND,
            command=command_tuple,
            approval_granted=True,
            timeout_seconds=timeout_seconds,
            output_name=output_name,
            warnings=(f"{tool} executable was not found.",),
        )
    except subprocess.TimeoutExpired:
        return MediaCommandExecutionResult(
            execution_id=f"media_command_{tool}_" + _sha16((command_tuple, "timeout")),
            tool=tool,
            status=MediaExecutionStatus.TIMEOUT,
            command=command_tuple,
            approval_granted=True,
            timeout_seconds=timeout_seconds,
            output_name=output_name,
            warnings=(f"{tool} execution timed out.",),
        )
    status = MediaExecutionStatus.SUCCESS if int(getattr(completed, "returncode", 1)) == 0 else MediaExecutionStatus.FAILED
    return MediaCommandExecutionResult(
        execution_id=f"media_command_{tool}_" + _sha16((command_tuple, getattr(completed, "returncode", None))),
        tool=tool,
        status=status,
        command=command_tuple,
        stdout=_redact_process_text(getattr(completed, "stdout", "")),
        stderr=_redact_process_text(getattr(completed, "stderr", "")),
        returncode=int(getattr(completed, "returncode", 1)),
        approval_granted=True,
        timeout_seconds=timeout_seconds,
        output_name=output_name,
    )


def execute_ffmpeg_mux_plan(
    plan: MediaMuxPlan,
    *,
    runner: Runner | None = None,
    approval_granted: bool = False,
    dry_run: bool = False,
    timeout_seconds: int = 120,
    cancel_requested: bool = False,
) -> MediaCommandExecutionResult:
    return execute_media_command(
        tool="ffmpeg",
        command=plan.executable_command,
        runner=runner,
        approval_granted=approval_granted,
        dry_run=dry_run,
        timeout_seconds=timeout_seconds,
        output_name=plan.output_filename,
        cancel_requested=cancel_requested,
    )


def execute_yt_dlp_command(
    *,
    command: Sequence[str],
    runner: Runner | None = None,
    approval_granted: bool = False,
    dry_run: bool = False,
    timeout_seconds: int = 120,
    output_name: str = "",
    cancel_requested: bool = False,
) -> MediaCommandExecutionResult:
    return execute_media_command(
        tool="yt-dlp",
        command=command,
        runner=runner,
        approval_granted=approval_granted,
        dry_run=dry_run,
        timeout_seconds=timeout_seconds,
        output_name=output_name,
        cancel_requested=cancel_requested,
    )
