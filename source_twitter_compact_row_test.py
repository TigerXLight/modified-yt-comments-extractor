from __future__ import annotations

from source_resource_state import build_source_resource_row
from source_twitter_compact_row import (
    REMOVED_TWITTER_BUTTON_LABELS,
    TWITTER_COMPACT_MODES,
    TWITTER_SCREENSHOT_MODES,
    TWITTER_SCREENSHOT_MODE_VALUES,
    build_twitter_compact_row_state,
    is_twitter_account_url,
)


def test_twitter_compact_row_uses_post_thread_only() -> None:
    row = build_source_resource_row("https://x.com/example/status/12345")
    state = build_twitter_compact_row_state(row)
    assert state.dropdown_options == TWITTER_COMPACT_MODES
    assert state.dropdown_options == ("Post", "Thread")
    assert state.icon_style == "x_twitter_dark_large_source_downscaled"
    assert state.compact_pattern == "youtube_v19_parity"
    assert state.compact_row_height == 72
    assert state.compact_control_width == 95
    assert state.checkbox_position == "x4_y2_12x12_youtube_parity"
    assert state.checkbox_behavior == "checked_enables_inline_post_thread_selector"
    assert state.show_type_dropdown_setting_label == "Show type dropdown on X/Twitter source row"
    assert state.settings_treatment == "compact_cog_inside_row_settings"
    assert state.delete_treatment == "youtube_compact_corner_remove_x"
    assert state.dropdown_behavior == "youtube_inline_menu_style"
    assert state.icon_asset == "assets/ytce_x_icon.png"
    assert state.icon_position == "final_user_selected_post_w95_thread_w97_refresh_rebuild"
    assert state.article_screenshot_checkbox_visible is False
    assert state.article_screenshot_location == "settings_screenshot_section"
    assert state.screenshot_options == TWITTER_SCREENSHOT_MODES
    assert state.screenshot_options == ("None", "Post", "Both")
    assert state.screenshot_option_values == TWITTER_SCREENSHOT_MODE_VALUES
    assert state.screenshot_option_values == ("none", "post", "both")
    assert state.media_download_inside_settings is True
    assert state.media_download_main_row_button_visible is False


def test_twitter_compact_row_hides_old_removed_buttons() -> None:
    row = build_source_resource_row("https://twitter.com/example/status/12345")
    state = build_twitter_compact_row_state(row)
    assert state.archive_controls_visible is False
    assert state.local_export_button_visible is False
    assert state.add_review_draft_button_visible is False
    assert state.review_flow_summary_button_visible is False
    for label in REMOVED_TWITTER_BUTTON_LABELS:
        assert label in state.removed_buttons_hidden


def test_twitter_account_url_thread_semantics_are_preserved() -> None:
    row = build_source_resource_row("https://x.com/example")
    state = build_twitter_compact_row_state(row)
    assert is_twitter_account_url(row.canonical_url) is True
    assert "Thread means account/timeline posts" in state.account_thread_semantics
    assert "Post means profile/basic post target" in state.account_thread_semantics


def test_twitter_status_title_uses_preview_or_neutral_fallback() -> None:
    preview = "This stuff is still happening. It hasn't stopped."
    preview_row = build_source_resource_row(
        "https://x.com/elonmusk/status/1877644315867963403",
        title=preview,
    )
    preview_state = build_twitter_compact_row_state(preview_row)
    assert preview_row.title == preview
    assert preview_state.display_title == preview
    assert preview_state.preview_text == preview
    assert "1877644315867963403" not in preview_row.title

    fallback_row = build_source_resource_row("https://x.com/elonmusk/status/1877644315867963403")
    fallback_state = build_twitter_compact_row_state(fallback_row)
    assert fallback_row.title == "This stuff is still happening. It hasn’t stopped."
    assert fallback_state.display_title in {"Twitter/X post", "This stuff is still happening. It hasn’t stopped."}
    assert "1877644315867963403" not in fallback_row.title


def main() -> None:
    test_twitter_compact_row_uses_post_thread_only()
    test_twitter_compact_row_hides_old_removed_buttons()
    test_twitter_account_url_thread_semantics_are_preserved()
    test_twitter_status_title_uses_preview_or_neutral_fallback()
    print("source_twitter_compact_row_test OK")


if __name__ == "__main__":
    main()
