from __future__ import annotations

import inspect

from webpage_video_preview_backend import (
    _browser_hover_preview_sample_times,
    build_browser_video_hover_preview_document,
    build_ffmpeg_video_frame_preview_command,
    build_ffmpeg_video_hover_preview_command,
    can_generate_video_frame_preview,
    can_generate_video_hover_preview,
    extract_video_hover_preview_frames_pil,
    video_frame_preview_cache_key,
    video_hover_preview_cache_key,
)


def test_can_generate_frame_preview_only_for_direct_video_files() -> None:
    assert can_generate_video_frame_preview("https://cdn.example.com/video.mp4")
    assert can_generate_video_frame_preview("https://cdn.example.com/video.webm")
    assert can_generate_video_frame_preview("https://cdn.example.com/media.bin", mime_type="video/mp4")
    assert not can_generate_video_frame_preview("https://cdn.example.com/master.m3u8")
    assert not can_generate_video_frame_preview("https://cdn.example.com/manifest.mpd")
    assert not can_generate_video_frame_preview("https://player.example.com/embed/123")
    assert not can_generate_video_frame_preview("https://cdn.example.com/audio.mp3", mime_type="audio/mpeg")


def test_hover_preview_uses_same_direct_video_safety_gate() -> None:
    assert can_generate_video_hover_preview("https://cdn.example.com/video.mp4")
    assert can_generate_video_hover_preview("https://cdn.example.com/media.bin", mime_type="video/mp4")
    assert not can_generate_video_hover_preview("https://cdn.example.com/master.m3u8")
    assert not can_generate_video_hover_preview("https://cdn.example.com/manifest.mpd")
    assert not can_generate_video_hover_preview("https://player.example.com/embed/123")


def test_ffmpeg_command_is_single_frame_pipe_and_header_safe() -> None:
    command = build_ffmpeg_video_frame_preview_command(
        "https://videos.example.com/clip.mp4",
        seek_seconds=1.25,
        referer="https://example.com/article",
    )
    assert command[0] == "ffmpeg"
    assert "-frames:v" in command
    assert "1" in command
    assert "image2pipe" in command
    assert "-vcodec" in command
    assert "mjpeg" in command
    assert "https://videos.example.com/clip.mp4" in command
    assert any("Referer: https://example.com/article" in part for part in command)


def test_ffmpeg_hover_command_outputs_short_gif_pipe() -> None:
    command = build_ffmpeg_video_hover_preview_command(
        "https://videos.example.com/clip.mp4",
        seek_seconds=0.5,
        duration_seconds=1.5,
        fps=4,
        referer="https://example.com/article",
    )
    assert command[0] == "ffmpeg"
    assert "-t" in command
    assert "fps=4" in " ".join(command)
    assert "-f" in command
    assert "gif" in command
    assert command[-1] == "-"
    assert "https://videos.example.com/clip.mp4" in command
    assert any("Referer: https://example.com/article" in part for part in command)


def test_hover_preview_default_window_samples_more_than_a_tiny_static_intro() -> None:
    signature = inspect.signature(extract_video_hover_preview_frames_pil)
    assert signature.parameters["seek_seconds"].default == 0.0
    assert signature.parameters["duration_seconds"].default == 12.0
    assert signature.parameters["fps"].default == 2
    assert signature.parameters["max_frames"].default == 24


def test_browser_hover_preview_document_uses_muted_preloaded_video() -> None:
    html = build_browser_video_hover_preview_document(
        "https://videos.example.com/clip.mp4?x=1&y=2",
        poster_url="https://images.example.com/poster.jpg",
    )
    assert '<video id="previewVideo"' in html
    assert 'preload="auto"' in html
    assert 'muted playsinline' in html
    assert 'crossorigin="anonymous"' in html
    assert 'https://videos.example.com/clip.mp4?x=1&amp;y=2' in html
    assert 'poster="https://images.example.com/poster.jpg"' in html


def test_browser_hover_preview_samples_early_window() -> None:
    sample_times = _browser_hover_preview_sample_times(duration_seconds=30.0, sample_count=32)
    assert sample_times[0] == 0.0
    assert len(sample_times) == 32
    assert sample_times[-1] == 30.0
    assert all(earlier <= later for earlier, later in zip(sample_times, sample_times[1:]))


def test_cache_key_is_stable_and_separate_from_image_url_cache() -> None:
    first = video_frame_preview_cache_key("https://videos.example.com/clip.mp4")
    second = video_frame_preview_cache_key("https://videos.example.com/clip.mp4")
    other = video_frame_preview_cache_key("https://videos.example.com/other.mp4")
    hover = video_hover_preview_cache_key("https://videos.example.com/clip.mp4")
    assert first == second
    assert first != other
    assert first.startswith("video-frame:")
    assert hover.startswith("video-hover:")
    assert first != hover


def main() -> None:
    test_can_generate_frame_preview_only_for_direct_video_files()
    test_hover_preview_uses_same_direct_video_safety_gate()
    test_ffmpeg_command_is_single_frame_pipe_and_header_safe()
    test_ffmpeg_hover_command_outputs_short_gif_pipe()
    test_hover_preview_default_window_samples_more_than_a_tiny_static_intro()
    test_browser_hover_preview_document_uses_muted_preloaded_video()
    test_browser_hover_preview_samples_early_window()
    test_cache_key_is_stable_and_separate_from_image_url_cache()
    print("webpage_video_preview_backend_test OK")


if __name__ == "__main__":
    main()
