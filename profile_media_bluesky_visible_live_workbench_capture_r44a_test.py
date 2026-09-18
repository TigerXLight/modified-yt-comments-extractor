from __future__ import annotations

import json
import shutil
from pathlib import Path

from profile_media_bluesky_visible_live_workbench_capture_r44a import (
    R44A_BLOCKED_STATUS,
    R44A_MARKER,
    R44A_PASS_STATUS,
    BlueskyVisibleLiveWorkbenchCaptureRequestR44A,
    build_bluesky_visible_live_workbench_capture_contract_r44a,
    build_bluesky_visible_live_workbench_capture_r44a,
    build_report,
    fake_visible_browser_snapshot_r44a,
)


def test_contract_records_safe_visible_live_boundaries() -> None:
    contract = build_bluesky_visible_live_workbench_capture_contract_r44a()
    assert contract["marker"] == R44A_MARKER
    assert contract["downstream_visible_dom_lane"] == "profile_media_bluesky_visible_dom_capture_r43z"
    assert contract["browser_profile_files_read_or_copied"] is False
    assert contract["webview2_internals_copied"] is False
    assert contract["cookie_or_token_extraction_performed"] is False
    assert contract["remote_media_downloads_performed_by_r44a"] is False


def test_injected_visible_browser_runner_feeds_r43z(tmp_path: Path) -> None:
    result = build_bluesky_visible_live_workbench_capture_r44a(tmp_path, browser_runner=fake_visible_browser_snapshot_r44a).run_account_export(
        BlueskyVisibleLiveWorkbenchCaptureRequestR44A(
            account_url="https://bsky.app/profile/example.bsky.social",
            account_handle="example.bsky.social",
            capture_timestamp="20260918T090000Z",
            output_root=str(tmp_path),
            explicit_live_mode=True,
            run_visible_live=True,
            max_items=5,
        )
    )
    assert result.status == R44A_PASS_STATUS, result.warnings
    assert result.injected_browser_runner_used is True
    assert result.browser_session_started is False
    assert result.network_actions_performed is False
    assert result.visible_record_count == 2
    assert result.bound_media_count >= 3
    assert result.unbound_media_count >= 1
    assert result.record_count == 2
    assert result.media_count >= 3
    assert result.screenshot_count >= 2
    assert Path(result.visible_dom_html_path).is_file()
    assert Path(result.visible_screenshot_path).is_file()
    assert Path(result.account_record_path).is_file()
    assert Path(result.media_index_path).is_file()
    media_index = json.loads(Path(result.media_index_path).read_text(encoding="utf-8"))
    assert all(row["metadata_only_remote_media_not_downloaded"] is True for row in media_index)
    assert all(row["remote_download_performed_by_r43u"] is False for row in media_index)
    assert "](" not in json.dumps(result.to_dict())


def test_external_browser_gate_blocks_without_allow_flag(tmp_path: Path) -> None:
    result = build_bluesky_visible_live_workbench_capture_r44a(tmp_path).run_account_export(
        BlueskyVisibleLiveWorkbenchCaptureRequestR44A(
            account_url="https://bsky.app/profile/example.bsky.social",
            account_handle="example.bsky.social",
            capture_timestamp="20260918T090100Z",
            output_root=str(tmp_path),
            explicit_live_mode=True,
            run_visible_live=True,
        )
    )
    assert result.status == R44A_BLOCKED_STATUS
    assert result.browser_session_started is False
    assert result.network_actions_performed is False
    assert result.side_effect_flags["cookie_or_token_extraction_performed"] is False


def test_workbench_route_reaches_r44a_with_injected_browser_runner(tmp_path: Path) -> None:
    import profile_media_bluesky_visible_live_workbench_capture_r44a as r44a
    from profile_media_universal_social_batch_workbench_app_shell_commands_r43l import build_universal_social_batch_workbench_app_shell_commands_r43l

    old = r44a.capture_visible_browser_snapshot_r44a
    r44a.capture_visible_browser_snapshot_r44a = fake_visible_browser_snapshot_r44a
    try:
        shell = build_universal_social_batch_workbench_app_shell_commands_r43l(output_root=tmp_path / "shell")
        result = shell.run_app_shell_command(
            {
                "command_name": "run_pending",
                "inputs": ("https://bsky.app/profile/example.bsky.social",),
                "capture_timestamp": "20260918T090200Z",
                "output_root": str(tmp_path / "app_shell"),
                "explicit_live_mode": True,
                "run_visible_live": True,
                "public_network_enabled": False,
                "fixture_mode": False,
                "max_items": 5,
            }
        )
    finally:
        r44a.capture_visible_browser_snapshot_r44a = old
    payload = result.to_dict()
    summary = payload.get("live_evidence_summary") or {}
    bluesky_summary = summary.get("bluesky_visible_live_summary") or {}
    assert bluesky_summary["r44a_status"] == R44A_PASS_STATUS
    assert bluesky_summary["injected_browser_runner_used"] is True
    assert bluesky_summary["record_count"] == 2
    assert bluesky_summary["media_count"] >= 3
    assert "](" not in json.dumps(payload)


def test_report_green(tmp_path: Path) -> None:
    report = build_report(tmp_path)
    data = report.to_dict()
    assert data["status"] == R44A_PASS_STATUS, [c for c in data["checks"] if c["status"] != "pass"]
    assert data["sample_result"]["status"] == R44A_PASS_STATUS
    assert data["workbench_route_result"]["live_evidence_summary"]["bluesky_visible_live_summary"]["r44a_status"] == R44A_PASS_STATUS
    flags = data["side_effect_flags"]
    assert flags["browser_profile_files_read_or_copied"] is False
    assert flags["cookie_or_token_extraction_performed"] is False
    assert flags["remote_media_downloads_performed"] is False
    assert "](" not in json.dumps(data)


def run_self_test() -> None:
    root = Path("profile_media_live_captures/r44a_bluesky_visible_live_workbench_capture_test")
    shutil.rmtree(root, ignore_errors=True)
    test_contract_records_safe_visible_live_boundaries()
    test_injected_visible_browser_runner_feeds_r43z(root / "injected")
    test_external_browser_gate_blocks_without_allow_flag(root / "blocked")
    test_workbench_route_reaches_r44a_with_injected_browser_runner(root / "workbench")
    test_report_green(root / "report")


if __name__ == "__main__":
    run_self_test()
    print("profile_media_bluesky_visible_live_workbench_capture_r44a_test: PASS")
