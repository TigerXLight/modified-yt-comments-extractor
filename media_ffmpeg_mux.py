from __future__ import annotations

import hashlib
import json
import subprocess
from dataclasses import asdict, dataclass, is_dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from media_jdownloader_external_config import JDownloaderExternalConfigReport


Runner = Callable[[Sequence[str]], subprocess.CompletedProcess[str]]


@dataclass(frozen=True)
class FFmpegMuxRequest:
    video_path: str
    audio_path: str
    output_path: str
    container: str = "mp4"
    ffmpeg_path: str = "ffmpeg"
    command_template: tuple[str, ...] = ()
    execute: bool = False

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class FFmpegMuxResult:
    status: str
    command: tuple[str, ...]
    execute: bool
    video_path: str
    audio_path: str
    output_path: str
    temp_output_path: str
    video_sha256: str = ""
    audio_sha256: str = ""
    output_sha256: str = ""
    ffmpeg_version: str = ""
    returncode: int | None = None
    stdout: str = ""
    stderr: str = ""
    warning: str = ""

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
    h = hashlib.sha256()
    with Path(path).open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def jdownloader_mux_template(
    config: JDownloaderExternalConfigReport,
    *,
    container: str = "mp4",
) -> tuple[str, ...]:
    normalized = str(container or "mp4").lower().lstrip(".")
    if normalized == "mkv":
        return tuple(config.mux_to_mkv_command_template)
    return tuple(config.mux_to_mp4_command_template)


def build_ffmpeg_mux_command(request: FFmpegMuxRequest) -> tuple[str, ...]:
    container = str(request.container or "mp4").lower().lstrip(".")
    template = tuple(request.command_template) or (
        "-i",
        "%video",
        "-i",
        "%audio",
        "-map",
        "0:0",
        "-c:v",
        "copy",
        "-map",
        "1:0",
        "-c:a",
        "copy",
        "-f",
        "matroska" if container == "mkv" else "mp4",
        "%out",
        "-y",
    )
    out = _temp_output_path(request.output_path)
    replacements = {
        "%video": str(request.video_path),
        "%audio": str(request.audio_path),
        "%out": str(out),
    }
    args = [replacements.get(str(item), str(item)) for item in template]
    return (str(request.ffmpeg_path or "ffmpeg"), *args)


def _temp_output_path(output_path: str | Path) -> Path:
    target = Path(output_path)
    suffix = target.suffix or ".media"
    return target.with_name(target.stem + ".part" + suffix)


def _default_runner(command: Sequence[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(command),
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def read_ffmpeg_version(ffmpeg_path: str = "ffmpeg", *, runner: Runner | None = None) -> str:
    run = runner or _default_runner
    completed = run((str(ffmpeg_path or "ffmpeg"), "-version"))
    text = (completed.stdout or completed.stderr or "").strip()
    return text.splitlines()[0] if text else ""


def mux_audio_video(
    request: FFmpegMuxRequest,
    *,
    runner: Runner | None = None,
) -> FFmpegMuxResult:
    command = build_ffmpeg_mux_command(request)
    temp_out = _temp_output_path(request.output_path)
    video_hash = sha256_file(request.video_path) if Path(request.video_path).is_file() else ""
    audio_hash = sha256_file(request.audio_path) if Path(request.audio_path).is_file() else ""
    ffmpeg_version = ""
    try:
        ffmpeg_version = read_ffmpeg_version(request.ffmpeg_path, runner=runner)
    except Exception as exc:  # pragma: no cover - version probing can fail on user machines.
        ffmpeg_version = f"version probe failed: {exc}"
    if not request.execute:
        return FFmpegMuxResult(
            status="planned",
            command=command,
            execute=False,
            video_path=str(request.video_path),
            audio_path=str(request.audio_path),
            output_path=str(request.output_path),
            temp_output_path=str(temp_out),
            video_sha256=video_hash,
            audio_sha256=audio_hash,
            ffmpeg_version=ffmpeg_version,
        )
    if not Path(request.video_path).is_file():
        return FFmpegMuxResult(
            status="missing_video",
            command=command,
            execute=True,
            video_path=str(request.video_path),
            audio_path=str(request.audio_path),
            output_path=str(request.output_path),
            temp_output_path=str(temp_out),
            video_sha256=video_hash,
            audio_sha256=audio_hash,
            ffmpeg_version=ffmpeg_version,
            warning="Video input is missing.",
        )
    if not Path(request.audio_path).is_file():
        return FFmpegMuxResult(
            status="missing_audio",
            command=command,
            execute=True,
            video_path=str(request.video_path),
            audio_path=str(request.audio_path),
            output_path=str(request.output_path),
            temp_output_path=str(temp_out),
            video_sha256=video_hash,
            audio_sha256=audio_hash,
            ffmpeg_version=ffmpeg_version,
            warning="Audio input is missing.",
        )
    temp_out.parent.mkdir(parents=True, exist_ok=True)
    if temp_out.exists():
        temp_out.unlink()
    run = runner or _default_runner
    completed = run(command)
    out_hash = ""
    status = "failed"
    if completed.returncode == 0 and temp_out.is_file():
        target = Path(request.output_path)
        if target.exists():
            target.unlink()
        temp_out.replace(target)
        out_hash = sha256_file(target)
        status = "muxed"
    return FFmpegMuxResult(
        status=status,
        command=command,
        execute=True,
        video_path=str(request.video_path),
        audio_path=str(request.audio_path),
        output_path=str(request.output_path),
        temp_output_path=str(temp_out),
        video_sha256=video_hash,
        audio_sha256=audio_hash,
        output_sha256=out_hash,
        ffmpeg_version=ffmpeg_version,
        returncode=completed.returncode,
        stdout=completed.stdout or "",
        stderr=completed.stderr or "",
    )


def write_ffmpeg_mux_plan(result: FFmpegMuxResult, output_path: str | Path) -> None:
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
