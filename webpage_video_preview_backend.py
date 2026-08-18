from __future__ import annotations

import hashlib
import subprocess
from io import BytesIO
from pathlib import Path
from urllib.parse import urlparse

from PIL import Image, ImageSequence


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


def video_hover_preview_cache_key(url: str) -> str:
    """Stable cache key for a remote/local animated hover preview."""
    digest = hashlib.sha1(str(url or "").encode("utf-8", "replace")).hexdigest()
    return f"video-hover:{digest}"


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


def can_generate_video_hover_preview(
    url: str,
    *,
    extension: str = "",
    mime_type: str = "",
) -> bool:
    """Return whether the tile can attempt a short animated hover preview.

    The hover preview deliberately shares the V78I direct-video safety gate.  It
    avoids HLS/DASH/embed/player URLs because those can be slow, fragmented, or
    require route-specific headers.  Those routes should continue showing poster
    thumbnails until a later specialized preview pass exists.
    """
    return can_generate_video_frame_preview(url, extension=extension, mime_type=mime_type)


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


def build_ffmpeg_video_hover_preview_command(
    url: str,
    *,
    seek_seconds: float = 0.35,
    duration_seconds: float = 6.0,
    fps: int = 3,
    user_agent: str = "Mozilla/5.0 YTCE video preview",
    referer: str = "",
) -> list[str]:
    """Build an ffmpeg command that emits a tiny animated GIF on stdout."""
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
            "-t",
            f"{max(0.25, float(duration_seconds)):.3f}",
            "-i",
            str(url or ""),
            "-vf",
            f"fps={max(1, int(fps))},scale='min(300,iw)':-2:flags=lanczos",
            "-loop",
            "0",
            "-f",
            "gif",
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


def extract_video_hover_preview_frames_pil(
    url: str,
    *,
    timeout: float = 5.5,
    seek_seconds: float = 0.0,
    duration_seconds: float = 6.0,
    fps: int = 3,
    referer: str = "",
    max_size: tuple[int, int] = (168, 128),
    max_frames: int = 10,
) -> tuple[Image.Image, ...]:
    """Extract a short hover-preview GIF and return small PIL frames.

    This gives the Video & Audio dialog a Video DownloadHelper-style moving
    preview on hover for direct MP4/WebM/etc. candidates.  It samples a
    wider early window than the first-frame preview because news clips often
    have static intros.  Callers prefetch and cache these frames so hover
    playback can start immediately.
    """
    command = build_ffmpeg_video_hover_preview_command(
        url,
        seek_seconds=seek_seconds,
        duration_seconds=duration_seconds,
        fps=fps,
        referer=referer,
    )
    try:
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=max(0.75, float(timeout)),
        )
    except FileNotFoundError as error:
        raise RuntimeError("ffmpeg was not found for video hover preview extraction.") from error
    except subprocess.TimeoutExpired as error:
        raise RuntimeError("ffmpeg timed out while extracting a video hover preview.") from error
    if result.returncode != 0 or not result.stdout:
        stderr_text = result.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(stderr_text or "ffmpeg did not produce a video hover preview.")
    try:
        image = Image.open(BytesIO(result.stdout))
    except Exception as error:
        raise RuntimeError("ffmpeg hover preview output was not a readable GIF/image.") from error
    frames: list[Image.Image] = []
    for frame in ImageSequence.Iterator(image):
        next_frame = frame.convert("RGBA")
        next_frame.thumbnail(max_size, Image.LANCZOS)
        if min(next_frame.size) >= 24:
            frames.append(next_frame.copy())
        if len(frames) >= max(1, int(max_frames)):
            break
    if len(frames) < 2:
        raise RuntimeError("Video hover preview did not contain multiple usable frames.")
    return tuple(frames)


__all__ = [
    "build_ffmpeg_video_frame_preview_command",
    "build_ffmpeg_video_hover_preview_command",
    "can_generate_video_frame_preview",
    "can_generate_video_hover_preview",
    "extract_video_frame_preview_pil",
    "extract_video_hover_preview_frames_pil",
    "video_frame_preview_cache_key",
    "video_hover_preview_cache_key",
]
