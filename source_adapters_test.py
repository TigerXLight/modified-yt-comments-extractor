from source_adapters import (
    AVAILABLE_SOURCE_ADAPTERS,
    CREDENTIAL_API_KEY,
    PLATFORM_VIDEO_SOCIAL,
    YOUTUBE_SOURCE_ADAPTER,
    find_source_adapter,
)


VALID_ID = "aB3_dE-9xYz"
CANONICAL_URL = f"https://www.youtube.com/watch?v={VALID_ID}"


def _assert_valid(value: str) -> None:
    adapter = YOUTUBE_SOURCE_ADAPTER
    assert adapter.can_handle(value)
    assert adapter.extract_source_id(value) == VALID_ID
    assert adapter.normalize_url(value) == CANONICAL_URL
    assert find_source_adapter(value) is adapter


def run_self_test() -> None:
    for value in [
        VALID_ID,
        f"https://www.youtube.com/watch?v={VALID_ID}",
        f"https://youtube.com/watch?v={VALID_ID}",
        f"https://www.youtube.com/watch?v={VALID_ID}&t=30s&list=PL123",
        f"https://youtu.be/{VALID_ID}",
        f"https://www.youtube.com/shorts/{VALID_ID}",
        f"https://youtube.com/embed/{VALID_ID}?start=30",
    ]:
        _assert_valid(value)

    for value in [
        "",
        "not a youtube url",
        "https://example.com/watch?v=aB3_dE-9xYz",
        "https://www.youtube.com/watch?v=too-short",
        "https://www.notyoutube.com/watch?v=aB3_dE-9xYz",
    ]:
        assert not YOUTUBE_SOURCE_ADAPTER.can_handle(value)
        assert find_source_adapter(value) is None

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
    assert metadata.platform_family == PLATFORM_VIDEO_SOCIAL
    assert metadata.credential_type == CREDENTIAL_API_KEY
    assert metadata.credentials_required
    assert not metadata.credentials_optional
    assert not metadata.supports_browser_capture
    assert not metadata.supports_manual_import
    assert "YouTube Data API key" in metadata.setup_hint
    assert not metadata.test_connection_supported
    assert "quota" in metadata.cost_or_rate_limit_notes.lower()
    assert "elsewhere" in metadata.access_limitations

    assert AVAILABLE_SOURCE_ADAPTERS == (YOUTUBE_SOURCE_ADAPTER,)


if __name__ == "__main__":
    run_self_test()
    print("Source adapter self-test passed.")
