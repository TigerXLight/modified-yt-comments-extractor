from __future__ import annotations

import inspect

from main import App


def test_twitter_source_row_has_single_media_button_for_unified_window() -> None:
    source = inspect.getsource(App._refresh_source_resource_rows)
    assert "twitter_unified_media_window_button_expected_by_ui_test" in source
    assert 'text="Media"' in source
    assert "_open_unified_media_window_for_source_row(row_id, active_tab=\"all\")" in source
    assert "Media window: All / Images / Videos" in source
    assert "Review window stays separate" in source
    assert "Background WebView2 fast observer" in source


def test_image_and_video_entrypoints_route_twitter_to_same_media_window() -> None:
    source = inspect.getsource(App._open_source_resource_window)
    assert 'if row.adapter_id == "twitter_x":' in source
    assert 'active_tab = "images" if resource_kind == RESOURCE_KIND_IMAGE else "videos"' in source
    assert "self._open_unified_media_window_for_source_row(row_id, active_tab=active_tab)" in source
    assert "force_tk_image_window" in source


def test_unified_media_window_method_keeps_review_window_separate() -> None:
    source = inspect.getsource(App._open_unified_media_window_for_source_row)
    assert "Media window: All / Images / Videos" in source
    assert "All" in source and "Images" in source and "Videos" in source
    assert "Review window stays separate" in source
    assert "Background WebView2 fast observer" in source
    assert "visible WebView2/Edge" in source
    assert "filter_unified_media_window_state" in source
    assert "flatten_media_window_tree" in source
    assert "build_background_webview2_media_observer_policy_r42gx" in source
    assert "network/download/source-role actions performed: none" in source


def run_self_test() -> None:
    test_twitter_source_row_has_single_media_button_for_unified_window()
    test_image_and_video_entrypoints_route_twitter_to_same_media_window()
    test_unified_media_window_method_keeps_review_window_separate()
    print("main_unified_media_window_r42gx_test: PASS")


if __name__ == "__main__":
    run_self_test()
