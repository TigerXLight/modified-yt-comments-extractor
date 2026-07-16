from source_adapters import (
    AVAILABLE_SOURCE_ADAPTERS,
    MSN_SOURCE_ADAPTER,
    NEWS_WEBSITE_SOURCE_ADAPTER,
    YOUTUBE_SOURCE_ADAPTER,
    find_source_adapter,
)

VALID_ID = "aB3_dE-9xYz"
CANONICAL_URL = f"https://www.youtube.com/watch?v={VALID_ID}"


def run_self_test() -> None:
    adapter = YOUTUBE_SOURCE_ADAPTER
    assert adapter.can_handle(CANONICAL_URL)
    assert adapter.normalize_url(CANONICAL_URL) == CANONICAL_URL
    assert adapter.extract_source_id(CANONICAL_URL) == VALID_ID
    assert find_source_adapter(CANONICAL_URL) is adapter

    for value in [
        f"https://www.youtube.com/watch?v={VALID_ID}",
        f"https://youtube.com/watch?v={VALID_ID}",
        f"https://www.youtube.com/watch?v={VALID_ID}&t=30s&list=PL123",
        f"https://youtu.be/{VALID_ID}?si=abc",
        f"https://www.youtube.com/shorts/{VALID_ID}",
        f"https://youtube.com/embed/{VALID_ID}?start=30",
    ]:
        assert YOUTUBE_SOURCE_ADAPTER.can_handle(value)
        assert YOUTUBE_SOURCE_ADAPTER.extract_source_id(value) == VALID_ID
        assert YOUTUBE_SOURCE_ADAPTER.normalize_url(value) == CANONICAL_URL

    for value in [
        "",
        "not a youtube url",
        "https://example.com/watch?v=aB3_dE-9xYz",
        "https://www.youtube.com/watch?v=too-short",
        "https://www.notyoutube.com/watch?v=aB3_dE-9xYz",
    ]:
        assert not YOUTUBE_SOURCE_ADAPTER.can_handle(value)

    capabilities = YOUTUBE_SOURCE_ADAPTER.capabilities
    assert capabilities.supports_comments
    assert capabilities.supports_replies
    assert capabilities.supports_livechat
    assert capabilities.supports_likes
    assert capabilities.supports_timestamps
    assert capabilities.supports_author_channel_ids
    assert capabilities.supports_transcripts

    metadata = YOUTUBE_SOURCE_ADAPTER.metadata
    assert metadata.display_name == "YouTube"
    assert metadata.platform_family == "video_social"
    assert metadata.credential_type == "api_key"
    assert metadata.credentials_required
    assert not metadata.credentials_optional
    assert not metadata.supports_browser_capture
    assert not metadata.supports_manual_import
    assert not metadata.test_connection_supported
    assert "quota" in metadata.cost_or_rate_limit_notes.lower()
    assert "URL parsing/validation metadata only" in metadata.access_limitations

    news_adapter = NEWS_WEBSITE_SOURCE_ADAPTER
    telegraph_url = "HTTPS://www.telegraph.co.uk/news/2026/07/10/example-story/?utm_source=x#comments"
    msn_url = "https://www.msn.com/en-gb/news/world/example-story/ar-AA123456?ocid=feeds"
    assert news_adapter.can_handle(telegraph_url)
    assert not news_adapter.can_handle(msn_url)
    assert find_source_adapter(telegraph_url) is news_adapter
    assert find_source_adapter(msn_url) is MSN_SOURCE_ADAPTER
    assert news_adapter.normalize_url(telegraph_url) == (
        "https://www.telegraph.co.uk/news/2026/07/10/example-story/"
    )
    assert news_adapter.extract_source_id(telegraph_url) == (
        "www.telegraph.co.uk/news/2026/07/10/example-story/"
    )

    for value in [
        "",
        "not a url",
        "ftp://www.telegraph.co.uk/news/example",
        "https://example.com/news/story",
        "https://fake-telegraph.co.uk/news/story",
        "https://msn.example.com/news/story",
    ]:
        assert not news_adapter.can_handle(value)

    news_capabilities = news_adapter.capabilities
    assert not news_capabilities.supports_comments
    assert not news_capabilities.supports_replies
    assert not news_capabilities.supports_livechat
    assert not news_capabilities.supports_likes
    assert not news_capabilities.supports_author_channel_ids
    assert not news_capabilities.supports_transcripts
    assert news_capabilities.supports_timestamps

    news_metadata = news_adapter.metadata
    assert news_metadata.display_name == "News Website"
    assert news_metadata.platform_family == "news_website"
    assert news_metadata.credential_type == "none"
    assert not news_metadata.credentials_required
    assert not news_metadata.credentials_optional
    assert not news_metadata.supports_browser_capture
    assert news_metadata.supports_manual_import
    assert not news_metadata.test_connection_supported
    assert "Telegraph-style" in news_metadata.setup_hint
    assert "metadata/URL-recognition skeleton only" in news_metadata.access_limitations
    assert "does not fetch" in news_metadata.access_limitations

    msn_adapter = MSN_SOURCE_ADAPTER
    assert msn_adapter.can_handle(msn_url)
    assert msn_adapter.normalize_url(msn_url) == (
        "https://www.msn.com/en-gb/news/world/example-story/ar-AA123456"
    )
    assert msn_adapter.extract_source_id(msn_url) == (
        "www.msn.com/en-gb/news/world/example-story/ar-AA123456"
    )
    assert not msn_adapter.can_handle("https://msn.example.com/news/story")

    msn_capabilities = msn_adapter.capabilities
    assert msn_capabilities.supports_comments
    assert msn_capabilities.supports_replies
    assert not msn_capabilities.supports_livechat
    assert not msn_capabilities.supports_transcripts

    msn_metadata = msn_adapter.metadata
    assert msn_metadata.display_name == "MSN"
    assert msn_metadata.platform_family == "news_website"
    assert msn_metadata.credential_type == "none"
    assert not msn_metadata.credentials_required
    assert msn_metadata.supports_manual_import
    assert "fixture" in msn_metadata.setup_hint.lower()
    assert "does not fetch" in msn_metadata.access_limitations
    assert "browser automation" in msn_metadata.access_limitations

    assert AVAILABLE_SOURCE_ADAPTERS == (
        YOUTUBE_SOURCE_ADAPTER,
        MSN_SOURCE_ADAPTER,
        NEWS_WEBSITE_SOURCE_ADAPTER,
    )


if __name__ == "__main__":
    run_self_test()
    print("Source adapter self-test passed.")
