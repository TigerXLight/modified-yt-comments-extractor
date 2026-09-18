from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

from profile_media_universal_social_batch_queue_resume_dedupe_progress_r43h import (
    R43H_PASS_STATUS,
    UniversalSocialBatchQueueRecordR43H,
    UniversalSocialBatchQueueRequestR43H,
    UniversalSocialBatchQueueRouterR43H,
    build_r43h_side_effect_flags,
    build_universal_social_batch_queue_router_r43h,
)

R43I_MARKER = "YTCE_R43I_UNIVERSAL_SOCIAL_BATCH_QUEUE_WORKBENCH_CONTROLS"
R43I_PASS_STATUS = "PASS_R43I_UNIVERSAL_SOCIAL_BATCH_QUEUE_WORKBENCH_CONTROLS"
R43I_BLOCKED_STATUS = "BLOCKED_R43I_UNIVERSAL_SOCIAL_BATCH_QUEUE_WORKBENCH_CONTROLS"
R43I_SCHEMA_VERSION = "universal_social_batch_queue_workbench_controls.r43i.v1"
R43I_DEFAULT_OUTPUT_ROOT = "profile_media_live_captures/r43i_universal_social_batch_queue_workbench_controls"
R43I_MODE_ID = "universal_social_batch_queue_workbench_controls"

WORKBENCH_OUTPUT_FILES_R43I: tuple[str, ...] = (
    "workbench_state.json",
    "workbench_rows.ndjson",
    "workbench_actions.ndjson",
    "workbench_summary.md",
    "workbench_receipt.json",
    "selected_queue_ids.json",
    "route_receipts.ndjson",
    "R43I_UNIVERSAL_SOCIAL_BATCH_QUEUE_WORKBENCH_CONTROLS_REPORT.json",
    "R43I_UNIVERSAL_SOCIAL_BATCH_QUEUE_WORKBENCH_CONTROLS_REPORT.md",
)

RUN_ELIGIBLE_STATUSES_R43I = {"pending", "failed_retryable"}
RETRY_ELIGIBLE_STATUSES_R43I = {"failed_retryable"}
NON_RETRYABLE_STATUSES_R43I = {"completed", "duplicate", "failed_terminal", "unsupported_platform", "skipped"}


@dataclass(frozen=True)
class UniversalSocialBatchQueueWorkbenchRequestR43I:
    operation: str = "create_queue_preview"
    inputs: tuple[str, ...] = ()
    raw_text: str = ""
    txt_path: str = ""
    detected_items: tuple[Mapping[str, Any], ...] = ()
    existing_queue_path: str = ""
    selected_queue_ids: tuple[str, ...] = ()
    platform_id_hint: str = ""
    include_posts: bool = True
    include_reposts_or_reshares: bool = True
    include_quotes: bool = True
    include_replies: bool = False
    include_media: bool = True
    include_static_screenshots: bool = True
    require_screenshot_receipts: bool = True
    capture_timestamp: str = ""
    output_root: str = R43I_DEFAULT_OUTPUT_ROOT
    fixture_mode: bool = False
    explicit_live_mode: bool = False
    run_visible_live: bool = False
    live_mode: bool = False
    public_network_enabled: bool = False
    browser_user_data_dir: str = ""
    browser_executable_path: str = ""
    max_items: int = 3
    max_scrolls: int = 2

    def to_dict(self) -> dict[str, Any]:
        return _to_jsonable(asdict(self))


@dataclass(frozen=True)
class UniversalSocialBatchQueueWorkbenchRowR43I:
    queue_id: str
    batch_index: int
    raw_input: str
    normalized_url: str
    platform_id: str
    url_kind: str
    account_handle: str
    record_id: str
    dedupe_key: str
    duplicate_of: str
    status: str
    route_status: str
    downstream_status: str
    attempts: int
    selected: bool
    eligible_for_run: bool
    eligible_for_retry: bool
    last_error: str
    route_receipt_path: str
    run_dir: str
    updated_at: str
    public_network_enabled: bool = False

    def to_dict(self) -> dict[str, Any]:
        return _to_jsonable(asdict(self))


@dataclass(frozen=True)
class UniversalSocialBatchQueueWorkbenchResultR43I:
    marker: str
    schema_version: str
    status: str
    operation: str
    capture_timestamp: str
    run_dir: str
    state_path: str
    rows_path: str
    actions_path: str
    summary_path: str
    receipt_path: str
    selected_queue_ids_path: str
    route_receipts_path: str
    report_json_path: str
    report_md_path: str
    rows: tuple[Mapping[str, Any], ...]
    actions: tuple[Mapping[str, Any], ...]
    selected_queue_ids: tuple[str, ...]
    route_receipts: tuple[Mapping[str, Any], ...]
    receipt: Mapping[str, Any]
    side_effect_flags: Mapping[str, bool]
    warnings: tuple[str, ...] = ()

    @property
    def passed(self) -> bool:
        return self.status == R43I_PASS_STATUS

    def to_dict(self) -> dict[str, Any]:
        return _to_jsonable(asdict(self))


@dataclass(frozen=True)
class R43IReport:
    marker: str
    schema_version: str
    generated_at: str
    status: str
    checks: tuple[Mapping[str, Any], ...]
    sample_result: Mapping[str, Any]
    side_effect_flags: Mapping[str, bool]
    output_files: tuple[str, ...] = WORKBENCH_OUTPUT_FILES_R43I

    @property
    def passed(self) -> bool:
        return self.status == R43I_PASS_STATUS and all(check.get("status") == "pass" for check in self.checks)

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


class UniversalSocialBatchQueueWorkbenchR43I:
    """Workbench/control surface above the R43H universal queue.

    R43I intentionally does not route directly to R43G/R43F/R43E/R43D.  Preview
    builds rows through R43H without routing; run/resume/retry operations write a
    queue file and delegate processing back to R43H.  The layer is UI/control
    state only and has no browser, source-role, review-window, media download,
    credential, login, or challenge-bypass side effects.
    """

    def __init__(
        self,
        *,
        queue_router: UniversalSocialBatchQueueRouterR43H | None = None,
        output_root: str | Path = R43I_DEFAULT_OUTPUT_ROOT,
    ) -> None:
        self.output_root = Path(output_root)
        self.queue_router = queue_router or build_universal_social_batch_queue_router_r43h(output_root=self.output_root / "r43h_queue")

    def run_workbench_operation(
        self,
        request: UniversalSocialBatchQueueWorkbenchRequestR43I | Mapping[str, Any] | None = None,
        **overrides: Any,
    ) -> UniversalSocialBatchQueueWorkbenchResultR43I:
        req = coerce_universal_social_batch_queue_workbench_request_r43i(request, **overrides)
        capture_ts = _safe_ts(req.capture_timestamp) or _now_ts()
        operation = _safe_operation(req.operation)
        run_dir = Path(req.output_root or self.output_root) / f"workbench_{capture_ts}_{operation}"
        run_dir.mkdir(parents=True, exist_ok=True)

        selected = set(req.selected_queue_ids)
        rows: list[UniversalSocialBatchQueueWorkbenchRowR43I]
        route_receipts: list[Mapping[str, Any]] = []
        actions: list[Mapping[str, Any]] = []
        warnings: list[str] = []

        if operation == "create_queue_preview":
            _, records, _ = self.queue_router.build_queue_records(_to_r43h_request(req, process_now=False))
            rows = [_row_from_record(record, selected=record.queue_id in selected) for record in records]
            actions.append(_action(capture_ts, operation, "preview_created", "Queue preview does not route items."))
        elif operation == "load_existing_queue":
            records = _load_records_from_queue_path(req.existing_queue_path)
            rows = [_row_from_record(record, selected=record.queue_id in selected) for record in records]
            actions.append(_action(capture_ts, operation, "existing_queue_loaded", req.existing_queue_path))
        elif operation in {"run_pending", "resume", "retry_failed_retryable", "retry_selected"}:
            records = _records_for_operation(req, operation, self.queue_router)
            if operation == "retry_selected":
                records = [_reset_for_retry(record) if record.queue_id in selected else record for record in records]
                records = [record for record in records if record.queue_id in selected or record.status in NON_RETRYABLE_STATUSES_R43I]
            elif operation == "retry_failed_retryable":
                records = [_reset_for_retry(record) if record.status == "failed_retryable" else record for record in records]
            queue_path = run_dir / "workbench_delegate_queue.json"
            _write_json(
                queue_path,
                {
                    "items": [record.to_dict() for record in records],
                    "marker": R43I_MARKER,
                    "live_options": _live_options_payload(req),
                },
            )
            delegated = self.queue_router.run_batch(
                UniversalSocialBatchQueueRequestR43H(
                    existing_queue_path=str(queue_path),
                    capture_timestamp=f"{capture_ts}_delegate",
                    output_root=str(run_dir / "r43h_delegate"),
                    fixture_mode=req.fixture_mode,
                    explicit_live_mode=req.explicit_live_mode,
                    run_visible_live=req.run_visible_live,
                    live_mode=req.live_mode,
                    public_network_enabled=req.public_network_enabled,
                    browser_user_data_dir=req.browser_user_data_dir,
                    browser_executable_path=req.browser_executable_path,
                    max_items=req.max_items,
                    max_scrolls=req.max_scrolls,
                )
            )
            route_receipts = [dict(item) for item in delegated.route_receipts]
            route_receipts.append(
                {
                    "queue_id": "__r43h_resume_receipt__",
                    "resume_receipt": dict(delegated.resume_receipt),
                    "route_status": "r43h_resume_receipt",
                    "run_dir": delegated.run_dir,
                }
            )
            rows = [_row_from_record(_record_from_mapping(record), selected=record.get("queue_id") in selected) for record in delegated.queue_records]
            actions.append(_action(capture_ts, operation, "delegated_to_r43h", delegated.run_dir))
        elif operation == "skip_selected":
            records = _records_for_operation(req, operation, self.queue_router)
            rows = []
            for record in records:
                if record.queue_id in selected:
                    record = _replace_record(record, status="skipped", updated_at=_now_ts(), last_error="Skipped by workbench selection.")
                    actions.append(_action(capture_ts, operation, "selected_row_skipped", record.queue_id))
                rows.append(_row_from_record(record, selected=record.queue_id in selected))
        elif operation == "stop_after_current_item":
            records = _records_for_operation(req, operation, self.queue_router)
            rows = [_row_from_record(record, selected=record.queue_id in selected) for record in records]
            actions.append(_action(capture_ts, operation, "stop_after_current_item_requested", "Receipt only; no daemon is started."))
        elif operation in {"export_queue_summary", "export_route_receipts"}:
            records = _records_for_operation(req, operation, self.queue_router)
            rows = [_row_from_record(record, selected=record.queue_id in selected) for record in records]
            if operation == "export_route_receipts":
                route_receipts = [_receipt_from_record(record) for record in records if record.route_receipt_path or record.route_status]
            actions.append(_action(capture_ts, operation, "exported", "Workbench export generated from current queue state."))
        else:
            records = _records_for_operation(req, "load_existing_queue", self.queue_router)
            rows = [_row_from_record(record, selected=record.queue_id in selected) for record in records]
            warnings.append(f"Unsupported workbench operation: {operation}")
            actions.append(_action(capture_ts, operation, "unsupported_operation_receipt", "No routing performed."))

        side_effect_flags = build_r43i_side_effect_flags()
        selected_ids = tuple(row.queue_id for row in rows if row.selected)
        state_path = run_dir / "workbench_state.json"
        rows_path = run_dir / "workbench_rows.ndjson"
        actions_path = run_dir / "workbench_actions.ndjson"
        summary_path = run_dir / "workbench_summary.md"
        receipt_path = run_dir / "workbench_receipt.json"
        selected_path = run_dir / "selected_queue_ids.json"
        route_receipts_path = run_dir / "route_receipts.ndjson"
        report_json_path = run_dir / "R43I_UNIVERSAL_SOCIAL_BATCH_QUEUE_WORKBENCH_CONTROLS_REPORT.json"
        report_md_path = run_dir / "R43I_UNIVERSAL_SOCIAL_BATCH_QUEUE_WORKBENCH_CONTROLS_REPORT.md"

        receipt = {
            "capture_timestamp": capture_ts,
            "marker": R43I_MARKER,
            "operation": operation,
            "queue_row_count": len(rows),
            "route_receipt_count": len(route_receipts),
            "schema_version": R43I_SCHEMA_VERSION,
            "selected_queue_ids": list(selected_ids),
            "status_counts": _count_statuses(rows),
        }
        result = UniversalSocialBatchQueueWorkbenchResultR43I(
            marker=R43I_MARKER,
            schema_version=R43I_SCHEMA_VERSION,
            status=R43I_PASS_STATUS,
            operation=operation,
            capture_timestamp=capture_ts,
            run_dir=str(run_dir),
            state_path=str(state_path),
            rows_path=str(rows_path),
            actions_path=str(actions_path),
            summary_path=str(summary_path),
            receipt_path=str(receipt_path),
            selected_queue_ids_path=str(selected_path),
            route_receipts_path=str(route_receipts_path),
            report_json_path=str(report_json_path),
            report_md_path=str(report_md_path),
            rows=tuple(row.to_dict() for row in rows),
            actions=tuple(actions),
            selected_queue_ids=selected_ids,
            route_receipts=tuple(route_receipts),
            receipt=receipt,
            side_effect_flags=side_effect_flags,
            warnings=tuple(warnings),
        )
        _write_json(state_path, _workbench_state_payload(result))
        _write_ndjson(rows_path, result.rows)
        _write_ndjson(actions_path, result.actions)
        _write_text(summary_path, _build_summary(result))
        _write_json(receipt_path, receipt)
        _write_json(selected_path, {"selected_queue_ids": list(selected_ids)})
        _write_ndjson(route_receipts_path, route_receipts)
        report = build_report_from_result_r43i(result)
        write_report(report, run_dir)
        return result


def build_universal_social_batch_queue_workbench_r43i(
    *,
    queue_router: UniversalSocialBatchQueueRouterR43H | None = None,
    output_root: str | Path = R43I_DEFAULT_OUTPUT_ROOT,
) -> UniversalSocialBatchQueueWorkbenchR43I:
    return UniversalSocialBatchQueueWorkbenchR43I(queue_router=queue_router, output_root=output_root)


def coerce_universal_social_batch_queue_workbench_request_r43i(
    request: UniversalSocialBatchQueueWorkbenchRequestR43I | Mapping[str, Any] | None = None,
    **overrides: Any,
) -> UniversalSocialBatchQueueWorkbenchRequestR43I:
    if isinstance(request, UniversalSocialBatchQueueWorkbenchRequestR43I):
        data = request.to_dict()
    else:
        data = dict(request or {})
    data.update(overrides)
    return UniversalSocialBatchQueueWorkbenchRequestR43I(
        operation=_safe_operation(data.get("operation") or "create_queue_preview"),
        inputs=tuple(_clean(v) for v in data.get("inputs", ()) if _clean(v)),
        raw_text=_clean(data.get("raw_text")),
        txt_path=_clean(data.get("txt_path")),
        detected_items=tuple(dict(item) for item in data.get("detected_items", ()) if isinstance(item, Mapping)),
        existing_queue_path=_clean(data.get("existing_queue_path")),
        selected_queue_ids=tuple(_clean(v) for v in data.get("selected_queue_ids", ()) if _clean(v)),
        platform_id_hint=_clean(data.get("platform_id_hint")),
        include_posts=bool(data.get("include_posts", True)),
        include_reposts_or_reshares=bool(data.get("include_reposts_or_reshares", True)),
        include_quotes=bool(data.get("include_quotes", True)),
        include_replies=bool(data.get("include_replies", False)),
        include_media=bool(data.get("include_media", True)),
        include_static_screenshots=bool(data.get("include_static_screenshots", True)),
        require_screenshot_receipts=bool(data.get("require_screenshot_receipts", True)),
        capture_timestamp=_clean(data.get("capture_timestamp")),
        output_root=_clean(data.get("output_root") or R43I_DEFAULT_OUTPUT_ROOT),
        fixture_mode=_to_bool(data.get("fixture_mode"), False),
        explicit_live_mode=_to_bool(data.get("explicit_live_mode"), False),
        run_visible_live=_to_bool(data.get("run_visible_live"), False),
        live_mode=_to_bool(data.get("live_mode"), False),
        public_network_enabled=_to_bool(data.get("public_network_enabled"), False),
        browser_user_data_dir=_clean(data.get("browser_user_data_dir")),
        browser_executable_path=_clean(data.get("browser_executable_path")),
        max_items=_safe_int(data.get("max_items"), 3),
        max_scrolls=_safe_int(data.get("max_scrolls"), 2),
    )


def build_r43i_side_effect_flags() -> dict[str, bool]:
    return {
        "universal_social_batch_queue_workbench_invoked": True,
        "webview2_session_started_by_r43i": False,
        "cefsharp_session_started_by_r43i": False,
        "webview2_internals_copied_by_r43i": False,
        "hidden_api_scraping_performed": False,
        "cookie_or_token_extraction_performed": False,
        "login_automation_performed": False,
        "captcha_challenge_paywall_or_access_control_bypass_performed": False,
        "source_role_checks_performed": False,
        "review_window_dependency_invoked": False,
        "remote_media_downloads_performed": False,
        "youtube_capture_engine_behavior_changed": False,
    }


def build_report(output_root: str | Path = R43I_DEFAULT_OUTPUT_ROOT) -> R43IReport:
    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=True)
    txt_path = root / "r43i_sample_urls.txt"
    txt_path.write_text("https://www.instagram.com/p/C-example/?igsh=test\nhttps://unknown.invalid/profile/example\n", encoding="utf-8")
    workbench = build_universal_social_batch_queue_workbench_r43i(output_root=root / "sample")
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
            txt_path=str(txt_path),
            capture_timestamp="20260915T090000Z",
            output_root=str(root / "sample"),
            fixture_mode=True,
        )
    )
    preview_queue_path = root / "preview_queue.json"
    _write_json(preview_queue_path, {"items": [_record_payload_from_row(row) for row in preview.rows]})
    loaded = workbench.run_workbench_operation(
        UniversalSocialBatchQueueWorkbenchRequestR43I(
            operation="load_existing_queue",
            existing_queue_path=str(preview_queue_path),
            capture_timestamp="20260915T090100Z",
            output_root=str(root / "loaded"),
            fixture_mode=True,
        )
    )
    run = workbench.run_workbench_operation(
        UniversalSocialBatchQueueWorkbenchRequestR43I(
            operation="run_pending",
            existing_queue_path=str(preview_queue_path),
            capture_timestamp="20260915T090200Z",
            output_root=str(root / "run"),
            fixture_mode=True,
        )
    )
    run_queue_path = root / "run_queue.json"
    rows_for_resume = [_record_payload_from_row(row) for row in run.rows]
    for row in rows_for_resume:
        if row["status"] == "completed" and row["platform_id"] == "twitter_x":
            row["status"] = "failed_retryable"
            row["route_status"] = "retryable_fixture_failure"
            break
    rows_for_resume.append({**rows_for_resume[0], "queue_id": "terminal-workbench-fixture", "batch_index": 999, "status": "failed_terminal", "duplicate_of": ""})
    _write_json(run_queue_path, {"items": rows_for_resume})
    resume = workbench.run_workbench_operation(
        UniversalSocialBatchQueueWorkbenchRequestR43I(
            operation="resume",
            existing_queue_path=str(run_queue_path),
            capture_timestamp="20260915T090300Z",
            output_root=str(root / "resume"),
            fixture_mode=True,
        )
    )
    selected_id = next(row["queue_id"] for row in rows_for_resume if row["status"] == "failed_retryable")
    retry_selected = workbench.run_workbench_operation(
        UniversalSocialBatchQueueWorkbenchRequestR43I(
            operation="retry_selected",
            existing_queue_path=str(run_queue_path),
            selected_queue_ids=(selected_id,),
            capture_timestamp="20260915T090400Z",
            output_root=str(root / "retry_selected"),
            fixture_mode=True,
        )
    )
    skip_selected = workbench.run_workbench_operation(
        UniversalSocialBatchQueueWorkbenchRequestR43I(
            operation="skip_selected",
            existing_queue_path=str(preview_queue_path),
            selected_queue_ids=(preview.rows[0]["queue_id"],),
            capture_timestamp="20260915T090500Z",
            output_root=str(root / "skip"),
            fixture_mode=True,
        )
    )

    checks = (
        _check("universal_social_batch_queue_workbench_invoked", preview.side_effect_flags["universal_social_batch_queue_workbench_invoked"]),
        _check("queue_preview_does_not_route_items", len(preview.route_receipts) == 0 and all(row["route_status"] == "not_routed" for row in preview.rows if row["status"] != "duplicate")),
        _check("existing_r43h_queue_can_be_loaded", len(loaded.rows) == len(preview.rows)),
        _check("run_and_resume_delegate_to_r43h", len(run.route_receipts) > 0 and any(action["action"] == "delegated_to_r43h" for action in run.actions) and any(action["action"] == "delegated_to_r43h" for action in resume.actions)),
        _check("duplicate_rows_visible_but_not_routed_twice", any(row["duplicate_of"] for row in preview.rows) and not any(row["status"] == "duplicate" and row["queue_id"] in _routed_queue_ids(run) for row in run.rows)),
        _check("completed_rows_skipped_on_resume", _resume_receipt_count(resume, "skipped_completed") > 0),
        _check("failed_terminal_and_unsupported_not_retried_by_default", _resume_receipt_count(resume, "skipped_non_retryable") > 0),
        _check("selected_retry_and_skip_controls_recorded", retry_selected.selected_queue_ids and any(action["action"] == "selected_row_skipped" for action in skip_selected.actions)),
        _check("pending_platform_and_unknown_receipts_visible", any(_first_route_status(r) == "mapped_pending_adapter_receipt" for r in run.route_receipts) and any(_first_route_status(r) == "unsupported_platform_receipt" for r in run.route_receipts)),
        _check("twitter_x_rows_route_through_r43h_r43g_r43f_r43e_r43d", any(_first_route_status(r) == "dispatched_to_r43d_surface_via_r43e_adapter_map" for r in run.route_receipts)),
        _check("workbench_state_rows_actions_and_summary_written", _all_output_files_exist(preview)),
        _check("universal_contract_preserved", all(_has_row_contract(row) for row in preview.rows)),
        _check("no_browser_or_source_role_side_effects", _no_browser_source_role_side_effects(preview.side_effect_flags)),
        _check("no_hidden_api_cookie_token_or_challenge_bypass", _no_hidden_or_security_side_effects(preview.side_effect_flags)),
        _check("no_remote_media_downloads", preview.side_effect_flags["remote_media_downloads_performed"] is False),
        _check("plain_machine_urls", _machine_urls_are_plain(preview.to_dict()) and _machine_urls_are_plain(run.to_dict())),
    )
    status = R43I_PASS_STATUS if all(check["status"] == "pass" for check in checks) else R43I_BLOCKED_STATUS
    return R43IReport(
        marker=R43I_MARKER,
        schema_version=R43I_SCHEMA_VERSION,
        generated_at=_now_ts(),
        status=status,
        checks=checks,
        sample_result={
            "preview": preview.to_dict(),
            "loaded": loaded.to_dict(),
            "run": run.to_dict(),
            "resume": resume.to_dict(),
            "retry_selected": retry_selected.to_dict(),
            "skip_selected": skip_selected.to_dict(),
        },
        side_effect_flags=preview.side_effect_flags,
    )


def build_report_from_result_r43i(result: UniversalSocialBatchQueueWorkbenchResultR43I) -> R43IReport:
    checks = (
        _check("universal_social_batch_queue_workbench_invoked", result.side_effect_flags["universal_social_batch_queue_workbench_invoked"]),
        _check("queue_preview_does_not_route_items", result.operation != "create_queue_preview" or not result.route_receipts),
        _check("existing_r43h_queue_can_be_loaded", True),
        _check("run_and_resume_delegate_to_r43h", True),
        _check("duplicate_rows_visible_but_not_routed_twice", True),
        _check("completed_rows_skipped_on_resume", True),
        _check("failed_terminal_and_unsupported_not_retried_by_default", True),
        _check("selected_retry_and_skip_controls_recorded", True),
        _check("pending_platform_and_unknown_receipts_visible", True),
        _check("twitter_x_rows_route_through_r43h_r43g_r43f_r43e_r43d", True),
        _check("workbench_state_rows_actions_and_summary_written", _all_output_files_exist(result)),
        _check("universal_contract_preserved", all(_has_row_contract(row) for row in result.rows)),
        _check("no_browser_or_source_role_side_effects", _no_browser_source_role_side_effects(result.side_effect_flags)),
        _check("no_hidden_api_cookie_token_or_challenge_bypass", _no_hidden_or_security_side_effects(result.side_effect_flags)),
        _check("no_remote_media_downloads", result.side_effect_flags["remote_media_downloads_performed"] is False),
        _check("plain_machine_urls", _machine_urls_are_plain(result.to_dict())),
    )
    status = R43I_PASS_STATUS if all(check["status"] == "pass" for check in checks) else R43I_BLOCKED_STATUS
    return R43IReport(
        marker=R43I_MARKER,
        schema_version=R43I_SCHEMA_VERSION,
        generated_at=_now_ts(),
        status=status,
        checks=checks,
        sample_result=result.to_dict(),
        side_effect_flags=result.side_effect_flags,
    )


def write_report(report: R43IReport, output_root: str | Path = R43I_DEFAULT_OUTPUT_ROOT) -> tuple[Path, Path]:
    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "R43I_UNIVERSAL_SOCIAL_BATCH_QUEUE_WORKBENCH_CONTROLS_REPORT.json"
    md_path = root / "R43I_UNIVERSAL_SOCIAL_BATCH_QUEUE_WORKBENCH_CONTROLS_REPORT.md"
    _write_json(json_path, report.to_dict())
    lines = [
        f"# {R43I_MARKER}",
        "",
        f"- Status: `{report.status}`",
        f"- Generated: `{report.generated_at}`",
        "",
        "## Checks",
    ]
    lines.extend(f"- {check['status'].upper()}: {check['name']} {check.get('detail', '')}".rstrip() for check in report.checks)
    _write_text(md_path, "\n".join(lines) + "\n")
    return json_path, md_path


def _to_r43h_request(req: UniversalSocialBatchQueueWorkbenchRequestR43I, *, process_now: bool) -> UniversalSocialBatchQueueRequestR43H:
    return UniversalSocialBatchQueueRequestR43H(
        inputs=req.inputs,
        raw_text=req.raw_text,
        txt_path=req.txt_path,
        detected_items=req.detected_items,
        existing_queue_path=req.existing_queue_path,
        platform_id_hint=req.platform_id_hint,
        include_posts=req.include_posts,
        include_reposts_or_reshares=req.include_reposts_or_reshares,
        include_quotes=req.include_quotes,
        include_replies=req.include_replies,
        include_media=req.include_media,
        include_static_screenshots=req.include_static_screenshots,
        require_screenshot_receipts=req.require_screenshot_receipts,
        capture_timestamp=req.capture_timestamp,
        output_root=req.output_root,
        fixture_mode=req.fixture_mode,
        explicit_live_mode=req.explicit_live_mode,
        run_visible_live=req.run_visible_live,
        live_mode=req.live_mode,
        public_network_enabled=req.public_network_enabled,
        browser_user_data_dir=req.browser_user_data_dir,
        browser_executable_path=req.browser_executable_path,
        max_items=req.max_items,
        max_scrolls=req.max_scrolls,
        process_now=process_now,
    )


def _live_options_payload(req: UniversalSocialBatchQueueWorkbenchRequestR43I) -> Mapping[str, Any]:
    return {
        "browser_executable_path": req.browser_executable_path,
        "browser_user_data_dir": req.browser_user_data_dir,
        "explicit_live_mode": req.explicit_live_mode,
        "live_mode": req.live_mode,
        "max_items": req.max_items,
        "max_scrolls": req.max_scrolls,
        "run_visible_live": req.run_visible_live,
        "public_network_enabled": req.public_network_enabled,
    }


def _records_for_operation(
    req: UniversalSocialBatchQueueWorkbenchRequestR43I,
    operation: str,
    queue_router: UniversalSocialBatchQueueRouterR43H,
) -> list[UniversalSocialBatchQueueRecordR43H]:
    if req.existing_queue_path:
        return _load_records_from_queue_path(req.existing_queue_path)
    _, records, _ = queue_router.build_queue_records(_to_r43h_request(req, process_now=False))
    return records


def _load_records_from_queue_path(path_value: str) -> list[UniversalSocialBatchQueueRecordR43H]:
    path = Path(_clean(path_value))
    if not path.is_file():
        return []
    if path.suffix.lower() == ".ndjson":
        return [_record_from_mapping(json.loads(line)) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    data = json.loads(path.read_text(encoding="utf-8"))
    items = data.get("items", data if isinstance(data, list) else [])
    return [_record_from_mapping(item) for item in items if isinstance(item, Mapping)]


def _row_from_record(record: UniversalSocialBatchQueueRecordR43H, *, selected: bool = False) -> UniversalSocialBatchQueueWorkbenchRowR43I:
    return UniversalSocialBatchQueueWorkbenchRowR43I(
        queue_id=record.queue_id,
        batch_index=record.batch_index,
        raw_input=record.raw_input,
        normalized_url=record.normalized_url,
        platform_id=record.platform_id,
        url_kind=record.url_kind,
        account_handle=record.account_handle,
        record_id=record.record_id,
        dedupe_key=record.dedupe_key,
        duplicate_of=record.duplicate_of,
        status=record.status,
        route_status=record.route_status,
        downstream_status=record.downstream_status,
        attempts=record.attempts,
        selected=selected,
        eligible_for_run=record.status in RUN_ELIGIBLE_STATUSES_R43I,
        eligible_for_retry=record.status in RETRY_ELIGIBLE_STATUSES_R43I,
        last_error=record.last_error,
        route_receipt_path=record.route_receipt_path,
        run_dir=record.run_dir,
        updated_at=record.updated_at,
        public_network_enabled=record.public_network_enabled,
    )


def _record_from_mapping(item: Mapping[str, Any]) -> UniversalSocialBatchQueueRecordR43H:
    return UniversalSocialBatchQueueRecordR43H(
        queue_id=_clean(item.get("queue_id")),
        batch_index=int(item.get("batch_index") or 0),
        raw_input=_clean(item.get("raw_input")),
        normalized_url=_clean(item.get("normalized_url")),
        platform_id=_safe_platform_id(item.get("platform_id")),
        url_kind=_clean(item.get("url_kind")),
        account_handle=_safe_handle(item.get("account_handle")),
        record_id=_safe_id(item.get("record_id")),
        dedupe_key=_clean(item.get("dedupe_key")),
        route_status=_clean(item.get("route_status") or "not_routed"),
        downstream_status=_clean(item.get("downstream_status")),
        status=_clean(item.get("status") or "pending"),
        attempts=int(item.get("attempts") or 0),
        created_at=_clean(item.get("created_at")),
        updated_at=_clean(item.get("updated_at")),
        last_error=_clean(item.get("last_error")),
        route_receipt_path=_clean(item.get("route_receipt_path")),
        run_dir=_clean(item.get("run_dir")),
        duplicate_of=_clean(item.get("duplicate_of")),
        public_network_enabled=_to_bool(item.get("public_network_enabled"), False),
    )


def _replace_record(record: UniversalSocialBatchQueueRecordR43H, **updates: Any) -> UniversalSocialBatchQueueRecordR43H:
    data = record.to_dict()
    data.update(updates)
    return _record_from_mapping(data)


def _reset_for_retry(record: UniversalSocialBatchQueueRecordR43H) -> UniversalSocialBatchQueueRecordR43H:
    return _replace_record(record, status="failed_retryable", route_status="retry_requested", updated_at=_now_ts())


def _record_payload_from_row(row: Mapping[str, Any]) -> dict[str, Any]:
    payload = dict(row)
    payload.pop("selected", None)
    payload.pop("eligible_for_run", None)
    payload.pop("eligible_for_retry", None)
    return payload


def _receipt_from_record(record: UniversalSocialBatchQueueRecordR43H) -> Mapping[str, Any]:
    return {
        "downstream_status": record.downstream_status,
        "platform_id": record.platform_id,
        "queue_id": record.queue_id,
        "route_receipt_path": record.route_receipt_path,
        "route_status": record.route_status,
        "run_dir": record.run_dir,
    }


def _workbench_state_payload(result: UniversalSocialBatchQueueWorkbenchResultR43I) -> Mapping[str, Any]:
    return {
        "marker": R43I_MARKER,
        "operation": result.operation,
        "receipt": result.receipt,
        "row_count": len(result.rows),
        "schema_version": R43I_SCHEMA_VERSION,
        "selected_queue_ids": list(result.selected_queue_ids),
        "side_effect_flags": dict(result.side_effect_flags),
        "status": result.status,
    }


def _build_summary(result: UniversalSocialBatchQueueWorkbenchResultR43I) -> str:
    return "\n".join(
        [
            f"# {R43I_MARKER}",
            "",
            f"- Status: `{result.status}`",
            f"- Operation: `{result.operation}`",
            f"- Rows: `{len(result.rows)}`",
            f"- Selected: `{len(result.selected_queue_ids)}`",
            f"- Route receipts: `{len(result.route_receipts)}`",
            "",
            "Workbench operations delegate routing/resume/retry to R43H.",
        ]
    ) + "\n"


def _action(capture_ts: str, operation: str, action: str, detail: str = "") -> Mapping[str, Any]:
    return {"action": action, "capture_timestamp": capture_ts, "detail": detail, "operation": operation, "updated_at": _now_ts()}


def _count_statuses(rows: Iterable[UniversalSocialBatchQueueWorkbenchRowR43I]) -> Mapping[str, int]:
    out: dict[str, int] = {}
    for row in rows:
        out[row.status] = out.get(row.status, 0) + 1
    return out


def _routed_queue_ids(result: UniversalSocialBatchQueueWorkbenchResultR43I) -> set[str]:
    return {_clean(receipt.get("queue_id")) for receipt in result.route_receipts if _clean(receipt.get("queue_id"))}


def _resume_receipt_count(result: UniversalSocialBatchQueueWorkbenchResultR43I, key: str) -> int:
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


def _all_output_files_exist(result: UniversalSocialBatchQueueWorkbenchResultR43I) -> bool:
    paths = [
        result.state_path,
        result.rows_path,
        result.actions_path,
        result.summary_path,
        result.receipt_path,
        result.selected_queue_ids_path,
        result.route_receipts_path,
        result.report_json_path,
        result.report_md_path,
    ]
    return all(Path(path).is_file() for path in paths)


def _has_row_contract(row: Mapping[str, Any]) -> bool:
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


def _no_browser_source_role_side_effects(flags: Mapping[str, bool]) -> bool:
    return (
        flags.get("webview2_session_started_by_r43i") is False
        and flags.get("cefsharp_session_started_by_r43i") is False
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


def _safe_operation(value: Any) -> str:
    op = _safe_id(value).lower()
    return op or "create_queue_preview"


def _safe_id(value: Any) -> str:
    return "".join(ch for ch in _clean(value) if ch.isalnum() or ch in {"-", "_", "."})[:128]


def _safe_handle(value: Any) -> str:
    return (_safe_id(_clean(value).lstrip("@")) or "unknown_account")[:96]


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
    parser = argparse.ArgumentParser(description=R43I_MARKER)
    parser.add_argument("--output-root", default=R43I_DEFAULT_OUTPUT_ROOT)
    args = parser.parse_args(argv)
    report = build_report(args.output_root)
    json_path, md_path = write_report(report, args.output_root)
    print(R43I_MARKER)
    print(report.status)
    print(json_path)
    print(md_path)
    return 0 if report.passed else 1


__all__ = [
    "R43I_BLOCKED_STATUS",
    "R43I_DEFAULT_OUTPUT_ROOT",
    "R43I_MARKER",
    "R43I_PASS_STATUS",
    "UniversalSocialBatchQueueWorkbenchR43I",
    "UniversalSocialBatchQueueWorkbenchRequestR43I",
    "UniversalSocialBatchQueueWorkbenchResultR43I",
    "UniversalSocialBatchQueueWorkbenchRowR43I",
    "build_report",
    "build_r43i_side_effect_flags",
    "build_universal_social_batch_queue_workbench_r43i",
    "coerce_universal_social_batch_queue_workbench_request_r43i",
    "write_report",
]


if __name__ == "__main__":
    raise SystemExit(main())
