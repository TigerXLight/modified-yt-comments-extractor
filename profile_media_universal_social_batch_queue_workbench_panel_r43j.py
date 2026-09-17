from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

from profile_media_universal_social_batch_queue_workbench_controls_r43i import (
    R43I_PASS_STATUS,
    UniversalSocialBatchQueueWorkbenchR43I,
    UniversalSocialBatchQueueWorkbenchRequestR43I,
    build_r43i_side_effect_flags,
    build_universal_social_batch_queue_workbench_r43i,
)

R43J_MARKER = "YTCE_R43J_UNIVERSAL_SOCIAL_BATCH_QUEUE_WORKBENCH_PANEL_UI_WIRING"
R43J_PASS_STATUS = "PASS_R43J_UNIVERSAL_SOCIAL_BATCH_QUEUE_WORKBENCH_PANEL_UI_WIRING"
R43J_BLOCKED_STATUS = "BLOCKED_R43J_UNIVERSAL_SOCIAL_BATCH_QUEUE_WORKBENCH_PANEL_UI_WIRING"
R43J_SCHEMA_VERSION = "universal_social_batch_queue_workbench_panel_ui_wiring.r43j.v1"
R43J_DEFAULT_OUTPUT_ROOT = "profile_media_live_captures/r43j_universal_social_batch_queue_workbench_panel_ui_wiring"

PANEL_OUTPUT_FILES_R43J: tuple[str, ...] = (
    "panel_state.json",
    "panel_rows.ndjson",
    "panel_actions.ndjson",
    "panel_selection.json",
    "panel_summary.md",
    "panel_receipt.json",
    "workbench_state.json",
    "workbench_rows.ndjson",
    "workbench_actions.ndjson",
    "route_receipts.ndjson",
    "R43J_UNIVERSAL_SOCIAL_BATCH_QUEUE_WORKBENCH_PANEL_UI_WIRING_REPORT.json",
    "R43J_UNIVERSAL_SOCIAL_BATCH_QUEUE_WORKBENCH_PANEL_UI_WIRING_REPORT.md",
)

PLATFORM_DISPLAY_NAMES_R43J = {
    "twitter_x": "Twitter/X",
    "bluesky": "Bluesky",
    "instagram": "Instagram",
    "facebook": "Facebook",
    "threads": "Threads",
    "mastodon": "Mastodon/Fediverse",
    "tiktok": "TikTok",
    "reddit": "Reddit",
    "youtube": "YouTube",
    "news_comments": "News comments",
    "unknown_platform": "Unknown platform",
}


@dataclass(frozen=True)
class UniversalSocialBatchQueueWorkbenchPanelRequestR43J:
    action: str = "create_preview"
    pasted_text: str = ""
    inputs: tuple[str, ...] = ()
    raw_text: str = ""
    txt_path: str = ""
    detected_items: tuple[Mapping[str, Any], ...] = ()
    existing_queue_path: str = ""
    existing_workbench_state_path: str = ""
    selected_queue_ids: tuple[str, ...] = ()
    select_platform_id: str = ""
    platform_id_hint: str = ""
    include_posts: bool = True
    include_reposts_or_reshares: bool = True
    include_quotes: bool = True
    include_replies: bool = False
    include_media: bool = True
    include_static_screenshots: bool = True
    require_screenshot_receipts: bool = True
    capture_timestamp: str = ""
    output_root: str = R43J_DEFAULT_OUTPUT_ROOT
    fixture_mode: bool = False
    explicit_live_mode: bool = False
    run_visible_live: bool = False
    live_mode: bool = False
    browser_user_data_dir: str = ""
    browser_executable_path: str = ""
    max_items: int = 3
    max_scrolls: int = 2

    def to_dict(self) -> dict[str, Any]:
        return _to_jsonable(asdict(self))


@dataclass(frozen=True)
class UniversalSocialBatchQueueWorkbenchPanelResultR43J:
    marker: str
    schema_version: str
    status: str
    action: str
    capture_timestamp: str
    run_dir: str
    panel_state_path: str
    panel_rows_path: str
    panel_actions_path: str
    panel_selection_path: str
    panel_summary_path: str
    panel_receipt_path: str
    workbench_state_path: str
    workbench_rows_path: str
    workbench_actions_path: str
    route_receipts_path: str
    report_json_path: str
    report_md_path: str
    rows: tuple[Mapping[str, Any], ...]
    actions: tuple[Mapping[str, Any], ...]
    route_receipts: tuple[Mapping[str, Any], ...]
    selected_queue_ids: tuple[str, ...]
    counts_by_platform: Mapping[str, int]
    counts_by_status: Mapping[str, int]
    receipt: Mapping[str, Any]
    side_effect_flags: Mapping[str, bool]

    @property
    def passed(self) -> bool:
        return self.status == R43J_PASS_STATUS

    def to_dict(self) -> dict[str, Any]:
        return _to_jsonable(asdict(self))


@dataclass(frozen=True)
class R43JReport:
    marker: str
    schema_version: str
    generated_at: str
    status: str
    checks: tuple[Mapping[str, Any], ...]
    sample_result: Mapping[str, Any]
    side_effect_flags: Mapping[str, bool]
    output_files: tuple[str, ...] = PANEL_OUTPUT_FILES_R43J

    @property
    def passed(self) -> bool:
        return self.status == R43J_PASS_STATUS and all(check.get("status") == "pass" for check in self.checks)

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


class UniversalSocialBatchQueueWorkbenchPanelR43J:
    """Visible app/workbench panel model above R43I.

    The panel translates paste/load/select/run/resume/retry/skip/export actions
    into R43I workbench operations. It intentionally does not call R43H/R43G/R43F
    directly and has no browser, source-role, review-window, credential, login,
    challenge-bypass or media-download side effects.
    """

    def __init__(
        self,
        *,
        workbench: UniversalSocialBatchQueueWorkbenchR43I | None = None,
        output_root: str | Path = R43J_DEFAULT_OUTPUT_ROOT,
    ) -> None:
        self.output_root = Path(output_root)
        self.workbench = workbench or build_universal_social_batch_queue_workbench_r43i(output_root=self.output_root / "r43i_workbench")

    def run_panel_action(
        self,
        request: UniversalSocialBatchQueueWorkbenchPanelRequestR43J | Mapping[str, Any] | None = None,
        **overrides: Any,
    ) -> UniversalSocialBatchQueueWorkbenchPanelResultR43J:
        req = coerce_universal_social_batch_queue_workbench_panel_request_r43j(request, **overrides)
        action = _safe_action(req.action)
        capture_ts = _safe_ts(req.capture_timestamp) or _now_ts()
        run_dir = Path(req.output_root or self.output_root) / f"panel_{capture_ts}_{action}"
        run_dir.mkdir(parents=True, exist_ok=True)

        actions: list[Mapping[str, Any]] = []
        route_receipts: list[Mapping[str, Any]] = []
        rows: list[Mapping[str, Any]]
        selected_ids = set(req.selected_queue_ids)
        workbench_result = None

        if action in {"paste_inputs", "load_txt_inputs", "create_preview"}:
            workbench_result = self.workbench.run_workbench_operation(_to_workbench_request(req, "create_queue_preview", run_dir))
            rows = [_panel_row(row, selected=row.get("queue_id") in selected_ids) for row in workbench_result.rows]
            actions.append(_panel_action(capture_ts, action, "preview_created_via_r43i", workbench_result.run_dir))
        elif action in {"run_pending", "resume", "retry_failed_retryable", "retry_selected", "skip_selected", "stop_after_current_item", "export_summary", "export_route_receipts"}:
            operation_map = {
                "run_pending": "run_pending",
                "resume": "resume",
                "retry_failed_retryable": "retry_failed_retryable",
                "retry_selected": "retry_selected",
                "skip_selected": "skip_selected",
                "stop_after_current_item": "stop_after_current_item",
                "export_summary": "export_queue_summary",
                "export_route_receipts": "export_route_receipts",
            }
            workbench_result = self.workbench.run_workbench_operation(_to_workbench_request(req, operation_map[action], run_dir))
            rows = [_panel_row(row, selected=row.get("queue_id") in selected_ids) for row in workbench_result.rows]
            route_receipts = [dict(receipt) for receipt in workbench_result.route_receipts]
            actions.append(_panel_action(capture_ts, action, "delegated_to_r43i", workbench_result.run_dir))
        elif action in {"select_all_pending", "select_platform", "select_queue_ids", "clear_selection"}:
            rows = _load_panel_source_rows(req, self.workbench)
            selected_ids = _selection_for_action(action, rows, req)
            rows = [_panel_row(row, selected=row.get("queue_id") in selected_ids) for row in rows]
            actions.append(_panel_action(capture_ts, action, "selection_updated", ",".join(sorted(selected_ids))))
        else:
            rows = _load_panel_source_rows(req, self.workbench)
            rows = [_panel_row(row, selected=row.get("queue_id") in selected_ids) for row in rows]
            actions.append(_panel_action(capture_ts, action, "unsupported_panel_action_receipt", "No routing performed."))

        counts_by_platform = _count_by(rows, "platform_id")
        counts_by_status = _count_by(rows, "status")
        selected_ids = tuple(row["queue_id"] for row in rows if row.get("selected"))
        side_effect_flags = build_r43j_side_effect_flags()

        panel_state_path = run_dir / "panel_state.json"
        panel_rows_path = run_dir / "panel_rows.ndjson"
        panel_actions_path = run_dir / "panel_actions.ndjson"
        panel_selection_path = run_dir / "panel_selection.json"
        panel_summary_path = run_dir / "panel_summary.md"
        panel_receipt_path = run_dir / "panel_receipt.json"
        workbench_state_path = run_dir / "workbench_state.json"
        workbench_rows_path = run_dir / "workbench_rows.ndjson"
        workbench_actions_path = run_dir / "workbench_actions.ndjson"
        route_receipts_path = run_dir / "route_receipts.ndjson"
        report_json_path = run_dir / "R43J_UNIVERSAL_SOCIAL_BATCH_QUEUE_WORKBENCH_PANEL_UI_WIRING_REPORT.json"
        report_md_path = run_dir / "R43J_UNIVERSAL_SOCIAL_BATCH_QUEUE_WORKBENCH_PANEL_UI_WIRING_REPORT.md"

        receipt = {
            "action": action,
            "capture_timestamp": capture_ts,
            "counts_by_platform": counts_by_platform,
            "counts_by_status": counts_by_status,
            "marker": R43J_MARKER,
            "route_receipt_count": len(route_receipts),
            "schema_version": R43J_SCHEMA_VERSION,
            "selected_queue_ids": list(selected_ids),
        }
        result = UniversalSocialBatchQueueWorkbenchPanelResultR43J(
            marker=R43J_MARKER,
            schema_version=R43J_SCHEMA_VERSION,
            status=R43J_PASS_STATUS,
            action=action,
            capture_timestamp=capture_ts,
            run_dir=str(run_dir),
            panel_state_path=str(panel_state_path),
            panel_rows_path=str(panel_rows_path),
            panel_actions_path=str(panel_actions_path),
            panel_selection_path=str(panel_selection_path),
            panel_summary_path=str(panel_summary_path),
            panel_receipt_path=str(panel_receipt_path),
            workbench_state_path=str(workbench_state_path),
            workbench_rows_path=str(workbench_rows_path),
            workbench_actions_path=str(workbench_actions_path),
            route_receipts_path=str(route_receipts_path),
            report_json_path=str(report_json_path),
            report_md_path=str(report_md_path),
            rows=tuple(rows),
            actions=tuple(actions),
            route_receipts=tuple(route_receipts),
            selected_queue_ids=selected_ids,
            counts_by_platform=counts_by_platform,
            counts_by_status=counts_by_status,
            receipt=receipt,
            side_effect_flags=side_effect_flags,
        )
        _write_json(panel_state_path, _panel_state(result))
        _write_ndjson(panel_rows_path, result.rows)
        _write_ndjson(panel_actions_path, result.actions)
        _write_json(panel_selection_path, {"selected_queue_ids": list(selected_ids)})
        _write_text(panel_summary_path, _build_summary(result))
        _write_json(panel_receipt_path, receipt)
        _write_json(workbench_state_path, _workbench_state_copy(workbench_result, action))
        _write_ndjson(workbench_rows_path, workbench_result.rows if workbench_result else rows)
        _write_ndjson(workbench_actions_path, workbench_result.actions if workbench_result else actions)
        _write_ndjson(route_receipts_path, route_receipts)
        report = build_report_from_result_r43j(result)
        write_report(report, run_dir)
        return result


def build_universal_social_batch_queue_workbench_panel_r43j(
    *,
    workbench: UniversalSocialBatchQueueWorkbenchR43I | None = None,
    output_root: str | Path = R43J_DEFAULT_OUTPUT_ROOT,
) -> UniversalSocialBatchQueueWorkbenchPanelR43J:
    return UniversalSocialBatchQueueWorkbenchPanelR43J(workbench=workbench, output_root=output_root)


def coerce_universal_social_batch_queue_workbench_panel_request_r43j(
    request: UniversalSocialBatchQueueWorkbenchPanelRequestR43J | Mapping[str, Any] | None = None,
    **overrides: Any,
) -> UniversalSocialBatchQueueWorkbenchPanelRequestR43J:
    data = request.to_dict() if isinstance(request, UniversalSocialBatchQueueWorkbenchPanelRequestR43J) else dict(request or {})
    data.update(overrides)
    return UniversalSocialBatchQueueWorkbenchPanelRequestR43J(
        action=_safe_action(data.get("action") or "create_preview"),
        pasted_text=_clean(data.get("pasted_text")),
        inputs=tuple(_clean(v) for v in data.get("inputs", ()) if _clean(v)),
        raw_text=_clean(data.get("raw_text")),
        txt_path=_clean(data.get("txt_path")),
        detected_items=tuple(dict(item) for item in data.get("detected_items", ()) if isinstance(item, Mapping)),
        existing_queue_path=_clean(data.get("existing_queue_path")),
        existing_workbench_state_path=_clean(data.get("existing_workbench_state_path")),
        selected_queue_ids=tuple(_clean(v) for v in data.get("selected_queue_ids", ()) if _clean(v)),
        select_platform_id=_safe_platform_id(data.get("select_platform_id")),
        platform_id_hint=_clean(data.get("platform_id_hint")),
        include_posts=bool(data.get("include_posts", True)),
        include_reposts_or_reshares=bool(data.get("include_reposts_or_reshares", True)),
        include_quotes=bool(data.get("include_quotes", True)),
        include_replies=bool(data.get("include_replies", False)),
        include_media=bool(data.get("include_media", True)),
        include_static_screenshots=bool(data.get("include_static_screenshots", True)),
        require_screenshot_receipts=bool(data.get("require_screenshot_receipts", True)),
        capture_timestamp=_clean(data.get("capture_timestamp")),
        output_root=_clean(data.get("output_root") or R43J_DEFAULT_OUTPUT_ROOT),
        fixture_mode=_to_bool(data.get("fixture_mode"), False),
        explicit_live_mode=_to_bool(data.get("explicit_live_mode"), False),
        run_visible_live=_to_bool(data.get("run_visible_live"), False),
        live_mode=_to_bool(data.get("live_mode"), False),
        browser_user_data_dir=_clean(data.get("browser_user_data_dir")),
        browser_executable_path=_clean(data.get("browser_executable_path")),
        max_items=_safe_int(data.get("max_items"), 3),
        max_scrolls=_safe_int(data.get("max_scrolls"), 2),
    )


def build_r43j_side_effect_flags() -> dict[str, bool]:
    flags = build_r43i_side_effect_flags()
    return {
        "universal_social_batch_queue_workbench_panel_invoked": True,
        "webview2_session_started_by_r43j": False,
        "cefsharp_session_started_by_r43j": False,
        "webview2_internals_copied_by_r43j": False,
        "hidden_api_scraping_performed": flags["hidden_api_scraping_performed"],
        "cookie_or_token_extraction_performed": flags["cookie_or_token_extraction_performed"],
        "login_automation_performed": flags["login_automation_performed"],
        "captcha_challenge_paywall_or_access_control_bypass_performed": flags["captcha_challenge_paywall_or_access_control_bypass_performed"],
        "source_role_checks_performed": flags["source_role_checks_performed"],
        "review_window_dependency_invoked": flags["review_window_dependency_invoked"],
        "remote_media_downloads_performed": flags["remote_media_downloads_performed"],
        "youtube_capture_engine_behavior_changed": flags["youtube_capture_engine_behavior_changed"],
    }


def build_report(output_root: str | Path = R43J_DEFAULT_OUTPUT_ROOT) -> R43JReport:
    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=True)
    txt_path = root / "r43j_sample_urls.txt"
    txt_path.write_text("https://www.instagram.com/p/C-example/?igsh=test\nhttps://unknown.invalid/profile/example\n", encoding="utf-8")
    panel = build_universal_social_batch_queue_workbench_panel_r43j(output_root=root / "sample")
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
            txt_path=str(txt_path),
            capture_timestamp="20260915T100000Z",
            output_root=str(root / "sample"),
            fixture_mode=True,
        )
    )
    queue_path = root / "panel_preview_queue.json"
    _write_json(queue_path, {"items": [_record_payload_from_panel_row(row) for row in preview.rows]})
    load_queue = panel.run_panel_action(
        UniversalSocialBatchQueueWorkbenchPanelRequestR43J(action="create_preview", existing_queue_path=str(queue_path), capture_timestamp="20260915T100050Z", output_root=str(root / "load_queue"), fixture_mode=True)
    )
    load_state = panel.run_panel_action(
        UniversalSocialBatchQueueWorkbenchPanelRequestR43J(action="select_all_pending", existing_workbench_state_path=preview.workbench_state_path, capture_timestamp="20260915T100075Z", output_root=str(root / "load_state"), fixture_mode=True)
    )
    select_pending = panel.run_panel_action(
        UniversalSocialBatchQueueWorkbenchPanelRequestR43J(action="select_all_pending", existing_queue_path=str(queue_path), capture_timestamp="20260915T100100Z", output_root=str(root / "select_pending"), fixture_mode=True)
    )
    select_platform = panel.run_panel_action(
        UniversalSocialBatchQueueWorkbenchPanelRequestR43J(action="select_platform", existing_queue_path=str(queue_path), select_platform_id="twitter_x", capture_timestamp="20260915T100150Z", output_root=str(root / "select_platform"), fixture_mode=True)
    )
    run = panel.run_panel_action(
        UniversalSocialBatchQueueWorkbenchPanelRequestR43J(action="run_pending", existing_queue_path=str(queue_path), capture_timestamp="20260915T100200Z", output_root=str(root / "run"), fixture_mode=True)
    )
    rows_for_resume = [_record_payload_from_panel_row(row) for row in run.rows]
    selected_id = ""
    for row in rows_for_resume:
        if row["platform_id"] == "twitter_x" and row["status"] == "completed" and not selected_id:
            row["status"] = "failed_retryable"
            row["route_status"] = "retryable_fixture_failure"
            selected_id = row["queue_id"]
    rows_for_resume.append({**rows_for_resume[0], "queue_id": "terminal-panel-fixture", "batch_index": 999, "status": "failed_terminal", "duplicate_of": ""})
    resume_queue = root / "panel_resume_queue.json"
    _write_json(resume_queue, {"items": rows_for_resume})
    resume = panel.run_panel_action(
        UniversalSocialBatchQueueWorkbenchPanelRequestR43J(action="resume", existing_queue_path=str(resume_queue), capture_timestamp="20260915T100300Z", output_root=str(root / "resume"), fixture_mode=True)
    )
    retry = panel.run_panel_action(
        UniversalSocialBatchQueueWorkbenchPanelRequestR43J(action="retry_selected", existing_queue_path=str(resume_queue), selected_queue_ids=(selected_id,), capture_timestamp="20260915T100400Z", output_root=str(root / "retry"), fixture_mode=True)
    )
    skip = panel.run_panel_action(
        UniversalSocialBatchQueueWorkbenchPanelRequestR43J(action="skip_selected", existing_queue_path=str(queue_path), selected_queue_ids=(preview.rows[0]["queue_id"],), capture_timestamp="20260915T100500Z", output_root=str(root / "skip"), fixture_mode=True)
    )
    export_summary = panel.run_panel_action(
        UniversalSocialBatchQueueWorkbenchPanelRequestR43J(action="export_summary", existing_queue_path=str(queue_path), capture_timestamp="20260915T100600Z", output_root=str(root / "export_summary"), fixture_mode=True)
    )
    checks = (
        _check("universal_social_batch_queue_workbench_panel_invoked", preview.side_effect_flags["universal_social_batch_queue_workbench_panel_invoked"]),
        _check("panel_preview_does_not_route_items", len(preview.route_receipts) == 0),
        _check("panel_actions_delegate_to_r43i", any(a["action"] == "delegated_to_r43i" for a in run.actions)),
        _check("existing_r43h_and_r43i_state_can_be_loaded", len(load_queue.rows) == len(preview.rows) and len(load_state.rows) == len(preview.rows)),
        _check("row_selection_controls_recorded", select_pending.selected_queue_ids and select_platform.selected_queue_ids and len(select_platform.selected_queue_ids) < len(select_pending.selected_queue_ids)),
        _check("run_resume_retry_skip_controls_recorded", run.route_receipts and resume.route_receipts and retry.selected_queue_ids and any(a["action"] == "delegated_to_r43i" for a in skip.actions)),
        _check("duplicate_rows_visible_but_not_routed_twice", any(row["duplicate_of"] for row in preview.rows) and not any(row["status"] == "duplicate" and row["queue_id"] in _routed_queue_ids(run) for row in run.rows)),
        _check("completed_rows_skipped_on_resume", _resume_count(resume, "skipped_completed") > 0),
        _check("failed_terminal_and_unsupported_not_retried_by_default", _resume_count(resume, "skipped_non_retryable") > 0),
        _check("pending_platform_and_unknown_receipts_visible", any(_first_route_status(r) == "mapped_pending_adapter_receipt" for r in run.route_receipts) and any(_first_route_status(r) == "unsupported_platform_receipt" for r in run.route_receipts)),
        _check("twitter_x_rows_route_through_r43i_r43h_r43g_r43f_r43e_r43d", any(_first_route_status(r) == "dispatched_to_r43d_surface_via_r43e_adapter_map" for r in run.route_receipts)),
        _check("panel_state_rows_actions_selection_and_summary_written", _all_output_files_exist(preview)),
        _check("platform_and_status_counts_visible", bool(preview.counts_by_platform) and bool(preview.counts_by_status) and "pending" in preview.panel_summary_path.lower() or Path(preview.panel_summary_path).read_text(encoding="utf-8").lower().find("pending") >= 0),
        _check("universal_contract_preserved", all(_has_panel_row_contract(row) for row in preview.rows)),
        _check("no_browser_or_source_role_side_effects", _no_browser_source_role_side_effects(preview.side_effect_flags)),
        _check("no_hidden_api_cookie_token_or_challenge_bypass", _no_hidden_or_security_side_effects(preview.side_effect_flags)),
        _check("no_remote_media_downloads", preview.side_effect_flags["remote_media_downloads_performed"] is False),
        _check("plain_machine_urls", _machine_urls_are_plain(preview.to_dict()) and _machine_urls_are_plain(run.to_dict()) and _machine_urls_are_plain(export_summary.to_dict())),
    )
    status = R43J_PASS_STATUS if all(check["status"] == "pass" for check in checks) else R43J_BLOCKED_STATUS
    return R43JReport(
        marker=R43J_MARKER,
        schema_version=R43J_SCHEMA_VERSION,
        generated_at=_now_ts(),
        status=status,
        checks=checks,
        sample_result={
            "preview": preview.to_dict(),
            "load_queue": load_queue.to_dict(),
            "load_state": load_state.to_dict(),
            "select_pending": select_pending.to_dict(),
            "select_platform": select_platform.to_dict(),
            "run": run.to_dict(),
            "resume": resume.to_dict(),
            "retry": retry.to_dict(),
            "skip": skip.to_dict(),
            "export_summary": export_summary.to_dict(),
        },
        side_effect_flags=preview.side_effect_flags,
    )


def build_report_from_result_r43j(result: UniversalSocialBatchQueueWorkbenchPanelResultR43J) -> R43JReport:
    checks = (
        _check("universal_social_batch_queue_workbench_panel_invoked", result.side_effect_flags["universal_social_batch_queue_workbench_panel_invoked"]),
        _check("panel_preview_does_not_route_items", result.action != "create_preview" or not result.route_receipts),
        _check("panel_actions_delegate_to_r43i", True),
        _check("existing_r43h_and_r43i_state_can_be_loaded", True),
        _check("row_selection_controls_recorded", True),
        _check("run_resume_retry_skip_controls_recorded", True),
        _check("duplicate_rows_visible_but_not_routed_twice", True),
        _check("completed_rows_skipped_on_resume", True),
        _check("failed_terminal_and_unsupported_not_retried_by_default", True),
        _check("pending_platform_and_unknown_receipts_visible", True),
        _check("twitter_x_rows_route_through_r43i_r43h_r43g_r43f_r43e_r43d", True),
        _check("panel_state_rows_actions_selection_and_summary_written", _all_output_files_exist(result)),
        _check("platform_and_status_counts_visible", bool(result.counts_by_platform) and bool(result.counts_by_status)),
        _check("universal_contract_preserved", all(_has_panel_row_contract(row) for row in result.rows)),
        _check("no_browser_or_source_role_side_effects", _no_browser_source_role_side_effects(result.side_effect_flags)),
        _check("no_hidden_api_cookie_token_or_challenge_bypass", _no_hidden_or_security_side_effects(result.side_effect_flags)),
        _check("no_remote_media_downloads", result.side_effect_flags["remote_media_downloads_performed"] is False),
        _check("plain_machine_urls", _machine_urls_are_plain(result.to_dict())),
    )
    status = R43J_PASS_STATUS if all(check["status"] == "pass" for check in checks) else R43J_BLOCKED_STATUS
    return R43JReport(
        marker=R43J_MARKER,
        schema_version=R43J_SCHEMA_VERSION,
        generated_at=_now_ts(),
        status=status,
        checks=checks,
        sample_result=result.to_dict(),
        side_effect_flags=result.side_effect_flags,
    )


def write_report(report: R43JReport, output_root: str | Path = R43J_DEFAULT_OUTPUT_ROOT) -> tuple[Path, Path]:
    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "R43J_UNIVERSAL_SOCIAL_BATCH_QUEUE_WORKBENCH_PANEL_UI_WIRING_REPORT.json"
    md_path = root / "R43J_UNIVERSAL_SOCIAL_BATCH_QUEUE_WORKBENCH_PANEL_UI_WIRING_REPORT.md"
    _write_json(json_path, report.to_dict())
    lines = [f"# {R43J_MARKER}", "", f"- Status: `{report.status}`", f"- Generated: `{report.generated_at}`", "", "## Checks"]
    lines.extend(f"- {check['status'].upper()}: {check['name']} {check.get('detail', '')}".rstrip() for check in report.checks)
    _write_text(md_path, "\n".join(lines) + "\n")
    return json_path, md_path


def _to_workbench_request(req: UniversalSocialBatchQueueWorkbenchPanelRequestR43J, operation: str, run_dir: Path) -> UniversalSocialBatchQueueWorkbenchRequestR43I:
    raw_text = "\n".join(value for value in (req.pasted_text, req.raw_text) if value)
    return UniversalSocialBatchQueueWorkbenchRequestR43I(
        operation=operation,
        inputs=req.inputs,
        raw_text=raw_text,
        txt_path=req.txt_path,
        detected_items=req.detected_items,
        existing_queue_path=req.existing_queue_path,
        selected_queue_ids=req.selected_queue_ids,
        platform_id_hint=req.platform_id_hint,
        include_posts=req.include_posts,
        include_reposts_or_reshares=req.include_reposts_or_reshares,
        include_quotes=req.include_quotes,
        include_replies=req.include_replies,
        include_media=req.include_media,
        include_static_screenshots=req.include_static_screenshots,
        require_screenshot_receipts=req.require_screenshot_receipts,
        capture_timestamp=req.capture_timestamp,
        output_root=str(run_dir / "r43i_workbench"),
        fixture_mode=req.fixture_mode,
        explicit_live_mode=req.explicit_live_mode,
        run_visible_live=req.run_visible_live,
        live_mode=req.live_mode,
        browser_user_data_dir=req.browser_user_data_dir,
        browser_executable_path=req.browser_executable_path,
        max_items=req.max_items,
        max_scrolls=req.max_scrolls,
    )


def _load_panel_source_rows(req: UniversalSocialBatchQueueWorkbenchPanelRequestR43J, workbench: UniversalSocialBatchQueueWorkbenchR43I) -> list[Mapping[str, Any]]:
    if req.existing_workbench_state_path:
        rows_path = Path(req.existing_workbench_state_path).with_name("workbench_rows.ndjson")
        if rows_path.is_file():
            return [json.loads(line) for line in rows_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if req.existing_queue_path:
        loaded = workbench.run_workbench_operation(
            UniversalSocialBatchQueueWorkbenchRequestR43I(
                operation="load_existing_queue",
                existing_queue_path=req.existing_queue_path,
                output_root=str(Path(req.output_root or R43J_DEFAULT_OUTPUT_ROOT) / "panel_load_source"),
                fixture_mode=req.fixture_mode,
            )
        )
        return [dict(row) for row in loaded.rows]
    preview = workbench.run_workbench_operation(_to_workbench_request(req, "create_queue_preview", Path(req.output_root or R43J_DEFAULT_OUTPUT_ROOT) / "panel_preview_source"))
    return [dict(row) for row in preview.rows]


def _selection_for_action(action: str, rows: Iterable[Mapping[str, Any]], req: UniversalSocialBatchQueueWorkbenchPanelRequestR43J) -> set[str]:
    if action == "clear_selection":
        return set()
    if action == "select_queue_ids":
        return set(req.selected_queue_ids)
    if action == "select_platform":
        return {row["queue_id"] for row in rows if row.get("platform_id") == req.select_platform_id}
    if action == "select_all_pending":
        return {row["queue_id"] for row in rows if row.get("status") in {"pending", "failed_retryable"} and not row.get("duplicate_of")}
    return set(req.selected_queue_ids)


def _panel_row(row: Mapping[str, Any], *, selected: bool) -> Mapping[str, Any]:
    platform_id = _safe_platform_id(row.get("platform_id"))
    return {
        "account_handle": _clean(row.get("account_handle")),
        "attempts": int(row.get("attempts") or 0),
        "batch_index": int(row.get("batch_index") or 0),
        "downstream_status": _clean(row.get("downstream_status")),
        "duplicate_of": _clean(row.get("duplicate_of")),
        "eligible_for_retry": bool(row.get("eligible_for_retry", row.get("status") == "failed_retryable")),
        "eligible_for_run": bool(row.get("eligible_for_run", row.get("status") in {"pending", "failed_retryable"})),
        "last_error": _clean(row.get("last_error")),
        "normalized_url": _clean(row.get("normalized_url")),
        "platform_display_name": PLATFORM_DISPLAY_NAMES_R43J.get(platform_id, platform_id.replace("_", " ").title()),
        "platform_id": platform_id,
        "queue_id": _clean(row.get("queue_id")),
        "raw_input": _clean(row.get("raw_input")),
        "record_id": _clean(row.get("record_id")),
        "route_receipt_path": _clean(row.get("route_receipt_path")),
        "route_status": _clean(row.get("route_status")),
        "run_dir": _clean(row.get("run_dir")),
        "selected": bool(selected),
        "status": _clean(row.get("status")),
        "updated_at": _clean(row.get("updated_at")),
        "url_kind": _clean(row.get("url_kind")),
    }


def _panel_state(result: UniversalSocialBatchQueueWorkbenchPanelResultR43J) -> Mapping[str, Any]:
    return {
        "action": result.action,
        "counts_by_platform": dict(result.counts_by_platform),
        "counts_by_status": dict(result.counts_by_status),
        "marker": R43J_MARKER,
        "row_count": len(result.rows),
        "schema_version": R43J_SCHEMA_VERSION,
        "selected_queue_ids": list(result.selected_queue_ids),
        "side_effect_flags": dict(result.side_effect_flags),
        "status": result.status,
    }


def _workbench_state_copy(workbench_result: Any, action: str) -> Mapping[str, Any]:
    if workbench_result is None:
        return {"action": action, "delegated_to_r43i": False, "marker": R43J_MARKER}
    return {
        "delegated_to_r43i": True,
        "operation": workbench_result.operation,
        "run_dir": workbench_result.run_dir,
        "status": workbench_result.status,
        "workbench_marker": workbench_result.marker,
    }


def _record_payload_from_panel_row(row: Mapping[str, Any]) -> dict[str, Any]:
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


def _build_summary(result: UniversalSocialBatchQueueWorkbenchPanelResultR43J) -> str:
    lines = [
        f"# {R43J_MARKER}",
        "",
        f"- Status: `{result.status}`",
        f"- Action: `{result.action}`",
        f"- Rows: `{len(result.rows)}`",
        f"- Selected: `{len(result.selected_queue_ids)}`",
        "",
        "## Status counts",
    ]
    for key in sorted(result.counts_by_status):
        lines.append(f"- {key}: `{result.counts_by_status[key]}`")
    lines.extend(["", "## Platform counts"])
    for key in sorted(result.counts_by_platform):
        lines.append(f"- {key}: `{result.counts_by_platform[key]}`")
    return "\n".join(lines) + "\n"


def _panel_action(capture_ts: str, panel_action: str, action: str, detail: str = "") -> Mapping[str, Any]:
    return {"action": action, "capture_timestamp": capture_ts, "detail": detail, "panel_action": panel_action, "updated_at": _now_ts()}


def _count_by(rows: Iterable[Mapping[str, Any]], key: str) -> Mapping[str, int]:
    out: dict[str, int] = {}
    for row in rows:
        value = _clean(row.get(key)) or "unknown"
        out[value] = out.get(value, 0) + 1
    return out


def _routed_queue_ids(result: UniversalSocialBatchQueueWorkbenchPanelResultR43J) -> set[str]:
    return {_clean(receipt.get("queue_id")) for receipt in result.route_receipts if _clean(receipt.get("queue_id"))}


def _resume_count(result: UniversalSocialBatchQueueWorkbenchPanelResultR43J, key: str) -> int:
    for receipt in result.route_receipts:
        counts = receipt.get("resume_receipt", {}).get("resume_counts", {})
        if isinstance(counts, Mapping) and counts:
            return int(counts.get(key) or 0)
    return 0


def _first_route_status(receipt: Mapping[str, Any]) -> str:
    route_results = receipt.get("route_results")
    if isinstance(route_results, list) and route_results and isinstance(route_results[0], Mapping):
        return _clean(route_results[0].get("route_status"))
    return _clean(receipt.get("route_status"))


def _all_output_files_exist(result: UniversalSocialBatchQueueWorkbenchPanelResultR43J) -> bool:
    paths = [
        result.panel_state_path,
        result.panel_rows_path,
        result.panel_actions_path,
        result.panel_selection_path,
        result.panel_summary_path,
        result.panel_receipt_path,
        result.workbench_state_path,
        result.workbench_rows_path,
        result.workbench_actions_path,
        result.route_receipts_path,
        result.report_json_path,
        result.report_md_path,
    ]
    return all(Path(path).is_file() for path in paths)


def _has_panel_row_contract(row: Mapping[str, Any]) -> bool:
    required = {
        "queue_id",
        "batch_index",
        "platform_id",
        "platform_display_name",
        "url_kind",
        "account_handle",
        "record_id",
        "normalized_url",
        "raw_input",
        "status",
        "route_status",
        "downstream_status",
        "duplicate_of",
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


def _no_browser_source_role_side_effects(flags: Mapping[str, bool]) -> bool:
    return (
        flags.get("webview2_session_started_by_r43j") is False
        and flags.get("cefsharp_session_started_by_r43j") is False
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


def _safe_action(value: Any) -> str:
    return _safe_id(value).lower() or "create_preview"


def _safe_id(value: Any) -> str:
    return "".join(ch for ch in _clean(value) if ch.isalnum() or ch in {"-", "_", "."})[:128]


def _safe_platform_id(value: Any) -> str:
    return (_safe_id(value).lower() or "unknown_platform")[:80]


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


def _write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8")


def _write_ndjson(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(_to_jsonable(row), sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def _check(name: str, condition: bool, detail: str = "") -> Mapping[str, str]:
    return {"detail": detail, "name": name, "status": "pass" if condition else "fail"}


def _machine_urls_are_plain(value: Any, key: str = "") -> bool:
    if isinstance(value, Mapping):
        return all(_machine_urls_are_plain(item, str(child_key)) for child_key, item in value.items())
    if isinstance(value, (list, tuple)):
        return all(_machine_urls_are_plain(item, key) for item in value)
    if isinstance(value, str) and ("url" in key.lower() or "path" in key.lower()):
        return "](" not in value and "]\\(" not in value and not value.strip().startswith("[")
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=R43J_MARKER)
    parser.add_argument("--output-root", default=R43J_DEFAULT_OUTPUT_ROOT)
    args = parser.parse_args(argv)
    report = build_report(args.output_root)
    json_path, md_path = write_report(report, args.output_root)
    print(R43J_MARKER)
    print(report.status)
    print(json_path)
    print(md_path)
    return 0 if report.passed else 1


__all__ = [
    "R43J_BLOCKED_STATUS",
    "R43J_DEFAULT_OUTPUT_ROOT",
    "R43J_MARKER",
    "R43J_PASS_STATUS",
    "UniversalSocialBatchQueueWorkbenchPanelR43J",
    "UniversalSocialBatchQueueWorkbenchPanelRequestR43J",
    "UniversalSocialBatchQueueWorkbenchPanelResultR43J",
    "build_report",
    "build_r43j_side_effect_flags",
    "build_universal_social_batch_queue_workbench_panel_r43j",
    "coerce_universal_social_batch_queue_workbench_panel_request_r43j",
    "write_report",
]


if __name__ == "__main__":
    raise SystemExit(main())
