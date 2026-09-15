from __future__ import annotations

import json
from pathlib import Path

from profile_media_universal_social_batch_queue_workbench_controls_r43i import (
    R43I_MARKER,
    R43I_PASS_STATUS,
    UniversalSocialBatchQueueWorkbenchRequestR43I,
    build_report,
    build_universal_social_batch_queue_workbench_r43i,
)


def test_preview_load_run_and_controls_delegate_to_r43h(tmp_path: Path) -> None:
    tmp_path.mkdir(parents=True, exist_ok=True)
    txt = tmp_path / "social_urls.txt"
    txt.write_text("https://www.instagram.com/p/C-example/?igsh=test\nhttps://unknown.invalid/profile/example\n", encoding="utf-8")
    workbench = build_universal_social_batch_queue_workbench_r43i(output_root=tmp_path)
    preview = workbench.run_workbench_operation(
        UniversalSocialBatchQueueWorkbenchRequestR43I(
            operation="create_queue_preview",
            inputs=(
                "https://x.com/example?utm_source=test",
                "https://x.com/example",
                "https://x.com/example/status/1111111111111111111?s=20",
                "https://twitter.com/example/status/1111111111111111111",
                "https://bsky.app/profile/example.bsky.social",
            ),
            raw_text="https://www.facebook.com/example/posts/12345",
            txt_path=str(txt),
            capture_timestamp="20260915T091000Z",
            output_root=str(tmp_path),
            fixture_mode=True,
        )
    )
    assert preview.status == R43I_PASS_STATUS
    assert len(preview.route_receipts) == 0
    assert any(row["duplicate_of"] for row in preview.rows)
    assert all(row["route_status"] == "not_routed" for row in preview.rows if row["status"] != "duplicate")

    queue_path = tmp_path / "preview_queue.json"
    queue_path.write_text(json.dumps({"items": [_record_from_row(row) for row in preview.rows]}, indent=2), encoding="utf-8")
    loaded = workbench.run_workbench_operation(
        UniversalSocialBatchQueueWorkbenchRequestR43I(
            operation="load_existing_queue",
            existing_queue_path=str(queue_path),
            capture_timestamp="20260915T091100Z",
            output_root=str(tmp_path / "loaded"),
            fixture_mode=True,
        )
    )
    assert len(loaded.rows) == len(preview.rows)

    run = workbench.run_workbench_operation(
        UniversalSocialBatchQueueWorkbenchRequestR43I(
            operation="run_pending",
            existing_queue_path=str(queue_path),
            capture_timestamp="20260915T091200Z",
            output_root=str(tmp_path / "run"),
            fixture_mode=True,
        )
    )
    assert any(action["action"] == "delegated_to_r43h" for action in run.actions)
    assert any(_first_route_status(receipt) == "dispatched_to_r43d_surface_via_r43e_adapter_map" for receipt in run.route_receipts)
    assert any(_first_route_status(receipt) == "mapped_pending_adapter_receipt" for receipt in run.route_receipts)
    assert any(_first_route_status(receipt) == "unsupported_platform_receipt" for receipt in run.route_receipts)

    rows_for_resume = [_record_from_row(row) for row in run.rows]
    selected_id = ""
    for row in rows_for_resume:
        if row["platform_id"] == "twitter_x" and row["status"] == "completed" and not selected_id:
            row["status"] = "failed_retryable"
            row["route_status"] = "retryable_fixture_failure"
            selected_id = row["queue_id"]
    rows_for_resume.append({**rows_for_resume[0], "queue_id": "terminal-workbench-test", "batch_index": 999, "status": "failed_terminal", "duplicate_of": ""})
    resume_queue = tmp_path / "resume_queue.json"
    resume_queue.write_text(json.dumps({"items": rows_for_resume}, indent=2), encoding="utf-8")
    resume = workbench.run_workbench_operation(
        UniversalSocialBatchQueueWorkbenchRequestR43I(
            operation="resume",
            existing_queue_path=str(resume_queue),
            capture_timestamp="20260915T091300Z",
            output_root=str(tmp_path / "resume"),
            fixture_mode=True,
        )
    )
    assert any(action["action"] == "delegated_to_r43h" for action in resume.actions)
    assert _resume_count(resume, "skipped_completed") > 0
    assert _resume_count(resume, "skipped_non_retryable") > 0

    retry = workbench.run_workbench_operation(
        UniversalSocialBatchQueueWorkbenchRequestR43I(
            operation="retry_selected",
            existing_queue_path=str(resume_queue),
            selected_queue_ids=(selected_id,),
            capture_timestamp="20260915T091400Z",
            output_root=str(tmp_path / "retry"),
            fixture_mode=True,
        )
    )
    assert selected_id in retry.selected_queue_ids
    assert any(action["action"] == "delegated_to_r43h" for action in retry.actions)

    skip = workbench.run_workbench_operation(
        UniversalSocialBatchQueueWorkbenchRequestR43I(
            operation="skip_selected",
            existing_queue_path=str(queue_path),
            selected_queue_ids=(preview.rows[0]["queue_id"],),
            capture_timestamp="20260915T091500Z",
            output_root=str(tmp_path / "skip"),
            fixture_mode=True,
        )
    )
    assert any(action["action"] == "selected_row_skipped" for action in skip.actions)
    assert any(row["status"] == "skipped" for row in skip.rows)


def test_detected_items_ndjson_and_report_boundaries(tmp_path: Path) -> None:
    workbench = build_universal_social_batch_queue_workbench_r43i(output_root=tmp_path)
    preview = workbench.run_workbench_operation(
        UniversalSocialBatchQueueWorkbenchRequestR43I(
            operation="create_queue_preview",
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
            capture_timestamp="20260915T092000Z",
            output_root=str(tmp_path / "detected"),
            fixture_mode=True,
        )
    )
    assert preview.status == R43I_PASS_STATUS
    assert Path(preview.state_path).exists()
    assert Path(preview.rows_path).read_text(encoding="utf-8").strip()
    assert all(_has_row_contract(row) for row in preview.rows)

    ndjson = tmp_path / "queue.ndjson"
    ndjson.write_text("".join(json.dumps(_record_from_row(row), sort_keys=True) + "\n" for row in preview.rows), encoding="utf-8")
    loaded = workbench.run_workbench_operation(
        UniversalSocialBatchQueueWorkbenchRequestR43I(
            operation="load_existing_queue",
            existing_queue_path=str(ndjson),
            capture_timestamp="20260915T092100Z",
            output_root=str(tmp_path / "ndjson_load"),
            fixture_mode=True,
        )
    )
    assert len(loaded.rows) == len(preview.rows)

    report = build_report(tmp_path / "report")
    data = report.to_dict()
    assert data["marker"] == R43I_MARKER
    assert data["status"] == R43I_PASS_STATUS, [check for check in data["checks"] if check["status"] != "pass"]
    required = {
        "universal_social_batch_queue_workbench_invoked",
        "queue_preview_does_not_route_items",
        "existing_r43h_queue_can_be_loaded",
        "run_and_resume_delegate_to_r43h",
        "duplicate_rows_visible_but_not_routed_twice",
        "completed_rows_skipped_on_resume",
        "failed_terminal_and_unsupported_not_retried_by_default",
        "selected_retry_and_skip_controls_recorded",
        "pending_platform_and_unknown_receipts_visible",
        "twitter_x_rows_route_through_r43h_r43g_r43f_r43e_r43d",
        "workbench_state_rows_actions_and_summary_written",
        "universal_contract_preserved",
        "no_browser_or_source_role_side_effects",
        "no_hidden_api_cookie_token_or_challenge_bypass",
        "no_remote_media_downloads",
        "plain_machine_urls",
    }
    assert required <= {check["name"] for check in data["checks"]}
    flags = data["side_effect_flags"]
    assert flags["webview2_session_started_by_r43i"] is False
    assert flags["cefsharp_session_started_by_r43i"] is False
    assert flags["webview2_internals_copied_by_r43i"] is False
    assert flags["hidden_api_scraping_performed"] is False
    assert flags["cookie_or_token_extraction_performed"] is False
    assert flags["captcha_challenge_paywall_or_access_control_bypass_performed"] is False
    assert flags["source_role_checks_performed"] is False
    assert flags["review_window_dependency_invoked"] is False
    assert flags["remote_media_downloads_performed"] is False
    assert flags["youtube_capture_engine_behavior_changed"] is False
    assert "](" not in json.dumps(data)


def _record_from_row(row: dict) -> dict:
    payload = dict(row)
    payload.pop("selected", None)
    payload.pop("eligible_for_run", None)
    payload.pop("eligible_for_retry", None)
    return payload


def _first_route_status(receipt: dict) -> str:
    route_results = receipt.get("route_results")
    if route_results:
        return route_results[0].get("route_status", "")
    return receipt.get("route_status", "")


def _resume_count(result, key: str) -> int:
    for receipt in result.route_receipts:
        counts = receipt.get("resume_receipt", {}).get("resume_counts", {})
        if counts:
            return int(counts.get(key) or 0)
    return 0


def _has_row_contract(row: dict) -> bool:
    required = {
        "queue_id",
        "batch_index",
        "raw_input",
        "normalized_url",
        "platform_id",
        "url_kind",
        "account_handle",
        "record_id",
        "dedupe_key",
        "duplicate_of",
        "status",
        "route_status",
        "downstream_status",
        "attempts",
        "selected",
        "eligible_for_run",
        "eligible_for_retry",
        "last_error",
        "route_receipt_path",
        "run_dir",
        "updated_at",
    }
    return required <= set(row)


def run_self_test() -> None:
    root = Path("profile_media_live_captures/r43i_universal_social_batch_queue_workbench_controls_test")
    root.mkdir(parents=True, exist_ok=True)
    test_preview_load_run_and_controls_delegate_to_r43h(root / "workbench")
    test_detected_items_ndjson_and_report_boundaries(root / "report")
    print("profile_media_universal_social_batch_queue_workbench_controls_r43i_test: PASS")


if __name__ == "__main__":
    run_self_test()
