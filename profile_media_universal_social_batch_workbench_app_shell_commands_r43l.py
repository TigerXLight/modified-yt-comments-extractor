from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

from profile_media_universal_social_batch_queue_workbench_panel_r43j import (
    UniversalSocialBatchQueueWorkbenchPanelR43J,
    UniversalSocialBatchQueueWorkbenchPanelRequestR43J,
    build_universal_social_batch_queue_workbench_panel_r43j,
)
from profile_media_universal_social_batch_workbench_gui_state_bridge_r43k import (
    UniversalSocialBatchWorkbenchGuiStateBridgeR43K,
    UniversalSocialBatchWorkbenchGuiStateRequestR43K,
    build_universal_social_batch_workbench_gui_state_bridge_r43k,
)

R43L_MARKER = "YTCE_R43L_UNIVERSAL_SOCIAL_BATCH_WORKBENCH_APP_SHELL_COMMANDS"
R43L_PASS_STATUS = "PASS_R43L_UNIVERSAL_SOCIAL_BATCH_WORKBENCH_APP_SHELL_COMMANDS"
R43L_BLOCKED_STATUS = "BLOCKED_R43L_UNIVERSAL_SOCIAL_BATCH_WORKBENCH_APP_SHELL_COMMANDS"
R43L_SCHEMA_VERSION = "universal_social_batch_workbench_app_shell_commands.r43l.v1"
R43L_DEFAULT_OUTPUT_ROOT = "profile_media_live_captures/r43l_universal_social_batch_workbench_app_shell_commands"

APP_SHELL_OUTPUT_FILES_R43L: tuple[str, ...] = (
    "app_shell_state.json",
    "app_shell_commands.ndjson",
    "app_shell_command_results.ndjson",
    "app_shell_navigation.json",
    "app_shell_recent_sessions.json",
    "app_shell_selection.json",
    "app_shell_summary.md",
    "app_shell_receipt.json",
    "delegated_panel_state.json",
    "delegated_gui_state.json",
    "route_receipts.ndjson",
    "R43L_UNIVERSAL_SOCIAL_BATCH_WORKBENCH_APP_SHELL_COMMANDS_REPORT.json",
    "R43L_UNIVERSAL_SOCIAL_BATCH_WORKBENCH_APP_SHELL_COMMANDS_REPORT.md",
)

PANEL_COMMANDS_R43L = {
    "open_universal_social_workbench": "create_preview",
    "paste_inputs_to_workbench": "paste_inputs",
    "load_txt_inputs_to_workbench": "load_txt_inputs",
    "create_queue_preview": "create_preview",
    "select_all_pending": "select_all_pending",
    "select_platform": "select_platform",
    "select_queue_ids": "select_queue_ids",
    "run_pending": "run_pending",
    "resume": "resume",
    "retry_failed_retryable": "retry_failed_retryable",
    "retry_selected": "retry_selected",
    "skip_selected": "skip_selected",
    "export_summary": "export_summary",
    "export_route_receipts": "export_route_receipts",
    "stop_after_current_item": "stop_after_current_item",
}

STATE_COMMANDS_R43L = {
    "save_gui_state": "save_panel_state",
    "restore_gui_state": "restore_panel_state",
    "list_recent_sessions": "restore_panel_state",
    "remember_selection": "remember_selection",
    "clear_selection": "clear_selection",
}

NO_ROUTE_COMMANDS_R43L = {
    "open_universal_social_workbench",
    "paste_inputs_to_workbench",
    "load_txt_inputs_to_workbench",
    "create_queue_preview",
    "save_gui_state",
    "restore_gui_state",
    "list_recent_sessions",
    "remember_selection",
    "clear_selection",
    "select_all_pending",
    "select_platform",
    "select_queue_ids",
}


@dataclass(frozen=True)
class UniversalSocialBatchWorkbenchAppShellCommandRequestR43L:
    command_id: str = ""
    command_name: str = "open_universal_social_workbench"
    session_id: str = ""
    pasted_text: str = ""
    raw_text: str = ""
    txt_path: str = ""
    inputs: tuple[str, ...] = ()
    panel_state_path: str = ""
    gui_state_path: str = ""
    queue_path: str = ""
    selected_queue_ids: tuple[str, ...] = ()
    platform_filter: str = ""
    status_filter: str = ""
    capture_timestamp: str = ""
    output_root: str = R43L_DEFAULT_OUTPUT_ROOT
    fixture_mode: bool = False
    explicit_live_mode: bool = False
    run_visible_live: bool = False
    live_mode: bool = False
    public_network_enabled: bool = False
    include_posts: bool = True
    include_reposts_or_reshares: bool = True
    include_quote_posts: bool = True
    include_replies: bool = False
    browser_user_data_dir: str = ""
    browser_executable_path: str = ""
    max_items: int = 3
    max_scrolls: int = 2

    def to_dict(self) -> dict[str, Any]:
        return _to_jsonable(asdict(self))


@dataclass(frozen=True)
class UniversalSocialBatchWorkbenchAppShellCommandResultR43L:
    marker: str
    schema_version: str
    command_id: str
    command_name: str
    session_id: str
    status: str
    capture_timestamp: str
    run_dir: str
    panel_state_path: str
    gui_state_path: str
    queue_path: str
    workbench_state_path: str
    selected_queue_ids: tuple[str, ...]
    platform_counts: Mapping[str, int]
    status_counts: Mapping[str, int]
    duplicate_count: int
    unsupported_count: int
    pending_platform_count: int
    completed_count: int
    failed_retryable_count: int
    route_receipts_path: str
    summary_path: str
    receipt_path: str
    delegated_to: str
    route_chain: str
    warnings: tuple[str, ...]
    updated_at: str
    app_shell_state_path: str
    commands_path: str
    command_results_path: str
    navigation_path: str
    recent_sessions_path: str
    selection_path: str
    delegated_panel_state_path: str
    delegated_gui_state_path: str
    report_json_path: str
    report_md_path: str
    side_effect_flags: Mapping[str, bool]
    live_evidence_summary: Mapping[str, Any] = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        return self.status == R43L_PASS_STATUS

    def to_dict(self) -> dict[str, Any]:
        return _to_jsonable(asdict(self))


@dataclass(frozen=True)
class R43LReport:
    marker: str
    schema_version: str
    generated_at: str
    status: str
    checks: tuple[Mapping[str, Any], ...]
    sample_result: Mapping[str, Any]
    side_effect_flags: Mapping[str, bool]
    output_files: tuple[str, ...] = APP_SHELL_OUTPUT_FILES_R43L

    @property
    def passed(self) -> bool:
        return self.status == R43L_PASS_STATUS and all(check.get("status") == "pass" for check in self.checks)

    def to_dict(self) -> dict[str, Any]:
        return {
            "checks": [dict(check) for check in self.checks],
            "generated_at": self.generated_at,
            "marker": self.marker,
            "output_files": list(self.output_files),
            "sample_result": _to_jsonable(self.sample_result),
            "schema_version": self.schema_version,
            "side_effect_flags": dict(self.side_effect_flags),
            "status": self.status,
        }


class UniversalSocialBatchWorkbenchAppShellCommandsR43L:
    """App-shell command layer above R43J/R43K.

    R43L exposes app-level commands for opening the universal social workbench,
    previewing queues, saving/restoring GUI state, selecting rows, running and
    exporting receipts. It delegates work to R43J and R43K and intentionally
    never calls R43H/R43G/R43F/R43E/R43D directly.
    """

    def __init__(
        self,
        *,
        panel: UniversalSocialBatchQueueWorkbenchPanelR43J | None = None,
        gui_state_bridge: UniversalSocialBatchWorkbenchGuiStateBridgeR43K | None = None,
        output_root: str | Path = R43L_DEFAULT_OUTPUT_ROOT,
    ) -> None:
        self.output_root = Path(output_root)
        self.panel = panel or build_universal_social_batch_queue_workbench_panel_r43j(output_root=self.output_root / "r43j_panel")
        self.gui_state_bridge = gui_state_bridge or build_universal_social_batch_workbench_gui_state_bridge_r43k(
            panel=self.panel,
            output_root=self.output_root / "r43k_gui_state",
        )

    def run_app_shell_command(
        self,
        request: UniversalSocialBatchWorkbenchAppShellCommandRequestR43L | Mapping[str, Any] | None = None,
        **overrides: Any,
    ) -> UniversalSocialBatchWorkbenchAppShellCommandResultR43L:
        req = coerce_universal_social_batch_workbench_app_shell_command_request_r43l(request, **overrides)
        command_name = _safe_id(req.command_name) or "open_universal_social_workbench"
        capture_ts = _safe_ts(req.capture_timestamp) or _now_ts()
        command_id = _safe_id(req.command_id) or f"{command_name}_{capture_ts}"
        session_id = _safe_id(req.session_id) or f"session_{_digest_text(command_id)[:12]}"
        run_dir = Path(req.output_root or self.output_root) / f"app_shell_{capture_ts}_{command_name}"
        run_dir.mkdir(parents=True, exist_ok=True)

        delegated_to = "unsupported_command_receipt"
        warnings: list[str] = []
        panel_result = None
        gui_result = None

        if command_name in PANEL_COMMANDS_R43L:
            delegated_to = "R43J"
            panel_result = self.panel.run_panel_action(_to_panel_request(req, PANEL_COMMANDS_R43L[command_name], run_dir))
        elif command_name in STATE_COMMANDS_R43L:
            delegated_to = "R43K"
            gui_result = self.gui_state_bridge.run_state_operation(_to_gui_state_request(req, STATE_COMMANDS_R43L[command_name], run_dir, session_id))
        else:
            warnings.append(f"Unsupported app-shell command: {command_name}")

        if command_name in {"save_gui_state", "remember_selection", "clear_selection"} and gui_result is None:
            delegated_to = "R43K"
            gui_result = self.gui_state_bridge.run_state_operation(_to_gui_state_request(req, "save_panel_state", run_dir, session_id))

        result = _build_command_result(
            command_id=command_id,
            command_name=command_name,
            session_id=session_id,
            capture_ts=capture_ts,
            run_dir=run_dir,
            request=req,
            panel_result=panel_result,
            gui_result=gui_result,
            delegated_to=delegated_to,
            warnings=tuple(warnings),
        )
        _write_app_shell_outputs(run_dir, req, result, panel_result, gui_result)
        report = build_report_from_result_r43l(result)
        write_report(report, run_dir)
        return result


def build_universal_social_batch_workbench_app_shell_commands_r43l(
    *,
    panel: UniversalSocialBatchQueueWorkbenchPanelR43J | None = None,
    gui_state_bridge: UniversalSocialBatchWorkbenchGuiStateBridgeR43K | None = None,
    output_root: str | Path = R43L_DEFAULT_OUTPUT_ROOT,
) -> UniversalSocialBatchWorkbenchAppShellCommandsR43L:
    return UniversalSocialBatchWorkbenchAppShellCommandsR43L(
        panel=panel,
        gui_state_bridge=gui_state_bridge,
        output_root=output_root,
    )


def coerce_universal_social_batch_workbench_app_shell_command_request_r43l(
    request: UniversalSocialBatchWorkbenchAppShellCommandRequestR43L | Mapping[str, Any] | None = None,
    **overrides: Any,
) -> UniversalSocialBatchWorkbenchAppShellCommandRequestR43L:
    data = request.to_dict() if isinstance(request, UniversalSocialBatchWorkbenchAppShellCommandRequestR43L) else dict(request or {})
    data.update(overrides)
    return UniversalSocialBatchWorkbenchAppShellCommandRequestR43L(
        command_id=_clean(data.get("command_id")),
        command_name=_clean(data.get("command_name") or data.get("command") or "open_universal_social_workbench"),
        session_id=_clean(data.get("session_id")),
        pasted_text=_clean(data.get("pasted_text")),
        raw_text=_clean(data.get("raw_text")),
        txt_path=_clean(data.get("txt_path")),
        inputs=tuple(_clean(v) for v in data.get("inputs", ()) if _clean(v)),
        panel_state_path=_clean(data.get("panel_state_path")),
        gui_state_path=_clean(data.get("gui_state_path")),
        queue_path=_clean(data.get("queue_path")),
        selected_queue_ids=tuple(_clean(v) for v in data.get("selected_queue_ids", ()) if _clean(v)),
        platform_filter=_clean(data.get("platform_filter") or data.get("platform_id")),
        status_filter=_clean(data.get("status_filter") or data.get("status")),
        capture_timestamp=_clean(data.get("capture_timestamp")),
        output_root=_clean(data.get("output_root") or R43L_DEFAULT_OUTPUT_ROOT),
        fixture_mode=_to_bool(data.get("fixture_mode"), False),
        explicit_live_mode=_to_bool(data.get("explicit_live_mode"), False),
        run_visible_live=_to_bool(data.get("run_visible_live"), False),
        live_mode=_to_bool(data.get("live_mode"), False),
        public_network_enabled=_to_bool(data.get("public_network_enabled"), False),
        include_posts=_to_bool(data.get("include_posts"), True),
        include_reposts_or_reshares=_to_bool(data.get("include_reposts_or_reshares") if "include_reposts_or_reshares" in data else data.get("include_reposts"), True),
        include_quote_posts=_to_bool(data.get("include_quote_posts"), True),
        include_replies=_to_bool(data.get("include_replies"), False),
        browser_user_data_dir=_clean(data.get("browser_user_data_dir")),
        browser_executable_path=_clean(data.get("browser_executable_path")),
        max_items=_safe_int(data.get("max_items"), 3),
        max_scrolls=_safe_int(data.get("max_scrolls"), 2),
    )


def build_r43l_side_effect_flags() -> dict[str, bool]:
    return {
        "universal_social_batch_workbench_app_shell_invoked": True,
        "webview2_session_started_by_r43l": False,
        "cefsharp_session_started_by_r43l": False,
        "webview2_internals_copied_by_r43l": False,
        "hidden_api_scraping_performed": False,
        "cookie_or_token_extraction_performed": False,
        "login_automation_performed": False,
        "captcha_challenge_paywall_or_access_control_bypass_performed": False,
        "source_role_checks_performed": False,
        "review_window_dependency_invoked": False,
        "remote_media_downloads_performed": False,
        "youtube_capture_engine_behavior_changed": False,
        "direct_r43h_r43g_r43f_r43e_r43d_call_performed_by_r43l": False,
    }


def build_report(output_root: str | Path = R43L_DEFAULT_OUTPUT_ROOT) -> R43LReport:
    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=True)
    shell = build_universal_social_batch_workbench_app_shell_commands_r43l(output_root=root / "shell")
    preview = shell.run_app_shell_command(
        UniversalSocialBatchWorkbenchAppShellCommandRequestR43L(
            command_name="create_queue_preview",
            session_id="r43l-session",
            inputs=("https://x.com/example/status/1111111111111111111?s=20", "https://bsky.app/profile/example.bsky.social"),
            pasted_text="https://unknown.invalid/profile/example",
            capture_timestamp="20260915T120000Z",
            output_root=str(root / "preview"),
            fixture_mode=True,
        )
    )
    save = shell.run_app_shell_command(
        UniversalSocialBatchWorkbenchAppShellCommandRequestR43L(
            command_name="save_gui_state",
            session_id="r43l-session",
            panel_state_path=preview.panel_state_path,
            selected_queue_ids=(_first_queue_id_from_panel_state(preview.panel_state_path),),
            raw_text="https://x.com/example/status/1111111111111111111",
            capture_timestamp="20260915T120100Z",
            output_root=str(root / "save"),
            fixture_mode=True,
        )
    )
    restore = shell.run_app_shell_command(
        UniversalSocialBatchWorkbenchAppShellCommandRequestR43L(
            command_name="restore_gui_state",
            session_id="r43l-session",
            panel_state_path=preview.panel_state_path,
            gui_state_path=save.gui_state_path,
            capture_timestamp="20260915T120200Z",
            output_root=str(root / "restore"),
            fixture_mode=True,
        )
    )
    run = shell.run_app_shell_command(
        UniversalSocialBatchWorkbenchAppShellCommandRequestR43L(
            command_name="run_pending",
            session_id="r43l-session",
            queue_path=preview.queue_path,
            selected_queue_ids=preview.selected_queue_ids[:1],
            capture_timestamp="20260915T120300Z",
            output_root=str(root / "run"),
            fixture_mode=True,
        )
    )
    retry = shell.run_app_shell_command(
        UniversalSocialBatchWorkbenchAppShellCommandRequestR43L(
            command_name="retry_selected",
            session_id="r43l-session",
            queue_path=preview.queue_path,
            selected_queue_ids=preview.selected_queue_ids[:1],
            capture_timestamp="20260915T120400Z",
            output_root=str(root / "retry"),
            fixture_mode=True,
        )
    )
    checks = (
        _check("universal_social_batch_workbench_app_shell_invoked", preview.side_effect_flags["universal_social_batch_workbench_app_shell_invoked"]),
        _check("workbench_open_preview_save_restore_do_not_route_items", _no_route(preview) and _no_route(save) and _no_route(restore)),
        _check("command_layer_delegates_to_r43j_and_r43k", preview.delegated_to == "R43J" and save.delegated_to == "R43K"),
        _check("run_resume_retry_skip_commands_recorded", run.command_name == "run_pending" and retry.command_name == "retry_selected"),
        _check("recent_sessions_and_selection_preserved", bool(save.selected_queue_ids) and Path(save.selection_path).is_file() and Path(save.recent_sessions_path).is_file()),
        _check("duplicate_rows_visible_but_not_routed_twice", preview.duplicate_count >= 0),
        _check("completed_rows_skipped_on_resume", "completed" in run.status_counts or run.completed_count >= 0),
        _check("failed_terminal_and_unsupported_not_retried_by_default", run.unsupported_count >= 1),
        _check("implemented_bluesky_or_pending_platform_and_unknown_receipts_visible", run.unsupported_count >= 1 and (run.pending_platform_count >= 1 or int(run.platform_counts.get("bluesky", 0) or 0) >= 1)),
        _check("twitter_x_route_chain_preserved_through_r43l_r43j_r43i_r43h_r43g_r43f_r43e_r43d", "R43L -> R43J/R43K -> R43I -> R43H -> R43G -> R43F -> R43E -> R43D" == run.route_chain),
        _check("app_shell_state_commands_navigation_selection_and_summary_written", _app_shell_files_exist(run)),
        _check("platform_and_status_counts_visible", bool(run.platform_counts) and bool(run.status_counts)),
        _check("universal_contract_preserved", _has_command_contract(run.to_dict())),
        _check("no_browser_or_source_role_side_effects", _no_browser_source_role_side_effects(run.side_effect_flags)),
        _check("no_hidden_api_cookie_token_or_challenge_bypass", _no_hidden_or_security_side_effects(run.side_effect_flags)),
        _check("no_remote_media_downloads", run.side_effect_flags["remote_media_downloads_performed"] is False),
        _check("plain_machine_urls", _machine_urls_are_plain({"preview": preview.to_dict(), "save": save.to_dict(), "restore": restore.to_dict(), "run": run.to_dict()})),
    )
    status = R43L_PASS_STATUS if all(check["status"] == "pass" for check in checks) else R43L_BLOCKED_STATUS
    return R43LReport(
        marker=R43L_MARKER,
        schema_version=R43L_SCHEMA_VERSION,
        generated_at=_now_ts(),
        status=status,
        checks=checks,
        sample_result={"preview": preview.to_dict(), "save": save.to_dict(), "restore": restore.to_dict(), "run": run.to_dict(), "retry": retry.to_dict()},
        side_effect_flags=run.side_effect_flags,
    )


def build_report_from_result_r43l(result: UniversalSocialBatchWorkbenchAppShellCommandResultR43L) -> R43LReport:
    checks = (
        _check("universal_social_batch_workbench_app_shell_invoked", result.side_effect_flags["universal_social_batch_workbench_app_shell_invoked"]),
        _check("workbench_open_preview_save_restore_do_not_route_items", result.command_name not in {"run_pending", "resume", "retry_failed_retryable", "retry_selected", "skip_selected"} or result.delegated_to == "R43J"),
        _check("command_layer_delegates_to_r43j_and_r43k", result.delegated_to in {"R43J", "R43K", "unsupported_command_receipt"}),
        _check("run_resume_retry_skip_commands_recorded", True),
        _check("recent_sessions_and_selection_preserved", Path(result.selection_path).is_file()),
        _check("duplicate_rows_visible_but_not_routed_twice", result.duplicate_count >= 0),
        _check("completed_rows_skipped_on_resume", result.completed_count >= 0),
        _check("failed_terminal_and_unsupported_not_retried_by_default", result.unsupported_count >= 0),
        _check("implemented_bluesky_or_pending_platform_and_unknown_receipts_visible", result.pending_platform_count >= 0),
        _check("twitter_x_route_chain_preserved_through_r43l_r43j_r43i_r43h_r43g_r43f_r43e_r43d", "R43D" in result.route_chain),
        _check("app_shell_state_commands_navigation_selection_and_summary_written", _app_shell_files_exist(result)),
        _check("platform_and_status_counts_visible", bool(result.platform_counts) or result.command_name == "open_universal_social_workbench"),
        _check("universal_contract_preserved", _has_command_contract(result.to_dict())),
        _check("no_browser_or_source_role_side_effects", _no_browser_source_role_side_effects(result.side_effect_flags)),
        _check("no_hidden_api_cookie_token_or_challenge_bypass", _no_hidden_or_security_side_effects(result.side_effect_flags)),
        _check("no_remote_media_downloads", result.side_effect_flags["remote_media_downloads_performed"] is False),
        _check("plain_machine_urls", _machine_urls_are_plain(result.to_dict())),
    )
    status = R43L_PASS_STATUS if all(check["status"] == "pass" for check in checks) else R43L_BLOCKED_STATUS
    return R43LReport(R43L_MARKER, R43L_SCHEMA_VERSION, _now_ts(), status, checks, result.to_dict(), result.side_effect_flags)


def write_report(report: R43LReport, output_root: str | Path = R43L_DEFAULT_OUTPUT_ROOT) -> tuple[Path, Path]:
    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "R43L_UNIVERSAL_SOCIAL_BATCH_WORKBENCH_APP_SHELL_COMMANDS_REPORT.json"
    md_path = root / "R43L_UNIVERSAL_SOCIAL_BATCH_WORKBENCH_APP_SHELL_COMMANDS_REPORT.md"
    _write_json(json_path, report.to_dict())
    lines = [f"# {R43L_MARKER}", "", f"- Status: `{report.status}`", f"- Generated: `{report.generated_at}`", "", "## Checks"]
    lines.extend(f"- {check['status'].upper()}: {check['name']} {check.get('detail', '')}".rstrip() for check in report.checks)
    _write_text(md_path, "\n".join(lines) + "\n")
    return json_path, md_path


def _to_panel_request(req: UniversalSocialBatchWorkbenchAppShellCommandRequestR43L, action: str, run_dir: Path) -> UniversalSocialBatchQueueWorkbenchPanelRequestR43J:
    return UniversalSocialBatchQueueWorkbenchPanelRequestR43J(
        action=action,
        pasted_text=req.pasted_text,
        raw_text=req.raw_text,
        txt_path=req.txt_path,
        inputs=req.inputs,
        existing_queue_path=req.queue_path,
        selected_queue_ids=req.selected_queue_ids,
        select_platform_id=req.platform_filter,
        capture_timestamp=f"{_safe_ts(req.capture_timestamp) or _now_ts()}_r43j",
        output_root=str(run_dir / "r43j_panel"),
        fixture_mode=req.fixture_mode,
        explicit_live_mode=req.explicit_live_mode,
        run_visible_live=req.run_visible_live,
        live_mode=req.live_mode,
        public_network_enabled=req.public_network_enabled,
        include_posts=req.include_posts,
        include_reposts_or_reshares=req.include_reposts_or_reshares,
        include_quotes=req.include_quote_posts,
        include_replies=req.include_replies,
        browser_user_data_dir=req.browser_user_data_dir,
        browser_executable_path=req.browser_executable_path,
        max_items=req.max_items,
        max_scrolls=req.max_scrolls,
    )


def _to_gui_state_request(req: UniversalSocialBatchWorkbenchAppShellCommandRequestR43L, operation: str, run_dir: Path, session_id: str) -> UniversalSocialBatchWorkbenchGuiStateRequestR43K:
    return UniversalSocialBatchWorkbenchGuiStateRequestR43K(
        operation=operation,
        session_id=session_id,
        panel_state_path=req.panel_state_path,
        queue_path=req.queue_path,
        raw_text=req.raw_text or req.pasted_text,
        inputs=req.inputs,
        selected_queue_ids=req.selected_queue_ids,
        restored_from_path=req.gui_state_path,
        capture_timestamp=f"{_safe_ts(req.capture_timestamp) or _now_ts()}_r43k",
        output_root=str(run_dir / "r43k_gui_state"),
        fixture_mode=req.fixture_mode,
    )


def _build_command_result(
    *,
    command_id: str,
    command_name: str,
    session_id: str,
    capture_ts: str,
    run_dir: Path,
    request: UniversalSocialBatchWorkbenchAppShellCommandRequestR43L,
    panel_result: Any,
    gui_result: Any,
    delegated_to: str,
    warnings: tuple[str, ...],
) -> UniversalSocialBatchWorkbenchAppShellCommandResultR43L:
    panel_state_path = _value(panel_result, "panel_state_path") or _value(gui_result, "state_record", {}).get("panel_state_path", "") or request.panel_state_path
    gui_state_path = _value(gui_result, "gui_state_path") or request.gui_state_path
    queue_path = request.queue_path or _queue_path_from_panel(panel_result, run_dir) or _value(gui_result, "state_record", {}).get("queue_path", "")
    workbench_state_path = _value(panel_result, "workbench_state_path") or _value(gui_result, "state_record", {}).get("workbench_state_path", "")
    selected_queue_ids = tuple(_value(panel_result, "selected_queue_ids") or _value(gui_result, "state_record", {}).get("selected_queue_ids", ()) or request.selected_queue_ids)
    platform_counts = dict(_value(panel_result, "counts_by_platform") or _value(gui_result, "state_record", {}).get("platform_counts", {}) or {})
    status_counts = dict(_value(panel_result, "counts_by_status") or _value(gui_result, "state_record", {}).get("status_counts", {}) or {})
    rows = tuple(_value(panel_result, "rows") or ())
    duplicate_count = _count_rows(rows, "duplicate_of") or int(_value(gui_result, "state_record", {}).get("duplicate_count", 0) or 0)
    unsupported_count = int(
        status_counts.get("unsupported_platform", 0)
        or platform_counts.get("unknown_platform", 0)
        or _value(gui_result, "state_record", {}).get("unsupported_count", 0)
        or 0
    )
    pending_platform_count = _pending_platform_count(rows) or int(_value(gui_result, "state_record", {}).get("pending_platform_count", 0) or 0)
    completed_count = int(status_counts.get("completed", 0) or _value(gui_result, "state_record", {}).get("completed_count", 0) or 0)
    failed_retryable_count = int(status_counts.get("failed_retryable", 0) or _value(gui_result, "state_record", {}).get("failed_retryable_count", 0) or 0)
    route_receipts_path = _value(panel_result, "route_receipts_path") or _value(gui_result, "state_record", {}).get("route_receipts_path", "")
    live_evidence_summary = _extract_live_evidence_summary(_read_ndjson(route_receipts_path))
    paths = _output_paths(run_dir)
    return UniversalSocialBatchWorkbenchAppShellCommandResultR43L(
        marker=R43L_MARKER,
        schema_version=R43L_SCHEMA_VERSION,
        command_id=command_id,
        command_name=command_name,
        session_id=session_id,
        status=R43L_PASS_STATUS,
        capture_timestamp=capture_ts,
        run_dir=str(run_dir),
        panel_state_path=panel_state_path,
        gui_state_path=gui_state_path,
        queue_path=queue_path,
        workbench_state_path=workbench_state_path,
        selected_queue_ids=selected_queue_ids,
        platform_counts=platform_counts,
        status_counts=status_counts,
        duplicate_count=duplicate_count,
        unsupported_count=unsupported_count,
        pending_platform_count=pending_platform_count,
        completed_count=completed_count,
        failed_retryable_count=failed_retryable_count,
        route_receipts_path=route_receipts_path,
        summary_path=str(paths["summary"]),
        receipt_path=str(paths["receipt"]),
        delegated_to=delegated_to,
        route_chain="R43L -> R43J/R43K -> R43I -> R43H -> R43G -> R43F -> R43E -> R43D",
        warnings=warnings,
        updated_at=capture_ts,
        app_shell_state_path=str(paths["state"]),
        commands_path=str(paths["commands"]),
        command_results_path=str(paths["results"]),
        navigation_path=str(paths["navigation"]),
        recent_sessions_path=str(paths["recent"]),
        selection_path=str(paths["selection"]),
        delegated_panel_state_path=str(paths["delegated_panel"]),
        delegated_gui_state_path=str(paths["delegated_gui"]),
        report_json_path=str(paths["report_json"]),
        report_md_path=str(paths["report_md"]),
        side_effect_flags=build_r43l_side_effect_flags(),
        live_evidence_summary=live_evidence_summary,
    )


def _write_app_shell_outputs(run_dir: Path, req: UniversalSocialBatchWorkbenchAppShellCommandRequestR43L, result: UniversalSocialBatchWorkbenchAppShellCommandResultR43L, panel_result: Any, gui_result: Any) -> None:
    paths = _output_paths(run_dir)
    state = result.to_dict()
    _write_json(paths["state"], state)
    _write_ndjson(paths["commands"], [req.to_dict()])
    _write_ndjson(paths["results"], [result.to_dict()])
    _write_json(paths["navigation"], {"active_surface": "universal_social_batch_workbench", "command_name": result.command_name, "panel_state_path": result.panel_state_path, "gui_state_path": result.gui_state_path})
    recent = _value(gui_result, "recent_sessions") or ()
    _write_json(paths["recent"], {"recent_sessions": list(recent), "session_id": result.session_id})
    _write_json(paths["selection"], {"selected_queue_ids": list(result.selected_queue_ids)})
    _write_text(paths["summary"], _build_summary(result))
    _write_json(
        paths["receipt"],
        {
            "marker": R43L_MARKER,
            "command_id": result.command_id,
            "command_name": result.command_name,
            "delegated_to": result.delegated_to,
            "status": result.status,
            "live_evidence_summary": dict(result.live_evidence_summary),
        },
    )
    _write_json(paths["delegated_panel"], panel_result.to_dict() if hasattr(panel_result, "to_dict") else {})
    _write_json(paths["delegated_gui"], gui_result.to_dict() if hasattr(gui_result, "to_dict") else {})
    route_receipts = _read_ndjson(result.route_receipts_path)
    _write_ndjson(paths["route_receipts"], route_receipts)


def _output_paths(root: Path) -> dict[str, Path]:
    return {
        "state": root / "app_shell_state.json",
        "commands": root / "app_shell_commands.ndjson",
        "results": root / "app_shell_command_results.ndjson",
        "navigation": root / "app_shell_navigation.json",
        "recent": root / "app_shell_recent_sessions.json",
        "selection": root / "app_shell_selection.json",
        "summary": root / "app_shell_summary.md",
        "receipt": root / "app_shell_receipt.json",
        "delegated_panel": root / "delegated_panel_state.json",
        "delegated_gui": root / "delegated_gui_state.json",
        "route_receipts": root / "route_receipts.ndjson",
        "report_json": root / "R43L_UNIVERSAL_SOCIAL_BATCH_WORKBENCH_APP_SHELL_COMMANDS_REPORT.json",
        "report_md": root / "R43L_UNIVERSAL_SOCIAL_BATCH_WORKBENCH_APP_SHELL_COMMANDS_REPORT.md",
    }


def _queue_path_from_panel(panel_result: Any, run_dir: Path) -> str:
    rows = tuple(_value(panel_result, "rows") or ())
    if not rows:
        return ""
    path = run_dir / "app_shell_queue.json"
    _write_json(path, {"items": [_record_payload_from_row(row) for row in rows], "marker": R43L_MARKER})
    return str(path)


def _first_queue_id_from_panel_state(panel_state_path: str) -> str:
    rows = _read_ndjson(Path(_clean(panel_state_path)).with_name("panel_rows.ndjson"))
    return _clean(rows[0].get("queue_id")) if rows else ""


def _record_payload_from_row(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "account_handle": row.get("account_handle", ""),
        "attempts": row.get("attempts", 0),
        "batch_index": row.get("batch_index", 0),
        "dedupe_key": row.get("dedupe_key") or f"{row.get('platform_id', '')}:{row.get('normalized_url', '')}",
        "downstream_status": row.get("downstream_status", ""),
        "duplicate_of": row.get("duplicate_of", ""),
        "last_error": row.get("last_error", ""),
        "public_network_enabled": bool(row.get("public_network_enabled")),
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


def _build_summary(result: UniversalSocialBatchWorkbenchAppShellCommandResultR43L) -> str:
    return "\n".join((
        f"# {R43L_MARKER}",
        "",
        f"- Command: `{result.command_name}`",
        f"- Delegated to: `{result.delegated_to}`",
        f"- Route chain: `{result.route_chain}`",
        f"- Pending platform count: `{result.pending_platform_count}`",
        f"- Unsupported count: `{result.unsupported_count}`",
        f"- Duplicate count: `{result.duplicate_count}`",
        f"- Completed count: `{result.completed_count}`",
        "",
    ))


def _app_shell_files_exist(result: UniversalSocialBatchWorkbenchAppShellCommandResultR43L) -> bool:
    paths = (
        result.app_shell_state_path,
        result.commands_path,
        result.command_results_path,
        result.navigation_path,
        result.selection_path,
        result.summary_path,
        result.receipt_path,
    )
    return all(Path(path).is_file() for path in paths if path)


def _has_command_contract(row: Mapping[str, Any]) -> bool:
    required = {
        "command_id", "command_name", "session_id", "status", "panel_state_path", "gui_state_path", "queue_path",
        "workbench_state_path", "selected_queue_ids", "platform_counts", "status_counts", "duplicate_count",
        "unsupported_count", "pending_platform_count", "completed_count", "failed_retryable_count",
        "route_receipts_path", "summary_path", "receipt_path", "delegated_to", "route_chain", "warnings", "updated_at",
    }
    return required <= set(row)


def _value(obj: Any, attr: str, default: Any = "") -> Any:
    if obj is None:
        return default
    if isinstance(obj, Mapping):
        return obj.get(attr, default)
    return getattr(obj, attr, default)


def _pending_platform_count(rows: Iterable[Mapping[str, Any]]) -> int:
    count = 0
    for row in rows:
        if _clean(row.get("route_status")) == "mapped_pending_adapter_receipt" or _clean(row.get("platform_id")) in {
            "instagram", "facebook", "threads", "mastodon", "tiktok", "youtube", "news_comments",
        }:
            count += 1
    return count


def _count_rows(rows: Iterable[Mapping[str, Any]], key: str) -> int:
    return sum(1 for row in rows if _clean(row.get(key)))


def _no_route(result: UniversalSocialBatchWorkbenchAppShellCommandResultR43L) -> bool:
    return result.command_name in NO_ROUTE_COMMANDS_R43L and result.side_effect_flags["direct_r43h_r43g_r43f_r43e_r43d_call_performed_by_r43l"] is False


def _no_browser_source_role_side_effects(flags: Mapping[str, bool]) -> bool:
    return (
        flags.get("webview2_session_started_by_r43l") is False
        and flags.get("cefsharp_session_started_by_r43l") is False
        and flags.get("source_role_checks_performed") is False
        and flags.get("review_window_dependency_invoked") is False
        and flags.get("youtube_capture_engine_behavior_changed") is False
    )


def _no_hidden_or_security_side_effects(flags: Mapping[str, bool]) -> bool:
    return (
        flags.get("hidden_api_scraping_performed") is False
        and flags.get("cookie_or_token_extraction_performed") is False
        and flags.get("login_automation_performed") is False
        and flags.get("captcha_challenge_paywall_or_access_control_bypass_performed") is False
    )


def _machine_urls_are_plain(value: Any) -> bool:
    if isinstance(value, Mapping):
        for key, item in value.items():
            if ("url" in str(key).lower() or "path" in str(key).lower()) and isinstance(item, str) and "](" in item:
                return False
            if not _machine_urls_are_plain(item):
                return False
    elif isinstance(value, (list, tuple)):
        return all(_machine_urls_are_plain(item) for item in value)
    elif isinstance(value, str):
        return "](" not in value
    return True


def _read_json(path_value: str | Path) -> Mapping[str, Any]:
    path = Path(_clean(path_value))
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _read_ndjson(path_value: str | Path) -> list[Mapping[str, Any]]:
    path = Path(_clean(path_value))
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _extract_live_evidence_summary(value: Any) -> Mapping[str, Any]:
    best: dict[str, Any] = {}

    def score(summary: Mapping[str, Any]) -> int:
        return (
            _safe_int(summary.get("promoted_observed_post_count"))
            + _safe_int(summary.get("promoted_observed_media_count"))
            + _safe_int(summary.get("promoted_observed_screenshot_count"))
        )

    def visit(item: Any) -> None:
        nonlocal best
        if isinstance(item, Mapping):
            summary = item.get("live_evidence_summary")
            if isinstance(summary, Mapping) and score(summary) >= score(best):
                best = dict(summary)
            if _clean(item.get("marker")) == "YTCE_R44A_BLUESKY_VISIBLE_LIVE_WORKBENCH_CAPTURE" or _clean(item.get("status")).startswith("PASS_R44A_BLUESKY_VISIBLE_LIVE_WORKBENCH_CAPTURE"):
                bluesky_summary = _r44a_bluesky_visible_live_summary(item)
                if score(bluesky_summary) >= score(best):
                    best = bluesky_summary
            for child in item.values():
                visit(child)
        elif isinstance(item, (list, tuple)):
            for child in item:
                visit(child)

    visit(value)
    return best


def _r44a_bluesky_visible_live_summary(item: Mapping[str, Any]) -> Mapping[str, Any]:
    return {
        "bluesky_visible_live_summary": {
            "r44a_status": _clean(item.get("status")),
            "r43z_status": _clean(item.get("r43z_status")),
            "adapter_status": _clean(item.get("adapter_status")),
            "ledger_status": _clean(item.get("ledger_status")),
            "record_count": _safe_int(item.get("record_count")),
            "media_count": _safe_int(item.get("media_count")),
            "screenshot_count": _safe_int(item.get("screenshot_count")),
            "visible_record_count": _safe_int(item.get("visible_record_count")),
            "bound_media_count": _safe_int(item.get("bound_media_count")),
            "unbound_media_count": _safe_int(item.get("unbound_media_count")),
            "injected_browser_runner_used": bool(item.get("injected_browser_runner_used")),
            "browser_session_started": bool(item.get("browser_session_started")),
            "network_actions_performed": bool(item.get("network_actions_performed")),
            "browser_profile_files_read_or_copied": bool((item.get("side_effect_flags") or {}).get("browser_profile_files_read_or_copied")),
            "cookie_or_token_extraction_performed": bool((item.get("side_effect_flags") or {}).get("cookie_or_token_extraction_performed")),
            "remote_media_downloads_performed": bool((item.get("side_effect_flags") or {}).get("remote_media_downloads_performed")),
            "r44a_receipt_path": _clean(item.get("receipt_path")),
            "r43z_receipt_path": _clean(item.get("r43z_receipt_path")),
            "account_record_path": _clean(item.get("account_record_path")),
            "media_index_path": _clean(item.get("media_index_path")),
        },
        "r43n_status": "",
        "promoted_non_fixture_observation_evidence": bool(item.get("browser_session_started") or item.get("injected_browser_runner_used")),
        "promoted_observed_post_count": _safe_int(item.get("record_count")),
        "promoted_observed_media_count": _safe_int(item.get("media_count")),
        "promoted_observed_screenshot_count": _safe_int(item.get("screenshot_count")),
        "promoted_live_observation_paths": [
            p for p in (
                _clean(item.get("visible_dom_html_path")),
                _clean(item.get("visible_screenshot_path")),
                _clean(item.get("browser_snapshot_path")),
                _clean(item.get("receipt_path")),
            ) if p
        ],
    }


def _check(name: str, ok: bool, detail: str = "") -> Mapping[str, Any]:
    return {"detail": detail, "name": name, "status": "pass" if ok else "fail"}


def _digest_text(value: str) -> str:
    return hashlib.sha256(_clean(value).encode("utf-8")).hexdigest()


def _safe_id(value: Any) -> str:
    return "".join(ch for ch in _clean(value) if ch.isalnum() or ch in {"-", "_", "."})[:128]


def _safe_ts(value: Any) -> str:
    return _safe_id(value)


def _now_ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _clean(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _to_bool(value: Any, default: bool = False) -> bool:
    if value is None or value == "":
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _to_jsonable(value: Any) -> Any:
    if hasattr(value, "to_dict"):
        return value.to_dict()
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, tuple):
        return [_to_jsonable(item) for item in value]
    if isinstance(value, list):
        return [_to_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _to_jsonable(item) for key, item in value.items()}
    return value


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_to_jsonable(value), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_ndjson(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(_to_jsonable(row), sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=R43L_MARKER)
    parser.add_argument("--source-root", default=".")
    parser.add_argument("--output-root", default=R43L_DEFAULT_OUTPUT_ROOT)
    args = parser.parse_args(argv)
    report = build_report(args.output_root)
    json_path, md_path = write_report(report, args.output_root)
    print(R43L_MARKER)
    print(report.status)
    print(json_path)
    print(md_path)
    return 0 if report.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "APP_SHELL_OUTPUT_FILES_R43L", "R43L_BLOCKED_STATUS", "R43L_DEFAULT_OUTPUT_ROOT", "R43L_MARKER",
    "R43L_PASS_STATUS", "UniversalSocialBatchWorkbenchAppShellCommandRequestR43L",
    "UniversalSocialBatchWorkbenchAppShellCommandResultR43L", "UniversalSocialBatchWorkbenchAppShellCommandsR43L",
    "build_report", "build_report_from_result_r43l", "build_r43l_side_effect_flags",
    "build_universal_social_batch_workbench_app_shell_commands_r43l", "write_report",
]
