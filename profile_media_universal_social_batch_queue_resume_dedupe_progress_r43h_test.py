from __future__ import annotations

import json
from pathlib import Path

from profile_media_universal_social_batch_queue_resume_dedupe_progress_r43h import (
    BATCH_QUEUE_OUTPUT_FILES_R43H,
    R43H_MARKER,
    R43H_PASS_STATUS,
    UniversalSocialBatchQueueRequestR43H,
    build_report,
    build_universal_social_batch_queue_router_r43h,
)


def test_batch_queue_preserves_duplicates_but_routes_canonical_items_once(tmp_path: Path) -> None:
    tmp_path.mkdir(parents=True, exist_ok=True)
    txt = tmp_path / "social_urls.txt"
    txt.write_text(
        "\n".join(
            [
                "https://www.instagram.com/p/C-example/?igsh=test",
                "https://unknown.invalid/profile/example",
            ]
        ),
        encoding="utf-8",
    )
    router = build_universal_social_batch_queue_router_r43h(output_root=tmp_path)
    result = router.run_batch(
        UniversalSocialBatchQueueRequestR43H(
            inputs=(
                "https://x.com/example?utm_source=test",
                "https://x.com/example",
                "https://x.com/example/status/1111111111111111111?s=20",
                "https://twitter.com/example/status/1111111111111111111",
                "https://bsky.app/profile/example.bsky.social",
            ),
            raw_text="https://www.facebook.com/example/posts/12345",
            txt_path=str(txt),
            capture_timestamp="20260915T081000Z",
            output_root=str(tmp_path),
            fixture_mode=True,
        )
    )
    assert result.status == R43H_PASS_STATUS
    assert result.total_items == 8
    assert result.duplicate_count >= 2
    assert result.routed_count == result.total_items - result.duplicate_count
    duplicate_rows = [row for row in result.queue_records if row["status"] == "duplicate"]
    assert duplicate_rows
    assert all(row["duplicate_of"] for row in duplicate_rows)
    route_receipts = [json.loads(line) for line in Path(result.route_receipts_path).read_text(encoding="utf-8").splitlines()]
    routed_queue_ids = {row["queue_id"] for row in route_receipts}
    assert not (routed_queue_ids & {row["queue_id"] for row in duplicate_rows})
    assert any(row["route_results"][0]["route_status"] == "dispatched_to_r43d_surface_via_r43e_adapter_map" for row in route_receipts)
    assert any(row["route_results"][0]["route_status"] == "mapped_pending_adapter_receipt" for row in route_receipts)
    assert any(row["route_results"][0]["route_status"] == "unsupported_platform_receipt" for row in route_receipts)
    for name in BATCH_QUEUE_OUTPUT_FILES_R43H:
        assert (Path(result.run_dir) / name).exists(), name


def test_detected_r43g_items_are_ingested_and_resume_policy_is_stable(tmp_path: Path) -> None:
    tmp_path.mkdir(parents=True, exist_ok=True)
    router = build_universal_social_batch_queue_router_r43h(output_root=tmp_path)
    initial = router.run_batch(
        UniversalSocialBatchQueueRequestR43H(
            detected_items=(
                {
                    "batch_index": 1,
                    "raw_input": "https://x.com/example/status/2222222222222222222?s=20",
                    "normalized_url": "https://x.com/example/status/2222222222222222222",
                    "platform_id": "twitter_x",
                    "url_kind": "post",
                    "account_handle": "example",
                    "record_id": "2222222222222222222",
                },
                {
                    "batch_index": 2,
                    "raw_input": "https://www.youtube.com/watch?v=qGNKkvxE61Q",
                    "normalized_url": "https://www.youtube.com/watch?v=qGNKkvxE61Q",
                    "platform_id": "youtube",
                    "url_kind": "video",
                    "account_handle": "unknown_account",
                    "record_id": "qGNKkvxE61Q",
                },
            ),
            capture_timestamp="20260915T081500Z",
            output_root=str(tmp_path),
            fixture_mode=True,
        )
    )
    records = [dict(row) for row in initial.queue_records]
    records[0]["status"] = "completed"
    records[1]["status"] = "failed_retryable"
    records.append({**records[0], "queue_id": "terminal-fixture", "batch_index": 99, "status": "failed_terminal", "duplicate_of": ""})
    queue_path = tmp_path / "resume_queue.json"
    queue_path.write_text(json.dumps({"items": records}, indent=2), encoding="utf-8")
    resumed = router.run_batch(
        UniversalSocialBatchQueueRequestR43H(
            existing_queue_path=str(queue_path),
            capture_timestamp="20260915T081600Z",
            output_root=str(tmp_path / "resume"),
            fixture_mode=True,
        )
    )
    assert resumed.status == R43H_PASS_STATUS
    assert resumed.skipped_completed_count == 1
    assert resumed.retried_count == 1
    assert resumed.skipped_non_retryable_count >= 1
    receipt = json.loads(Path(resumed.resume_receipt_path).read_text(encoding="utf-8"))
    assert receipt["resume_counts"]["skipped_completed"] == 1
    assert receipt["resume_counts"]["retried"] == 1
    assert "terminal-fixture" in receipt["skipped_non_retryable_queue_ids"]


def test_report_checks_boundaries_and_plain_machine_urls(tmp_path: Path) -> None:
    report = build_report(tmp_path)
    data = report.to_dict()
    assert data["marker"] == R43H_MARKER
    assert data["status"] == R43H_PASS_STATUS, [check for check in data["checks"] if check["status"] != "pass"]
    names = {check["name"] for check in data["checks"]}
    required = {
        "universal_social_batch_queue_invoked",
        "r43g_detection_results_ingested",
        "one_url_many_urls_and_txt_inputs_supported",
        "duplicates_collapsed_by_normalized_url_and_record_key",
        "duplicate_items_do_not_route_twice",
        "queue_resume_skips_completed_and_retries_pending",
        "failed_terminal_and_unsupported_not_retried_by_default",
        "per_item_progress_events_written",
        "platform_pending_and_unknown_receipts_preserved",
        "twitter_x_items_route_through_r43f_r43e_r43d_when_processed",
        "universal_contract_preserved",
        "stable_batch_summary_and_receipts_written",
        "green_packaging_preserves_relative_paths",
        "no_browser_or_source_role_side_effects",
        "no_hidden_api_cookie_token_or_challenge_bypass",
        "no_remote_media_downloads",
        "plain_machine_urls",
    }
    assert required <= names
    flags = data["side_effect_flags"]
    assert flags["webview2_session_started_by_r43h"] is False
    assert flags["cefsharp_session_started_by_r43h"] is False
    assert flags["webview2_internals_copied_by_r43h"] is False
    assert flags["hidden_api_scraping_performed"] is False
    assert flags["cookie_or_token_extraction_performed"] is False
    assert flags["captcha_challenge_paywall_or_access_control_bypass_performed"] is False
    assert flags["source_role_checks_performed"] is False
    assert flags["review_window_dependency_invoked"] is False
    assert flags["remote_media_downloads_performed"] is False
    assert flags["youtube_capture_engine_behavior_changed"] is False
    assert "](" not in json.dumps(data)


def run_self_test() -> None:
    root = Path("profile_media_live_captures/r43h_universal_social_batch_queue_resume_dedupe_progress_test")
    root.mkdir(parents=True, exist_ok=True)
    test_batch_queue_preserves_duplicates_but_routes_canonical_items_once(root / "queue")
    test_detected_r43g_items_are_ingested_and_resume_policy_is_stable(root / "resume")
    test_report_checks_boundaries_and_plain_machine_urls(root / "report")
    print("profile_media_universal_social_batch_queue_resume_dedupe_progress_r43h_test: PASS")


if __name__ == "__main__":
    run_self_test()
