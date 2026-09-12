from __future__ import annotations

import tempfile
from pathlib import Path

from profile_media_bbc_podcast_adapter_r42ge import (
    ROUTE_APPLE_PODCASTS_METADATA_RSS,
    ROUTE_BBC_SOUNDS_YTDLP_FFMPEG_COPY,
    ROUTE_PODCAST_RSS_PUBLIC_ENCLOSURE,
    ROUTE_SPOTIFY_PODCAST_METADATA_ONLY,
    build_bbc_sounds_episode_plan,
    build_podcast_episode_plan,
    extract_bbc_audio_id,
    validate_bbc_podcast_adapter,
)


def test_extract_bbc_audio_ids() -> None:
    assert extract_bbc_audio_id("https://www.bbc.co.uk/programmes/m0031724") == "m0031724"
    assert extract_bbc_audio_id("https://www.bbc.co.uk/sounds/play/m0031724") == "m0031724"
    assert extract_bbc_audio_id("https://www.bbc.co.uk/iplayer/episode/m0031724/example") == "m0031724"
    assert extract_bbc_audio_id("https://www.bbc.co.uk/news/articles/example") == ""


def test_bbc_plan_preserves_original_and_derives_m4a() -> None:
    with tempfile.TemporaryDirectory() as td:
        plan = build_bbc_sounds_episode_plan(
            "https://www.bbc.co.uk/programmes/m0031724",
            output_root=td,
            title="BBC Radio 4 Today",
            date_label="2026-09-08",
        )
        assert plan.supported
        assert plan.family_id == "bbc_sounds"
        assert plan.programme_id == "m0031724"
        assert plan.sounds_id == "m0031724"
        assert plan.route_preference == ROUTE_BBC_SOUNDS_YTDLP_FFMPEG_COPY
        assert plan.original_asset is not None
        assert plan.audio_only_asset is not None
        assert plan.original_asset.path.endswith("_FULL_[m0031724].mp4")
        assert plan.audio_only_asset.path.endswith("_AUDIO_[m0031724].m4a")
        assert len(plan.commands) == 2
        assert plan.commands[0].command[:3] == ("yt-dlp", "-f", "bestaudio")
        assert plan.commands[1].command[:2] == ("ffmpeg", "-i")
        assert "-map_metadata" in plan.commands[1].command
        assert all(not command.execute for command in plan.commands)


def test_bbc_plan_skips_existing_assets_without_downloading() -> None:
    with tempfile.TemporaryDirectory() as td:
        existing = Path(td) / "BBC_Sounds_m0031724_FULL_[m0031724].mp4"
        existing.write_bytes(b"already downloaded once")
        plan = build_bbc_sounds_episode_plan("https://www.bbc.co.uk/programmes/m0031724", output_root=td)
        assert plan.original_asset is not None
        assert plan.original_asset.exists
        assert plan.commands[0].status == "skip_existing_original"
        assert not plan.commands[0].execute


def test_podcast_family_plans() -> None:
    rss = build_podcast_episode_plan("https://feeds.example.test/show/podcast.rss")
    assert rss.family_id == "podcast_rss"
    assert rss.supported
    assert rss.route_preference == ROUTE_PODCAST_RSS_PUBLIC_ENCLOSURE

    apple = build_podcast_episode_plan("https://podcasts.apple.com/gb/podcast/example-show/id123456789")
    assert apple.family_id == "apple_podcasts"
    assert apple.supported
    assert apple.route_preference == ROUTE_APPLE_PODCASTS_METADATA_RSS

    spotify_episode = build_podcast_episode_plan("https://open.spotify.com/episode/1234567890")
    assert spotify_episode.family_id == "spotify_podcast"
    assert spotify_episode.supported
    assert spotify_episode.route_preference == ROUTE_SPOTIFY_PODCAST_METADATA_ONLY
    assert spotify_episode.capability_labels["direct_audio"] == "unsupported"

    spotify_track = build_podcast_episode_plan("https://open.spotify.com/track/1234567890")
    assert spotify_track.family_id == "spotify_podcast"
    assert not spotify_track.supported
    assert spotify_track.url_kind == "spotify_music_or_non_podcast_unsupported"
    assert spotify_track.capability_labels["music_download"] == "excluded"


def test_validation_report_passes_and_is_side_effect_free() -> None:
    with tempfile.TemporaryDirectory() as td:
        report = validate_bbc_podcast_adapter(source_root=".", output_root=td)
        assert report.passed
        assert "no network fetch" in report.side_effects
        assert "no media download" in report.side_effects
        assert any(check["check_id"] == "bbc_sounds_route" and check["status"] == "pass" for check in report.checks)
        assert any(check["check_id"] == "spotify_music_excluded" and check["status"] == "pass" for check in report.checks)


if __name__ == "__main__":
    test_extract_bbc_audio_ids()
    test_bbc_plan_preserves_original_and_derives_m4a()
    test_bbc_plan_skips_existing_assets_without_downloading()
    test_podcast_family_plans()
    test_validation_report_passes_and_is_side_effect_free()
    print("profile_media_bbc_podcast_adapter_r42ge_test OK")
