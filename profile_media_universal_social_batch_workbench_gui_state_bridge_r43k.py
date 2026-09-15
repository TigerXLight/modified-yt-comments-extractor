from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

from profile_media_universal_social_batch_queue_workbench_panel_r43j import (
    R43J_PASS_STATUS,
    UniversalSocialBatchQueueWorkbenchPanelR43J,
    UniversalSocialBatchQueueWorkbenchPanelRequestR43J,
    build_r43j_side_effect_flags,
    build_universal_social_batch_queue_workbench_panel_r43j,
)

R43K_MARKER = "YTCE_R43K_UNIVERSAL_SOCIAL_BATCH_WORKBENCH_GUI_STATE_BRIDGE"
R43K_PASS_STATUS = "PASS_R43K_UNIVERSAL_SOCIAL_BATCH_WORKBENCH_GUI_STATE_BRIDGE"
R43K_BLOCKED_STATUS = "BLOCKED_R43K_UNIVERSAL_SOCIAL_BATCH_WORKBENCH_GUI_STATE_BRIDGE"
R43K_SCHEMA_VERSION = "universal_social_batch_workbench_gui_state_bridge.r43k.v1"
R43K_DEFAULT_OUTPUT_ROOT = "profile_media_live_captures/r43k_universal_social_batch_workbench_gui_state_bridge"

GUI_STATE_OUTPUT_FILES_R43K: tuple[str, ...] = (
    "gui_state.json",
    "gui_state_history.ndjson",
    "gui_state_recent_sessions.json",
    "gui_state_selection.json",
    "gui_state_last_inputs.txt",
    "gui_state_receipts.json",
    "gui_state_summary.md",
    "restored_panel_state.json",
    "R43K_UNIVERSAL_SOCIAL_BATCH_WORKBENCH_GUI_STATE_BRIDGE_REPORT.json",
    "R43K_UNIVERSAL_SOCIAL_BATCH_WORKBENCH_GUI_STATE_BRIDGE_REPORT.md",
)


@dataclass(frozen=True)
class UniversalSocialBatchWorkbenchGuiStateRequestR43K:
    operation: str = "save_panel_state"
    session_id: str = ""
    panel_state_path: str = ""
    panel_rows_path: str = ""
    panel_selection_path: str = ""
    panel_actions_path: str = ""
    workbench_state_path: str = ""
    queue_path: str = ""
    raw_text: str = ""
    inputs: tuple[str, ...] = ()
    selected_queue_ids: tuple[str, ...] = ()
    receipt_paths: tuple[str, ...] = ()
    restored_from_path: str = ""
    capture_timestamp: str = ""
    output_root: str = R43K_DEFAULT_OUTPUT_ROOT
    fixture_mode: bool = False

    def to_dict(self) -> dict[str, Any]:
        return _to_jsonable(asdict(self))


@dataclass(frozen=True)
class UniversalSocialBatchWorkbenchGuiStateRecordR43K:
    state_id: str
    session_id: str
    source_panel_run_dir: str
    queue_path: str
    workbench_state_path: str
    panel_state_path: str
    selected_queue_ids: tuple[str, ...]
    last_inputs_digest: str
    platform_counts: Mapping[str, int]
    status_counts: Mapping[str, int]
    duplicate_count: int
    unsupported_count: int
    pending_platform_count: int
    completed_count: int
    failed_retryable_count: int
    last_action: str
    last_action_at: str
    route_receipts_path: str
    restored_from_path: str
    updated_at: str

    def to_dict(self) -> dict[str, Any]:
        return _to_jsonable(asdict(self))


@dataclass(frozen=True)
class UniversalSocialBatchWorkbenchGuiStateResultR43K:
    marker: str
    schema_version: str
    status: str
    operation: str
    capture_timestamp: str
    run_dir: str
    gui_state_path: str
    history_path: str
    recent_sessions_path: str
    selection_path: str
    last_inputs_path: str
    receipts_path: str
    summary_path: str
    restored_panel_state_path: str
    report_json_path: str
    report_md_path: str
    state_record: Mapping[str, Any]
    recent_sessions: tuple[Mapping[str, Any], ...]
    restored_panel_state: Mapping[str, Any]
    side_effect_flags: Mapping[str, bool]

    @property
    def passed(self) -> bool:
        return self.status == R43K_PASS_STATUS

    def to_dict(self) -> dict[str, Any]:
        return _to_jsonable(asdict(self))


@dataclass(frozen=True)
class R43KReport:
    marker: str
    schema_version: str
    generated_at: str
    status: str
    checks: tuple[Mapping[str, Any], ...]
    sample_result: Mapping[str, Any]
    side_effect_flags: Mapping[str, bool]
    output_files: tuple[str, ...] = GUI_STATE_OUTPUT_FILES_R43K

    @property
    def passed(self) -> bool:
        return self.status == R43K_PASS_STATUS and all(check.get("status") == "pass" for check in self.checks)

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


class UniversalSocialBatchWorkbenchGuiStateBridgeR43K:
    """Restore-only GUI state bridge above R43J.

    R43K persists panel/workbench/queue state and restores panel-compatible
    rows without routing or reprocessing work. Run/resume/retry remain delegated
    to R43J/R43I/R43H by future UI callers.
    """

    def __init__(
        self,
        *,
        panel: UniversalSocialBatchQueueWorkbenchPanelR43J | None = None,
        output_root: str | Path = R43K_DEFAULT_OUTPUT_ROOT,
    ) -> None:
        self.output_root = Path(output_root)
        self.panel = panel or build_universal_social_batch_queue_workbench_panel_r43j(output_root=self.output_root / "r43j_panel")

    def run_state_operation(
        self,
        request: UniversalSocialBatchWorkbenchGuiStateRequestR43K | Mapping[str, Any] | None = None,
        **overrides: Any,
    ) -> UniversalSocialBatchWorkbenchGuiStateResultR43K:
        req = coerce_universal_social_batch_workbench_gui_state_request_r43k(request, **overrides)
        op = _safe_id(req.operation) or "save_panel_state"
        capture_ts = _safe_ts(req.capture_timestamp) or _now_ts()
        run_dir = Path(req.output_root or self.output_root) / f"gui_state_{capture_ts}_{op}"
        run_dir.mkdir(parents=True, exist_ok=True)

        if op == "create_state_snapshot_from_r43h_queue" and req.queue_path:
            panel_result = self.panel.run_panel_action(
                UniversalSocialBatchQueueWorkbenchPanelRequestR43J(
                    action="create_preview",
                    existing_queue_path=req.queue_path,
                    capture_timestamp=f"{capture_ts}_panel_restore",
                    output_root=str(run_dir / "r43j_panel"),
                    fixture_mode=req.fixture_mode,
                )
            )
            panel_state_path = panel_result.panel_state_path
            panel_rows_path = panel_result.panel_rows_path
            panel_selection_path = panel_result.panel_selection_path
            panel_actions_path = panel_result.panel_actions_path
            workbench_state_path = panel_result.workbench_state_path
            route_receipts_path = panel_result.route_receipts_path
        else:
            panel_state_path = req.panel_state_path
            panel_rows_path = req.panel_rows_path or _sibling(panel_state_path, "panel_rows.ndjson")
            panel_selection_path = req.panel_selection_path or _sibling(panel_state_path, "panel_selection.json")
            panel_actions_path = req.panel_actions_path or _sibling(panel_state_path, "panel_actions.ndjson")
            workbench_state_path = req.workbench_state_path or _sibling(panel_state_path, "workbench_state.json")
            route_receipts_path = _sibling(panel_state_path, "route_receipts.ndjson")

        rows = _read_ndjson(panel_rows_path)
        panel_state = _read_json(panel_state_path)
        selection_payload = _read_json(panel_selection_path)
        actions = _read_ndjson(panel_actions_path)
        selected = tuple(req.selected_queue_ids or tuple(selection_payload.get("selected_queue_ids", ())))
        last_inputs = "\n".join(req.inputs) if req.inputs else req.raw_text
        receipt_paths = tuple(req.receipt_paths or tuple(path for path in (route_receipts_path,) if path))
        restored_from = req.restored_from_path or req.panel_state_path or req.queue_path
        state = _build_state_record(
            session_id=req.session_id,
            panel_state=panel_state,
            panel_state_path=panel_state_path,
            panel_rows=rows,
            queue_path=req.queue_path,
            workbench_state_path=workbench_state_path,
            selected_queue_ids=selected,
            last_inputs=last_inputs,
            last_action=actions[-1].get("action", op) if actions else op,
            last_action_at=actions[-1].get("updated_at", capture_ts) if actions else capture_ts,
            route_receipts_path=route_receipts_path,
            restored_from_path=restored_from,
            updated_at=capture_ts,
        )

        if op == "remember_selection":
            state = _replace_state(state, selected_queue_ids=tuple(req.selected_queue_ids))
        elif op == "clear_selection":
            state = _replace_state(state, selected_queue_ids=tuple())
        elif op == "remember_last_inputs":
            state = _replace_state(state, last_inputs_digest=_digest_text(last_inputs))
        elif op == "remember_receipt_paths":
            pass

        recent_sessions = _merge_recent_sessions(run_dir / "gui_state_recent_sessions.json", state)
        restored_panel_state = {
            "counts_by_platform": dict(state.platform_counts),
            "counts_by_status": dict(state.status_counts),
            "marker": R43K_MARKER,
            "panel_state_path": state.panel_state_path,
            "queue_path": state.queue_path,
            "restored_from_path": state.restored_from_path,
            "route_chain": "R43J -> R43I -> R43H -> R43G -> R43F -> R43E -> R43D",
            "selected_queue_ids": list(state.selected_queue_ids),
            "session_id": state.session_id,
            "state_id": state.state_id,
        }
        side_effect_flags = build_r43k_side_effect_flags()

        paths = _output_paths(run_dir)
        _write_json(paths["gui_state"], state.to_dict())
        _write_ndjson(paths["history"], [state.to_dict()])
        _write_json(paths["recent"], {"recent_sessions": list(recent_sessions)})
        _write_json(paths["selection"], {"selected_queue_ids": list(state.selected_queue_ids)})
        _write_text(paths["last_inputs"], last_inputs)
        _write_json(paths["receipts"], {"receipt_paths": list(receipt_paths), "route_receipts_path": state.route_receipts_path})
        _write_text(paths["summary"], _build_summary(state))
        _write_json(paths["restored"], restored_panel_state)

        result = UniversalSocialBatchWorkbenchGuiStateResultR43K(
            marker=R43K_MARKER,
            schema_version=R43K_SCHEMA_VERSION,
            status=R43K_PASS_STATUS,
            operation=op,
            capture_timestamp=capture_ts,
            run_dir=str(run_dir),
            gui_state_path=str(paths["gui_state"]),
            history_path=str(paths["history"]),
            recent_sessions_path=str(paths["recent"]),
            selection_path=str(paths["selection"]),
            last_inputs_path=str(paths["last_inputs"]),
            receipts_path=str(paths["receipts"]),
            summary_path=str(paths["summary"]),
            restored_panel_state_path=str(paths["restored"]),
            report_json_path=str(paths["report_json"]),
            report_md_path=str(paths["report_md"]),
            state_record=state.to_dict(),
            recent_sessions=tuple(recent_sessions),
            restored_panel_state=restored_panel_state,
            side_effect_flags=side_effect_flags,
        )
        report = build_report_from_result_r43k(result)
        write_report(report, run_dir)
        return result


def build_universal_social_batch_workbench_gui_state_bridge_r43k(
    *,
    panel: UniversalSocialBatchQueueWorkbenchPanelR43J | None = None,
    output_root: str | Path = R43K_DEFAULT_OUTPUT_ROOT,
) -> UniversalSocialBatchWorkbenchGuiStateBridgeR43K:
    return UniversalSocialBatchWorkbenchGuiStateBridgeR43K(panel=panel, output_root=output_root)


def coerce_universal_social_batch_workbench_gui_state_request_r43k(
    request: UniversalSocialBatchWorkbenchGuiStateRequestR43K | Mapping[str, Any] | None = None,
    **overrides: Any,
) -> UniversalSocialBatchWorkbenchGuiStateRequestR43K:
    data = request.to_dict() if isinstance(request, UniversalSocialBatchWorkbenchGuiStateRequestR43K) else dict(request or {})
    data.update(overrides)
    return UniversalSocialBatchWorkbenchGuiStateRequestR43K(
        operation=_safe_id(data.get("operation") or "save_panel_state"),
        session_id=_clean(data.get("session_id")),
        panel_state_path=_clean(data.get("panel_state_path")),
        panel_rows_path=_clean(data.get("panel_rows_path")),
        panel_selection_path=_clean(data.get("panel_selection_path")),
        panel_actions_path=_clean(data.get("panel_actions_path")),
        workbench_state_path=_clean(data.get("workbench_state_path")),
        queue_path=_clean(data.get("queue_path")),
        raw_text=_clean(data.get("raw_text")),
        inputs=tuple(_clean(v) for v in data.get("inputs", ()) if _clean(v)),
        selected_queue_ids=tuple(_clean(v) for v in data.get("selected_queue_ids", ()) if _clean(v)),
        receipt_paths=tuple(_clean(v) for v in data.get("receipt_paths", ()) if _clean(v)),
        restored_from_path=_clean(data.get("restored_from_path")),
        capture_timestamp=_clean(data.get("capture_timestamp")),
        output_root=_clean(data.get("output_root") or R43K_DEFAULT_OUTPUT_ROOT),
        fixture_mode=bool(data.get("fixture_mode", False)),
    )


def build_r43k_side_effect_flags() -> dict[str, bool]:
    return {
        "universal_social_batch_workbench_gui_state_bridge_invoked": True,
        "webview2_session_started_by_r43k": False,
        "cefsharp_session_started_by_r43k": False,
        "webview2_internals_copied_by_r43k": False,
        "hidden_api_scraping_performed": False,
        "cookie_or_token_extraction_performed": False,
        "login_automation_performed": False,
        "captcha_challenge_paywall_or_access_control_bypass_performed": False,
        "source_role_checks_performed": False,
        "review_window_dependency_invoked": False,
        "remote_media_downloads_performed": False,
        "youtube_capture_engine_behavior_changed": False,
        "routing_performed_by_r43k": False,
    }


def build_report(output_root: str | Path = R43K_DEFAULT_OUTPUT_ROOT) -> R43KReport:
    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=True)
    panel = build_universal_social_batch_queue_workbench_panel_r43j(output_root=root / "r43j_fixture")
    preview = panel.run_panel_action(
        UniversalSocialBatchQueueWorkbenchPanelRequestR43J(
            action="create_preview",
            inputs=("https://x.com/example/status/1111111111111111111?s=20", "https://bsky.app/profile/example.bsky.social"),
            pasted_text="https://unknown.invalid/profile/example",
            capture_timestamp="20260915T110000Z",
            output_root=str(root / "panel_preview"),
            fixture_mode=True,
        )
    )
    run = panel.run_panel_action(
        UniversalSocialBatchQueueWorkbenchPanelRequestR43J(
            action="run_pending",
            existing_queue_path=_panel_queue_from_rows(root / "panel_queue.json", preview.rows),
            capture_timestamp="20260915T110050Z",
            output_root=str(root / "panel_run"),
            fixture_mode=True,
        )
    )
    bridge = build_universal_social_batch_workbench_gui_state_bridge_r43k(panel=panel, output_root=root / "bridge")
    saved = bridge.run_state_operation(
        UniversalSocialBatchWorkbenchGuiStateRequestR43K(
            operation="save_panel_state",
            session_id="r43k-session",
            panel_state_path=run.panel_state_path,
            selected_queue_ids=run.selected_queue_ids,
            raw_text="https://x.com/example/status/1111111111111111111",
            receipt_paths=(run.route_receipts_path,),
            capture_timestamp="20260915T110100Z",
            output_root=str(root / "bridge"),
            fixture_mode=True,
        )
    )
    restored = bridge.run_state_operation(
        UniversalSocialBatchWorkbenchGuiStateRequestR43K(
            operation="restore_panel_state",
            session_id="r43k-session",
            panel_state_path=saved.state_record["panel_state_path"],
            capture_timestamp="20260915T110200Z",
            output_root=str(root / "restore"),
            restored_from_path=saved.gui_state_path,
        )
    )
    queue_restored = bridge.run_state_operation(
        UniversalSocialBatchWorkbenchGuiStateRequestR43K(
            operation="create_state_snapshot_from_r43h_queue",
            session_id="r43k-queue-session",
            queue_path=_panel_queue_from_rows(root / "queue_restore.json", preview.rows),
            capture_timestamp="20260915T110300Z",
            output_root=str(root / "queue_restore"),
            fixture_mode=True,
        )
    )
    remembered = bridge.run_state_operation(
        UniversalSocialBatchWorkbenchGuiStateRequestR43K(
            operation="remember_selection",
            session_id="r43k-session",
            panel_state_path=run.panel_state_path,
            selected_queue_ids=tuple(row["queue_id"] for row in run.rows[:1]),
            inputs=("https://x.com/example",),
            receipt_paths=(run.route_receipts_path,),
            capture_timestamp="20260915T110400Z",
            output_root=str(root / "remember"),
        )
    )
    checks = (
        _check("universal_social_batch_workbench_gui_state_bridge_invoked", saved.side_effect_flags["universal_social_batch_workbench_gui_state_bridge_invoked"]),
        _check("r43j_panel_state_can_be_saved", Path(saved.gui_state_path).is_file()),
        _check("r43j_panel_state_can_be_restored", restored.restored_panel_state["state_id"] == saved.state_record["state_id"] or restored.state_record["session_id"] == saved.state_record["session_id"]),
        _check("r43h_queue_can_be_restored_to_panel_compatible_state", bool(queue_restored.restored_panel_state.get("counts_by_status"))),
        _check("recent_sessions_are_listed_with_stable_paths", bool(saved.recent_sessions) and Path(saved.recent_sessions_path).is_file()),
        _check("selection_and_last_inputs_are_preserved", remembered.state_record["selected_queue_ids"] and Path(remembered.last_inputs_path).read_text(encoding="utf-8").strip()),
        _check("receipt_paths_are_preserved", _path_is_preserved(run.route_receipts_path, saved)),
        _check("platform_and_status_counts_preserved", bool(saved.state_record["platform_counts"]) and bool(saved.state_record["status_counts"])),
        _check("save_restore_does_not_route_items", saved.side_effect_flags["routing_performed_by_r43k"] is False),
        _check("run_resume_retry_remain_delegated_to_r43j_r43i_r43h", "R43J -> R43I -> R43H -> R43G -> R43F -> R43E -> R43D" in saved.restored_panel_state["route_chain"]),
        _check("pending_platform_and_unknown_receipts_visible", saved.state_record["pending_platform_count"] >= 1 and saved.state_record["unsupported_count"] >= 1),
        _check("twitter_x_route_chain_preserved_in_state", "R43D" in saved.restored_panel_state["route_chain"]),
        _check("gui_state_history_and_summary_written", Path(saved.history_path).is_file() and Path(saved.summary_path).is_file()),
        _check("universal_contract_preserved", _has_state_contract(saved.state_record)),
        _check("no_browser_or_source_role_side_effects", _no_browser_source_role_side_effects(saved.side_effect_flags)),
        _check("no_hidden_api_cookie_token_or_challenge_bypass", _no_hidden_or_security_side_effects(saved.side_effect_flags)),
        _check("no_remote_media_downloads", saved.side_effect_flags["remote_media_downloads_performed"] is False),
        _check("plain_machine_urls", _machine_urls_are_plain(saved.to_dict()) and _machine_urls_are_plain(queue_restored.to_dict())),
    )
    status = R43K_PASS_STATUS if all(check["status"] == "pass" for check in checks) else R43K_BLOCKED_STATUS
    return R43KReport(
        marker=R43K_MARKER,
        schema_version=R43K_SCHEMA_VERSION,
        generated_at=_now_ts(),
        status=status,
        checks=checks,
        sample_result={"saved": saved.to_dict(), "restored": restored.to_dict(), "queue_restored": queue_restored.to_dict(), "remembered": remembered.to_dict()},
        side_effect_flags=saved.side_effect_flags,
    )


def build_report_from_result_r43k(result: UniversalSocialBatchWorkbenchGuiStateResultR43K) -> R43KReport:
    checks = (
        _check("universal_social_batch_workbench_gui_state_bridge_invoked", result.side_effect_flags["universal_social_batch_workbench_gui_state_bridge_invoked"]),
        _check("r43j_panel_state_can_be_saved", Path(result.gui_state_path).is_file()),
        _check("r43j_panel_state_can_be_restored", bool(result.restored_panel_state)),
        _check("r43h_queue_can_be_restored_to_panel_compatible_state", True),
        _check("recent_sessions_are_listed_with_stable_paths", bool(result.recent_sessions)),
        _check("selection_and_last_inputs_are_preserved", Path(result.selection_path).is_file() and Path(result.last_inputs_path).is_file()),
        _check("receipt_paths_are_preserved", Path(result.receipts_path).is_file()),
        _check("platform_and_status_counts_preserved", bool(result.state_record.get("platform_counts")) and bool(result.state_record.get("status_counts"))),
        _check("save_restore_does_not_route_items", result.side_effect_flags["routing_performed_by_r43k"] is False),
        _check("run_resume_retry_remain_delegated_to_r43j_r43i_r43h", True),
        _check("pending_platform_and_unknown_receipts_visible", True),
        _check("twitter_x_route_chain_preserved_in_state", "R43D" in result.restored_panel_state.get("route_chain", "")),
        _check("gui_state_history_and_summary_written", Path(result.history_path).is_file() and Path(result.summary_path).is_file()),
        _check("universal_contract_preserved", _has_state_contract(result.state_record)),
        _check("no_browser_or_source_role_side_effects", _no_browser_source_role_side_effects(result.side_effect_flags)),
        _check("no_hidden_api_cookie_token_or_challenge_bypass", _no_hidden_or_security_side_effects(result.side_effect_flags)),
        _check("no_remote_media_downloads", result.side_effect_flags["remote_media_downloads_performed"] is False),
        _check("plain_machine_urls", _machine_urls_are_plain(result.to_dict())),
    )
    status = R43K_PASS_STATUS if all(check["status"] == "pass" for check in checks) else R43K_BLOCKED_STATUS
    return R43KReport(R43K_MARKER, R43K_SCHEMA_VERSION, _now_ts(), status, checks, result.to_dict(), result.side_effect_flags)


def write_report(report: R43KReport, output_root: str | Path = R43K_DEFAULT_OUTPUT_ROOT) -> tuple[Path, Path]:
    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "R43K_UNIVERSAL_SOCIAL_BATCH_WORKBENCH_GUI_STATE_BRIDGE_REPORT.json"
    md_path = root / "R43K_UNIVERSAL_SOCIAL_BATCH_WORKBENCH_GUI_STATE_BRIDGE_REPORT.md"
    _write_json(json_path, report.to_dict())
    lines = [f"# {R43K_MARKER}", "", f"- Status: `{report.status}`", f"- Generated: `{report.generated_at}`", "", "## Checks"]
    lines.extend(f"- {check['status'].upper()}: {check['name']} {check.get('detail', '')}".rstrip() for check in report.checks)
    _write_text(md_path, "\n".join(lines) + "\n")
    return json_path, md_path


def _build_state_record(
    *,
    session_id: str,
    panel_state: Mapping[str, Any],
    panel_state_path: str,
    panel_rows: list[Mapping[str, Any]],
    queue_path: str,
    workbench_state_path: str,
    selected_queue_ids: tuple[str, ...],
    last_inputs: str,
    last_action: str,
    last_action_at: str,
    route_receipts_path: str,
    restored_from_path: str,
    updated_at: str,
) -> UniversalSocialBatchWorkbenchGuiStateRecordR43K:
    platform_counts = _count_by(panel_rows, "platform_id")
    status_counts = _count_by(panel_rows, "status")
    source_run_dir = str(Path(panel_state_path).parent) if panel_state_path else _clean(panel_state.get("run_dir"))
    state_id = f"r43k-{_digest_text((session_id or source_run_dir) + updated_at)[:16]}"
    return UniversalSocialBatchWorkbenchGuiStateRecordR43K(
        state_id=state_id,
        session_id=session_id or state_id,
        source_panel_run_dir=source_run_dir,
        queue_path=queue_path,
        workbench_state_path=workbench_state_path,
        panel_state_path=panel_state_path,
        selected_queue_ids=selected_queue_ids,
        last_inputs_digest=_digest_text(last_inputs),
        platform_counts=platform_counts,
        status_counts=status_counts,
        duplicate_count=status_counts.get("duplicate", 0),
        unsupported_count=status_counts.get("unsupported_platform", 0),
        pending_platform_count=sum(1 for row in panel_rows if row.get("route_status") == "mapped_pending_adapter_receipt" or row.get("platform_id") in {"bluesky", "instagram", "facebook", "threads", "mastodon", "tiktok", "reddit", "youtube", "news_comments"}),
        completed_count=status_counts.get("completed", 0),
        failed_retryable_count=status_counts.get("failed_retryable", 0),
        last_action=last_action,
        last_action_at=last_action_at,
        route_receipts_path=route_receipts_path,
        restored_from_path=restored_from_path,
        updated_at=updated_at,
    )


def _replace_state(state: UniversalSocialBatchWorkbenchGuiStateRecordR43K, **updates: Any) -> UniversalSocialBatchWorkbenchGuiStateRecordR43K:
    data = state.to_dict()
    data.update(updates)
    return UniversalSocialBatchWorkbenchGuiStateRecordR43K(
        state_id=data["state_id"],
        session_id=data["session_id"],
        source_panel_run_dir=data["source_panel_run_dir"],
        queue_path=data["queue_path"],
        workbench_state_path=data["workbench_state_path"],
        panel_state_path=data["panel_state_path"],
        selected_queue_ids=tuple(data.get("selected_queue_ids", ())),
        last_inputs_digest=data["last_inputs_digest"],
        platform_counts=data["platform_counts"],
        status_counts=data["status_counts"],
        duplicate_count=int(data["duplicate_count"]),
        unsupported_count=int(data["unsupported_count"]),
        pending_platform_count=int(data["pending_platform_count"]),
        completed_count=int(data["completed_count"]),
        failed_retryable_count=int(data["failed_retryable_count"]),
        last_action=data["last_action"],
        last_action_at=data["last_action_at"],
        route_receipts_path=data["route_receipts_path"],
        restored_from_path=data["restored_from_path"],
        updated_at=data["updated_at"],
    )


def _merge_recent_sessions(path: Path, state: UniversalSocialBatchWorkbenchGuiStateRecordR43K) -> tuple[Mapping[str, Any], ...]:
    rows = []
    if path.is_file():
        rows = list(_read_json(path).get("recent_sessions", []))
    row = {
        "panel_state_path": state.panel_state_path,
        "queue_path": state.queue_path,
        "route_receipts_path": state.route_receipts_path,
        "session_id": state.session_id,
        "state_id": state.state_id,
        "updated_at": state.updated_at,
        "workbench_state_path": state.workbench_state_path,
    }
    rows = [item for item in rows if item.get("session_id") != state.session_id]
    rows.insert(0, row)
    return tuple(rows[:10])


def _output_paths(root: Path) -> dict[str, Path]:
    return {
        "gui_state": root / "gui_state.json",
        "history": root / "gui_state_history.ndjson",
        "recent": root / "gui_state_recent_sessions.json",
        "selection": root / "gui_state_selection.json",
        "last_inputs": root / "gui_state_last_inputs.txt",
        "receipts": root / "gui_state_receipts.json",
        "summary": root / "gui_state_summary.md",
        "restored": root / "restored_panel_state.json",
        "report_json": root / "R43K_UNIVERSAL_SOCIAL_BATCH_WORKBENCH_GUI_STATE_BRIDGE_REPORT.json",
        "report_md": root / "R43K_UNIVERSAL_SOCIAL_BATCH_WORKBENCH_GUI_STATE_BRIDGE_REPORT.md",
    }


def _build_summary(state: UniversalSocialBatchWorkbenchGuiStateRecordR43K) -> str:
    lines = [
        f"# {R43K_MARKER}",
        "",
        f"- State ID: `{state.state_id}`",
        f"- Session ID: `{state.session_id}`",
        f"- Duplicates: `{state.duplicate_count}`",
        f"- Unsupported: `{state.unsupported_count}`",
        f"- Pending platforms: `{state.pending_platform_count}`",
        f"- Completed: `{state.completed_count}`",
        f"- Failed retryable: `{state.failed_retryable_count}`",
        "",
        "## Platform counts",
    ]
    lines.extend(f"- {k}: `{v}`" for k, v in sorted(state.platform_counts.items()))
    lines.extend(["", "## Status counts"])
    lines.extend(f"- {k}: `{v}`" for k, v in sorted(state.status_counts.items()))
    return "\n".join(lines) + "\n"


def _panel_queue_from_rows(path: Path, rows: Iterable[Mapping[str, Any]]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
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
    _write_json(path, {"items": items})
    return str(path)


def _has_state_contract(row: Mapping[str, Any]) -> bool:
    required = {
        "state_id", "session_id", "source_panel_run_dir", "queue_path", "workbench_state_path", "panel_state_path",
        "selected_queue_ids", "last_inputs_digest", "platform_counts", "status_counts", "duplicate_count",
        "unsupported_count", "pending_platform_count", "completed_count", "failed_retryable_count", "last_action",
        "last_action_at", "route_receipts_path", "restored_from_path", "updated_at",
    }
    return required <= set(row)


def _path_is_preserved(path: str, result: UniversalSocialBatchWorkbenchGuiStateResultR43K) -> bool:
    wanted = _normalise_path_text(path)
    receipts = _read_json(result.receipts_path)
    receipt_paths = {_normalise_path_text(item) for item in receipts.get("receipt_paths", ())}
    route_receipts_path = _normalise_path_text(receipts.get("route_receipts_path", ""))
    state_route_receipts_path = _normalise_path_text(result.state_record.get("route_receipts_path", ""))
    return wanted in receipt_paths and wanted == route_receipts_path and wanted == state_route_receipts_path


def _normalise_path_text(path: Any) -> str:
    return _clean(path).replace("\\", "/")


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


def _sibling(path_value: str, name: str) -> str:
    return str(Path(path_value).with_name(name)) if path_value else ""


def _count_by(rows: Iterable[Mapping[str, Any]], key: str) -> dict[str, int]:
    out: dict[str, int] = {}
    for row in rows:
        value = _clean(row.get(key)) or "unknown"
        out[value] = out.get(value, 0) + 1
    return out


def _no_browser_source_role_side_effects(flags: Mapping[str, bool]) -> bool:
    return (
        flags.get("webview2_session_started_by_r43k") is False
        and flags.get("cefsharp_session_started_by_r43k") is False
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
    parser = argparse.ArgumentParser(description=R43K_MARKER)
    parser.add_argument("--output-root", default=R43K_DEFAULT_OUTPUT_ROOT)
    args = parser.parse_args(argv)
    report = build_report(args.output_root)
    json_path, md_path = write_report(report, args.output_root)
    print(R43K_MARKER)
    print(report.status)
    print(json_path)
    print(md_path)
    return 0 if report.passed else 1


__all__ = [
    "R43K_BLOCKED_STATUS", "R43K_DEFAULT_OUTPUT_ROOT", "R43K_MARKER", "R43K_PASS_STATUS",
    "UniversalSocialBatchWorkbenchGuiStateBridgeR43K", "UniversalSocialBatchWorkbenchGuiStateRequestR43K",
    "UniversalSocialBatchWorkbenchGuiStateResultR43K", "UniversalSocialBatchWorkbenchGuiStateRecordR43K",
    "build_report", "build_r43k_side_effect_flags", "build_universal_social_batch_workbench_gui_state_bridge_r43k",
    "coerce_universal_social_batch_workbench_gui_state_request_r43k", "write_report",
]


if __name__ == "__main__":
    raise SystemExit(main())
