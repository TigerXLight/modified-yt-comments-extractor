from source_website_method_catalog import (
    AccessModeLabel,
    SourceMethodStatus,
    build_default_source_website_method_catalog,
    source_method_catalog_summary_lines,
)


def test_catalog_contains_existing_youtube_and_generic_sources() -> None:
    catalog = build_default_source_website_method_catalog()
    assert catalog.find_method("youtube_transcripts").status == SourceMethodStatus.EXISTING_SUPPORTED
    assert catalog.find_method("youtube_comments").status == SourceMethodStatus.EXISTING_SUPPORTED
    assert catalog.find_method("youtube_livechat").status == SourceMethodStatus.EXISTING_SUPPORTED
    assert catalog.find_method("generic_article_text").supports_readable_article_text is True
    assert catalog.find_method("generic_full_page_screenshot").supports_full_page_screenshot is True
    assert catalog.find_method("archive_only_import").default_access_modes == (
        AccessModeLabel.ARCHIVED_COPY,
        AccessModeLabel.MANUAL_IMPORT,
    )


def test_catalog_has_future_social_and_video_adapter_families() -> None:
    catalog = build_default_source_website_method_catalog()
    expected = {
        "reddit_comments",
        "tiktok_comments",
        "twitch_livechat",
        "bluesky_threads",
        "threads_posts",
        "instagram_comments",
        "facebook_comments",
        "pinterest_comments",
        "medium_responses",
        "tumblr_posts_notes",
        "linkedin_posts_comments",
        "quora_answers_comments",
        "forum_threads",
        "news_site_comments",
        "vimeo_media",
        "dailymotion_media",
        "rumble_media",
        "peertube_media",
        "odysee_media",
        "kick_livechat",
    }
    actual = {method.method_id for method in catalog.methods()}
    assert expected.issubset(actual)
    assert all(catalog.find_method(method_id).status == SourceMethodStatus.PLANNED_ADAPTER_FAMILY for method_id in expected)


def test_catalog_does_not_claim_live_execution() -> None:
    catalog = build_default_source_website_method_catalog()
    serialized = str(catalog.to_dict()).lower()
    forbidden = ["completed evidence", "live verified", "downloaded media", "credentials_value", "api_key"]
    assert not any(token in serialized for token in forbidden)
    assert catalog.find_method("generic_comments_site_selector").status == SourceMethodStatus.LIVE_APPROVED_ONLY


def test_catalog_summary_lines_are_human_readable() -> None:
    lines = source_method_catalog_summary_lines()
    joined = "\n".join(lines)
    assert "Source method families:" in joined
    assert "Existing supported:" in joined
    assert "Boundary:" in joined


def main() -> None:
    test_catalog_contains_existing_youtube_and_generic_sources()
    test_catalog_has_future_social_and_video_adapter_families()
    test_catalog_does_not_claim_live_execution()
    test_catalog_summary_lines_are_human_readable()
    print("source_website_method_catalog_test: OK")


if __name__ == "__main__":
    main()
