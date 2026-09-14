from __future__ import annotations

import inspect

from main import App


def test_app_registers_r42gz_independent_fast_media_lane_without_startup_run() -> None:
    source = inspect.getsource(App.__init__)
    assert "R42GZ_INDEPENDENT_FAST_MEDIA_WEBVIEW2_CAPTURE_LANE" in source
    assert "background_webview2_media_observer_backend" in source
    assert "build_independent_fast_media_webview2_lane_r42gz" in source
    assert "independent fast Media WebView2 lane" in source
    assert "not run at startup" in source
    assert "separate from the review/source-role WebView2 lane" in source


def test_media_window_uses_independent_media_lane_backend_attribute() -> None:
    source = inspect.getsource(App._open_unified_media_window_for_source_row)
    assert "R42GZ_INDEPENDENT_FAST_MEDIA_WEBVIEW2_CAPTURE_LANE" in source
    assert "independent/media-only" in source
    assert "not the review/source-role WebView2 lane" in source
    assert 'getattr(self, "background_webview2_media_observer_backend", None)' in source
    assert "run_background_webview2_media_observer_for_row_r42gy" in source
    assert "Review window stays separate" in source
    assert "visible WebView2/Edge" in source


def test_existing_twitter_entrypoints_still_route_to_unified_media_window() -> None:
    source = inspect.getsource(App._open_source_resource_window)
    assert 'if row.adapter_id == "twitter_x":' in source
    assert "self._open_unified_media_window_for_source_row(row_id, active_tab=active_tab)" in source


def run_self_test() -> None:
    test_app_registers_r42gz_independent_fast_media_lane_without_startup_run()
    test_media_window_uses_independent_media_lane_backend_attribute()
    test_existing_twitter_entrypoints_still_route_to_unified_media_window()
    print("main_independent_fast_media_webview2_lane_r42gz_test: PASS")


if __name__ == "__main__":
    run_self_test()
