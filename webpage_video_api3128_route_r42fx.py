from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence
from urllib.parse import urlsplit

R42FX_MARKER = "YTCE_R42FX_UNIVERSAL_WEBPAGE_VIDEO_API3128_ROUTE"
API3128_BACKEND_ID = "jdownloader_internal"
API3128_ROUTE_USED = "api3128"
API3128_ROUTE_LABEL = "API3128-backed JDownloader internal bridge"
YTDLP_ROLE = "fallback_only_after_jdownloader_api3128"
STATUS_PLAN_ONLY = "plan_only"
STATUS_UNSUPPORTED = "unsupported"
STATUS_SUCCESS = "success"
STATUS_FAILED = "failed"

PUBLIC_MEDIA_STREAM_EXTENSIONS = (".m3u8", ".mpd", ".f4m", ".ism", ".ism/manifest")
PUBLIC_MEDIA_FILE_EXTENSIONS = (
    ".mp4",
    ".m4v",
    ".mov",
    ".webm",
    ".mkv",
    ".avi",
    ".ts",
    ".m2ts",
    ".mp3",
    ".m4a",
    ".aac",
    ".ogg",
    ".opus",
    ".wav",
    ".flac",
)
EMBED_OR_PLAYER_KINDS = ("embed", "iframe", "player", "stream", "manifest", "video", "audio")
LOCAL_HOSTS = {"127.0.0.1", "localhost", "::1"}


@dataclass(frozen=True)
class WebpageVideoApi3128HandoffPlan:
    status: str
    route_preference: str
    backend_id: str
    route_used: str
    media_url: str
    source_url: str = ""
    source_adapter_id: str = "webpage"
    resource_id: str = ""
    output_dir: str = ""
    package_name: str = ""
    source_title_or_id: str = ""
    components: tuple[str, ...] = ("video", "audio")
    max_height: int = 0
    wait: bool = True
    timeout_seconds: float = 180.0
    side_effects_performed: bool = False
    yt_dlp_role: str = YTDLP_ROLE
    warning: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "backend_id": self.backend_id,
            "components": list(self.components),
            "max_height": self.max_height,
            "media_url": self.media_url,
            "output_dir": self.output_dir,
            "package_name": self.package_name,
            "resource_id": self.resource_id,
            "route_preference": self.route_preference,
            "route_used": self.route_used,
            "r42fx_marker": R42FX_MARKER,
            "side_effects_performed": self.side_effects_performed,
            "source_adapter_id": self.source_adapter_id,
            "source_title_or_id": self.source_title_or_id,
            "source_url": self.source_url,
            "status": self.status,
            "timeout_seconds": self.timeout_seconds,
            "wait": self.wait,
            "warning": self.warning,
            "yt_dlp_role": self.yt_dlp_role,
        }


@dataclass(frozen=True)
class WebpageVideoApi3128ExecutionResult:
    status: str
    plan: WebpageVideoApi3128HandoffPlan
    local_file_paths: tuple[str, ...] = ()
    manifest_path: str = ""
    message: str = ""
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()
    side_effects_performed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "errors": list(self.errors),
            "local_file_paths": list(self.local_file_paths),
            "manifest_path": self.manifest_path,
            "message": self.message,
            "plan": self.plan.to_dict(),
            "r42fx_marker": R42FX_MARKER,
            "side_effects_performed": self.side_effects_performed,
            "status": self.status,
            "warnings": list(self.warnings),
        }


def _value_for_dict(obj: Any, *names: str, default: str = "") -> str:
    if isinstance(obj, Mapping):
        for name in names:
            value = obj.get(name)
            if value:
                return str(value)
    for name in names:
        value = getattr(obj, name, None)
        if value:
            return str(value)
    return default


def _safe_name(value: str, default: str = "webpage_media") -> str:
    text = " ".join(str(value or "").split()) or default
    safe = "".join(ch if ch.isalnum() or ch in {"-", "_", ".", " "} else "_" for ch in text)
    safe = safe.strip(" ._")
    return (safe or default)[:120]


def _path_extension(url: str) -> str:
    path = urlsplit(str(url or "")).path or ""
    lower = path.lower()
    for suffix in PUBLIC_MEDIA_STREAM_EXTENSIONS:
        if lower.endswith(suffix):
            return suffix
    return Path(path).suffix.lower()


def _host(url: str) -> str:
    return (urlsplit(str(url or "")).hostname or "").lower()


def _is_http_url(url: str) -> bool:
    return urlsplit(str(url or "").strip()).scheme.lower() in {"http", "https"}


def is_public_web_media_candidate(url: str) -> bool:
    if not _is_http_url(url):
        return False
    return _host(url) not in LOCAL_HOSTS


def should_attempt_webpage_video_api3128_first(
    media_url: str,
    *,
    extension: str = "",
    mime_type: str = "",
    kind: str = "",
    source_url: str = "",
) -> bool:
    """Return whether public web media should be handed to API3128/JDownloader first.

    This is deliberately conservative for local fixtures and non-HTTP browser-only tokens,
    but broad for public direct files, stream manifests, embeds/players, and video/audio MIME.
    It performs no network calls.
    """
    if not is_public_web_media_candidate(media_url):
        return False
    ext = (extension or _path_extension(media_url) or "").strip().lower()
    mime = str(mime_type or "").strip().lower()
    item_kind = str(kind or "").strip().lower()
    if ext in PUBLIC_MEDIA_FILE_EXTENSIONS or ext in PUBLIC_MEDIA_STREAM_EXTENSIONS:
        return True
    if any(mime.startswith(prefix) for prefix in ("video/", "audio/", "application/vnd.apple.mpegurl", "application/dash+xml")):
        return True
    if item_kind in EMBED_OR_PLAYER_KINDS:
        return True
    host = _host(media_url)
    if host and any(token in host for token in ("youtube", "youtu.be", "vimeo", "dailymotion", "twitter", "x.com", "tiktok")):
        return True
    return bool(source_url and is_public_web_media_candidate(source_url))


def build_webpage_video_api3128_handoff_plan(
    *,
    media_url: str,
    output_dir: str,
    source_url: str = "",
    source_adapter_id: str = "webpage",
    resource_id: str = "",
    display_name: str = "",
    extension: str = "",
    mime_type: str = "",
    kind: str = "",
    max_height: int = 0,
    components: Sequence[str] = ("video", "audio"),
    wait: bool = True,
    timeout_seconds: float = 180.0,
) -> WebpageVideoApi3128HandoffPlan:
    media_url = str(media_url or "").strip()
    supported = should_attempt_webpage_video_api3128_first(
        media_url,
        extension=extension,
        mime_type=mime_type,
        kind=kind,
        source_url=source_url,
    )
    display = _safe_name(display_name or resource_id or urlsplit(media_url).netloc or "webpage media")
    package = _safe_name(f"YTCE R42FX {display}")
    return WebpageVideoApi3128HandoffPlan(
        status=STATUS_PLAN_ONLY if supported else STATUS_UNSUPPORTED,
        route_preference="jdownloader_api3128_first_for_public_web_media",
        backend_id=API3128_BACKEND_ID,
        route_used=API3128_ROUTE_USED,
        media_url=media_url,
        source_url=str(source_url or ""),
        source_adapter_id=str(source_adapter_id or "webpage"),
        resource_id=str(resource_id or ""),
        output_dir=str(output_dir or ""),
        package_name=package,
        source_title_or_id=display,
        components=tuple(str(part) for part in components if str(part or "")) or ("video", "audio"),
        max_height=max(0, int(max_height or 0)),
        wait=bool(wait),
        timeout_seconds=float(timeout_seconds or 180.0),
        side_effects_performed=False,
        warning="" if supported else "Candidate is not a public HTTP(S) media/player URL; keep direct/local path handling.",
    )


def write_webpage_video_api3128_handoff_plan(plan: WebpageVideoApi3128HandoffPlan, path: str | Path) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(plan.to_dict(), indent=2, sort_keys=True), encoding="utf-8")
    return target


def _completed_files_from_manifest(path: str | Path) -> tuple[str, ...]:
    manifest_path = Path(path)
    if not manifest_path.is_file():
        return ()
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception:
        return ()
    candidates: list[str] = []
    for key in ("files", "local_file_paths", "downloaded_files", "outputs"):
        value = payload.get(key) if isinstance(payload, dict) else None
        if isinstance(value, list):
            for item in value:
                if isinstance(item, str):
                    candidates.append(item)
                elif isinstance(item, dict):
                    for item_key in ("path", "file", "local_path", "output_path"):
                        if item.get(item_key):
                            candidates.append(str(item[item_key]))
                            break
    single = payload.get("output_path") if isinstance(payload, dict) else ""
    if single:
        candidates.append(str(single))
    existing = []
    for candidate in candidates:
        p = Path(candidate)
        if p.is_file() and p.stat().st_size > 0:
            existing.append(str(p))
    return tuple(dict.fromkeys(existing))


def run_webpage_video_api3128_handoff(
    plan: WebpageVideoApi3128HandoffPlan,
    *,
    request_builder: Callable[..., Any] | None = None,
    backend_runner: Callable[..., Any] | None = None,
    internal_job_runner: Any = None,
) -> WebpageVideoApi3128ExecutionResult:
    if plan.status == STATUS_UNSUPPORTED:
        return WebpageVideoApi3128ExecutionResult(
            status=STATUS_UNSUPPORTED,
            plan=plan,
            message=plan.warning or "Unsupported candidate for API3128 route.",
            warnings=tuple(filter(None, (plan.warning,))),
            side_effects_performed=False,
        )
    handoff_dir = Path(plan.output_dir or ".") / "_jdownloader_api3128_handoff"
    handoff_dir.mkdir(parents=True, exist_ok=True)
    plan_path = handoff_dir / f"{_safe_name(plan.resource_id or plan.source_title_or_id)}_{int(time.time())}_plan.json"
    write_webpage_video_api3128_handoff_plan(plan, plan_path)

    if request_builder is None or backend_runner is None:
        from shared_media_backend import (  # type: ignore
            build_shared_jdownloader_media_request,
            run_shared_jdownloader_media_backend,
        )

        request_builder = request_builder or build_shared_jdownloader_media_request
        backend_runner = backend_runner or run_shared_jdownloader_media_backend

    request = request_builder(
        source_adapter_id=plan.source_adapter_id,
        source_url=plan.media_url,
        output_dir=Path(plan.output_dir),
        package_name=plan.package_name,
        source_title_or_id=plan.source_title_or_id,
        max_height=plan.max_height or None,
        components=plan.components,
        video="video" in plan.components,
        audio="audio" in plan.components,
        image="image" in plan.components,
        description=True,
        wait=plan.wait,
        timeout_seconds=plan.timeout_seconds,
        monitor_timeout_seconds=120.0,
        overall_timeout_seconds=max(180.0, float(plan.timeout_seconds or 180.0)),
        plan_json_path=plan_path,
    )
    result = backend_runner(request, internal_job_runner=internal_job_runner)
    manifest_path = _value_for_dict(result, "manifest_path", "download_manifest_path", default="")
    files = _completed_files_from_manifest(manifest_path) if manifest_path else ()
    status = _value_for_dict(result, "status", default="")
    message = _value_for_dict(result, "message", "summary", default="")
    warnings = tuple(str(item) for item in (_value_for_dict(result, "warnings", default="") or "").split("\n") if item)
    if files:
        return WebpageVideoApi3128ExecutionResult(
            status=STATUS_SUCCESS,
            plan=plan,
            local_file_paths=files,
            manifest_path=manifest_path,
            message=message or "API3128/JDownloader produced local media files.",
            warnings=warnings,
            side_effects_performed=True,
        )
    return WebpageVideoApi3128ExecutionResult(
        status=STATUS_FAILED if status else STATUS_FAILED,
        plan=plan,
        manifest_path=manifest_path,
        message=message or "API3128/JDownloader route did not report a completed local media file.",
        warnings=warnings,
        errors=("no_completed_local_media_file",),
        side_effects_performed=True,
    )


def download_webpage_video_audio_item_via_api3128(
    *,
    row: Any,
    item: Any,
    resource_id: str,
    output_dir: str | Path,
    internal_job_runner: Any = None,
) -> WebpageVideoApi3128ExecutionResult:
    media_url = _value_for_dict(item, "reference_url", "canonical_url", "url", "source_url")
    page_url = _value_for_dict(row, "canonical_url", "raw_url")
    plan = build_webpage_video_api3128_handoff_plan(
        media_url=media_url,
        output_dir=str(output_dir),
        source_url=page_url,
        source_adapter_id=_value_for_dict(row, "adapter_id", default="webpage"),
        resource_id=str(resource_id or _value_for_dict(item, "resource_id")),
        display_name=_value_for_dict(item, "display_name", "title", default=resource_id),
        extension=_value_for_dict(item, "extension"),
        mime_type=_value_for_dict(item, "mime_type"),
        kind=_value_for_dict(item, "resource_kind", "kind", "media_type"),
        max_height=int(_value_for_dict(item, "height", default="0") or 0),
    )
    return run_webpage_video_api3128_handoff(plan, internal_job_runner=internal_job_runner)


def render_webpage_video_api3128_result_for_log(result: WebpageVideoApi3128ExecutionResult) -> str:
    if result.status == STATUS_SUCCESS:
        return f"API3128/JDownloader media route succeeded: {len(result.local_file_paths)} file(s)."
    if result.status == STATUS_UNSUPPORTED:
        return f"API3128/JDownloader media route skipped: {result.message}"
    return f"API3128/JDownloader media route failed: {result.message}"
