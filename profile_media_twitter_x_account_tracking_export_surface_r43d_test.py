from __future__ import annotations

import json
import shutil
from pathlib import Path

from profile_media_twitter_x_account_tracking_export_surface_r43d import (
    R43D_MARKER,
    R43D_PASS_STATUS,
    TwitterXAccountTrackingExportRequestR43D,
    build_report,
    build_twitter_x_account_tracking_export_surface_contract_r43d,
    build_twitter_x_account_tracking_export_surface_r43d,
)


def test_contract_keeps_tracking_outside_webview2_and_review_lane() -> None:
    contract = build_twitter_x_account_tracking_export_surface_contract_r43d()
    assert contract["marker"] == R43D_MARKER
    assert contract["independent_fast_media_lane"] is True
    assert contract["webview2_internals_copied"] is False
    assert contract["review_window_dependency"] is False
    assert contract["source_role_interface_dependency"] is False
    assert contract["source_role_checks_enabled"] is False
    assert contract["hidden_x_api_scraping_enabled"] is False
    assert contract["remote_media_downloads_enabled"] is False


def test_surface_writes_request_runbook_and_invokes_r43b_r43a_r43c(tmp_path: Path) -> None:
    surface = build_twitter_x_account_tracking_export_surface_r43d(output_root=tmp_path)
    result = surface.run_account_export(
        TwitterXAccountTrackingExportRequestR43D(
            account_url="https://x.com/example",
            account_handle="example",
            capture_timestamp="20260915T030000Z",
            output_root=str(tmp_path),
            fixture_mode=True,
        )
    )
    assert result.status == R43D_PASS_STATUS
    assert result.record_count == 2
    assert result.post_count == 1
    assert result.repost_count == 1
    assert result.media_count == 2
    assert Path(result.request_path).is_file()
    assert Path(result.runbook_path).is_file()
    assert Path(result.surface_receipt_path).is_file()
    assert Path(result.account_record_path).is_file()
    assert Path(result.screenshot_receipts_index_path).is_file()
    account_record = Path(result.account_record_path).read_text(encoding="utf-8")
    runbook = Path(result.runbook_path).read_text(encoding="utf-8")
    assert "post_4444444444444444444" in account_record
    assert "repost_5555555555555555555__original_9999999999999999999" in account_record
    assert "media/images" in account_record
    assert "media/videos" in account_record
    assert "Screenshot receipts index" in runbook
    receipt = json.loads(Path(result.surface_receipt_path).read_text(encoding="utf-8"))
    assert receipt["surface_contract"]["webview2_role"].startswith("site rendering and observation only")
    assert receipt["side_effect_flags"]["webview2_session_started_by_r43d"] is False
    assert receipt["side_effect_flags"]["source_role_checks_performed"] is False


def test_report_green(tmp_path: Path) -> None:
    report = build_report(tmp_path)
    assert report.status == R43D_PASS_STATUS, [c for c in report.checks if c.get("status") != "pass"]
    assert report.passed
    data = report.to_dict()
    assert data["surface_result"]["status"] == R43D_PASS_STATUS
    assert data["surface_result"]["screenshot_receipts_index_path"]
    assert all(c["status"] == "pass" for c in data["checks"])


def run_self_test() -> None:
    test_contract_keeps_tracking_outside_webview2_and_review_lane()
    root = Path("profile_media_live_captures/r43d_twitter_x_account_tracking_export_surface_test")
    shutil.rmtree(root, ignore_errors=True)
    test_surface_writes_request_runbook_and_invokes_r43b_r43a_r43c(root / "surface")
    test_report_green(root / "report")


if __name__ == "__main__":
    run_self_test()
    print("profile_media_twitter_x_account_tracking_export_surface_r43d_test: PASS")
