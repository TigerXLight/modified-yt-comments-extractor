from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_v68_modules_exist_and_use_shared_backend() -> None:
    assert (ROOT / "twitter_media_backend.py").exists()
    assert (ROOT / "twitter_reference_sources.py").exists()
    media_source = (ROOT / "twitter_media_backend.py").read_text(encoding="utf-8")
    assert "run_shared_jdownloader_media_backend" in media_source
    assert 'source_adapter_id="twitter_x"' in media_source
    assert "evidence_completion_claim" in media_source
    assert "allow_untested_jdownloader" in media_source


def test_twitter_adapter_no_longer_says_no_media_download() -> None:
    source = (ROOT / "source_adapters.py").read_text(encoding="utf-8")
    assert "twitter_x_media_shared_backend" in source
    twitter_section = source[source.index("class TwitterXSourceAdapter") : source.index("YOUTUBE_SOURCE_ADAPTER")]
    assert "shared JDownloader media backend" in twitter_section
    assert "It does not browse X/Twitter, automate a browser, call the API, use cookies, or download media." not in twitter_section


def test_reference_registry_mentions_uploaded_reference_families() -> None:
    source = (ROOT / "twitter_reference_sources.py").read_text(encoding="utf-8")
    assert "Twitter Exporter" in source
    assert "Video Download Helper" in source
    assert "Video Downloader Professional" in source
    assert "twitter-openapi" in source
    assert "vdhcoapp" in source


def main() -> None:
    test_v68_modules_exist_and_use_shared_backend()
    test_twitter_adapter_no_longer_says_no_media_download()
    test_reference_registry_mentions_uploaded_reference_families()
    print("assert_twitter_shared_media_backend_v68 OK")


if __name__ == "__main__":
    main()
