from __future__ import annotations

import json
from pathlib import Path

from profile_media_universal_social_batch_queue_workbench_panel_r43j import (
    UniversalSocialBatchQueueWorkbenchPanelRequestR43J,
    build_universal_social_batch_queue_workbench_panel_r43j,
)
from profile_media_universal_social_batch_workbench_gui_state_bridge_r43k import (
    R43K_MARKER,
    R43K_PASS_STATUS,
    UniversalSocialBatchWorkbenchGuiStateRequestR43K,
    build_report,
    build_universal_social_batch_workbench_gui_state_bridge_r43k,
)


def test_save_restore_selection_inputs_receipts_and_queue_snapshot(tmp_path: Path) -> None:
    tmp_path.mkdir(parents=True, exist_ok=True)
    panel = build_universal_social_batch_queue_workbench_panel_r43j(output_root=tmp_path / "panel")
    preview = panel.run_panel_action(
        UniversalSocialBatchQueueWorkbenchPanelRequestR43J(
            action="create_preview",
            inputs=("https://x.com/example/status/1111111111111111111?s=20", "https://bsky.app/profile/example.bsky.social"),
            pasted_text="https://unknown.invalid/profile/example",
            capture_timestamp="20260915T111000Z",
            output_root=str(tmp_path / "panel_preview"),
            fixture_mode=True,
        )
    )
    queue_path = tmp_path / "queue.json"
    _write_queue(queue_path, preview.rows)
    run = panel.run_panel_action(
        UniversalSocialBatchQueueWorkbenchPanelRequestR43J(
            action="run_pending",
            existing_queue_path=str(queue_path),
            capture_timestamp="20260915T111050Z",
            output_root=str(tmp_path / "panel_run"),
            fixture_mode=True,
        )
    )
    selected = (run.rows[0]["queue_id"],)
    bridge = build_universal_social_batch_workbench_gui_state_bridge_r43k(output_root=tmp_path / "bridge")
    saved = bridge.run_state_operation(
        UniversalSocialBatchWorkbenchGuiStateRequestR43K(
            operation="save_panel_state",
            session_id="session-a",
            panel_state_path=run.panel_state_path,
            selected_queue_ids=selected,
            raw_text="https://x.com/example/status/1111111111111111111",
            receipt_paths=(run.route_receipts_path,),
            capture_timestamp="20260915T111100Z",
            output_root=str(tmp_path / "bridge_save"),
        )
    )
    assert saved.status == R43K_PASS_STATUS
    assert saved.state_record["selected_queue_ids"] == list(selected)
    assert saved.state_record["platform_counts"]
    assert saved.state_record["status_counts"]
    assert saved.state_record["pending_platform_count"] >= 1
    assert saved.state_record["unsupported_count"] >= 1
    assert Path(saved.gui_state_path).exists()
    assert Path(saved.history_path).exists()
    receipts = json.loads(Path(saved.receipts_path).read_text(encoding="utf-8"))
    assert _norm(run.route_receipts_path) in {_norm(path) for path in receipts["receipt_paths"]}
    assert _norm(run.route_receipts_path) == _norm(receipts["route_receipts_path"])

    restored = bridge.run_state_operation(
        UniversalSocialBatchWorkbenchGuiStateRequestR43K(
            operation="restore_panel_state",
            session_id="session-a",
            panel_state_path=run.panel_state_path,
            restored_from_path=saved.gui_state_path,
            capture_timestamp="20260915T111200Z",
            output_root=str(tmp_path / "bridge_restore"),
        )
    )
    assert restored.restored_panel_state["counts_by_platform"] == saved.restored_panel_state["counts_by_platform"]
    assert "R43J -> R43I -> R43H -> R43G -> R43F -> R43E -> R43D" == restored.restored_panel_state["route_chain"]

    queue_restored = bridge.run_state_operation(
        UniversalSocialBatchWorkbenchGuiStateRequestR43K(
            operation="create_state_snapshot_from_r43h_queue",
            session_id="queue-session",
            queue_path=str(queue_path),
            capture_timestamp="20260915T111300Z",
            output_root=str(tmp_path / "bridge_queue"),
            fixture_mode=True,
        )
    )
    assert queue_restored.restored_panel_state["counts_by_status"]
    assert Path(queue_restored.restored_panel_state_path).exists()

    remembered = bridge.run_state_operation(
        UniversalSocialBatchWorkbenchGuiStateRequestR43K(
            operation="remember_selection",
            session_id="session-a",
            panel_state_path=run.panel_state_path,
            selected_queue_ids=selected,
            inputs=("https://x.com/example",),
            receipt_paths=(run.route_receipts_path,),
            capture_timestamp="20260915T111400Z",
            output_root=str(tmp_path / "bridge_remember"),
        )
    )
    assert remembered.state_record["selected_queue_ids"] == list(selected)
    assert Path(remembered.last_inputs_path).read_text(encoding="utf-8").strip()


def test_report_checks_and_boundaries(tmp_path: Path) -> None:
    report = build_report(tmp_path)
    data = report.to_dict()
    assert data["marker"] == R43K_MARKER
    assert data["status"] == R43K_PASS_STATUS, [check for check in data["checks"] if check["status"] != "pass"]
    required = {
        "universal_social_batch_workbench_gui_state_bridge_invoked",
        "r43j_panel_state_can_be_saved",
        "r43j_panel_state_can_be_restored",
        "r43h_queue_can_be_restored_to_panel_compatible_state",
        "recent_sessions_are_listed_with_stable_paths",
        "selection_and_last_inputs_are_preserved",
        "receipt_paths_are_preserved",
        "platform_and_status_counts_preserved",
        "save_restore_does_not_route_items",
        "run_resume_retry_remain_delegated_to_r43j_r43i_r43h",
        "pending_platform_and_unknown_receipts_visible",
        "twitter_x_route_chain_preserved_in_state",
        "gui_state_history_and_summary_written",
        "universal_contract_preserved",
        "no_browser_or_source_role_side_effects",
        "no_hidden_api_cookie_token_or_challenge_bypass",
        "no_remote_media_downloads",
        "plain_machine_urls",
    }
    assert required <= {check["name"] for check in data["checks"]}
    flags = data["side_effect_flags"]
    assert flags["webview2_session_started_by_r43k"] is False
    assert flags["cefsharp_session_started_by_r43k"] is False
    assert flags["hidden_api_scraping_performed"] is False
    assert flags["cookie_or_token_extraction_performed"] is False
    assert flags["source_role_checks_performed"] is False
    assert flags["review_window_dependency_invoked"] is False
    assert flags["remote_media_downloads_performed"] is False
    assert flags["youtube_capture_engine_behavior_changed"] is False
    assert flags["routing_performed_by_r43k"] is False
    assert "](" not in json.dumps(data)


def _write_queue(path: Path, rows) -> None:
    items = []
    for row in rows:
        items.append({
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
        })
    path.write_text(json.dumps({"items": items}, indent=2), encoding="utf-8")


def _norm(path: str) -> str:
    return path.replace("\\", "/")


def run_self_test() -> None:
    root = Path("profile_media_live_captures/r43k_universal_social_batch_workbench_gui_state_bridge_test")
    root.mkdir(parents=True, exist_ok=True)
    test_save_restore_selection_inputs_receipts_and_queue_snapshot(root / "bridge")
    test_report_checks_and_boundaries(root / "report")
    print("profile_media_universal_social_batch_workbench_gui_state_bridge_r43k_test: PASS")


if __name__ == "__main__":
    run_self_test()
