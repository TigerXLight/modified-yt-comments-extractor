from source_url_media_ui_contract import (
    ArchiveIconStatus,
    UrlResourceKind,
    build_default_source_url_ui_roadmap_state,
    build_example_youtube_source_url_row,
)


def test_youtube_row_uses_generic_source_url_flow_not_youtube_button() -> None:
    row = build_example_youtube_source_url_row("https://www.youtube.com/watch?v=FWxVutcyEq4&t=217s")
    data = row.to_dict()
    assert data["no_youtube_specific_button"] is True
    assert data["source_url_enter_submits"] is True
    assert row.page_title == "Special DJ by TAKU INOUE"
    assert row.platform_label == "YouTube"
    assert any(choice.kind == UrlResourceKind.TRANSCRIPT and choice.inject_into_transcript_editor for choice in row.resource_choices)
    assert any(choice.kind == UrlResourceKind.VIDEO and choice.selected_for_download for choice in row.resource_choices)


def test_clear_editor_keeps_files_contract() -> None:
    state = build_default_source_url_ui_roadmap_state(["https://www.youtube.com/watch?v=FWxVutcyEq4&t=217s"])
    rules = state.files_ordering_rule
    assert rules.clear_editor_does_not_delete_file is True
    assert rules.imported_replacement_keeps_previous_file is True
    assert rules.audio_can_play_without_transcript is True
    assert state.to_dict()["injection_selection_count"] == 1


def test_archive_status_icons_are_status_not_submit_actions() -> None:
    row = build_example_youtube_source_url_row("https://www.youtube.com/watch?v=FWxVutcyEq4&t=217s")
    statuses = {icon.provider_id: icon.status for icon in row.archive_icons}
    assert statuses["wayback"] == ArchiveIconStatus.UNKNOWN
    assert statuses["archive_today"] == ArchiveIconStatus.UNKNOWN
    assert all(icon.submit_requires_explicit_user_action for icon in row.archive_icons)


def test_generic_urls_have_text_screenshot_and_archive_choices() -> None:
    state = build_default_source_url_ui_roadmap_state(["https://news.invalid/story"])
    row = state.resolved_rows[0]
    kinds = {choice.kind for choice in row.resource_choices}
    assert UrlResourceKind.ARTICLE_TEXT in kinds
    assert UrlResourceKind.IMAGE in kinds
    assert len(row.archive_icons) == 2


def main() -> None:
    test_youtube_row_uses_generic_source_url_flow_not_youtube_button()
    test_clear_editor_keeps_files_contract()
    test_archive_status_icons_are_status_not_submit_actions()
    test_generic_urls_have_text_screenshot_and_archive_choices()
    print("source_url_media_ui_contract_test: OK")


if __name__ == "__main__":
    main()
