from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from profile_media_live_twitter_x_single_account_smoke_harness_r43n import (
    R43N_BLOCKED_NEEDS_VISIBLE_SESSION,
    R43N_BLOCKED_NO_LIVE_OBSERVATIONS,
    R43N_BLOCKED_PLACEHOLDER_TARGET_URL,
    R43N_MARKER,
    R43N_PASS_STATUS,
    LiveTwitterXSingleAccountSmokeRequestR43N,
    build_live_twitter_x_single_account_smoke_harness_r43n,
    build_report,
)


def _stub_visible_runner(**kwargs):
    output_dir = Path(kwargs["output_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)
    network_events_path = output_dir / "network_events.jsonl"
    media_inventory_path = output_dir / "media_inventory.json"
    rendered_dom_path = output_dir / "rendered_dom_snapshot.html"
    manifest_path = output_dir / "browser_session_manifest.json"
    network_events_path.write_text(
        json.dumps({"url": "https://video.twimg.com/ext_tw_video/r43n_visible.mp4", "resource_type": "media"}) + "\n",
        encoding="utf-8",
    )
    media_inventory_path.write_text(
        json.dumps(
            [
                {
                    "media_id": "r43n_visible_media",
                    "media_type": "video",
                    "media_url": "https://video.twimg.com/ext_tw_video/r43n_visible.mp4",
                    "source_url": kwargs["source_url"],
                    "provenance": "visible_session_observation",
                }
            ]
        ),
        encoding="utf-8",
    )
    rendered_dom_path.write_text("<html><article>R43N visible session observation</article></html>", encoding="utf-8")
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


def _stub_empty_visible_runner(**kwargs):
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


def test_safe_automated_report_blocks_for_visible_session_without_fake_pass() -> None:
    output_root = "profile_media_live_captures/r43n_live_twitter_x_single_account_smoke_harness_real_observation_receipt/test_safe"
    result = build_report(output_root)
    root_report = Path(output_root) / "R43N_LIVE_TWITTER_X_SINGLE_ACCOUNT_SMOKE_HARNESS_REAL_OBSERVATION_RECEIPT_REPORT.json"
    payload = json.loads(root_report.read_text(encoding="utf-8"))

    assert result.status == R43N_BLOCKED_PLACEHOLDER_TARGET_URL
    assert payload["marker"] == R43N_MARKER
    assert payload["status"] == R43N_BLOCKED_PLACEHOLDER_TARGET_URL
    assert payload["bad_checks"] == []
    receipt = payload["sample_result"]["observation_receipt"]
    assert receipt["non_fixture_observation_evidence"] == []
    assert receipt["placeholder_target_detected"] is True
    assert receipt["r43d_live_mode_requested"] is True
    assert receipt["r43b_media_lane_backend_present"] is True
    assert receipt["explicit_live_mode"] is True
    assert receipt["visible_session_required"] is True
    assert receipt["side_effect_flags"]["browser_started_during_automated_tests"] is False
    assert receipt["side_effect_flags"]["network_access_during_automated_tests"] is False
    assert "](" not in json.dumps(payload, sort_keys=True)
    assert "]\\(" not in json.dumps(payload, sort_keys=True)


def test_injected_visible_runner_can_produce_non_fixture_pass_without_browser_start() -> None:
    output_root = "profile_media_live_captures/r43n_live_twitter_x_single_account_smoke_harness_real_observation_receipt/test_stub_pass"
    harness = build_live_twitter_x_single_account_smoke_harness_r43n(output_root=output_root)
    result = harness.run_smoke(
        LiveTwitterXSingleAccountSmokeRequestR43N(
            account_url="https://x.com/realsmokeaccount",
            capture_timestamp="20260916T030000Z",
            output_root=output_root,
            run_visible_live=True,
            automated_test_mode=True,
            include_static_screenshots=False,
            require_screenshot_receipts=False,
        ),
        live_runner=_stub_visible_runner,
    )

    assert result.status == R43N_PASS_STATUS
    assert result.bad_checks == ()
    receipt = result.observation_receipt
    assert receipt["r42gz_boundary_invoked"] is True
    assert receipt["observed_media_count"] >= 1
    assert receipt["non_fixture_observation_evidence"]
    assert receipt["live_observation_paths"]
    assert receipt["r43o_visible_session_binding_invoked"] is True
    assert receipt["r43o_visible_session_binding_status"]
    assert receipt["visible_session_binding_receipt_path"]
    assert receipt["visible_session_binding_files_written"]
    assert receipt["side_effect_flags"]["browser_started_during_automated_tests"] is False
    assert receipt["side_effect_flags"]["network_access_during_automated_tests"] is False
    assert receipt["side_effect_flags"]["remote_media_downloads_performed"] is False
    assert "R43L -> R43J/R43K -> R43I -> R43H -> R43G -> R43F -> R43E -> R43D" in receipt["route_chain"]


def test_placeholder_urls_are_blocked_even_when_visible_live_requested() -> None:
    output_root = "profile_media_live_captures/r43n_live_twitter_x_single_account_smoke_harness_real_observation_receipt/test_placeholder_block"
    harness = build_live_twitter_x_single_account_smoke_harness_r43n(output_root=output_root)
    calls = []

    def forbidden_runner(**kwargs):
        calls.append(kwargs)
        return _stub_visible_runner(**kwargs)

    account_result = harness.run_smoke(
        LiveTwitterXSingleAccountSmokeRequestR43N(
            account_url="[https://x.com/PUT\\_HANDLE\\_HERE](https://x.com/PUT_HANDLE_HERE)",
            capture_timestamp="20260916T031000Z",
            output_root=output_root,
            run_visible_live=True,
            automated_test_mode=False,
        ),
        live_runner=forbidden_runner,
    )
    post_result = harness.run_smoke(
        LiveTwitterXSingleAccountSmokeRequestR43N(
            post_url="[https://x.com/PUT\\_HANDLE\\_HERE/status/PUT\\_STATUS\\_ID\\_HERE](https://x.com/PUT_HANDLE_HERE/status/PUT_STATUS_ID_HERE)",
            capture_timestamp="20260916T031100Z",
            output_root=output_root,
            max_items=1,
            max_scrolls=1,
            run_visible_live=True,
            automated_test_mode=False,
        ),
        live_runner=forbidden_runner,
    )
    real_named_placeholder_result = harness.run_smoke(
        LiveTwitterXSingleAccountSmokeRequestR43N(
            post_url="[https://x.com/REAL\\_HANDLE/status/REAL\\_STATUS\\_ID](https://x.com/REAL_HANDLE/status/REAL_STATUS_ID)",
            capture_timestamp="20260916T031200Z",
            output_root=output_root,
            max_items=1,
            max_scrolls=1,
            run_visible_live=True,
            automated_test_mode=False,
        ),
        live_runner=forbidden_runner,
    )

    assert account_result.status == R43N_BLOCKED_PLACEHOLDER_TARGET_URL
    assert post_result.status == R43N_BLOCKED_PLACEHOLDER_TARGET_URL
    assert real_named_placeholder_result.status == R43N_BLOCKED_PLACEHOLDER_TARGET_URL
    assert calls == []
    for result in (account_result, post_result, real_named_placeholder_result):
        assert result.bad_checks == ()
        receipt = result.observation_receipt
        assert receipt["placeholder_target_detected"] is True
        assert receipt["r43o_visible_session_binding_invoked"] is False
        assert receipt["r42gz_boundary_invoked"] is False
        assert receipt["non_fixture_observation_evidence"] == []
        assert receipt["live_observation_paths"] == []


def test_visible_session_attempt_with_zero_counts_does_not_create_r43n_evidence() -> None:
    output_root = "profile_media_live_captures/r43n_live_twitter_x_single_account_smoke_harness_real_observation_receipt/test_stub_empty"
    harness = build_live_twitter_x_single_account_smoke_harness_r43n(output_root=output_root)
    result = harness.run_smoke(
        LiveTwitterXSingleAccountSmokeRequestR43N(
            account_url="https://x.com/realsmokeaccount",
            capture_timestamp="20260916T043000Z",
            output_root=output_root,
            run_visible_live=True,
            automated_test_mode=True,
            include_static_screenshots=False,
            require_screenshot_receipts=False,
        ),
        live_runner=_stub_empty_visible_runner,
    )

    assert result.status == R43N_BLOCKED_NO_LIVE_OBSERVATIONS
    assert result.bad_checks == ()
    receipt = result.observation_receipt
    assert receipt["r43o_visible_session_binding_invoked"] is True
    assert receipt["r42gz_boundary_invoked"] is True
    assert receipt["observed_post_count"] == 0
    assert receipt["observed_media_count"] == 0
    assert receipt["observed_screenshot_count"] == 0
    assert receipt["materialization_receipt_count"] == 0
    assert receipt["non_fixture_observation_evidence"] == []
    assert receipt["live_observation_paths"] == []
    assert receipt["visible_session_binding_files_written"]


if __name__ == "__main__":
    test_safe_automated_report_blocks_for_visible_session_without_fake_pass()
    test_injected_visible_runner_can_produce_non_fixture_pass_without_browser_start()
    test_placeholder_urls_are_blocked_even_when_visible_live_requested()
    test_visible_session_attempt_with_zero_counts_does_not_create_r43n_evidence()
    print("PASS profile_media_live_twitter_x_single_account_smoke_harness_r43n_test")
