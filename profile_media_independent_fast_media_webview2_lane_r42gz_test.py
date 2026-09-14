from __future__ import annotations

from pathlib import Path

from profile_media_independent_fast_media_webview2_lane_r42gz import (
    R42GZ_BACKEND_ID,
    R42GZ_MARKER,
    R42GZ_MODE_ID,
    R42GZ_PASS_STATUS,
    _fixture_row,
    _fixture_twitter_media_lane_runner,
    build_independent_fast_media_webview2_lane_contract_r42gz,
    build_independent_fast_media_webview2_lane_r42gz,
    build_report,
)
from profile_media_background_webview2_media_observer_r42gy import R42GY_PASS_STATUS, run_background_webview2_media_observer_for_row_r42gy
from profile_media_unified_media_window_tabs_r42gw import TAB_ALL


def test_lane_contract_is_independent_and_media_only() -> None:
    contract = build_independent_fast_media_webview2_lane_contract_r42gz()
    assert contract["marker"] == R42GZ_MARKER
    assert contract["mode_id"] == R42GZ_MODE_ID
    assert contract["media_only"] is True
    assert contract["per_link_basis"] is True
    assert contract["independent_lane"] is True
    assert contract["review_window_dependency"] is False
    assert contract["source_role_interface_dependency"] is False
    assert contract["source_role_checks_enabled"] is False
    assert contract["source_role_back_and_forth_enabled"] is False
    assert contract["does_not_use_slow_review_source_role_webview2_lane"] is True


def test_independent_lane_adapts_browser_capture_fixture(tmp_path: Path | None = None) -> None:
    root = tmp_path or Path("profile_media_live_captures/r42gz_test_independent_backend_direct")
    backend = build_independent_fast_media_webview2_lane_r42gz(
        runner=_fixture_twitter_media_lane_runner,
        live=False,
        headless=True,
        browser_user_data_dir="profile_media_browser_profiles/r42gz_test_independent_lane",
        fixture_mode=True,
    )
    result = dict(
        backend.observe_media(
            {
                "source_row_id": "twitter_x:r42gz:test",
                "source_url": "https://x.com/example/status/9876543210",
                "adapter_id": "twitter_x",
                "output_root": root,
                "capture_timestamp": "20260914T000000Z",
            }
        )
    )
    assert result["marker"] == R42GZ_MARKER
    assert result["backend_id"] == R42GZ_BACKEND_ID
    assert result["mode_id"] == R42GZ_MODE_ID
    assert result["review_window_dependency"] is False
    assert result["source_role_interface_dependency"] is False
    assert result["source_role_checks_enabled"] is False
    assert result["source_role_back_and_forth_enabled"] is False
    assert result["downloads_performed"] is False
    assert result["source_role_assignment_performed"] is False
    assert len(result["events"]) >= 5
    assert len(result["media_inventory"]) >= 1
    assert "r42gz_dom.jpg" in result["final_dom"]
    assert "r42gz_independent_fast_media_webview2_lane" in result["lane_output_dir"]


def test_independent_lane_feeds_r42gy_r42gv_r42gw_pipeline(tmp_path: Path | None = None) -> None:
    root = tmp_path or Path("profile_media_live_captures/r42gz_test_independent_r42gy_pipeline")
    backend = build_independent_fast_media_webview2_lane_r42gz(
        runner=_fixture_twitter_media_lane_runner,
        live=False,
        headless=True,
        browser_user_data_dir="profile_media_browser_profiles/r42gz_test_independent_lane",
        fixture_mode=True,
    )
    receipt = run_background_webview2_media_observer_for_row_r42gy(
        _fixture_row(),
        backend=backend,
        output_root=root,
        active_tab=TAB_ALL,
        capture_timestamp="20260914T000000Z",
    )
    payload = receipt.to_dict()
    state = payload.get("unified_media_window_state") or {}
    assert receipt.status == R42GY_PASS_STATUS
    assert receipt.observation_count >= 1
    assert Path(receipt.observation_store_path).is_file()
    assert state.get("tabs") == ["all", "images", "videos"]
    assert state.get("package_count", 0) >= 2
    assert int(state.get("segment_child_count") or 0) >= 2


def test_report_green(tmp_path: Path | None = None) -> None:
    root = tmp_path or Path("profile_media_live_captures/r42gz_test_independent_report")
    report = build_report(root)
    failed = [check for check in report.checks if check.get("status") != "pass"]
    assert report.status == R42GZ_PASS_STATUS, failed
    assert not failed


def run_self_test() -> None:
    test_lane_contract_is_independent_and_media_only()
    test_independent_lane_adapts_browser_capture_fixture()
    test_independent_lane_feeds_r42gy_r42gv_r42gw_pipeline()
    test_report_green()
    print("profile_media_independent_fast_media_webview2_lane_r42gz_test: PASS")


if __name__ == "__main__":
    run_self_test()
