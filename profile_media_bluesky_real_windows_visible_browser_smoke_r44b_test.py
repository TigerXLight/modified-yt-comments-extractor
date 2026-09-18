from __future__ import annotations

from pathlib import Path

from profile_media_bluesky_real_windows_visible_browser_smoke_r44b import (
    R44B_PASS_STATUS,
    BlueskyRealWindowsVisibleBrowserSmokeRequestR44B,
    build_bluesky_real_windows_visible_browser_smoke_r44b,
    build_report,
)
from profile_media_bluesky_visible_live_workbench_capture_r44a import fake_visible_browser_snapshot_r44a


def test_injected_smoke_exercises_full_chain(tmp_path: Path) -> None:
    runner = build_bluesky_real_windows_visible_browser_smoke_r44b(tmp_path / "runner", browser_runner=fake_visible_browser_snapshot_r44a)
    result = runner.run_account_export(
        BlueskyRealWindowsVisibleBrowserSmokeRequestR44B(
            account_url="https://bsky.app/profile/example.bsky.social",
            account_handle="example.bsky.social",
            capture_timestamp="20260918T093000Z",
            output_root=str(tmp_path / "runner"),
            fixture_mode=True,
            real_visible_smoke=False,
            max_items=5,
        )
    )
    assert result.status == R44B_PASS_STATUS
    assert result.r44a_status.startswith("PASS_R44A")
    assert result.r43z_status.startswith("PASS_R43Z")
    assert result.adapter_status.startswith("PASS_R43V")
    assert result.ledger_status.startswith("PASS_R43U")
    assert result.record_count == 2
    assert result.visible_record_count == 2
    assert result.media_count >= 3
    assert result.bound_media_count >= 3
    assert result.screenshot_count >= 2
    assert Path(result.visible_dom_html_path).is_file()
    assert Path(result.visible_screenshot_path).is_file()
    assert result.injected_browser_runner_used is True
    assert result.browser_session_started is False
    assert result.network_actions_performed is False
    assert result.side_effect_flags["cookie_or_token_extraction_performed"] is False
    assert result.side_effect_flags["remote_media_downloads_performed"] is False


def test_report_passes_without_real_browser_or_network(tmp_path: Path) -> None:
    report = build_report(tmp_path / "report")
    assert report.status == R44B_PASS_STATUS
    assert report.passed
    assert report.sample_result["injected_browser_runner_used"] is True
    assert report.sample_result["browser_session_started"] is False
    assert report.sample_result["network_actions_performed"] is False
    assert report.sample_result["live_media_binding_status"] == "MEDIA_PRESENT_AND_BOUND"


def test_r44a_capture_source_has_render_readiness_wait() -> None:
    source = Path("profile_media_bluesky_visible_live_workbench_capture_r44a.py").read_text(encoding="utf-8")
    assert "_wait_for_bluesky_rendered_post_links_r44a" in source
    assert "post_link_count" in source
    assert "render_wait_status" in source


def run_self_test() -> None:
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        test_injected_smoke_exercises_full_chain(root / "a")
        test_report_passes_without_real_browser_or_network(root / "b")
        test_r44a_capture_source_has_render_readiness_wait()
    print("profile_media_bluesky_real_windows_visible_browser_smoke_r44b_test: PASS")


if __name__ == "__main__":
    run_self_test()
