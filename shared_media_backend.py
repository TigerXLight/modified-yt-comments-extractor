from __future__ import annotations

import json
from dataclasses import asdict, dataclass, is_dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from jdownloader_internal_backend import build_internal_youtube_download_command
from jdownloader_internal_job import (
    InternalJDownloaderJobRequest,
    InternalJDownloaderJobResult,
    build_youtube_job_request,
    run_internal_youtube_job,
)
from jdownloader_internal_paths import JDOWNLOADER_INTERNAL_BACKEND_ID


SHARED_MEDIA_BACKEND_ID_JDOWNLOADER = "shared_media_jdownloader"
SHARED_MEDIA_BACKEND_ARCHITECTURE_TAG = "source_adapter_declares_shared_backend_executes"


@dataclass(frozen=True)
class SharedMediaBackendRequest:
    source_adapter_id: str
    source_url: str
    output_dir: str
    package_name: str
    source_title_or_id: str = ""
    max_height: int = 1080
    components: tuple[str, ...] = ()
    video: bool = True
    audio: bool = True
    image: bool = True
    description: bool = True
    wait: bool = True
    timeout_seconds: int = 180
    monitor_timeout_seconds: float = 120.0
    overall_timeout_seconds: float = 180.0
    plan_json_path: str = ""

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class SharedMediaBackendResult:
    shared_backend_id: str
    backend_id: str
    status: str
    source_adapter_id: str
    source_url: str
    output_dir: str
    execution_manifest_path: str = ""
    engine_status: str = ""
    readiness_status: str = ""
    submission_status: str = ""
    phase: str = ""
    files_count: int = 0
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()
    route_metadata: dict[str, Any] | None = None
    plan_json_paths: tuple[str, ...] = ()
    plan_summary: dict[str, Any] | None = None
    job_request: InternalJDownloaderJobRequest | None = None
    internal_job_result: InternalJDownloaderJobResult | None = None

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


SharedInternalJobRunner = Callable[[InternalJDownloaderJobRequest], InternalJDownloaderJobResult]


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


def build_shared_jdownloader_media_request(
    *,
    source_adapter_id: str,
    source_url: str,
    output_dir: str | Path,
    package_name: str,
    source_title_or_id: str = "",
    max_height: int = 1080,
    components: Sequence[str] = (),
    video: bool = True,
    audio: bool = True,
    image: bool = True,
    description: bool = True,
    wait: bool = True,
    timeout_seconds: int = 180,
    monitor_timeout_seconds: float = 120.0,
    overall_timeout_seconds: float = 180.0,
    plan_json_path: str | Path = "",
) -> SharedMediaBackendRequest:
    """Build the shared media backend request.

    Source adapters describe what media they want. This backend layer performs
    the JDownloader execution. Today it preserves the proven YouTube/JD path;
    later adapters can call this same contract without importing JD internals.
    """
    return SharedMediaBackendRequest(
        source_adapter_id=str(source_adapter_id or ""),
        source_url=str(source_url or ""),
        output_dir=str(output_dir),
        package_name=str(package_name or ""),
        source_title_or_id=str(source_title_or_id or ""),
        max_height=int(max_height or 0),
        components=tuple(str(component) for component in components),
        video=bool(video),
        audio=bool(audio),
        image=bool(image),
        description=bool(description),
        wait=bool(wait),
        timeout_seconds=int(timeout_seconds or 0),
        monitor_timeout_seconds=float(monitor_timeout_seconds or 0),
        overall_timeout_seconds=float(overall_timeout_seconds or 0),
        plan_json_path=str(plan_json_path or ""),
    )


def _build_internal_job_request(request: SharedMediaBackendRequest) -> InternalJDownloaderJobRequest:
    # This uses the existing proven request builder for compatibility. The
    # shared interface is source-adapter neutral; the implementation can be
    # generalized further when non-YouTube adapters are wired to JD.
    return build_youtube_job_request(
        source_url=request.source_url,
        output_dir=request.output_dir,
        package_name=request.package_name,
        source_title_or_id=request.source_title_or_id,
        max_height=request.max_height,
        video=request.video,
        audio=request.audio,
        image=request.image,
        description=request.description,
        wait=request.wait,
        timeout_seconds=request.timeout_seconds,
        monitor_timeout_seconds=request.monitor_timeout_seconds,
        overall_timeout_seconds=request.overall_timeout_seconds,
    )


def _write_jdownloader_plan_json(
    *,
    request: SharedMediaBackendRequest,
    job_request: InternalJDownloaderJobRequest,
    path: str | Path,
) -> dict[str, Any]:
    command = build_internal_youtube_download_command(
        source_url=request.source_url,
        output_dir=job_request.output_dir,
        package_name=job_request.package_name,
        max_height=request.max_height,
        video=request.video,
        audio=request.audio,
        image=request.image,
        description=request.description,
        manifest_path=job_request.manifest_path,
        wait=job_request.wait,
        timeout_seconds=job_request.timeout_seconds,
    )
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(command.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
    return command.to_dict()


def run_shared_jdownloader_media_backend(
    request: SharedMediaBackendRequest,
    *,
    internal_job_runner: SharedInternalJobRunner | None = None,
) -> SharedMediaBackendResult:
    runner = internal_job_runner or run_internal_youtube_job
    job_request = _build_internal_job_request(request)
    plan_paths: list[str] = []
    command_dict: dict[str, Any] = {}
    if request.plan_json_path:
        command_dict = _write_jdownloader_plan_json(request=request, job_request=job_request, path=request.plan_json_path)
        plan_paths.append(str(request.plan_json_path))

    job_result = runner(job_request)
    if job_result.manifest_path:
        plan_paths.append(job_result.manifest_path)

    plan_summary = {
        "component": "jdownloader_internal",
        "backend_id": JDOWNLOADER_INTERNAL_BACKEND_ID,
        "shared_backend_id": SHARED_MEDIA_BACKEND_ID_JDOWNLOADER,
        "source_adapter_id": request.source_adapter_id,
        "quality": str(request.max_height or ""),
        "height": request.max_height,
        "command": list(command_dict.get("command", ())),
        "plan_json": str(request.plan_json_path or ""),
        "job_request": job_request.to_dict(),
        "job_result": job_result.to_dict(),
        "yt_dlp_fallback_backend_id": command_dict.get("fallback_backend_id", ""),
    }

    return SharedMediaBackendResult(
        shared_backend_id=SHARED_MEDIA_BACKEND_ID_JDOWNLOADER,
        backend_id=JDOWNLOADER_INTERNAL_BACKEND_ID,
        status=job_result.status,
        source_adapter_id=request.source_adapter_id,
        source_url=job_result.source_url,
        output_dir=job_result.output_dir,
        execution_manifest_path=job_result.manifest_path,
        engine_status=job_result.engine_status,
        readiness_status=job_result.readiness_status,
        submission_status=job_result.submission_status,
        phase=job_result.phase,
        files_count=job_result.files_count,
        warnings=tuple(job_result.warnings),
        errors=tuple(job_result.errors),
        route_metadata=getattr(job_result, "route_metadata", None),
        plan_json_paths=tuple(plan_paths),
        plan_summary=plan_summary,
        job_request=job_request,
        internal_job_result=job_result,
    )
