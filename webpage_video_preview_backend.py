from __future__ import annotations

import hashlib
import subprocess
from io import BytesIO
from html import escape as _html_escape
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



def _browser_hover_preview_sample_times(
    *,
    duration_seconds: float = 3.0,
    sample_count: int = 16,
) -> tuple[float, ...]:
    """Return early sample times for browser-backed hover previews.

    ReactHoverVideoPlayer and yt-hover style previews feel instant because the
    video element is preloaded before hover and the hover handler only switches
    state.  Our Tk grid cannot embed that player directly, so V78L samples the
    same early playback window ahead of hover and caches the frames.
    """
    count = max(2, min(18, int(sample_count)))
    duration = max(0.6, float(duration_seconds))
    if count == 2:
        return (0.0, min(duration, 1.0))
    step = duration / float(count - 1)
    return tuple(round(min(duration, max(0.0, index * step)), 3) for index in range(count))


def build_browser_video_hover_preview_document(
    url: str,
    *,
    poster_url: str = "",
) -> str:
    """Build the tiny document used by Playwright to preload a video element.

    This mirrors the browser-hover references more closely than ffmpeg-on-hover:
    preload a muted video element first, then capture already-decoded frames for
    the Tk hover animation cache.
    """
    escaped_url = _html_escape(str(url or ""), quote=True)
    escaped_poster = _html_escape(str(poster_url or ""), quote=True)
    poster_attr = f' poster="{escaped_poster}"' if escaped_poster else ""
    return f"""<!doctype html>
<html>
<head>
<meta charset=\"utf-8\">
<style>
  html, body {{ margin: 0; width: 100%; height: 100%; background: #111; overflow: hidden; }}
  video {{ width: 100%; height: 100%; object-fit: contain; background: #111; }}
</style>
</head>
<body>
<video id=\"previewVideo\" src=\"{escaped_url}\"{poster_attr} muted playsinline preload=\"auto\" crossorigin=\"anonymous\"></video>
<script>
  const video = document.getElementById('previewVideo');
  video.muted = true;
  video.volume = 0;
</script>
</body>
</html>"""


def extract_video_hover_preview_frames_pil_browser(
    url: str,
    *,
    timeout: float = 7.5,
    referer: str = "",
    poster_url: str = "",
    max_size: tuple[int, int] = (168, 128),
    duration_seconds: float = 3.0,
    sample_count: int = 16,
    frame_delay_ms: int = 75,
    browser_executable_path: str | None = None,
) -> tuple[Image.Image, ...]:
    """Extract hover-preview frames using a real browser video element.

    This is the V78L path inspired by ReactHoverVideoPlayer/yt-hover: browser
    media decoding happens before hover; the Tk tile receives cached frames that
    can cycle immediately.  Playwright is optional at runtime.  Callers should
    catch RuntimeError and fall back to ffmpeg when unavailable.
    """
    text = str(url or "").strip()
    if not text:
        raise RuntimeError("No video URL was supplied for browser hover preview.")
    try:
        from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
        from playwright.sync_api import sync_playwright
    except Exception as error:
        raise RuntimeError(f"Playwright unavailable for browser video hover preview: {type(error).__name__}: {error}") from error

    timeout_ms = int(max(1200.0, float(timeout) * 1000.0))
    frames: list[Image.Image] = []
    sample_times = _browser_hover_preview_sample_times(
        duration_seconds=duration_seconds,
        sample_count=sample_count,
    )
    try:
        with sync_playwright() as playwright:
            launch_kwargs: dict[str, object] = {"headless": True}
            if browser_executable_path:
                launch_kwargs["executable_path"] = browser_executable_path
            browser = playwright.chromium.launch(**launch_kwargs)
            headers: dict[str, str] = {}
            if referer:
                headers["Referer"] = str(referer)
            context_kwargs: dict[str, object] = {
                "viewport": {"width": max_size[0] * 2, "height": max_size[1] * 2},
                "ignore_https_errors": True,
                "user_agent": "Mozilla/5.0 YTCE browser video hover preview",
            }
            if headers:
                context_kwargs["extra_http_headers"] = headers
            context = browser.new_context(**context_kwargs)
            page = context.new_page()
            page.set_content(build_browser_video_hover_preview_document(text, poster_url=poster_url), wait_until="domcontentloaded")
            locator = page.locator("#previewVideo")
            try:
                locator.evaluate(
                    """async (video) => {
                      video.muted = true;
                      video.volume = 0;
                      video.preload = 'auto';
                      video.load();
                      if (video.readyState >= 2) return true;
                      await new Promise((resolve, reject) => {
                        const done = () => { cleanup(); resolve(true); };
                        const fail = () => { cleanup(); reject(new Error('video load error')); };
                        const cleanup = () => {
                          video.removeEventListener('loadeddata', done);
                          video.removeEventListener('canplay', done);
                          video.removeEventListener('error', fail);
                        };
                        video.addEventListener('loadeddata', done, { once: true });
                        video.addEventListener('canplay', done, { once: true });
                        video.addEventListener('error', fail, { once: true });
                      });
                      return true;
                    }""",
                    timeout=timeout_ms,
                )
            except PlaywrightTimeoutError:
                # Some CDNs do not report canplay quickly, but still paint the
                # first frame.  Continue to screenshot attempts below.
                pass
            def _capture_current_video_frame() -> bool:
                try:
                    png_bytes = locator.screenshot(type="png", timeout=max(800, min(timeout_ms, 2500)))
                    image = Image.open(BytesIO(png_bytes)).convert("RGBA")
                    image.thumbnail(max_size, Image.LANCZOS)
                    if min(image.size) >= 24:
                        frames.append(image.copy())
                        return True
                except Exception:
                    return False
                return False

            requested_frames = max(2, min(18, int(sample_count)))
            delay_ms = max(35, min(220, int(frame_delay_ms)))

            # V78M smooth path: let the browser's media decoder play naturally
            # and screenshot a short burst.  This is closer to real hover-video
            # playback than V78L's sparse seek-to-sample slideshow.
            try:
                locator.evaluate(
                    """async (video) => {
                      video.muted = true;
                      video.volume = 0;
                      const seekToStart = async () => {
                        if ((video.currentTime || 0) <= 0.08) return true;
                        await new Promise((resolve) => {
                          let finished = false;
                          const cleanup = () => video.removeEventListener('seeked', done);
                          const done = () => { if (!finished) { finished = true; cleanup(); resolve(true); } };
                          video.addEventListener('seeked', done, { once: true });
                          try { video.currentTime = 0; } catch (_err) { done(); }
                          setTimeout(done, 450);
                        });
                        return true;
                      };
                      await seekToStart();
                      try { await video.play(); } catch (_err) {}
                      return true;
                    }""",
                    timeout=timeout_ms,
                )
                for _index in range(requested_frames):
                    try:
                        page.wait_for_timeout(delay_ms)
                    except Exception:
                        pass
                    _capture_current_video_frame()
                try:
                    locator.evaluate("video => { try { video.pause(); } catch (_err) {} return true; }", timeout=900)
                except Exception:
                    pass
            except Exception:
                pass

            unique_digests_so_far = {hashlib.sha1(frame.tobytes()).hexdigest() + str(frame.size) for frame in frames}
            if len(frames) < 2 or len(unique_digests_so_far) < 2:
                frames.clear()
                for sample_time in sample_times:
                    try:
                        locator.evaluate(
                            """async (video, seconds) => {
                              video.muted = true;
                              video.volume = 0;
                              const duration = Number.isFinite(video.duration) ? video.duration : 0;
                              const target = duration ? Math.min(Math.max(0, seconds), Math.max(0, duration - 0.05)) : Math.max(0, seconds);
                              if (Math.abs((video.currentTime || 0) - target) > 0.05) {
                                await new Promise((resolve) => {
                                  let finished = false;
                                  const cleanup = () => video.removeEventListener('seeked', done);
                                  const done = () => { if (!finished) { finished = true; cleanup(); resolve(true); } };
                                  video.addEventListener('seeked', done, { once: true });
                                  try { video.currentTime = target; } catch (_err) { done(); }
                                  setTimeout(done, 450);
                                });
                              }
                              try { await video.play(); } catch (_err) {}
                              await new Promise((resolve) => setTimeout(resolve, 80));
                              video.pause();
                              return true;
                            }""",
                            [sample_time],
                            timeout=timeout_ms,
                        )
                    except Exception:
                        pass
                    _capture_current_video_frame()
            try:
                context.close()
                browser.close()
            except Exception:
                pass
    except Exception as error:
        raise RuntimeError(f"Browser video hover preview failed: {type(error).__name__}: {error}") from error

    # Avoid returning a visually static animation if every screenshot is the
    # exact same frame/poster.
    unique_digests = {hashlib.sha1(frame.tobytes()).hexdigest() + str(frame.size) for frame in frames}
    if len(frames) < 2 or len(unique_digests) < 2:
        raise RuntimeError("Browser video hover preview did not produce multiple distinct frames.")
    return tuple(frames[: max(2, min(18, int(sample_count)))])

def extract_video_hover_preview_frames_pil(
    url: str,
    *,
    timeout: float = 5.5,
    seek_seconds: float = 0.0,
    duration_seconds: float = 3.0,
    fps: int = 8,
    referer: str = "",
    max_size: tuple[int, int] = (168, 128),
    max_frames: int = 16,
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
    "build_browser_video_hover_preview_document",
    "extract_video_hover_preview_frames_pil_browser",
    "extract_video_hover_preview_frames_pil",
    "_browser_hover_preview_sample_times",
    "video_frame_preview_cache_key",
    "video_hover_preview_cache_key",
]
