from __future__ import annotations

import tempfile
from pathlib import Path

from profile_media_background_webview2_media_observer_r42gy import (
    BACKGROUND_WEBVIEW2_MODE_ID,
    R42GY_ESCALATE_VISIBLE_STATUS,
    R42GY_MARKER,
    R42GY_PASS_STATUS,
    _fixture_backend,
    _fixture_escalation_backend,
    _fixture_row,
    build_background_webview2_observation_request_r42gy,
    build_report,
    run_background_webview2_media_observer_for_row_r42gy,
)
from profile_media_unified_media_window_tabs_r42gw import TAB_ALL, flatten_media_window_tree


def test_request_records_background_webview2_mode_and_boundaries() -> None:
    row = _fixture_row()
    request = build_background_webview2_observation_request_r42gy(row, active_tab=TAB_ALL, output_root="out")
    assert request["marker"] == R42GY_MARKER
    assert request["mode_id"] == BACKGROUND_WEBVIEW2_MODE_ID
    assert request["review_window_separate"] is True
    assert "no token or cookie extraction" in request["hard_boundaries"]
    assert request["source_url"] == "https://x.com/example/status/1234567890"


def test_fixture_backend_writes_observation_store_and_media_tree() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        row = _fixture_row()
        receipt = run_background_webview2_media_observer_for_row_r42gy(
            row,
            backend=_fixture_backend,
            output_root=tmp,
            capture_timestamp="20260914T000000Z",
        )
        assert receipt.status == R42GY_PASS_STATUS
        assert receipt.observation_count >= 5
        assert receipt.segment_count >= 2
        assert Path(receipt.observation_store_path).is_file()
        assert Path(receipt.segment_table_path).is_file()
        assert receipt.unified_media_window_state is not None
        state = receipt.unified_media_window_state
        assert list(state.tabs) == ["all", "images", "videos"]
        assert state.review_window_separate is True
        assert state.segment_child_count >= 2
        rows = list(flatten_media_window_tree(state, tab_id=TAB_ALL, include_children=True))
        assert any(row.get("row_role") == "package" for row in rows)
        assert any(row.get("media_class") == "segment" and row.get("selectable") is False for row in rows)
        assert receipt.bridge_state and receipt.bridge_state["media_state_source_model"] == "r42gv_visible_browser_observation_store"


def test_escalation_backend_does_not_build_hidden_bypass_path() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        receipt = run_background_webview2_media_observer_for_row_r42gy(
            _fixture_row(),
            backend=_fixture_escalation_backend,
            output_root=tmp,
            capture_timestamp="20260914T000001Z",
        )
        assert receipt.status == R42GY_ESCALATE_VISIBLE_STATUS
        assert receipt.visible_escalation_required is True
        assert receipt.observation_count == 0
        flags = receipt.side_effect_flags
        assert flags["captcha_or_challenge_bypass_performed"] is False
        assert flags["cookie_or_token_extraction_performed"] is False
        assert flags["hidden_x_api_scraping_performed"] is False


def test_no_backend_is_blocked_not_claimed_success() -> None:
    receipt = run_background_webview2_media_observer_for_row_r42gy(
        _fixture_row(),
        backend=None,
        output_root="unused",
        capture_timestamp="20260914T000002Z",
    )
    assert receipt.status.startswith("BLOCKED_")
    assert receipt.observation_count == 0
    assert receipt.side_effect_flags["background_webview2_backend_called"] is False


def test_report_green() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        report = build_report(tmp)
        failed = [check for check in report.checks if check.get("status") != "pass"]
        assert report.status == R42GY_PASS_STATUS, failed
        assert report.passed, failed
        names = {check["name"] for check in report.checks if check["status"] == "pass"}
        assert "background_webview2_backend_invoked" in names
        assert "r42gv_observation_store_written" in names
        assert "unified_media_window_state_refreshed_from_observer" in names
        assert "visible_escalation_triggered_for_challenge" in names
        assert "plain_machine_urls" in names


def run_self_test() -> None:
    test_request_records_background_webview2_mode_and_boundaries()
    test_fixture_backend_writes_observation_store_and_media_tree()
    test_escalation_backend_does_not_build_hidden_bypass_path()
    test_no_backend_is_blocked_not_claimed_success()
    test_report_green()
    print("profile_media_background_webview2_media_observer_r42gy_test: PASS")


if __name__ == "__main__":
    run_self_test()
