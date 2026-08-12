from __future__ import annotations

import json
import tempfile
from pathlib import Path

from source_resource_state import build_source_resource_row, normalize_source_url_token
from youtube_gui_media_queue import (
    YOUTUBE_GUI_COMPONENT_AUDIO,
    YOUTUBE_GUI_COMPONENT_AUTO_SUBTITLES,
    YOUTUBE_GUI_COMPONENT_SUBTITLES,
    YOUTUBE_GUI_COMPONENT_THUMBNAIL,
    YOUTUBE_GUI_COMPONENT_VIDEO,
    YOUTUBE_GUI_MEDIA_QUEUE_STATUS_READY,
    YouTubeGuiMediaPreferences,
    normalized_youtube_quality_labels,
    queue_youtube_gui_source_row_selection,
    youtube_available_quality_labels_from_discovery,
    youtube_quality_height,
)
from youtube_media_download_backend import YouTubeMediaDiscovery, YouTubeMediaFormat


def test_source_url_token_accepts_markdown_youtube_url() -> None:
    raw = r"[https://www.youtube.com/watch?v=dQw4w9WgXcQ](https://www.youtube.com/watch?v=dQw4w9WgXcQ)"
    assert normalize_source_url_token(raw) == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    row = build_source_resource_row(raw)
    assert row.adapter_id == "youtube"
    assert row.canonical_url.startswith("https://")
    assert row.title.startswith("YouTube video")
    assert row.archive_statuses == ()


def test_youtube_quality_labels_and_heights() -> None:
    prefs = YouTubeGuiMediaPreferences(enabled_quality_labels=("1080", "720"), default_quality_label="720")
    assert normalized_youtube_quality_labels(prefs) == ("1080", "720")
    assert youtube_quality_height("4k") == 2160
    assert youtube_quality_height("1080") == 1080
    assert youtube_quality_height("360") == 360
    assert youtube_quality_height("144") == 144


def test_youtube_available_quality_labels_from_discovery() -> None:
    discovery = YouTubeMediaDiscovery(
        source_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        title="Your Sunset",
        formats=(
            YouTubeMediaFormat(format_id="140", ext="m4a", vcodec="none", acodec="mp4a", height=None),
            YouTubeMediaFormat(format_id="160", ext="mp4", vcodec="avc1", acodec="none", height=144),
            YouTubeMediaFormat(format_id="133", ext="mp4", vcodec="avc1", acodec="none", height=240),
            YouTubeMediaFormat(format_id="134", ext="mp4", vcodec="avc1", acodec="none", height=360),
            YouTubeMediaFormat(format_id="135", ext="mp4", vcodec="avc1", acodec="none", height=480),
            YouTubeMediaFormat(format_id="136", ext="mp4", vcodec="avc1", acodec="none", height=720),
            YouTubeMediaFormat(format_id="137", ext="mp4", vcodec="avc1", acodec="none", height=1080),
        ),
    )
    assert youtube_available_quality_labels_from_discovery(discovery) == ("1080", "720", "480", "360", "240", "144")



def test_youtube_available_quality_labels_does_not_invent_fallbacks_without_formats() -> None:
    discovery = YouTubeMediaDiscovery(
        source_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        title="No Formats Yet",
        formats=(),
    )
    assert youtube_available_quality_labels_from_discovery(discovery) == ()
    assert youtube_available_quality_labels_from_discovery(discovery, fallback=("1080",)) == ("1080",)


def test_queue_youtube_gui_source_row_selection_writes_mux_audio_and_metadata_files() -> None:
    row = build_source_resource_row("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    prefs = YouTubeGuiMediaPreferences(
        video_enabled=True,
        separate_audio_enabled=True,
        thumbnail_enabled=True,
        subtitles_enabled=True,
        auto_subtitles_enabled=True,
        enabled_quality_labels=("1080", "720"),
        default_quality_label="1080",
    )

    with tempfile.TemporaryDirectory() as tmp:
        discovery = YouTubeMediaDiscovery(
            source_url=row.canonical_url,
            title="Your Sunset",
            channel="TEKKEN Project - Topic",
            channel_follower_count=13500,
            upload_date="20240225",
            view_count=429265,
            description="Provided to YouTube by NexTone Inc.",
        )
        result = queue_youtube_gui_source_row_selection(
            row=row,
            quality_label="1080",
            preferences=prefs,
            output_root=tmp,
            discovery=discovery,
        )

        assert result.status == YOUTUBE_GUI_MEDIA_QUEUE_STATUS_READY
        assert result.selected_quality_label == "1080"
        assert result.selected_components == (
            YOUTUBE_GUI_COMPONENT_VIDEO,
            YOUTUBE_GUI_COMPONENT_AUDIO,
            YOUTUBE_GUI_COMPONENT_THUMBNAIL,
            YOUTUBE_GUI_COMPONENT_SUBTITLES,
            YOUTUBE_GUI_COMPONENT_AUTO_SUBTITLES,
        )
        assert Path(result.metadata_txt_path).is_file()
        assert Path(result.manifest_json_path).is_file()
        assert len(result.plan_json_paths) == 2
        manifest = json.loads(Path(result.manifest_json_path).read_text(encoding="utf-8"))
        assert manifest["selected_quality_label"] == "1080"
        assert manifest["selected_height"] == 1080
        assert "video" in manifest["selected_components"]
        metadata = Path(result.metadata_txt_path).read_text(encoding="utf-8")
        assert "Title: Your Sunset" in metadata
        assert "Channel: TEKKEN Project - Topic" in metadata
        assert "Subscribers: 13,500" in metadata
        assert "Date: 2024-02-25" in metadata
        assert "Views: 429,265" in metadata
        assert "Description: Provided to YouTube by NexTone Inc." in metadata
        assert "Source:" in metadata
        assert "Go adds this YouTube media selection to FILES automatically" in metadata
        video_plan = json.loads(Path(result.plan_json_paths[0]).read_text(encoding="utf-8"))
        audio_plan = json.loads(Path(result.plan_json_paths[1]).read_text(encoding="utf-8"))
        assert "+bestaudio" in video_plan["format_selector"]
        assert "--merge-output-format" in video_plan["command"]
        assert "--write-thumbnail" in video_plan["command"]
        assert "--write-subs" in video_plan["command"]
        assert "--write-auto-subs" in video_plan["command"]
        assert "-x" in audio_plan["command"]
        assert "--audio-format" in audio_plan["command"]


def test_queue_youtube_gui_source_row_selection_audio_only_disables_mux_plan() -> None:
    row = build_source_resource_row("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    prefs = YouTubeGuiMediaPreferences(video_enabled=False, separate_audio_enabled=True, thumbnail_enabled=False, subtitles_enabled=False, auto_subtitles_enabled=False)
    with tempfile.TemporaryDirectory() as tmp:
        result = queue_youtube_gui_source_row_selection(row=row, quality_label="1080", preferences=prefs, output_root=tmp)
        assert result.status == YOUTUBE_GUI_MEDIA_QUEUE_STATUS_READY
        assert result.auto_mux is False
        assert result.selected_components == (YOUTUBE_GUI_COMPONENT_AUDIO,)
        assert len(result.plan_json_paths) == 1
        plan = json.loads(Path(result.plan_json_paths[0]).read_text(encoding="utf-8"))
        assert "-x" in plan["command"]
        assert "--merge-output-format" not in plan["command"]


def main() -> None:
    test_source_url_token_accepts_markdown_youtube_url()
    test_youtube_quality_labels_and_heights()
    test_youtube_available_quality_labels_from_discovery()
    test_youtube_available_quality_labels_does_not_invent_fallbacks_without_formats()
    test_queue_youtube_gui_source_row_selection_writes_mux_audio_and_metadata_files()
    test_queue_youtube_gui_source_row_selection_audio_only_disables_mux_plan()
    print("youtube_gui_media_queue_test OK")


if __name__ == "__main__":
    main()
