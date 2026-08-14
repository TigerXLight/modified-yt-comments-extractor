from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import asdict, dataclass, is_dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from jdownloader_internal_paths import JDOWNLOADER_INTERNAL_BACKEND_ID


VIDEO_EXTENSIONS = {".mp4", ".mkv", ".webm", ".mov", ".avi", ".flv", ".m4v"}
AUDIO_EXTENSIONS = {".m4a", ".mp3", ".opus", ".ogg", ".wav", ".aac", ".flac"}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"}
DESCRIPTION_EXTENSIONS = {".description", ".txt", ".md", ".srt", ".vtt"}
METADATA_EXTENSIONS = {".json", ".info.json", ".xml", ".nfo"}
ACTIVE_SUFFIXES = (".part", ".part.met", ".jdresume")
INTERNAL_MANIFEST_NAMES = {"jdownloader-internal-download-manifest.json", "jdownloader-internal-download-manifest.json.tmp"}


Clock = Callable[[], float]
Sleeper = Callable[[float], None]


@dataclass(frozen=True)
class JDownloaderInternalFileRecord:
    kind: str
    path: str
    size: int
    sha256: str

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class JDownloaderInternalManifest:
    backend_id: str
    source_url: str
    output_dir: str
    status: str
    phase: str
    engine: dict[str, Any]
    timings: dict[str, int]
    files: tuple[JDownloaderInternalFileRecord, ...]
    normalized_source_url: str = ""
    original_source_url: str = ""
    submission_status: str = ""
    submission_attempts: tuple[dict[str, Any], ...] = ()
    route_metadata: dict[str, Any] | None = None
    api3128_enabled: bool = False
    api3128_used: bool = False
    api3128_addlinks_ms: int = 0
    api3128_package_complete_ms: int = 0
    api3128_child_count: int = 0
    api3128_move_ms: int = 0
    api3128_start_ms: int = 0
    api3128_first_running_ms: int = 0
    api3128_finished_ms: int = 0
    flashgot_fallback_used: bool = False
    route_used: str = ""
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class MonitorResult:
    status: str
    files: tuple[JDownloaderInternalFileRecord, ...]
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()
    elapsed_ms: int = 0
    first_file_seen_ms: int = 0
    pre_download_wait_ms: int = 0
    active_download_ms: int = 0

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


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def safe_download_folder_name(value: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in str(value or "").strip())
    cleaned = "_".join(part for part in cleaned.split("_") if part)
    return cleaned[:96] or "youtube_media"


def default_youtube_download_root() -> Path:
    home = Path(os.environ.get("USERPROFILE") or Path.home())
    return home / "Downloads" / "YTCE_YOUTUBE_MEDIA_DOWNLOADS"


def create_youtube_download_output_dir(
    *,
    safe_title_or_id: str,
    timestamp: str | None = None,
    root: str | Path | None = None,
) -> Path:
    root_path = Path(root) if root is not None else default_youtube_download_root()
    stamp = timestamp or time.strftime("%Y%m%d_%H%M%S")
    output_dir = root_path / f"{safe_download_folder_name(safe_title_or_id)}_{stamp}"
    output_dir.mkdir(parents=True, exist_ok=False)
    return output_dir


def classify_download_file(path: str | Path) -> str:
    file_path = Path(path)
    name = file_path.name.lower()
    suffix = file_path.suffix.lower()
    if name.endswith(".info.json") or suffix in METADATA_EXTENSIONS:
        return "metadata"
    if suffix in VIDEO_EXTENSIONS:
        return "video"
    if suffix in AUDIO_EXTENSIONS:
        return "audio"
    if suffix in IMAGE_EXTENSIONS:
        return "image"
    if suffix in DESCRIPTION_EXTENSIONS:
        return "description"
    if suffix in {".log", ".err", ".out"}:
        return "log"
    return "unknown"


def _is_active_download_path(path: Path) -> bool:
    lower_name = path.name.lower()
    return any(lower_name.endswith(suffix) for suffix in ACTIVE_SUFFIXES)


def collect_completed_files(output_dir: str | Path) -> tuple[JDownloaderInternalFileRecord, ...]:
    root = Path(output_dir)
    if not root.exists():
        return ()
    records: list[JDownloaderInternalFileRecord] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or _is_active_download_path(path):
            continue
        if path.name in INTERNAL_MANIFEST_NAMES:
            continue
        records.append(
            JDownloaderInternalFileRecord(
                kind=classify_download_file(path),
                path=str(path),
                size=path.stat().st_size,
                sha256=sha256_file(path),
            )
        )
    return tuple(records)


def has_active_part_files(output_dir: str | Path) -> bool:
    root = Path(output_dir)
    return any(path.is_file() and _is_active_download_path(path) for path in root.rglob("*")) if root.exists() else False


def wait_for_download_completion(
    output_dir: str | Path,
    *,
    timeout_seconds: float = 300.0,
    poll_interval_seconds: float = 1.0,
    stable_checks_required: int = 3,
    clock: Clock = time.monotonic,
    sleeper: Sleeper = time.sleep,
) -> MonitorResult:
    start = clock()
    stable_checks = 0
    last_sizes: dict[str, int] = {}
    warnings: list[str] = []
    first_file_seen_at: float | None = None
    while True:
        elapsed = clock() - start
        files = collect_completed_files(output_dir)
        active = has_active_part_files(output_dir)
        if files and first_file_seen_at is None:
            first_file_seen_at = clock()
        current_sizes = {record.path: record.size for record in files}
        if files and not active and current_sizes == last_sizes:
            stable_checks += 1
        else:
            stable_checks = 0
        last_sizes = current_sizes
        if files and not active and stable_checks >= stable_checks_required:
            done_at = clock()
            elapsed_ms = int((done_at - start) * 1000)
            first_seen_ms = int(((first_file_seen_at or done_at) - start) * 1000)
            return MonitorResult(
                status="success",
                files=files,
                warnings=tuple(warnings),
                elapsed_ms=elapsed_ms,
                first_file_seen_ms=first_seen_ms,
                pre_download_wait_ms=first_seen_ms,
                active_download_ms=max(0, elapsed_ms - first_seen_ms),
            )
        if elapsed >= timeout_seconds:
            status = "partial" if files else "timeout"
            errors = () if files else ("No completed files appeared before timeout.",)
            if active:
                warnings.append("Active .part files were still present at timeout.")
            done_at = clock()
            elapsed_ms = int((done_at - start) * 1000)
            first_seen_ms = int(((first_file_seen_at or done_at) - start) * 1000) if first_file_seen_at is not None else 0
            return MonitorResult(
                status=status,
                files=files,
                warnings=tuple(warnings),
                errors=errors,
                elapsed_ms=elapsed_ms,
                first_file_seen_ms=first_seen_ms,
                pre_download_wait_ms=first_seen_ms if first_seen_ms else elapsed_ms,
                active_download_ms=max(0, elapsed_ms - first_seen_ms) if first_seen_ms else 0,
            )
        sleeper(poll_interval_seconds)


def build_download_manifest(
    *,
    source_url: str,
    normalized_source_url: str = "",
    original_source_url: str = "",
    output_dir: str | Path,
    status: str,
    engine: Mapping[str, Any],
    timings: Mapping[str, int],
    files: Sequence[JDownloaderInternalFileRecord],
    phase: str = "",
    submission_status: str = "",
    submission_attempts: Sequence[Mapping[str, Any]] = (),
    route_metadata: Mapping[str, Any] | None = None,
    warnings: Sequence[str] = (),
    errors: Sequence[str] = (),
) -> JDownloaderInternalManifest:
    route = dict(route_metadata or {})
    return JDownloaderInternalManifest(
        backend_id=JDOWNLOADER_INTERNAL_BACKEND_ID,
        source_url=source_url,
        normalized_source_url=normalized_source_url,
        original_source_url=original_source_url,
        output_dir=str(output_dir),
        status=status,
        phase=phase or status,
        engine=dict(engine),
        timings={str(key): int(value or 0) for key, value in timings.items()},
        files=tuple(files),
        submission_status=str(submission_status or ""),
        submission_attempts=tuple(dict(attempt) for attempt in submission_attempts),
        route_metadata=route,
        api3128_enabled=bool(route.get("api3128_enabled", False)),
        api3128_used=bool(route.get("api3128_used", False)),
        api3128_addlinks_ms=int(route.get("api3128_addlinks_ms", 0) or 0),
        api3128_package_complete_ms=int(route.get("api3128_package_complete_ms", 0) or 0),
        api3128_child_count=int(route.get("api3128_child_count", 0) or 0),
        api3128_move_ms=int(route.get("api3128_move_ms", 0) or 0),
        api3128_start_ms=int(route.get("api3128_start_ms", 0) or 0),
        api3128_first_running_ms=int(route.get("api3128_first_running_ms", 0) or 0),
        api3128_finished_ms=int(route.get("api3128_finished_ms", 0) or 0),
        flashgot_fallback_used=bool(route.get("flashgot_fallback_used", False)),
        route_used=str(route.get("route_used", "") or ""),
        warnings=tuple(warnings),
        errors=tuple(errors),
    )


def write_download_manifest(manifest: JDownloaderInternalManifest, path: str | Path) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temp_target = target.with_name(f"{target.name}.tmp")
    temp_target.write_text(json.dumps(manifest.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
    temp_target.replace(target)
    return target
