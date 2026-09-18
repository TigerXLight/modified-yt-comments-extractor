from __future__ import annotations

import json
from pathlib import Path

from profile_media_universal_social_batch_workbench_app_shell_commands_r43l import (
    R43L_MARKER,
    R43L_PASS_STATUS,
    UniversalSocialBatchWorkbenchAppShellCommandRequestR43L,
    build_report,
    build_universal_social_batch_workbench_app_shell_commands_r43l,
)


def test_app_shell_delegates_panel_and_gui_state_commands(tmp_path: Path) -> None:
    shell = build_universal_social_batch_workbench_app_shell_commands_r43l(output_root=tmp_path / "shell")
    preview = shell.run_app_shell_command(
        UniversalSocialBatchWorkbenchAppShellCommandRequestR43L(
            command_name="create_queue_preview",
            session_id="session-a",
            inputs=("https://x.com/example/status/1111111111111111111?s=20", "https://bsky.app/profile/example.bsky.social"),
            pasted_text="https://unknown.invalid/profile/example",
            capture_timestamp="20260915T130000Z",
            output_root=str(tmp_path / "preview"),
            fixture_mode=True,
        )
    )
    assert preview.status == R43L_PASS_STATUS
    assert preview.delegated_to == "R43J"
    assert Path(preview.panel_state_path).exists()
    assert Path(preview.queue_path).exists()
    assert preview.pending_platform_count >= 0
    assert preview.platform_counts.get("bluesky", 0) >= 1
    assert preview.unsupported_count >= 1

    selected = (_first_queue_id(preview.panel_state_path),)
    saved = shell.run_app_shell_command(
        UniversalSocialBatchWorkbenchAppShellCommandRequestR43L(
            command_name="save_gui_state",
            session_id="session-a",
            panel_state_path=preview.panel_state_path,
            selected_queue_ids=selected,
            raw_text="https://x.com/example/status/1111111111111111111",
            capture_timestamp="20260915T130100Z",
            output_root=str(tmp_path / "save"),
            fixture_mode=True,
        )
    )
    assert saved.delegated_to == "R43K"
    assert saved.selected_queue_ids == selected
    assert Path(saved.gui_state_path).exists()
    assert Path(saved.selection_path).exists()
    assert Path(saved.recent_sessions_path).exists()

    restored = shell.run_app_shell_command(
        UniversalSocialBatchWorkbenchAppShellCommandRequestR43L(
            command_name="restore_gui_state",
            session_id="session-a",
            panel_state_path=preview.panel_state_path,
            gui_state_path=saved.gui_state_path,
            capture_timestamp="20260915T130200Z",
            output_root=str(tmp_path / "restore"),
            fixture_mode=True,
        )
    )
    assert restored.delegated_to == "R43K"
    assert "R43L -> R43J/R43K -> R43I -> R43H -> R43G -> R43F -> R43E -> R43D" == restored.route_chain

    run = shell.run_app_shell_command(
        UniversalSocialBatchWorkbenchAppShellCommandRequestR43L(
            command_name="run_pending",
            session_id="session-a",
            queue_path=preview.queue_path,
            selected_queue_ids=selected,
            capture_timestamp="20260915T130300Z",
            output_root=str(tmp_path / "run"),
            fixture_mode=True,
        )
    )
    assert run.delegated_to == "R43J"
    assert Path(run.route_receipts_path).exists()
    assert run.side_effect_flags["direct_r43h_r43g_r43f_r43e_r43d_call_performed_by_r43l"] is False
    assert run.side_effect_flags["webview2_session_started_by_r43l"] is False
    assert run.side_effect_flags["source_role_checks_performed"] is False
    assert run.side_effect_flags["remote_media_downloads_performed"] is False
    assert "](" not in json.dumps(run.to_dict())


def test_report_checks_and_boundaries(tmp_path: Path) -> None:
    report = build_report(tmp_path)
    data = report.to_dict()
    assert data["marker"] == R43L_MARKER
    assert data["status"] == R43L_PASS_STATUS, [check for check in data["checks"] if check["status"] != "pass"]
    required = {
        "universal_social_batch_workbench_app_shell_invoked",
        "workbench_open_preview_save_restore_do_not_route_items",
        "command_layer_delegates_to_r43j_and_r43k",
        "run_resume_retry_skip_commands_recorded",
        "recent_sessions_and_selection_preserved",
        "duplicate_rows_visible_but_not_routed_twice",
        "completed_rows_skipped_on_resume",
        "failed_terminal_and_unsupported_not_retried_by_default",
        "implemented_bluesky_or_pending_platform_and_unknown_receipts_visible",
        "twitter_x_route_chain_preserved_through_r43l_r43j_r43i_r43h_r43g_r43f_r43e_r43d",
        "app_shell_state_commands_navigation_selection_and_summary_written",
        "platform_and_status_counts_visible",
        "universal_contract_preserved",
        "no_browser_or_source_role_side_effects",
        "no_hidden_api_cookie_token_or_challenge_bypass",
        "no_remote_media_downloads",
        "plain_machine_urls",
    }
    assert required <= {check["name"] for check in data["checks"]}
    flags = data["side_effect_flags"]
    assert flags["webview2_session_started_by_r43l"] is False
    assert flags["cefsharp_session_started_by_r43l"] is False
    assert flags["hidden_api_scraping_performed"] is False
    assert flags["cookie_or_token_extraction_performed"] is False
    assert flags["source_role_checks_performed"] is False
    assert flags["review_window_dependency_invoked"] is False
    assert flags["remote_media_downloads_performed"] is False
    assert flags["youtube_capture_engine_behavior_changed"] is False
    assert flags["direct_r43h_r43g_r43f_r43e_r43d_call_performed_by_r43l"] is False
    assert "](" not in json.dumps(data)


def _first_queue_id(panel_state_path: str) -> str:
    rows_path = Path(panel_state_path).with_name("panel_rows.ndjson")
    first = rows_path.read_text(encoding="utf-8").splitlines()[0]
    return json.loads(first)["queue_id"]


def run_self_test() -> None:
    root = Path("profile_media_live_captures/r43l_universal_social_batch_workbench_app_shell_commands_test")
    root.mkdir(parents=True, exist_ok=True)
    test_app_shell_delegates_panel_and_gui_state_commands(root / "shell")
    test_report_checks_and_boundaries(root / "report")
    print("profile_media_universal_social_batch_workbench_app_shell_commands_r43l_test: PASS")


if __name__ == "__main__":
    run_self_test()
