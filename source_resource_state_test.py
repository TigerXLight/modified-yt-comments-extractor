from source_resource_state import (
    ARCHIVE_SERVICE_ARCHIVE_TODAY,
    ARCHIVE_SERVICE_ARCHIVEBOX,
    ARCHIVE_SERVICE_LOCAL_WEB_ARCHIVE,
    ARCHIVE_SERVICE_WAYBACK,
    ARCHIVE_STATUS_AUTO_CHECK_DISABLED,
    ARCHIVE_STATUS_AVAILABLE,
    ARCHIVE_STATUS_NOT_AVAILABLE,
    DISCUSSION_MODE_COMMENTS,
    RESOURCE_KIND_IMAGE,
    RESOURCE_KIND_VIDEO_AUDIO,
    SourceResourceItem,
    SourceResourceRowState,
    MediaResourceFilterState,
    archive_status_presentation,
    build_selected_media_preservation_preview,
    build_discussion_capture_options,
    build_discussion_selection_state,
    build_resource_download_dry_run,
    build_source_resource_row,
    cancel_resource_selection,
    canonicalize_msn_url,
    clear_resource_selection,
    extract_source_url_tokens,
    filter_resource_dialog_items,
    parse_source_url_intake,
    remove_source_resource_row,
    resource_dialog_state_for_row,
    select_all_resources,
    source_action_plan_text,
    state_to_json,
)


MSN_URL = (
    "HTTPS://www.msn.com/en-gb/news/world/special-dj-by-taku-inoue/"
    "ar-AA123456?ocid=feeds&utm_source=tracking#comments"
)
YOUTUBE_URL = "https://www.youtube.com/watch?v=aB3_dE-9xYz"
TWITTER_URL = "https://x.com/example/status/12345"


def test_msn_canonicalization_removes_tracking_and_preserves_article_id() -> None:
    canonical = canonicalize_msn_url(MSN_URL)

    assert canonical == (
        "https://www.msn.com/en-gb/news/world/special-dj-by-taku-inoue/ar-AA123456"
    )
    assert "ocid" not in canonical
    assert "utm_source" not in canonical
    assert "#comments" not in canonical


def test_source_row_uses_real_msn_title_without_fake_fixture_media() -> None:
    row = build_source_resource_row(MSN_URL)

    assert row.adapter_id == "msn"
    assert row.adapter_display_name == "MSN"
    assert row.title == "Special Dj By Taku Inoue"
    assert row.comments_supported is True
    assert row.livechat_supported is False
    assert row.image_resources == ()
    assert row.video_audio_resources == ()
    assert any("no longer injects fake fixture media" in warning for warning in row.warnings)


def test_archive_status_presentation_is_accessible_and_does_not_fabricate_dates() -> None:
    saved = archive_status_presentation(
        ARCHIVE_SERVICE_WAYBACK,
        ARCHIVE_STATUS_AVAILABLE,
        saved_date="2026-07-15",
    )
    missing = archive_status_presentation(
        ARCHIVE_SERVICE_ARCHIVE_TODAY,
        ARCHIVE_STATUS_NOT_AVAILABLE,
        saved_date="2026-07-15",
    )

    assert saved.color_name == "green"
    assert saved.label == "Saved"
    assert saved.saved_date == "2026-07-15"
    archivebox = archive_status_presentation(
        ARCHIVE_SERVICE_ARCHIVEBOX,
        "not_checked",
    )
    assert archivebox.label == "Not checked"
    assert archivebox.color_name == "gray"
    assert missing.color_name == "red"
    assert missing.label == "Not saved"
    assert missing.saved_date == ""


def test_archive_auto_check_disabled_starts_gray_without_checks() -> None:
    row = build_source_resource_row(MSN_URL, archive_auto_check_enabled=False)

    assert {status.status for status in row.archive_statuses} == {
        ARCHIVE_STATUS_AUTO_CHECK_DISABLED
    }
    assert {status.color_name for status in row.archive_statuses} == {"gray"}
    assert [status.service_id for status in row.archive_statuses] == [
        ARCHIVE_SERVICE_WAYBACK,
        ARCHIVE_SERVICE_ARCHIVE_TODAY,
        ARCHIVE_SERVICE_LOCAL_WEB_ARCHIVE,
    ]


def test_twitter_row_uses_compact_settings_only_controls() -> None:
    row = build_source_resource_row(TWITTER_URL)

    assert row.adapter_id == "twitter_x"
    assert row.archive_statuses == ()
    assert row.image_resources == ()
    assert row.video_audio_resources == ()
    assert "Post/Thread" in row.comments_status
    assert "settings" in row.comments_status
    assert "shared backend" in row.comments_status
    assert "shared backend" in row.provenance
    assert row.title in {"Twitter/X post", "This stuff is still happening. It hasn’t stopped."}
    assert row.display_title in {"Twitter/X post", "This stuff is still happening. It hasn’t stopped."}
    assert row.preview_text in {"", "This stuff is still happening. It hasn’t stopped."}

    preview = "This stuff is still happening. It hasn't stopped."
    preview_row = build_source_resource_row(
        "https://x.com/elonmusk/status/1877644315867963403",
        title=preview,
    )
    assert preview_row.title == preview
    assert preview_row.display_title == preview
    assert preview_row.preview_text == preview
    assert "1877644315867963403" not in preview_row.title


def test_url_token_parser_accepts_mixed_separators_and_encoded_commas() -> None:
    encoded = "https://www.msn.com/en-us/news/story/ar-AA999999?title=a%2Cb"
    tokens = extract_source_url_tokens(
        f"{YOUTUBE_URL}, {MSN_URL};\n{encoded} trailing words"
    )

    assert tokens == (YOUTUBE_URL, MSN_URL, encoded)


def test_source_url_intake_preserves_order_dedupes_and_retains_invalid_text() -> None:
    text = f"bad words {MSN_URL}, {YOUTUBE_URL} {MSN_URL} https://example.invalid/x"
    result = parse_source_url_intake(text)

    assert [row.adapter_id for row in result.rows] == ["msn", "youtube", "webpage"]
    assert result.accepted_raw_urls == (MSN_URL, YOUTUBE_URL, "https://example.invalid/x")
    assert result.duplicate_raw_urls == (MSN_URL,)
    assert "https://example.invalid/x" not in result.invalid_tokens
    assert "bad" in result.invalid_tokens
    assert result.remaining_text
    assert "network" in result.scope




def test_generic_webpage_row_accepts_localhost_for_image_discovery() -> None:
    url = "http://127.0.0.1:8765/article.html"
    row = build_source_resource_row(url)

    assert row.adapter_id == "webpage"
    assert row.adapter_display_name == "Webpage"
    assert row.canonical_url == url
    assert row.title == "Article.Html"
    assert row.comments_supported is False
    assert row.livechat_supported is False
    assert row.image_resources == ()
    assert "media discovery is user-triggered" in row.provenance

    result = parse_source_url_intake(url)
    assert len(result.rows) == 1
    assert result.rows[0].adapter_id == "webpage"
    assert result.invalid_tokens == ()

def test_discussion_selection_persists_and_falls_back_after_removal() -> None:
    msn = build_source_resource_row(MSN_URL)
    youtube = build_source_resource_row(YOUTUBE_URL)
    selected = build_discussion_selection_state((msn, youtube), youtube.row_id)
    fallback = build_discussion_selection_state((msn,), youtube.row_id)

    assert selected.selected_row_id == youtube.row_id
    assert selected.comments_supported is True
    assert selected.livechat_supported is True
    assert fallback.selected_row_id == msn.row_id
    assert fallback.fallback_applied is True
    assert fallback.comments_supported is True
    assert fallback.livechat_supported is False


def test_screenshot_intents_are_independent_and_inactive_when_parent_off() -> None:
    msn = build_source_resource_row(MSN_URL)
    options = build_discussion_capture_options(
        (msn,),
        selected_row_id=msn.row_id,
        webpage_selected=True,
        webpage_screenshot_requested=True,
        comments_selected=False,
        livechat_selected=True,
        comments_screenshot_requested=True,
        livechat_screenshot_requested=True,
    )

    assert options.webpage_active is True
    assert options.webpage_screenshot_active is True
    assert options.comments_screenshot_requested is True
    assert options.livechat_screenshot_requested is True
    assert options.comments_screenshot_active is False
    assert options.livechat_screenshot_active is False


def test_source_removal_updates_selection_and_allows_readd() -> None:
    msn = build_source_resource_row(MSN_URL)
    youtube = build_source_resource_row(YOUTUBE_URL)

    remaining, selected = remove_source_resource_row(
        (msn, youtube),
        msn.row_id,
        selected_row_id=msn.row_id,
    )
    assert remaining == (youtube,)
    assert selected == youtube.row_id

    final_rows, final_selected = remove_source_resource_row(
        remaining,
        youtube.row_id,
        selected_row_id=youtube.row_id,
    )
    assert final_rows == ()
    assert final_selected == ""

    readded = parse_source_url_intake(MSN_URL, existing_rows=final_rows)
    assert len(readded.rows) == 1


def test_resource_dialog_selection_all_clear_cancel_and_dry_run() -> None:
    row = build_source_resource_row(MSN_URL)
    state = resource_dialog_state_for_row(row, RESOURCE_KIND_IMAGE)
    selected = select_all_resources(state)
    cleared = clear_resource_selection(selected)
    cancelled = cancel_resource_selection(selected)
    dry_run = build_resource_download_dry_run(selected)

    assert len(state.resources) == 0
    assert selected.selection_count == 0
    assert cleared.selected_resource_ids == ()
    assert cancelled.selected_resource_ids == state.committed_resource_ids
    assert dry_run.selected_count == 0
    assert dry_run.downloads_performed == "none"
    assert "not enabled" in dry_run.message


def test_video_audio_resource_dialog_has_no_fake_fixture_media() -> None:
    row = build_source_resource_row(MSN_URL)
    state = resource_dialog_state_for_row(row, RESOURCE_KIND_VIDEO_AUDIO)

    assert state.resources == ()


def test_media_resource_filters_and_preservation_preview_are_local_only() -> None:
    row = SourceResourceRowState(
        row_id="row-1",
        raw_url="https://example.com/article",
        canonical_url="https://example.com/article",
        adapter_id="generic",
        adapter_display_name="Generic",
        source_id="article",
        title="Article",
        domain="example.com",
        display_label="Article",
        image_resources=(
            SourceResourceItem(
                resource_id="img-1",
                source_row_id="row-1",
                resource_kind=RESOURCE_KIND_IMAGE,
                reference_url="https://example.com/media/photo.jpg",
                display_name="Main photo",
                media_type="image",
                extension="jpg",
                width=1200,
                height=800,
                from_link=True,
                provenance="page link candidate",
            ),
            SourceResourceItem(
                resource_id="img-2",
                source_row_id="row-1",
                resource_kind=RESOURCE_KIND_IMAGE,
                reference_url="https://cdn.example.com/icon.png",
                display_name="Icon",
                media_type="image",
                extension="png",
                width=120,
                height=120,
                from_link=False,
                provenance="decorative candidate",
            ),
        ),
    )
    state = resource_dialog_state_for_row(row, RESOURCE_KIND_IMAGE)
    filtered = filter_resource_dialog_items(
        state,
        MediaResourceFilterState(
            url_filter="photo",
            min_width=600,
            min_height=400,
            only_linked_resources=True,
        ),
    )
    selected = filtered.__class__(
        source_row_id=filtered.source_row_id,
        resource_kind=filtered.resource_kind,
        resources=filtered.resources,
        selected_resource_ids=("img-1",),
        committed_resource_ids=(),
    )
    preview = build_selected_media_preservation_preview(row, selected)

    assert [item.resource_id for item in filtered.resources] == ["img-1"]
    assert preview.selected_count == 1
    assert preview.records[0]["schema_version"] == "rendered-citation-media-intake-v77e"
    assert preview.records[0]["media_url"] == "https://example.com/media/photo.jpg"
    assert preview.records[0]["local_file_present"] is False
    assert preview.records[0]["local_file_role"] == "source_reference_only"
    assert preview.network_actions_performed == "none"
    assert preview.downloads_performed == "none"
    assert preview.files_written == "none"
    assert preview.records[0]["safety_flags"]["web_download_performed"] is False
    assert preview.records[0]["safety_flags"]["media_download_performed"] is False


def test_action_plan_and_json_are_deterministic_and_local_only() -> None:
    row = build_source_resource_row(MSN_URL)
    discussion = build_discussion_capture_options(
        (row,),
        selected_row_id=row.row_id,
        webpage_selected=True,
        webpage_screenshot_requested=True,
        comments_selected=True,
        livechat_selected=False,
        comments_screenshot_requested=True,
        livechat_screenshot_requested=True,
    )
    text = source_action_plan_text(
        row=row,
        discussion=discussion,
        archive_auto_check_enabled=True,
        images_selected=1,
        video_audio_selected=2,
    )
    rendered_json = state_to_json(row)

    assert "Source action plan" in text
    assert "Webpage selected: enabled" in text
    assert "Webpage screenshot intent: enabled" in text
    assert "Comments screenshot intent: enabled" in text
    assert "Livechat screenshot intent: inactive" in text
    assert "Network actions performed: none" in text
    assert '"adapter_id": "msn"' in rendered_json
    assert "requests" not in rendered_json
    assert "selenium" not in rendered_json


def run_self_test() -> None:
    test_msn_canonicalization_removes_tracking_and_preserves_article_id()
    test_source_row_uses_real_msn_title_without_fake_fixture_media()
    test_archive_status_presentation_is_accessible_and_does_not_fabricate_dates()
    test_archive_auto_check_disabled_starts_gray_without_checks()
    test_twitter_row_uses_compact_settings_only_controls()
    test_url_token_parser_accepts_mixed_separators_and_encoded_commas()
    test_source_url_intake_preserves_order_dedupes_and_retains_invalid_text()
    test_discussion_selection_persists_and_falls_back_after_removal()
    test_screenshot_intents_are_independent_and_inactive_when_parent_off()
    test_source_removal_updates_selection_and_allows_readd()
    test_resource_dialog_selection_all_clear_cancel_and_dry_run()
    test_video_audio_resource_dialog_has_no_fake_fixture_media()
    test_media_resource_filters_and_preservation_preview_are_local_only()
    test_action_plan_and_json_are_deterministic_and_local_only()


if __name__ == "__main__":
    run_self_test()
    print("source_resource_state.py: OK")
