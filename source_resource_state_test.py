from source_resource_state import (
    ARCHIVE_SERVICE_ARCHIVE_TODAY,
    ARCHIVE_SERVICE_ARCHIVEBOX,
    ARCHIVE_SERVICE_WAYBACK,
    ARCHIVE_STATUS_AUTO_CHECK_DISABLED,
    ARCHIVE_STATUS_AVAILABLE,
    ARCHIVE_STATUS_NOT_AVAILABLE,
    DISCUSSION_MODE_COMMENTS,
    RESOURCE_KIND_IMAGE,
    RESOURCE_KIND_VIDEO_AUDIO,
    archive_status_presentation,
    build_discussion_capture_options,
    build_discussion_selection_state,
    build_resource_download_dry_run,
    build_source_resource_row,
    cancel_resource_selection,
    canonicalize_msn_url,
    clear_resource_selection,
    extract_source_url_tokens,
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


def test_msn_canonicalization_removes_tracking_and_preserves_article_id() -> None:
    canonical = canonicalize_msn_url(MSN_URL)

    assert canonical == (
        "https://www.msn.com/en-gb/news/world/special-dj-by-taku-inoue/ar-AA123456"
    )
    assert "ocid" not in canonical
    assert "utm_source" not in canonical
    assert "#comments" not in canonical


def test_source_row_uses_msn_fixture_resources_and_comments_without_livechat() -> None:
    row = build_source_resource_row(MSN_URL)

    assert row.adapter_id == "msn"
    assert row.adapter_display_name == "MSN"
    assert row.title == "Special DJ by TAKU INOUE"
    assert row.comments_supported is True
    assert row.livechat_supported is False
    assert row.image_resources[0].display_name == "Special DJ hero image"
    assert row.image_resources[1].animated is True
    assert row.video_audio_resources[0].media_type == "video"
    assert row.video_audio_resources[1].extension == "mp3"
    assert any("shadow-root" in warning for warning in row.warnings)


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
        ARCHIVE_SERVICE_ARCHIVEBOX,
    ]


def test_url_token_parser_accepts_mixed_separators_and_encoded_commas() -> None:
    encoded = "https://www.msn.com/en-us/news/story/ar-AA999999?title=a%2Cb"
    tokens = extract_source_url_tokens(
        f"{YOUTUBE_URL}, {MSN_URL};\n{encoded} trailing words"
    )

    assert tokens == (YOUTUBE_URL, MSN_URL, encoded)


def test_source_url_intake_preserves_order_dedupes_and_retains_invalid_text() -> None:
    text = f"bad words {MSN_URL}, {YOUTUBE_URL} {MSN_URL} https://example.invalid/x"
    result = parse_source_url_intake(text)

    assert [row.adapter_id for row in result.rows] == ["msn", "youtube"]
    assert result.accepted_raw_urls == (MSN_URL, YOUTUBE_URL)
    assert result.duplicate_raw_urls == (MSN_URL,)
    assert "https://example.invalid/x" in result.invalid_tokens
    assert "bad" in result.invalid_tokens
    assert result.remaining_text
    assert "network" in result.scope


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

    assert len(state.resources) == 2
    assert selected.selection_count == 2
    assert cleared.selected_resource_ids == ()
    assert cancelled.selected_resource_ids == state.committed_resource_ids
    assert dry_run.selected_count == 2
    assert dry_run.downloads_performed == "none"
    assert "not enabled" in dry_run.message


def test_video_audio_resource_dialog_filters_media_resources() -> None:
    row = build_source_resource_row(MSN_URL)
    state = resource_dialog_state_for_row(row, RESOURCE_KIND_VIDEO_AUDIO)

    assert [item.media_type for item in state.resources] == ["video", "audio"]


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
    test_source_row_uses_msn_fixture_resources_and_comments_without_livechat()
    test_archive_status_presentation_is_accessible_and_does_not_fabricate_dates()
    test_archive_auto_check_disabled_starts_gray_without_checks()
    test_url_token_parser_accepts_mixed_separators_and_encoded_commas()
    test_source_url_intake_preserves_order_dedupes_and_retains_invalid_text()
    test_discussion_selection_persists_and_falls_back_after_removal()
    test_screenshot_intents_are_independent_and_inactive_when_parent_off()
    test_source_removal_updates_selection_and_allows_readd()
    test_resource_dialog_selection_all_clear_cancel_and_dry_run()
    test_video_audio_resource_dialog_filters_media_resources()
    test_action_plan_and_json_are_deterministic_and_local_only()


if __name__ == "__main__":
    run_self_test()
    print("source_resource_state.py: OK")
