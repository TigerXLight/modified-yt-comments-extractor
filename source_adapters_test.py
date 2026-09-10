from source_adapters import (
    AVAILABLE_SOURCE_ADAPTERS,
    ACCOUNT_CHANNEL_SOURCE_ADAPTER,
    SOURCE_METHOD_PROFILES,
    MSN_SOURCE_ADAPTER,
    NEWS_WEBSITE_SOURCE_ADAPTER,
    TWITTER_X_SOURCE_ADAPTER,
    YOUTUBE_SOURCE_ADAPTER,
    default_source_method_profile_for_adapter,
    find_source_adapter,
    find_source_method_profile,
    source_method_profile_ids,
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
    assert msn_metadata.supports_browser_capture
    assert msn_metadata.supports_manual_import
    assert "headless browser capture" in msn_metadata.setup_hint.lower()
    assert "open a visible browser by default" in msn_metadata.access_limitations
    assert "replay success" in msn_metadata.access_limitations

    twitter_url = "https://x.com/example/status/1234567890?utm_source=test"
    twitter_adapter = TWITTER_X_SOURCE_ADAPTER
    assert twitter_adapter.can_handle(twitter_url)
    assert twitter_adapter.normalize_url(twitter_url) == "https://x.com/example/status/1234567890"
    assert twitter_adapter.extract_source_id(twitter_url) == "x.com/example/status/1234567890"
    assert find_source_adapter("https://twitter.com/example/status/123") is twitter_adapter
    assert not twitter_adapter.can_handle("https://notx.com/example/status/123")
    twitter_metadata = twitter_adapter.metadata
    assert twitter_metadata.display_name == "X / Twitter"
    assert twitter_metadata.supports_manual_import
    assert twitter_metadata.supports_browser_capture
    assert "shared JDownloader media backend" in twitter_metadata.access_limitations

    channel_url = "slack://workspace/channel/message/123?thread=456"
    channel_adapter = ACCOUNT_CHANNEL_SOURCE_ADAPTER
    assert channel_adapter.can_handle(channel_url)
    assert find_source_adapter(channel_url) is channel_adapter
    assert channel_adapter.normalize_url("SLACK://workspace/channel/message/123?thread=456") == channel_url
    assert channel_adapter.extract_source_id(channel_url).startswith("slack:")
    assert channel_adapter.metadata.display_name == "Account / Channel"
    assert channel_adapter.metadata.platform_family == "account_channel"
    assert channel_adapter.metadata.supports_manual_import
    assert not channel_adapter.metadata.supports_browser_capture
    assert "performs no polling" in channel_adapter.metadata.access_limitations
    assert not channel_adapter.can_handle("ftp://workspace/channel/message/123")
    assert not channel_adapter.can_handle("slack://")

    assert AVAILABLE_SOURCE_ADAPTERS == (
        YOUTUBE_SOURCE_ADAPTER,
        MSN_SOURCE_ADAPTER,
        TWITTER_X_SOURCE_ADAPTER,
        NEWS_WEBSITE_SOURCE_ADAPTER,
        ACCOUNT_CHANNEL_SOURCE_ADAPTER,
    )

    assert source_method_profile_ids() == tuple(profile.profile_id for profile in SOURCE_METHOD_PROFILES)
    msn_profile = default_source_method_profile_for_adapter("msn")
    assert msn_profile.profile_id == "msn_article_comments_shadow_manual_import"
    assert msn_profile.archive_fallback_supported
    assert msn_profile.manual_import_supported
    assert msn_profile.network_actions_performed is False
    assert "source_role_labels" in msn_profile.supported_modes
    assert "media_source_chain_fields" in msn_profile.supported_modes
    assert "disputed_framing_source_author_correction_notes" in msn_profile.supported_modes
    assert "source_role_labels_future" not in msn_profile.supported_modes
    assert "media_source_chain_fields_future" not in msn_profile.supported_modes
    assert "disputed_framing_source_author_correction_notes_future" not in msn_profile.supported_modes
    assert "media_source_chain_sidecar" in msn_profile.expected_artifact_types
    assert "disputed_framing_manual_notes" in msn_profile.expected_artifact_types
    twitter_profile = default_source_method_profile_for_adapter("twitter_x")
    assert twitter_profile.profile_id == "twitter_x_post_reply_archive_fallback"
    assert "archive_result" in twitter_profile.expected_artifact_types
    twitter_public_profile = find_source_method_profile("twitter_x_public_post_archive")
    assert twitter_public_profile.adapter_id == "twitter_x"
    assert twitter_public_profile.archive_fallback_supported
    assert "canonical_url_expectation" in twitter_public_profile.required_operator_fields
    twitter_reply_profile = find_source_method_profile("twitter_x_reply_thread_archive")
    assert twitter_reply_profile.adapter_id == "twitter_x"
    assert "parent_post_reference" in twitter_reply_profile.required_operator_fields
    twitter_media_profile = find_source_method_profile("twitter_x_media_shared_backend")
    assert twitter_media_profile.adapter_id == "twitter_x"
    assert "jdownloader_api3128" in twitter_media_profile.supported_modes
    assert "media_files" in twitter_media_profile.expected_artifact_types
    assert twitter_media_profile.network_actions_performed is True
    assert twitter_media_profile.browser_automation_performed is True
    assert find_source_method_profile("youtube_media_transcript_comment").adapter_id == "youtube"
    assert find_source_method_profile("generic_article_html").adapter_id == "news_website"
    assert find_source_method_profile("generic_article_comments").adapter_id == "news_website"
    assert find_source_method_profile("archive_only_import").adapter_id == "manual_local_import"
    account_channel_profile = find_source_method_profile("account_channel_two_sided_source_link")
    assert account_channel_profile.adapter_id == "account_channel"
    assert "inbound_source_candidate" in account_channel_profile.supported_modes
    assert "outbound_review_status" in account_channel_profile.supported_modes
    assert "operator_approval_for_poll_or_send" in account_channel_profile.required_operator_fields
    assert default_source_method_profile_for_adapter("account_channel").profile_id == "account_channel_two_sided_source_link"
    assert default_source_method_profile_for_adapter("manual_local_import").profile_id == "manual_local_file_import"
    assert default_source_method_profile_for_adapter("unknown").profile_id == "generic_article_comment_manual"


if __name__ == "__main__":
    run_self_test()
    print("Source adapter self-test passed.")
