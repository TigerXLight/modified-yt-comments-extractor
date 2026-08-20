from __future__ import annotations

import hashlib
from html import escape as _html_escape
from pathlib import Path
import tempfile
import threading
import time
import webbrowser
from urllib.parse import urlparse


_LIVE_PREVIEWABLE_VIDEO_EXTENSIONS = {
    ".mp4",
    ".m4v",
    ".webm",
    ".mov",
    ".mkv",
    ".avi",
    ".flv",
    ".3gp",
}
_LIVE_PREVIEW_STREAM_EXTENSIONS = {
    ".m3u8",
    ".mpd",
    ".f4m",
    ".ism/manifest",
}


def _path_extension_from_url(url: str) -> str:
    parsed = urlparse(str(url or ""))
    path = parsed.path.lower()
    for suffix in sorted((*_LIVE_PREVIEW_STREAM_EXTENSIONS, *_LIVE_PREVIEWABLE_VIDEO_EXTENSIONS), key=len, reverse=True):
        if path.endswith(suffix):
            return suffix
    return Path(path).suffix.lower()


def can_open_browser_video_live_preview(
    url: str,
    *,
    extension: str = "",
    mime_type: str = "",
) -> bool:
    """Return whether a media candidate is suitable for live browser playback.

    V78P deliberately keeps this to direct video files first. HLS/DASH/embed
    candidates stay on the existing poster/download-review path until a later
    route-specific player handles fragmented manifests and headers.
    """
    text = str(url or "").strip()
    if not text:
        return False
    lower = text.lower()
    if lower.startswith(("javascript:", "data:", "mailto:")):
        return False
    ext = str(extension or "").lower() or _path_extension_from_url(text)
    mime = str(mime_type or "").lower()
    if ext in _LIVE_PREVIEW_STREAM_EXTENSIONS or any(token in lower for token in (".m3u8", ".mpd", "/manifest")):
        return False
    if ext in _LIVE_PREVIEWABLE_VIDEO_EXTENSIONS:
        return True
    return mime.startswith("video/")


def _preview_file_path(media_url: str) -> Path:
    digest = hashlib.sha1(str(media_url or "").encode("utf-8", "replace")).hexdigest()[:16]
    root = Path(tempfile.gettempdir()) / "ytce_live_video_preview"
    root.mkdir(parents=True, exist_ok=True)
    return root / f"ytce_live_video_preview_{digest}.html"


def build_browser_video_live_preview_html(
    media_url: str,
    *,
    title: str = "Video live preview",
    poster_url: str = "",
) -> str:
    """Build a tiny browser player page for stable real-media preview playback."""
    safe_title = _html_escape(str(title or "Video live preview"), quote=True)
    safe_url = _html_escape(str(media_url or ""), quote=True)
    safe_poster = _html_escape(str(poster_url or ""), quote=True)
    poster_attr = f' poster="{safe_poster}"' if safe_poster else ""
    return f'''<!doctype html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{safe_title}</title>
<style>
  :root {{ color-scheme: dark; }}
  html, body {{ margin: 0; height: 100%; background: #0b0f12; color: #eef3f6; font-family: system-ui, -apple-system, Segoe UI, sans-serif; }}
  body {{ display: flex; flex-direction: column; }}
  header {{ padding: 10px 12px; font-size: 13px; line-height: 1.35; background: #111820; border-bottom: 1px solid #26323b; }}
  header strong {{ display: block; overflow: hidden; white-space: nowrap; text-overflow: ellipsis; }}
  header span {{ color: #9facb6; font-size: 11px; overflow-wrap: anywhere; }}
  main {{ flex: 1; min-height: 0; display: flex; align-items: center; justify-content: center; padding: 10px; }}
  video {{ width: 100%; height: 100%; max-height: calc(100vh - 74px); background: #000; border-radius: 8px; object-fit: contain; }}
  .hint {{ position: fixed; right: 12px; bottom: 10px; color: #a9b6bf; font-size: 11px; opacity: .85; }}
</style>
</head>
<body>
<header><strong>{safe_title}</strong><span>{safe_url}</span></header>
<main>
  <video id="player" src="{safe_url}"{poster_attr} controls autoplay muted loop playsinline preload="auto"></video>
</main>
<div class="hint">Muted live browser preview. Use controls for sound/scrub.</div>
<script>
(function() {{
  const player = document.getElementById('player');
  player.muted = true;
  player.volume = 0;
  const tryPlay = () => player.play().catch(() => {{}});
  player.addEventListener('canplay', tryPlay, {{ once: true }});
  player.addEventListener('loadeddata', tryPlay, {{ once: true }});
  setTimeout(tryPlay, 150);
  window.addEventListener('keydown', (event) => {{
    if (event.key === ' ') {{ event.preventDefault(); player.paused ? player.play() : player.pause(); }}
    if (event.key === 'ArrowLeft') {{ player.currentTime = Math.max(0, player.currentTime - 5); }}
    if (event.key === 'ArrowRight') {{ player.currentTime = Math.min(player.duration || Infinity, player.currentTime + 5); }}
    if (event.key.toLowerCase() === 'm') {{ player.muted = !player.muted; }}
  }});
}})();
</script>
</body>
</html>
'''


def write_browser_video_live_preview_file(
    media_url: str,
    *,
    title: str = "Video live preview",
    poster_url: str = "",
) -> Path:
    path = _preview_file_path(media_url)
    path.write_text(
        build_browser_video_live_preview_html(media_url, title=title, poster_url=poster_url),
        encoding="utf-8",
        newline="\n",
    )
    return path


def _open_with_playwright_window(path: Path, *, referer: str = "", user_agent: str = "Mozilla/5.0 YTCE live video preview") -> bool:
    try:
        from playwright.sync_api import sync_playwright  # type: ignore
    except Exception:
        return False

    def runner() -> None:
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(
                    headless=False,
                    args=["--window-size=760,520", "--autoplay-policy=no-user-gesture-required"],
                )
                headers = {"User-Agent": user_agent}
                if referer:
                    headers["Referer"] = referer
                context = browser.new_context(
                    viewport={"width": 760, "height": 520},
                    user_agent=user_agent,
                    extra_http_headers=headers,
                )
                page = context.new_page()
                page.goto(path.as_uri(), wait_until="domcontentloaded", timeout=12000)
                try:
                    page.evaluate("""() => {
                      const video = document.querySelector('video');
                      if (video) { video.muted = true; video.volume = 0; video.play().catch(() => {}); }
                    }""")
                except Exception:
                    pass
                while True:
                    try:
                        if page.is_closed():
                            break
                        page.wait_for_timeout(500)
                    except Exception:
                        break
                try:
                    browser.close()
                except Exception:
                    pass
        except Exception:
            try:
                webbrowser.open(path.as_uri(), new=1, autoraise=True)
            except Exception:
                pass

    threading.Thread(target=runner, daemon=True).start()
    return True


def open_browser_video_live_preview(
    media_url: str,
    *,
    title: str = "Video live preview",
    referer: str = "",
    poster_url: str = "",
    prefer_playwright: bool = True,
) -> Path:
    """Open a real browser/player preview without blocking the Tk UI.

    Returns the generated local HTML player path. A Playwright window is used
    when available because it is closer to Video DownloadHelper's browser-side
    behaviour and can carry a referer header. The fallback opens the same HTML
    player in the system default browser.
    """
    path = write_browser_video_live_preview_file(media_url, title=title, poster_url=poster_url)
    opened_with_playwright = False
    if prefer_playwright:
        opened_with_playwright = _open_with_playwright_window(path, referer=referer)
    if not opened_with_playwright:
        def opener() -> None:
            time.sleep(0.05)
            webbrowser.open(path.as_uri(), new=1, autoraise=True)
        threading.Thread(target=opener, daemon=True).start()
    return path
