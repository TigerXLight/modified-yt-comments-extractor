from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_v68b_reference_registry_is_complete_for_supplied_list() -> None:
    source = (ROOT / "twitter_reference_sources.py").read_text(encoding="utf-8")
    for expected in (
        "twitter_filter_skills_rxliuli",
        "twitter_filter_rxliuli_store",
        "clean_twitter_rxliuli_store",
        "xkit_rxliuli",
        "ffmpeg_online_rxliuli",
        "webdatamaster_rxliuli",
        "google_translate_api_free_rxliuli",
        "x_article_exporter_annismckenzie",
        "video_downloader_pro_alasim",
        "youtube_js_paulrouget",
        "libav_js_paulrouget",
        "jocly_aclap",
    ):
        assert expected in source
    assert "implementation_area" in source
    assert "not_currently_relevant" in source


def test_source_resource_status_mentions_settings_and_shared_backend() -> None:
    source = (ROOT / "source_resource_state.py").read_text(encoding="utf-8")
    assert "settings and shared backend" in source


def main() -> None:
    test_v68b_reference_registry_is_complete_for_supplied_list()
    test_source_resource_status_mentions_settings_and_shared_backend()
    print("assert_twitter_reference_expansion_v68b OK")


if __name__ == "__main__":
    main()
