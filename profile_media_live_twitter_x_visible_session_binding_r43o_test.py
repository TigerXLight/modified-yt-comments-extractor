from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from profile_media_live_twitter_x_visible_session_binding_r43o import (
    R43O_BLOCKED_NEEDS_VISIBLE_SESSION,
    R43O_BLOCKED_NO_LIVE_OBSERVATIONS,
    R43O_MARKER,
    R43O_PASS_STATUS,
    LiveTwitterXVisibleSessionBindingRequestR43O,
    build_live_twitter_x_visible_session_binding_r43o,
    build_report,
)


def _stub_observation_runner(**kwargs):
    output_dir = Path(kwargs["output_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)
    network_events_path = output_dir / "network_events.jsonl"
    media_inventory_path = output_dir / "media_inventory.json"
    rendered_dom_path = output_dir / "rendered_dom_snapshot.html"
    manifest_path = output_dir / "browser_session_manifest.json"
    network_events_path.write_text(
        json.dumps({"url": "https://video.twimg.com/ext_tw_video/r43o_visible.mp4", "resource_type": "media"}) + "\n",
        encoding="utf-8",
    )
    media_inventory_path.write_text(
        json.dumps(
            [
                {
                    "media_id": "r43o_visible_media",
                    "media_type": "video",
                    "media_url": "https://video.twimg.com/ext_tw_video/r43o_visible.mp4",
                    "source_url": kwargs["source_url"],
                    "provenance": "visible_session_observation",
                }
            ]
        ),
        encoding="utf-8",
    )
    rendered_dom_path.write_text("<html><article>R43O visible session observation</article></html>", encoding="utf-8")
    manifest_path.write_text(json.dumps({"status": "success", "source_url": kwargs["source_url"]}), encoding="utf-8")
    return SimpleNamespace(
        status="success",
        output_dir=str(output_dir),
        network_events_path=str(network_events_path),
        media_inventory_path=str(media_inventory_path),
        rendered_dom_path=str(rendered_dom_path),
        manifest_path=str(manifest_path),
        warnings=(),
        errors=(),
    )


def _stub_empty_runner(**kwargs):
    output_dir = Path(kwargs["output_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)
    network_events_path = output_dir / "network_events.jsonl"
    media_inventory_path = output_dir / "media_inventory.json"
    manifest_path = output_dir / "browser_session_manifest.json"
    network_events_path.write_text("", encoding="utf-8")
    media_inventory_path.write_text("[]", encoding="utf-8")
    manifest_path.write_text(json.dumps({"status": "planned", "source_url": kwargs["source_url"]}), encoding="utf-8")
    return SimpleNamespace(
        status="planned",
        output_dir=str(output_dir),
        network_events_path=str(network_events_path),
        media_inventory_path=str(media_inventory_path),
        rendered_dom_path="",
        manifest_path=str(manifest_path),
        warnings=("no observations",),
        errors=(),
    )


def test_safe_report_needs_visible_session_without_launch() -> None:
    output_root = "profile_media_live_captures/r43o_live_twitter_x_visible_session_binding/test_safe"
    result = build_report(output_root)
    report_path = Path(output_root) / "R43O_LIVE_TWITTER_X_VISIBLE_SESSION_BINDING_REPORT.json"
    payload = json.loads(report_path.read_text(encoding="utf-8"))

    assert result.status == R43O_BLOCKED_NEEDS_VISIBLE_SESSION
    assert payload["marker"] == R43O_MARKER
    assert payload["bad_checks"] == []
    receipt = payload["sample_result"]["receipt"]
    assert receipt["visible_session_launched_or_attached"] is False
    assert receipt["visible_navigation_attempted"] is False
    assert receipt["observer_started"] is False
    assert receipt["side_effect_flags"]["browser_started_during_automated_tests"] is False
    assert receipt["side_effect_flags"]["network_access_during_automated_tests"] is False
    assert "](" not in json.dumps(payload, sort_keys=True)


def test_stubbed_visible_binding_can_record_real_boundary_without_browser_start() -> None:
    output_root = "profile_media_live_captures/r43o_live_twitter_x_visible_session_binding/test_stub_pass"
    binding = build_live_twitter_x_visible_session_binding_r43o(output_root=output_root)
    result = binding.run_binding(
        LiveTwitterXVisibleSessionBindingRequestR43O(
            target_url="https://x.com/realsmokeaccount",
            account_handle="realsmokeaccount",
            capture_timestamp="20260916T041000Z",
            output_root=output_root,
            run_visible_live=True,
            automated_test_mode=True,
        ),
        runner=_stub_observation_runner,
    )

    assert result.status == R43O_PASS_STATUS
    assert result.bad_checks == ()
    receipt = result.receipt
    assert receipt["r42gz_boundary_invoked"] is True
    assert receipt["visible_session_launched_or_attached"] is True
    assert receipt["visible_navigation_attempted"] is True
    assert receipt["observer_started"] is True
    assert receipt["files_written"]
    assert receipt["observed_media_count"] >= 1
    assert receipt["r43p_runner_output_promotion_invoked"] is True
    assert "promoted_observed_media_count" in receipt
    assert receipt["promoted_live_observation_paths"]
    assert receipt["side_effect_flags"]["browser_started_during_automated_tests"] is False
    assert receipt["side_effect_flags"]["network_access_during_automated_tests"] is False


def test_stubbed_visible_binding_reports_no_live_observations() -> None:
    output_root = "profile_media_live_captures/r43o_live_twitter_x_visible_session_binding/test_stub_empty"
    binding = build_live_twitter_x_visible_session_binding_r43o(output_root=output_root)
    result = binding.run_binding(
        LiveTwitterXVisibleSessionBindingRequestR43O(
            target_url="https://x.com/realsmokeaccount",
            account_handle="realsmokeaccount",
            capture_timestamp="20260916T041100Z",
            output_root=output_root,
            run_visible_live=True,
            automated_test_mode=True,
        ),
        runner=_stub_empty_runner,
    )

    assert result.status == R43O_BLOCKED_NO_LIVE_OBSERVATIONS
    assert result.bad_checks == ()
    receipt = result.receipt
    assert receipt["visible_navigation_attempted"] is True
    assert receipt["observer_started"] is True
    assert receipt["observed_media_count"] == 0
    assert receipt["files_written"]
    assert receipt["r43p_runner_output_promotion_invoked"] is True
    assert receipt["promoted_observed_post_count"] == 0
    assert receipt["promoted_observed_media_count"] == 0
    assert receipt["promoted_observed_screenshot_count"] == 0


if __name__ == "__main__":
    test_safe_report_needs_visible_session_without_launch()
    test_stubbed_visible_binding_can_record_real_boundary_without_browser_start()
    test_stubbed_visible_binding_reports_no_live_observations()
    print("PASS profile_media_live_twitter_x_visible_session_binding_r43o_test")
