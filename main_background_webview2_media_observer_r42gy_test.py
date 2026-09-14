from __future__ import annotations

import inspect

from main import App


def test_unified_media_window_has_background_observer_runtime_button() -> None:
    source = inspect.getsource(App._open_unified_media_window_for_source_row)
    assert "R42GY_BACKGROUND_WEBVIEW2_FAST_MEDIA_OBSERVER_RUNTIME" in source
    assert "Run background WebView2" in source
    assert "run_background_webview2_media_observer_for_row_r42gy" in source
    assert "background_webview2_media_observer_backend" in source
    assert "base_state_box" in source
    assert "Review window stays separate" in source


def test_background_observer_runtime_keeps_visible_escalation_policy() -> None:
    source = inspect.getsource(App._open_unified_media_window_for_source_row)
    assert "background_webview2_backend_not_configured" in source
    assert "ESCALATE_R42GY_VISIBLE_WEBVIEW2_OR_EDGE_HUMAN_CONFIRMATION" in source
    assert "visible WebView2/Edge" in source
    assert "No background WebView2 observer backend" in source


def test_existing_twitter_entrypoints_still_route_to_unified_media_window() -> None:
    source = inspect.getsource(App._open_source_resource_window)
    assert 'if row.adapter_id == "twitter_x":' in source
    assert "self._open_unified_media_window_for_source_row(row_id, active_tab=active_tab)" in source


def run_self_test() -> None:
    test_unified_media_window_has_background_observer_runtime_button()
    test_background_observer_runtime_keeps_visible_escalation_policy()
    test_existing_twitter_entrypoints_still_route_to_unified_media_window()
    print("main_background_webview2_media_observer_r42gy_test: PASS")


if __name__ == "__main__":
    run_self_test()
