from __future__ import annotations

import shutil
from pathlib import Path

from webpage_video_hover_stream_backend import (
    build_ffmpeg_tile_hover_stream_command,
    can_stream_video_tile_hover,
    resolve_video_tile_hover_ffmpeg,
    video_tile_hover_stream_cache_key,
)


def test_tile_hover_accepts_direct_video_and_rejects_streams() -> None:
    assert can_stream_video_tile_hover("https://videos.example.test/path/1024x576_MP4_clip.mp4")
    assert can_stream_video_tile_hover("https://cdn.example.test/video", mime_type="video/mp4")
    assert not can_stream_video_tile_hover("https://cdn.example.test/master.m3u8")
    assert not can_stream_video_tile_hover("javascript:alert(1)")


def test_tile_hover_command_uses_contiguous_fixed_size_raw_frames() -> None:
    command = build_ffmpeg_tile_hover_stream_command(
        "https://videos.example.test/path/clip.mp4",
        ffmpeg_path="ffmpeg-custom",
        frame_size=(168, 96),
        duration_seconds=6.0,
        fps=20,
        referer="https://example.test/article",
    )
    joined = " ".join(command)
    assert command[0] == "ffmpeg-custom"
    assert "-fflags" in command
    assert "nobuffer" in command
    assert "-t" in command
    assert "6.000" in command
    assert "fps=20" in joined
    assert "scale=168:96:force_original_aspect_ratio=decrease" in joined
    assert "pad=168:96" in joined
    assert "-f" in command
    assert "rawvideo" in command
    assert "-pix_fmt" in command
    assert "rgba" in command
    assert "Referer: https://example.test/article" in joined


def test_tile_hover_command_caps_to_vdh_length_loop_segment() -> None:
    command = build_ffmpeg_tile_hover_stream_command(
        "https://videos.example.test/path/1024x576_MP4_clip.mp4",
        ffmpeg_path="ffmpeg-test",
        duration_seconds=99.0,
        fps=20,
    )
    assert "6.000" in command


def test_tile_hover_cache_key_is_stable_and_namespaced() -> None:
    one = video_tile_hover_stream_cache_key("https://example.test/video.mp4")
    two = video_tile_hover_stream_cache_key("https://example.test/video.mp4")
    other = video_tile_hover_stream_cache_key("https://example.test/other.mp4")
    assert one == two
    assert one != other
    assert one.startswith("video-hover-stream:")


def test_resolve_ffmpeg_prefers_bundled_jdownloader_binary(tmp_path: Path, monkeypatch=None) -> None:
    shutil.rmtree(tmp_path, ignore_errors=True)
    bundled = tmp_path / "third_party" / "jdownloader" / "runtime" / "JDownloader 2" / "tools" / "Windows" / "ffmpeg" / "x64" / "ffmpeg.exe"
    bundled.parent.mkdir(parents=True)
    bundled.write_bytes(b"")
    if monkeypatch is not None:
        monkeypatch.delenv("FFMPEG_BINARY", raising=False)
    assert resolve_video_tile_hover_ffmpeg(tmp_path) == str(bundled)


if __name__ == "__main__":
    test_tile_hover_accepts_direct_video_and_rejects_streams()
    test_tile_hover_command_uses_contiguous_fixed_size_raw_frames()
    test_tile_hover_command_caps_to_vdh_length_loop_segment()
    test_tile_hover_cache_key_is_stable_and_namespaced()
    test_resolve_ffmpeg_prefers_bundled_jdownloader_binary(Path(__file__).resolve().parent / "_tmp_ffmpeg_probe")
    print("webpage_video_hover_stream_backend_test OK")
