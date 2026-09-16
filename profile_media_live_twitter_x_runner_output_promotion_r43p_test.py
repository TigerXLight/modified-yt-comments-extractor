from __future__ import annotations

import json
from pathlib import Path

from profile_media_live_twitter_x_runner_output_promotion_r43p import (
    R43P_MARKER,
    R43P_NETWORK_ONLY_STATUS,
    R43P_PASS_STATUS,
    TwitterXRunnerOutputPromotionRequestR43P,
    build_report,
    promote_twitter_x_runner_outputs_r43p,
)


def _write_full_runner_outputs(root: Path) -> None:
    capture = root / "r42gt_visible_browser_media_package" / "source_exports" / "twitter_x" / "examaddaorg" / "capture_20260916T061500Z"
    post_dir = capture / "posts" / "https_x.com_examaddaorg"
    store = root / "visible_browser_media_observation_store"
    post_dir.mkdir(parents=True, exist_ok=True)
    store.mkdir(parents=True, exist_ok=True)
    (root / "screenshot.png").write_bytes(b"real-png-bytes")
    (root / "rendered_dom_snapshot.html").write_text("<html><article data-testid=\"tweet\">Exam Adda observed</article></html>", encoding="utf-8")
    (root / "network_events.jsonl").write_text(json.dumps({"url": "https://x.com/examaddaorg"}) + "\n", encoding="utf-8")
    (root / "api_pages.jsonl").write_text(json.dumps({"url": "https://x.com/examaddaorg"}) + "\n", encoding="utf-8")
    (root / "network_response_bodies.jsonl").write_text(json.dumps({"body_sha256": "abc"}) + "\n", encoding="utf-8")
    (store / "visible_browser_media_observations.json").write_text(json.dumps({"observations": [{"media_url": "https://pbs.twimg.com/media/r43p.jpg"}]}), encoding="utf-8")
    (store / "visible_browser_media_observations.ndjson").write_text(json.dumps({"media_url": "https://pbs.twimg.com/media/r43p.jpg"}) + "\n", encoding="utf-8")
    (capture / "media_index.json").write_text(json.dumps({"media": [{"media_url": "https://pbs.twimg.com/media/r43p.jpg"}]}), encoding="utf-8")
    (capture / "media_index.ndjson").write_text(json.dumps({"media_url": "https://pbs.twimg.com/media/r43p.jpg"}) + "\n", encoding="utf-8")
    (capture / "timeline.ndjson").write_text(json.dumps({"post_id": "examaddaorg"}) + "\n", encoding="utf-8")
    (post_dir / "post.json").write_text(json.dumps({"post_id": "examaddaorg"}), encoding="utf-8")


def test_full_runner_outputs_promote_counts_and_plain_urls() -> None:
    root = Path("profile_media_live_captures/r43p_live_twitter_x_runner_output_promotion/test_full_runner")
    runner_root = root / "runner_outputs"
    _write_full_runner_outputs(runner_root)

    result = promote_twitter_x_runner_outputs_r43p(
        TwitterXRunnerOutputPromotionRequestR43P(
            runner_output_dir=str(runner_root),
            output_root=str(root),
            source_url="[https://x.com/examaddaorg](https://x.com/examaddaorg)",
            account_handle="examaddaorg",
            capture_timestamp="20260916T061500Z",
        )
    )
    receipt = json.loads(Path(result.receipt_path).read_text(encoding="utf-8"))

    assert result.status == R43P_PASS_STATUS
    assert result.bad_checks == ()
    assert receipt["marker"] == R43P_MARKER
    assert receipt["normalized_url"] == "https://x.com/examaddaorg"
    assert receipt["promoted_observed_screenshot_count"] == 1
    assert receipt["promoted_observed_post_count"] >= 2
    assert receipt["promoted_observed_media_count"] >= 3
    assert receipt["promoted_network_event_count"] == 1
    assert receipt["promoted_api_page_count"] == 1
    assert receipt["promoted_response_body_count"] == 1
    assert receipt["promoted_non_fixture_observation_evidence"] is True
    assert receipt["promotion_pass_eligible_for_live_smoke"] is True
    assert receipt["promoted_live_observation_paths"]
    assert "](" not in json.dumps(receipt, sort_keys=True)


def test_network_only_outputs_are_recorded_but_not_live_pass() -> None:
    root = Path("profile_media_live_captures/r43p_live_twitter_x_runner_output_promotion/test_network_only")
    runner_root = root / "runner_outputs"
    runner_root.mkdir(parents=True, exist_ok=True)
    (runner_root / "network_events.jsonl").write_text(json.dumps({"url": "https://x.com/examaddaorg"}) + "\n", encoding="utf-8")
    (runner_root / "api_pages.jsonl").write_text(json.dumps({"url": "https://x.com/examaddaorg"}) + "\n", encoding="utf-8")

    result = promote_twitter_x_runner_outputs_r43p(
        {
            "runner_output_dir": str(runner_root),
            "output_root": str(root),
            "source_url": "https://x.com/examaddaorg",
            "account_handle": "examaddaorg",
        }
    )
    receipt = result.receipt

    assert receipt["status"] == R43P_NETWORK_ONLY_STATUS
    assert receipt["promoted_network_event_count"] == 1
    assert receipt["promoted_api_page_count"] == 1
    assert receipt["promoted_observed_post_count"] == 0
    assert receipt["promoted_observed_media_count"] == 0
    assert receipt["promoted_observed_screenshot_count"] == 0
    assert receipt["promotion_pass_eligible_for_live_smoke"] is False


def test_cli_report_builds_required_marker_and_status() -> None:
    output_root = "profile_media_live_captures/r43p_live_twitter_x_runner_output_promotion/test_report"
    result = build_report(output_root)
    report = json.loads((Path(output_root) / "R43P_LIVE_TWITTER_X_RUNNER_OUTPUT_PROMOTION_REPORT.json").read_text(encoding="utf-8"))

    assert result.bad_checks == ()
    assert report["marker"] == R43P_MARKER
    assert report["status"] == R43P_PASS_STATUS
    assert report["bad_checks"] == []


if __name__ == "__main__":
    test_full_runner_outputs_promote_counts_and_plain_urls()
    test_network_only_outputs_are_recorded_but_not_live_pass()
    test_cli_report_builds_required_marker_and_status()
    print("PASS profile_media_live_twitter_x_runner_output_promotion_r43p_test")
