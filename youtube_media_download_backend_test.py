from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

from media_jdownloader_external_config import JDownloaderExternalConfigReport
from youtube_media_download_backend import (
    build_youtube_ytdlp_download_plan,
    resolve_ytdlp_command,
    normalize_media_source_url_arg,
    normalize_media_source_url_arg_strict,
    discover_youtube_media_with_ytdlp,
    youtube_format_selector_from_jdownloader,
    youtube_metadata_text_from_discovery,
    write_youtube_media_metadata_text,
)


def _fake_ytdlp_runner(command):
    data = {
        "title": "Example Video",
        "uploader": "Uploader",
        "duration": 12,
        "upload_date": "20240225",
        "view_count": 429265,
        "channel_follower_count": 13500,
        "description": "Line one.\nLine two.",
        "webpage_url": "https://www.youtube.com/watch?v=abc123",
        "formats": [
            {"format_id": "137", "ext": "mp4", "vcodec": "avc1", "acodec": "none", "height": 1080, "url": "https://example/video"},
            {"format_id": "140", "ext": "m4a", "vcodec": "none", "acodec": "mp4a", "abr": 128, "url": "https://example/audio"},
        ],
        "subtitles": {"en": []},
    }
    return subprocess.CompletedProcess(command, 0, stdout=json.dumps(data), stderr="")


def test_normalize_media_source_url_arg_strips_markdown_url() -> None:
    assert normalize_media_source_url_arg("[https://www.youtube.com/watch?v=abc123](https://www.youtube.com/watch?v=abc123)") == "https://www.youtube.com/watch?v=abc123"


def test_normalize_media_source_url_arg_handles_escaped_markdown_and_surrounding_text() -> None:
    assert normalize_media_source_url_arg("[https://www.youtube.com/watch?v=VIDEO\\_ID](https://www.youtube.com/watch?v=VIDEO_ID)") == "https://www.youtube.com/watch?v=VIDEO_ID"
    assert normalize_media_source_url_arg("URL: https://www.youtube.com/watch?v=abc123") == "https://www.youtube.com/watch?v=abc123"


def test_normalize_media_source_url_arg_strict_rejects_leftover_markdown() -> None:
    assert normalize_media_source_url_arg_strict("[https://www.youtube.com/watch?v=VIDEO\\_ID](https://www.youtube.com/watch?v=VIDEO_ID)") == "https://www.youtube.com/watch?v=VIDEO_ID"
    try:
        normalize_media_source_url_arg_strict("[not a url](not a url)")
    except ValueError as exc:
        assert "raw http" in str(exc) or "raw URL" in str(exc)
    else:
        raise AssertionError("invalid markdown should be rejected")



def test_normalize_media_source_url_arg_handles_cmd_markdown() -> None:
    pasted = r"[https://www.youtube.com/watch?v=VIDEO\_ID](https://www.youtube.com/watch?v=VIDEO_ID)"
    assert normalize_media_source_url_arg(pasted) == "https://www.youtube.com/watch?v=VIDEO_ID"
    assert normalize_media_source_url_arg_strict(pasted) == "https://www.youtube.com/watch?v=VIDEO_ID"



def test_normalize_media_source_url_arg_handles_nested_markdown_from_cmd() -> None:
    pasted = r"[[https://www.youtube.com/watch?v=VIDEO\_ID\](https://www.youtube.com/watch?v=VIDEO\_ID)](https://www.youtube.com/watch?v=VIDEO_ID]\(https://www.youtube.com/watch?v=VIDEO_ID\))"
    assert normalize_media_source_url_arg(pasted) == "https://www.youtube.com/watch?v=VIDEO_ID"
    assert normalize_media_source_url_arg_strict(pasted) == "https://www.youtube.com/watch?v=VIDEO_ID"


def test_discover_youtube_media_with_ytdlp_parses_formats() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        discovery = discover_youtube_media_with_ytdlp(
            "https://www.youtube.com/watch?v=abc123",
            output_dir=tmp,
            runner=_fake_ytdlp_runner,
        )
        assert discovery.title == "Example Video"
        assert len(discovery.formats) == 2
        assert discovery.formats[0].height == 1080
        assert Path(discovery.raw_info_json_path).is_file()


def test_youtube_metadata_text_sidecar_matches_project_export_shape() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        discovery = discover_youtube_media_with_ytdlp(
            "[https://www.youtube.com/watch?v=abc123](https://www.youtube.com/watch?v=abc123)",
            output_dir=tmp,
            runner=_fake_ytdlp_runner,
        )
        text = youtube_metadata_text_from_discovery(discovery)
        assert "Title: Example Video" in text
        assert "Channel: Uploader" in text
        assert "Subscribers: 13.5K" in text
        assert "Date: Feb " in text and "2024" in text
        assert "Views: 429,265" in text
        assert "Description: Line one." in text
        assert "Source: https://www.youtube.com/watch?v=abc123" in text
        target = Path(tmp) / "youtube-media-metadata.txt"
        write_youtube_media_metadata_text(discovery, target)
        assert target.read_text(encoding="utf-8") == text


def test_youtube_format_selector_uses_jdownloader_max_resolution() -> None:
    cfg = JDownloaderExternalConfigReport(
        source_path="x",
        source_kind="directory",
        youtube_main_config={"maxvideoresolution": "P_1440"},
    )
    selector = youtube_format_selector_from_jdownloader(cfg)
    assert "height<=1440" in selector
    assert "bestvideo" in selector
    assert "bestaudio" in selector


def test_build_youtube_ytdlp_download_plan_is_safe_dry_run_by_default() -> None:
    cfg = JDownloaderExternalConfigReport(
        source_path="x",
        source_kind="directory",
        youtube_main_config={"maxvideoresolution": "P_2160"},
    )
    with tempfile.TemporaryDirectory() as tmp:
        plan = build_youtube_ytdlp_download_plan(
            "https://www.youtube.com/watch?v=abc123",
            output_dir=tmp,
            jdownloader_config=cfg,
            ffmpeg_location="C:/tools/ffmpeg",
        )
        assert plan.dry_run is True
        assert "--simulate" in plan.command
        assert "--merge-output-format" in plan.command
        assert "--ffmpeg-location" in plan.command
        assert "height<=2160" in plan.format_selector


def test_build_youtube_ytdlp_download_plan_normalizes_markdown_url() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        plan = build_youtube_ytdlp_download_plan(
            "[https://www.youtube.com/watch?v=abc123](https://www.youtube.com/watch?v=abc123)",
            output_dir=tmp,
        )
        assert plan.source_url == "https://www.youtube.com/watch?v=abc123"
        assert plan.command[-1] == "https://www.youtube.com/watch?v=abc123"


def test_resolve_ytdlp_command_accepts_explicit_sequence() -> None:
    resolution = resolve_ytdlp_command([sys.executable, "-m", "yt_dlp"])
    assert resolution.command == (sys.executable, "-m", "yt_dlp")
    assert resolution.source == "explicit-sequence"


def test_build_youtube_ytdlp_download_plan_accepts_command_sequence() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        plan = build_youtube_ytdlp_download_plan(
            "https://www.youtube.com/watch?v=abc123",
            output_dir=tmp,
            yt_dlp_path=("python", "-m", "yt_dlp"),
        )
        assert plan.command[:3] == ("python", "-m", "yt_dlp")
        assert plan.command[-1] == "https://www.youtube.com/watch?v=abc123"


if __name__ == "__main__":
    test_normalize_media_source_url_arg_strips_markdown_url()
    test_normalize_media_source_url_arg_handles_escaped_markdown_and_surrounding_text()
    test_normalize_media_source_url_arg_strict_rejects_leftover_markdown()
    test_normalize_media_source_url_arg_handles_cmd_markdown()
    test_normalize_media_source_url_arg_handles_nested_markdown_from_cmd()
    test_discover_youtube_media_with_ytdlp_parses_formats()
    test_youtube_metadata_text_sidecar_matches_project_export_shape()
    test_youtube_format_selector_uses_jdownloader_max_resolution()
    test_build_youtube_ytdlp_download_plan_is_safe_dry_run_by_default()
    test_build_youtube_ytdlp_download_plan_normalizes_markdown_url()
    test_resolve_ytdlp_command_accepts_explicit_sequence()
    test_build_youtube_ytdlp_download_plan_accepts_command_sequence()
    print("youtube_media_download_backend_test OK")
