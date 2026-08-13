from __future__ import annotations

from source_resource_state import build_source_resource_row
from source_twitter_compact_row import (
    REMOVED_TWITTER_BUTTON_LABELS,
    TWITTER_COMPACT_MODES,
    build_twitter_compact_row_state,
    is_twitter_account_url,
)


def test_twitter_compact_row_uses_post_thread_only() -> None:
    row = build_source_resource_row("https://x.com/example/status/12345")
    state = build_twitter_compact_row_state(row)
    assert state.dropdown_options == TWITTER_COMPACT_MODES
    assert state.dropdown_options == ("Post", "Thread")
    assert state.icon_style == "x_twitter_dark"
    assert state.compact_pattern == "youtube_v19_parity"
    assert state.article_screenshot_checkbox_visible is True
    assert state.visible_capture_options == ("article_screenshot",)
    assert state.media_download_inside_settings is True


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


def main() -> None:
    test_twitter_compact_row_uses_post_thread_only()
    test_twitter_compact_row_hides_old_removed_buttons()
    test_twitter_account_url_thread_semantics_are_preserved()
    print("source_twitter_compact_row_test OK")


if __name__ == "__main__":
    main()
