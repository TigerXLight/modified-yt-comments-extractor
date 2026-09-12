import subprocess
import sys
import tempfile
from pathlib import Path

from profile_media_source_family_matrix_r42gc import (
    REQUIRED_FAMILIES,
    ROUTE_API3128_JDOWNLOADER_FIRST,
    ROUTE_BBC_SOUNDS_YTDLP_FFMPEG_COPY,
    SIDE_EFFECT_BOUNDARY,
    STATUS_BASELINE_EXISTS_NOT_CLOSED,
    STATUS_PROVEN_MANUAL_ROUTE,
    STATUS_SPECIALIST_REQUIRED,
    STATUS_TESTED_TRUE,
    STATUS_VALIDATED_CURRENT_METHOD,
    SOURCE_FAMILY_CAPABILITIES,
    classify_source_family,
    source_family_ids,
    validate_source_family_matrix,
)


def _capability(family_id):
    for capability in SOURCE_FAMILY_CAPABILITIES:
        if capability.family_id == family_id:
            return capability
    raise AssertionError(f"missing capability {family_id}")


def _assert_cli_accepts_repeated_url_arguments() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        output_root = Path(temp_dir) / "r42gc_cli_report"
        completed = subprocess.run(
            [
                sys.executable,
                str(Path(__file__).resolve().parent / "profile_media_source_family_matrix_r42gc.py"),
                "--source-root",
                str(Path(__file__).resolve().parent),
                "--output-root",
                str(output_root),
                "--url",
                "https://www.bbc.co.uk/programmes/m0031724",
                "--url",
                "https://open.spotify.com/track/1234567890",
            ],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        assert completed.returncode == 0, completed.stdout + completed.stderr
        assert "R42GC universal source adapter family matrix" in completed.stdout
        assert "URL: https://www.bbc.co.uk/programmes/m0031724" in completed.stdout
        assert "family=bbc_sounds" in completed.stdout
        assert "URL: https://open.spotify.com/track/1234567890" in completed.stdout
        assert "spotify_music_or_non_podcast_unsupported" in completed.stdout
        assert (output_root / "r42gc_universal_source_family_matrix.json").is_file()
        assert (output_root / "r42gc_universal_source_family_matrix.md").is_file()


def run_self_test() -> None:
    ids = source_family_ids()
    assert len(ids) == len(set(ids))
    for family_id in REQUIRED_FAMILIES:
        assert family_id in ids

    generic_article = classify_source_family("https://metro.co.uk/2026/07/17/example-story/")
    assert generic_article.family_id == "generic_article"
    assert generic_article.adapter_hint == "news_website"
    assert generic_article.url_kind == "generic_public_webpage_or_article"
    assert generic_article.supported
    assert generic_article.safety_note == SIDE_EFFECT_BOUNDARY

    generic_media = classify_source_family("https://cdn.example.test/path/video.mp4")
    assert generic_media.family_id == "generic_webpage_media"
    assert generic_media.url_kind == "direct_public_media_candidate"
    assert generic_media.route_preference == ROUTE_API3128_JDOWNLOADER_FIRST
    assert generic_media.capability.video_audio == STATUS_TESTED_TRUE

    bbc_programme = classify_source_family("https://www.bbc.co.uk/programmes/m0031724")
    assert bbc_programme.family_id == "bbc_sounds"
    assert bbc_programme.url_kind == "bbc_sounds_or_programme_audio"
    assert bbc_programme.route_preference == ROUTE_BBC_SOUNDS_YTDLP_FFMPEG_COPY
    assert bbc_programme.capability.video_audio == STATUS_PROVEN_MANUAL_ROUTE

    bbc_sounds = classify_source_family("https://www.bbc.co.uk/sounds/play/m0031724")
    assert bbc_sounds.family_id == "bbc_sounds"

    podcast_rss = classify_source_family("https://feeds.example.test/show/podcast.rss")
    assert podcast_rss.family_id == "podcast_rss"
    assert podcast_rss.url_kind == "podcast_or_feed_url"

    apple = classify_source_family("https://podcasts.apple.com/gb/podcast/example-show/id123456789")
    assert apple.family_id == "apple_podcasts"
    assert apple.url_kind == "apple_podcast_show_or_episode"

    spotify_episode = classify_source_family("https://open.spotify.com/episode/1234567890")
    assert spotify_episode.family_id == "spotify_podcast"
    assert spotify_episode.supported
    assert "podcast" in spotify_episode.url_kind

    spotify_show = classify_source_family("https://open.spotify.com/show/1234567890")
    assert spotify_show.family_id == "spotify_podcast"
    assert spotify_show.supported

    spotify_track = classify_source_family("https://open.spotify.com/track/1234567890")
    assert spotify_track.family_id == "spotify_podcast"
    assert spotify_track.url_kind == "spotify_music_or_non_podcast_unsupported"
    assert not spotify_track.supported
    assert "out of scope" in spotify_track.reason

    youtube = classify_source_family("https://www.youtube.com/watch?v=aB3_dE-9xYz")
    assert youtube.family_id == "youtube"
    assert youtube.adapter_hint == "youtube"

    twitter = classify_source_family("https://x.com/example/status/1234567890")
    assert twitter.family_id == "twitter_x"
    assert twitter.capability.video_audio == STATUS_VALIDATED_CURRENT_METHOD
    assert twitter.capability.comments == STATUS_VALIDATED_CURRENT_METHOD

    twitter2 = classify_source_family("https://twitter.com/example/status/1234567890")
    assert twitter2.family_id == "twitter_x"

    instagram = classify_source_family("https://www.instagram.com/p/ABC123/")
    assert instagram.family_id == "instagram"
    assert instagram.capability.specialist_layer_required
    assert instagram.capability.video_audio == STATUS_SPECIALIST_REQUIRED

    wayback = classify_source_family("https://web.archive.org/web/20260717224516/https://metro.co.uk/example/")
    assert wayback.family_id == "archive_wayback"
    assert wayback.url_kind == "wayback_capture_url"

    archive_today = classify_source_family("https://archive.ph/6mr3C")
    assert archive_today.family_id == "archive_today"
    assert archive_today.url_kind == "archive_today_capture_url"

    local_warc = classify_source_family(r"C:\captures\example.warc.gz")
    assert local_warc.family_id == "local_warc_archive"
    assert local_warc.url_kind == "local_archive_package"

    local_wacz = classify_source_family(r"C:\captures\example.wacz")
    assert local_wacz.family_id == "local_warc_archive"

    unsupported_local = classify_source_family(r"C:\captures\notes.txt")
    assert not unsupported_local.supported
    assert unsupported_local.url_kind == "local_non_archive_path"

    unsupported_scheme = classify_source_family("ftp://example.com/file.mp4")
    assert not unsupported_scheme.supported
    assert unsupported_scheme.url_kind == "unsupported_scheme"

    assert _capability("generic_webpage_media").route_preference == ROUTE_API3128_JDOWNLOADER_FIRST
    assert _capability("bbc_sounds").route_preference == ROUTE_BBC_SOUNDS_YTDLP_FFMPEG_COPY
    assert _capability("twitter_x").comments == STATUS_VALIDATED_CURRENT_METHOD
    assert _capability("instagram").specialist_layer_required

    _assert_cli_accepts_repeated_url_arguments()

    report = validate_source_family_matrix(".")
    assert report.passed
    assert not report.missing_required_families
    assert report.family_count >= len(REQUIRED_FAMILIES)
    assert "source-family capability router" in report.conclusion
    assert "no network fetch" in report.side_effects
    assert sum(1 for check in report.checks if check["status"] == "fail") == 0


if __name__ == "__main__":
    run_self_test()
    print("profile_media_source_family_matrix_r42gc_test OK")
