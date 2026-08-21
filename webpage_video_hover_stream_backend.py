from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import time
from pathlib import Path
from urllib.parse import urlparse

from PIL import Image


_TILE_HOVER_VIDEO_EXTENSIONS = {
    ".mp4",
    ".m4v",
    ".webm",
    ".mov",
    ".mkv",
    ".avi",
    ".flv",
    ".3gp",
}
_TILE_HOVER_STREAM_EXTENSIONS = {
    ".m3u8",
    ".mpd",
    ".f4m",
    ".ism/manifest",
}


def video_tile_hover_stream_cache_key(url: str) -> str:
    """Stable cache key for real-video tile hover frames."""
    digest = hashlib.sha1(str(url or "").encode("utf-8", "replace")).hexdigest()
    return f"video-hover-stream:{digest}"


def _path_extension_from_url(url: str) -> str:
    parsed = urlparse(str(url or ""))
    path = parsed.path.lower()
    for suffix in sorted((*_TILE_HOVER_STREAM_EXTENSIONS, *_TILE_HOVER_VIDEO_EXTENSIONS), key=len, reverse=True):
        if path.endswith(suffix):
            return suffix
    return Path(path).suffix.lower()


def can_stream_video_tile_hover(
    url: str,
    *,
    extension: str = "",
    mime_type: str = "",
) -> bool:
    """Return whether the URL is suitable for direct in-tile video-frame playback."""
    text = str(url or "").strip()
    if not text:
        return False
    lower = text.lower()
    if lower.startswith(("javascript:", "data:", "mailto:")):
        return False
    ext = str(extension or "").lower() or _path_extension_from_url(text)
    mime = str(mime_type or "").lower()
    if ext in _TILE_HOVER_STREAM_EXTENSIONS or any(token in lower for token in (".m3u8", ".mpd", "/manifest")):
        return False
    if ext in _TILE_HOVER_VIDEO_EXTENSIONS:
        return True
    return mime.startswith("video/")


def _project_ffmpeg_path(project_root: Path | None = None) -> Path | None:
    root = Path(project_root or Path.cwd())
    candidates = (
        root / "third_party" / "jdownloader" / "runtime" / "JDownloader 2" / "tools" / "Windows" / "ffmpeg" / "x64" / "ffmpeg.exe",
        root / "tools" / "ffmpeg" / "ffmpeg.exe",
        root / "ffmpeg.exe",
    )
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


def resolve_video_tile_hover_ffmpeg(project_root: Path | str | None = None) -> str:
    """Return the ffmpeg executable used for in-tile hover playback.

    Prefer the bundled JDownloader ffmpeg if present so the hover feature does
    not depend on a global PATH entry.  Fall back to FFMPEG_BINARY / ffmpeg.
    """
    env_value = os.environ.get("FFMPEG_BINARY", "").strip()
    if env_value:
        return env_value
    bundled = _project_ffmpeg_path(Path(project_root) if project_root else None)
    if bundled is not None:
        return str(bundled)
    return shutil.which("ffmpeg") or "ffmpeg"


def build_ffmpeg_tile_hover_stream_command(
    url: str,
    *,
    ffmpeg_path: str = "",
    frame_size: tuple[int, int] = (168, 96),
    duration_seconds: float = 6.0,
    fps: int = 20,
    seek_seconds: float = 0.0,
    user_agent: str = "Mozilla/5.0 YTCE tile video hover",
    referer: str = "",
    project_root: Path | str | None = None,
) -> list[str]:
    """Build an ffmpeg raw-video command for real opening-segment tile playback."""
    width = max(96, int(frame_size[0] or 168))
    height = max(54, int(frame_size[1] or 96))
    fps_value = max(6, min(30, int(fps or 20)))
    executable = ffmpeg_path or resolve_video_tile_hover_ffmpeg(project_root)
    command = [
        executable,
        "-hide_banner",
        "-loglevel",
        "error",
        "-nostdin",
        "-fflags",
        "nobuffer",
        "-flags",
        "low_delay",
        "-probesize",
        "32768",
        "-analyzeduration",
        "150000",
    ]
    seek = max(0.0, float(seek_seconds or 0.0))
    if seek > 0:
        command.extend(["-ss", f"{seek:.3f}"])
    header_lines: list[str] = []
    if user_agent:
        command.extend(["-user_agent", user_agent])
        header_lines.append(f"User-Agent: {user_agent}")
    if referer:
        header_lines.append(f"Referer: {referer}")
    if header_lines:
        command.extend(["-headers", "\r\n".join(header_lines) + "\r\n"])
    scale_filter = (
        f"fps={fps_value},"
        f"scale={width}:{height}:force_original_aspect_ratio=decrease:flags=bilinear,"
        f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,"
        "setsar=1"
    )
    command.extend(
        [
            "-i",
            str(url or ""),
            "-t",
            f"{max(0.5, min(6.0, float(duration_seconds or 6.0))):.3f}",
            "-an",
            "-vf",
            scale_filter,
            "-f",
            "rawvideo",
            "-pix_fmt",
            "rgba",
            "-",
        ]
    )
    return command


def _read_exact(pipe: object, size: int, deadline: float) -> bytes:
    chunks: list[bytes] = []
    remaining = size
    while remaining > 0 and time.monotonic() < deadline:
        data = pipe.read(remaining)  # type: ignore[attr-defined]
        if not data:
            break
        chunks.append(data)
        remaining -= len(data)
    return b"".join(chunks)


def extract_video_tile_hover_stream_frames_pil(
    url: str,
    *,
    timeout: float = 8.5,
    first_frame_timeout: float = 1.6,
    frame_size: tuple[int, int] = (168, 96),
    duration_seconds: float = 6.0,
    fps: int = 20,
    seek_seconds: float = 0.0,
    referer: str = "",
    max_frames: int | None = None,
    project_root: Path | str | None = None,
) -> tuple[Image.Image, ...]:
    """Decode the opening segment of a direct video URL into tile-sized frames.

    This is intended for Tk hover playback: the UI caches the returned frames by
    URL and cycles them on pointer enter.  It uses real contiguous decoded video
    frames rather than sparse screenshots/GIF captures.
    """
    text = str(url or "").strip()
    if not text:
        raise RuntimeError("No video URL was supplied for tile hover playback.")
    if not can_stream_video_tile_hover(text):
        raise RuntimeError("URL is not a direct video suitable for tile hover playback.")
    width = max(96, int(frame_size[0] or 168))
    height = max(54, int(frame_size[1] or 96))
    fps_value = max(6, min(30, int(fps or 20)))
    limit = max(2, min(360, int(max_frames or round(max(0.5, float(duration_seconds or 6.0)) * fps_value))))
    frame_bytes = width * height * 4
    command = build_ffmpeg_tile_hover_stream_command(
        text,
        frame_size=(width, height),
        duration_seconds=duration_seconds,
        fps=fps_value,
        seek_seconds=seek_seconds,
        referer=referer,
        project_root=project_root,
    )
    process: subprocess.Popen[bytes] | None = None
    frames: list[Image.Image] = []
    start = time.monotonic()
    deadline = start + max(0.75, float(timeout or 8.5))
    first_deadline = start + max(0.5, min(float(timeout or 8.5), float(first_frame_timeout or 1.6)))
    try:
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.DEVNULL,
        )
        assert process.stdout is not None
        while len(frames) < limit and time.monotonic() < deadline:
            current_deadline = first_deadline if not frames else deadline
            raw = _read_exact(process.stdout, frame_bytes, current_deadline)
            if len(raw) != frame_bytes:
                break
            image = Image.frombytes("RGBA", (width, height), raw)
            frames.append(image.copy())
        try:
            process.kill()
        except Exception:
            pass
        try:
            _, stderr = process.communicate(timeout=0.35)
        except Exception:
            stderr = b""
    except FileNotFoundError as error:
        raise RuntimeError("ffmpeg was not found for video tile hover playback.") from error
    finally:
        if process is not None:
            try:
                process.kill()
            except Exception:
                pass
    if len(frames) < 2:
        stderr_text = ""
        try:
            stderr_text = stderr.decode("utf-8", errors="replace").strip()  # type: ignore[name-defined]
        except Exception:
            stderr_text = ""
        raise RuntimeError(stderr_text or "ffmpeg did not produce enough tile hover video frames.")
    return tuple(frames)


__all__ = [
    "build_ffmpeg_tile_hover_stream_command",
    "can_stream_video_tile_hover",
    "extract_video_tile_hover_stream_frames_pil",
    "resolve_video_tile_hover_ffmpeg",
    "video_tile_hover_stream_cache_key",
]
