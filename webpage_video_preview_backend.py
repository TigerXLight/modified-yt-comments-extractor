from __future__ import annotations

import hashlib
import subprocess
from io import BytesIO
from pathlib import Path
from urllib.parse import urlparse

from PIL import Image


_PREVIEWABLE_VIDEO_EXTENSIONS = {
    ".mp4",
    ".m4v",
    ".webm",
    ".mov",
    ".mkv",
    ".avi",
    ".flv",
    ".3gp",
}
_NON_FRAME_STREAM_EXTENSIONS = {
    ".m3u8",
    ".mpd",
    ".f4m",
    ".ism/manifest",
}


def video_frame_preview_cache_key(url: str) -> str:
    """Stable cache key for a remote/local video frame preview."""
    digest = hashlib.sha1(str(url or "").encode("utf-8", "replace")).hexdigest()
    return f"video-frame:{digest}"


def _path_extension_from_url(url: str) -> str:
    parsed = urlparse(str(url or ""))
    path = parsed.path.lower()
    for suffix in sorted((*_NON_FRAME_STREAM_EXTENSIONS, *_PREVIEWABLE_VIDEO_EXTENSIONS), key=len, reverse=True):
        if path.endswith(suffix):
            return suffix
    return Path(path).suffix.lower()


def can_generate_video_frame_preview(
    url: str,
    *,
    extension: str = "",
    mime_type: str = "",
) -> bool:
    """Return whether a candidate is safe/cheap enough for a first-frame preview.

    V78I intentionally limits first-frame extraction to direct video files. HLS,
    DASH, and embedded player URLs should keep their poster/thumbnail path or the
    PLAY/VID badge until a later route-specific preview pass exists.
    """
    text = str(url or "").strip()
    if not text:
        return False
    lower = text.lower()
    if lower.startswith(("javascript:", "data:", "mailto:")):
        return False
    ext = str(extension or "").lower() or _path_extension_from_url(text)
    mime = str(mime_type or "").lower()
    if ext in _NON_FRAME_STREAM_EXTENSIONS or any(token in lower for token in (".m3u8", ".mpd", "/manifest")):
        return False
    if ext in _PREVIEWABLE_VIDEO_EXTENSIONS:
        return True
    return mime.startswith("video/")


def build_ffmpeg_video_frame_preview_command(
    url: str,
    *,
    seek_seconds: float = 1.0,
    user_agent: str = "Mozilla/5.0 YTCE video preview",
    referer: str = "",
) -> list[str]:
    """Build an ffmpeg command that emits one JPEG frame on stdout."""
    command = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-nostdin",
        "-ss",
        f"{max(0.0, float(seek_seconds)):.3f}",
    ]
    header_lines: list[str] = []
    if user_agent:
        command.extend(["-user_agent", user_agent])
        header_lines.append(f"User-Agent: {user_agent}")
    if referer:
        header_lines.append(f"Referer: {referer}")
    if header_lines:
        command.extend(["-headers", "\r\n".join(header_lines) + "\r\n"])
    command.extend(
        [
            "-i",
            str(url or ""),
            "-frames:v",
            "1",
            "-vf",
            "scale='min(360,iw)':-2",
            "-f",
            "image2pipe",
            "-vcodec",
            "mjpeg",
            "-",
        ]
    )
    return command


def extract_video_frame_preview_pil(
    url: str,
    *,
    timeout: float = 2.5,
    seek_seconds: float = 1.0,
    referer: str = "",
    max_size: tuple[int, int] = (168, 128),
) -> Image.Image:
    """Extract a small first-frame preview with ffmpeg and return a PIL image.

    The caller should use this sparingly and cache the result.  It is intended
    for direct MP4/WebM/etc. candidates whose page poster/thumbnail is missing,
    so the Video & Audio picker can distinguish duplicate-looking resources.
    """
    command = build_ffmpeg_video_frame_preview_command(
        url,
        seek_seconds=seek_seconds,
        referer=referer,
    )
    try:
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=max(0.5, float(timeout)),
        )
    except FileNotFoundError as error:
        raise RuntimeError("ffmpeg was not found for video preview frame extraction.") from error
    except subprocess.TimeoutExpired as error:
        raise RuntimeError("ffmpeg timed out while extracting a video preview frame.") from error
    if result.returncode != 0 or not result.stdout:
        stderr_text = result.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(stderr_text or "ffmpeg did not produce a video preview frame.")
    image = Image.open(BytesIO(result.stdout))
    image = image.convert("RGBA")
    image.thumbnail(max_size, Image.LANCZOS)
    if min(image.size) < 24:
        raise RuntimeError("Extracted video preview frame is too small.")
    return image.copy()


__all__ = [
    "build_ffmpeg_video_frame_preview_command",
    "can_generate_video_frame_preview",
    "extract_video_frame_preview_pil",
    "video_frame_preview_cache_key",
]
