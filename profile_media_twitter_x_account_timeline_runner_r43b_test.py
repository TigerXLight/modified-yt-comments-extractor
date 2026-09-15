from __future__ import annotations

import json
import tempfile
from pathlib import Path

from profile_media_twitter_x_account_timeline_runner_r43b import (
    R43B_MARKER,
    R43B_PASS_STATUS,
    TwitterXAccountTimelineRunnerConfigR43B,
    _FixtureMediaLaneBackendR43B,
    _fixture_record_source_with_pause_recovery,
    _fixture_timeline_records,
    build_report,
    build_twitter_x_account_timeline_runner_contract_r43b,
    build_twitter_x_account_timeline_runner_r43b,
)


def test_timeline_runner_writes_progress_pause_recovery_and_ledger() -> None:
    with tempfile.TemporaryDirectory(prefix="r43b_timeline_runner_") as tmp:
        root = Path(tmp)
        runner = build_twitter_x_account_timeline_runner_r43b(
            media_lane_backend=_FixtureMediaLaneBackendR43B(),
            record_source=_fixture_record_source_with_pause_recovery,
            config=TwitterXAccountTimelineRunnerConfigR43B(
                output_root=str(root / "runner"),
                ledger_output_root=str(root / "source_exports" / "twitter_x"),
                fixture_mode=True,
            ),
        )
        result = runner.run(
            account_handle="examaddaorg",
            account_url="https://x.com/examaddaorg",
            capture_timestamp="20260914T000000Z",
            initial_records=_fixture_timeline_records(root / "fixtures")[:1],
        )
        assert result.status == R43B_PASS_STATUS
        assert result.record_count == 2
        assert result.post_count == 1
        assert result.repost_count == 1
        assert result.pause_event_count >= 1
        assert result.recovery_event_count >= 1
        assert Path(result.progress_events_path).is_file()
        assert Path(result.timeline_records_path).is_file()
        assert Path(result.account_record_path).is_file()
        assert Path(result.media_index_path).is_file()
        events = [json.loads(line) for line in Path(result.progress_events_path).read_text(encoding="utf-8").splitlines() if line.strip()]
        assert any(event["event_type"] == "paused_rate_limit" for event in events)
        assert any(event["event_type"] == "auto_recovery_resumed" for event in events)
        account_record = Path(result.account_record_path).read_text(encoding="utf-8")
        assert "dates/2026-09-14/" in account_record
        assert "dates/2026-09-15/" in account_record
        assert "post_1001/post.md" in account_record
        assert "repost_2002__original_9009/post.md" in account_record
        assert "static_screenshot" in account_record
        assert "media/images" in account_record
        assert "media/manifests" in account_record
        assert result.side_effect_flags["hidden_x_api_scraping_performed"] is False
        assert result.side_effect_flags["remote_media_downloads_performed"] is False
        assert result.side_effect_flags["source_role_checks_performed"] is False


def test_contract_keeps_webview2_as_observation_not_tracking_layer() -> None:
    contract = build_twitter_x_account_timeline_runner_contract_r43b()
    assert contract["marker"] == R43B_MARKER
    assert contract["uses_independent_fast_media_webview2_lane"] is True
    assert contract["webview2_role"].startswith("site rendering")
    assert contract["review_window_dependency"] is False
    assert contract["source_role_interface_dependency"] is False
    assert contract["source_role_checks_enabled"] is False
    assert contract["review_back_and_forth_enabled"] is False
    assert contract["hidden_x_api_scraping_enabled"] is False
    assert contract["remote_media_downloads_enabled"] is False


def test_dynamic_pause_recovery_policy_has_no_fixed_4000_per_hour_threshold() -> None:
    contract = build_twitter_x_account_timeline_runner_contract_r43b()
    assert contract["fixed_records_per_hour_limit"] == 0
    assert "no fixed" in contract["dynamic_rate_limit_policy"]
    source = Path("profile_media_twitter_x_account_timeline_runner_r43b.py").read_text(encoding="utf-8", errors="replace")
    assert "4000" not in source


def test_report_green() -> None:
    with tempfile.TemporaryDirectory(prefix="r43b_report_") as tmp:
        report = build_report(Path(tmp))
        failed = [dict(check) for check in report.checks if check.get("status") != "pass"]
        assert report.status == R43B_PASS_STATUS, failed
        assert report.passed, failed
        payload = report.to_dict()
        assert payload["marker"] == R43B_MARKER
        assert payload["timeline_result"]["record_count"] >= 2
        assert payload["timeline_result"]["pause_event_count"] >= 1
        assert payload["timeline_result"]["recovery_event_count"] >= 1


def run_self_test() -> None:
    test_timeline_runner_writes_progress_pause_recovery_and_ledger()
    test_contract_keeps_webview2_as_observation_not_tracking_layer()
    test_dynamic_pause_recovery_policy_has_no_fixed_4000_per_hour_threshold()
    test_report_green()


if __name__ == "__main__":
    run_self_test()
    print("profile_media_twitter_x_account_timeline_runner_r43b_test: PASS")
