from __future__ import annotations

from pathlib import Path

from webpage_video_live_preview_backend import (
    build_browser_video_live_preview_html,
    can_open_browser_video_live_preview,
    write_browser_video_live_preview_file,
)


def run_tests() -> None:
    assert can_open_browser_video_live_preview("https://example.test/video.mp4")
    assert can_open_browser_video_live_preview("https://example.test/no-ext", mime_type="video/mp4")
    assert not can_open_browser_video_live_preview("https://example.test/stream.m3u8")
    assert not can_open_browser_video_live_preview("javascript:alert(1)")
    html = build_browser_video_live_preview_html(
        "https://example.test/video.mp4?x=1&y=2",
        title="Clip <one>",
        poster_url="https://example.test/poster.jpg",
    )
    assert "<video" in html
    assert "controls autoplay muted loop" in html
    assert "Clip &lt;one&gt;" in html
    assert "x=1&amp;y=2" in html
    path = write_browser_video_live_preview_file("https://example.test/video.mp4", title="Clip")
    assert path.exists()
    assert path.suffix == ".html"
    assert Path(path).read_text(encoding="utf-8").startswith("<!doctype html>")


if __name__ == "__main__":
    run_tests()
    print("webpage_video_live_preview_backend_test OK")
