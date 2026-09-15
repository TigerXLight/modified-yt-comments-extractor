from __future__ import annotations

import json
from pathlib import Path

from profile_media_universal_social_batch_queue_workbench_panel_r43j import (
    R43J_MARKER,
    R43J_PASS_STATUS,
    UniversalSocialBatchQueueWorkbenchPanelRequestR43J,
    build_report,
    build_universal_social_batch_queue_workbench_panel_r43j,
)


def test_panel_preview_selection_and_r43i_delegated_actions(tmp_path: Path) -> None:
    tmp_path.mkdir(parents=True, exist_ok=True)
    txt = tmp_path / "social_urls.txt"
    txt.write_text("https://www.instagram.com/p/C-example/?igsh=test\nhttps://unknown.invalid/profile/example\n", encoding="utf-8")
    panel = build_universal_social_batch_queue_workbench_panel_r43j(output_root=tmp_path)
    preview = panel.run_panel_action(
        UniversalSocialBatchQueueWorkbenchPanelRequestR43J(
            action="create_preview",
            inputs=(
                "https://x.com/example?utm_source=test",
                "https://x.com/example",
                "https://x.com/example/status/1111111111111111111?s=20",
                "https://twitter.com/example/status/1111111111111111111",
                "https://bsky.app/profile/example.bsky.social",
            ),
            pasted_text="[fb](https://www.facebook.com/example/posts/12345)",
            txt_path=str(txt),
            capture_timestamp="20260915T101000Z",
            output_root=str(tmp_path),
            fixture_mode=True,
        )
    )
    assert preview.status == R43J_PASS_STATUS
    assert len(preview.route_receipts) == 0
    assert any(row["duplicate_of"] for row in preview.rows)
    assert "twitter_x" in preview.counts_by_platform
    assert "pending" in preview.counts_by_status
    assert Path(preview.panel_state_path).exists()
    assert Path(preview.panel_summary_path).read_text(encoding="utf-8").lower().find("duplicate") >= 0

    queue_path = tmp_path / "panel_queue.json"
    queue_path.write_text(json.dumps({"items": [_record_from_panel_row(row) for row in preview.rows]}, indent=2), encoding="utf-8")
    loaded = panel.run_panel_action(
        UniversalSocialBatchQueueWorkbenchPanelRequestR43J(
            action="create_preview",
            existing_queue_path=str(queue_path),
            capture_timestamp="20260915T101050Z",
            output_root=str(tmp_path / "loaded"),
            fixture_mode=True,
        )
    )
    assert len(loaded.rows) == len(preview.rows)

    loaded_state = panel.run_panel_action(
        UniversalSocialBatchQueueWorkbenchPanelRequestR43J(
            action="select_all_pending",
            existing_workbench_state_path=preview.workbench_state_path,
            capture_timestamp="20260915T101075Z",
            output_root=str(tmp_path / "state_load"),
            fixture_mode=True,
        )
    )
    assert len(loaded_state.rows) == len(preview.rows)
    assert loaded_state.selected_queue_ids

    selected_platform = panel.run_panel_action(
        UniversalSocialBatchQueueWorkbenchPanelRequestR43J(
            action="select_platform",
            existing_queue_path=str(queue_path),
            select_platform_id="twitter_x",
            capture_timestamp="20260915T101100Z",
            output_root=str(tmp_path / "select_platform"),
            fixture_mode=True,
        )
    )
    assert selected_platform.selected_queue_ids
    assert all(row["platform_id"] == "twitter_x" for row in selected_platform.rows if row["selected"])

    run = panel.run_panel_action(
        UniversalSocialBatchQueueWorkbenchPanelRequestR43J(
            action="run_pending",
            existing_queue_path=str(queue_path),
            capture_timestamp="20260915T101200Z",
            output_root=str(tmp_path / "run"),
            fixture_mode=True,
        )
    )
    assert any(action["action"] == "delegated_to_r43i" for action in run.actions)
    assert any(_first_route_status(receipt) == "dispatched_to_r43d_surface_via_r43e_adapter_map" for receipt in run.route_receipts)
    assert any(_first_route_status(receipt) == "mapped_pending_adapter_receipt" for receipt in run.route_receipts)
    assert any(_first_route_status(receipt) == "unsupported_platform_receipt" for receipt in run.route_receipts)

    rows_for_resume = [_record_from_panel_row(row) for row in run.rows]
    selected_id = ""
    for row in rows_for_resume:
        if row["platform_id"] == "twitter_x" and row["status"] == "completed" and not selected_id:
            row["status"] = "failed_retryable"
            row["route_status"] = "retryable_fixture_failure"
            selected_id = row["queue_id"]
    rows_for_resume.append({**rows_for_resume[0], "queue_id": "terminal-panel-test", "batch_index": 999, "status": "failed_terminal", "duplicate_of": ""})
    resume_queue = tmp_path / "resume_queue.json"
    resume_queue.write_text(json.dumps({"items": rows_for_resume}, indent=2), encoding="utf-8")
    resume = panel.run_panel_action(
        UniversalSocialBatchQueueWorkbenchPanelRequestR43J(
            action="resume",
            existing_queue_path=str(resume_queue),
            capture_timestamp="20260915T101300Z",
            output_root=str(tmp_path / "resume"),
            fixture_mode=True,
        )
    )
    assert _resume_count(resume, "skipped_completed") > 0
    assert _resume_count(resume, "skipped_non_retryable") > 0

    retry = panel.run_panel_action(
        UniversalSocialBatchQueueWorkbenchPanelRequestR43J(
            action="retry_selected",
            existing_queue_path=str(resume_queue),
            selected_queue_ids=(selected_id,),
            capture_timestamp="20260915T101400Z",
            output_root=str(tmp_path / "retry"),
            fixture_mode=True,
        )
    )
    assert selected_id in retry.selected_queue_ids
    skip = panel.run_panel_action(
        UniversalSocialBatchQueueWorkbenchPanelRequestR43J(
            action="skip_selected",
            existing_queue_path=str(queue_path),
            selected_queue_ids=(preview.rows[0]["queue_id"],),
            capture_timestamp="20260915T101500Z",
            output_root=str(tmp_path / "skip"),
            fixture_mode=True,
        )
    )
    assert any(action["action"] == "delegated_to_r43i" for action in skip.actions)


def test_report_checks_side_effects_and_plain_urls(tmp_path: Path) -> None:
    report = build_report(tmp_path)
    data = report.to_dict()
    assert data["marker"] == R43J_MARKER
    assert data["status"] == R43J_PASS_STATUS, [check for check in data["checks"] if check["status"] != "pass"]
    required = {
        "universal_social_batch_queue_workbench_panel_invoked",
        "panel_preview_does_not_route_items",
        "panel_actions_delegate_to_r43i",
        "existing_r43h_and_r43i_state_can_be_loaded",
        "row_selection_controls_recorded",
        "run_resume_retry_skip_controls_recorded",
        "duplicate_rows_visible_but_not_routed_twice",
        "completed_rows_skipped_on_resume",
        "failed_terminal_and_unsupported_not_retried_by_default",
        "pending_platform_and_unknown_receipts_visible",
        "twitter_x_rows_route_through_r43i_r43h_r43g_r43f_r43e_r43d",
        "panel_state_rows_actions_selection_and_summary_written",
        "platform_and_status_counts_visible",
        "universal_contract_preserved",
        "no_browser_or_source_role_side_effects",
        "no_hidden_api_cookie_token_or_challenge_bypass",
        "no_remote_media_downloads",
        "plain_machine_urls",
    }
    assert required <= {check["name"] for check in data["checks"]}
    flags = data["side_effect_flags"]
    assert flags["webview2_session_started_by_r43j"] is False
    assert flags["cefsharp_session_started_by_r43j"] is False
    assert flags["webview2_internals_copied_by_r43j"] is False
    assert flags["hidden_api_scraping_performed"] is False
    assert flags["cookie_or_token_extraction_performed"] is False
    assert flags["captcha_challenge_paywall_or_access_control_bypass_performed"] is False
    assert flags["source_role_checks_performed"] is False
    assert flags["review_window_dependency_invoked"] is False
    assert flags["remote_media_downloads_performed"] is False
    assert flags["youtube_capture_engine_behavior_changed"] is False
    assert "](" not in json.dumps(data)


def _record_from_panel_row(row: dict) -> dict:
    return {
        "account_handle": row.get("account_handle", ""),
        "attempts": row.get("attempts", 0),
        "batch_index": row.get("batch_index", 0),
        "dedupe_key": f"{row.get('platform_id', '')}:{row.get('normalized_url', '')}",
        "downstream_status": row.get("downstream_status", ""),
        "duplicate_of": row.get("duplicate_of", ""),
        "last_error": row.get("last_error", ""),
        "normalized_url": row.get("normalized_url", ""),
        "platform_id": row.get("platform_id", ""),
        "queue_id": row.get("queue_id", ""),
        "raw_input": row.get("raw_input", ""),
        "record_id": row.get("record_id", ""),
        "route_receipt_path": row.get("route_receipt_path", ""),
        "route_status": row.get("route_status", "not_routed"),
        "run_dir": row.get("run_dir", ""),
        "status": row.get("status", "pending"),
        "updated_at": row.get("updated_at", ""),
        "url_kind": row.get("url_kind", ""),
    }


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


def run_self_test() -> None:
    root = Path("profile_media_live_captures/r43j_universal_social_batch_queue_workbench_panel_ui_wiring_test")
    root.mkdir(parents=True, exist_ok=True)
    test_panel_preview_selection_and_r43i_delegated_actions(root / "panel")
    test_report_checks_side_effects_and_plain_urls(root / "report")
    print("profile_media_universal_social_batch_queue_workbench_panel_r43j_test: PASS")


if __name__ == "__main__":
    run_self_test()
