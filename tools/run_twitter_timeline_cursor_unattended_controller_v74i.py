from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
for _path in (str(ROOT), str(TOOLS)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

import run_twitter_timeline_cursor_batch_v74h as batch_tool

CONTROLLER_SCHEMA_VERSION = "twitter_timeline_cursor_unattended_controller.v74i"
CONTROLLER_STATE_SCHEMA_VERSION = "twitter_timeline_cursor_unattended_state.v74i"

CONTINUABLE_REASONS = {
    "soft_page_budget_pause_boundary",
    "resume_cooldown_not_elapsed",
    "max_pages_reached",
}

STOP_NOW_REASONS = {
    "rate_limited_pause_boundary",
    "auth_or_access_boundary",
    "transient_retry_pause_boundary",
    "no_bottom_cursor_observed",
    "no_seed_bottom_cursor_observed",
    "resume_next_cursor_url_missing",
    "no_timeline_seed_records_found",
    "no_initial_timeline_response_found",
    "no_new_records_boundary",
    "repeated_cursor_boundary",
    "max_records_reached",
    "cursor_scheduler_exception",
    "cursor_resume_exception",
}


def _read_json(path: str | Path) -> dict[str, Any]:
    p = Path(path)
    if not p.exists():
        return {}
    try:
        data = json.loads(p.read_text(encoding="utf-8", errors="replace"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def _write_json(path: str | Path, data: Mapping[str, Any]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(dict(data), indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")


def _append_jsonl(path: str | Path, data: Mapping[str, Any]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(dict(data), ensure_ascii=False, sort_keys=True) + "\n")


def _int(value: Any, default: int = 0) -> int:
    try:
        if value is None or value == "":
            return int(default)
        return int(float(value))
    except Exception:
        return int(default)


def _float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return float(default)
        return float(value)
    except Exception:
        return float(default)


def _utc_from_epoch(epoch: int) -> str:
    if not epoch:
        return ""
    try:
        return datetime.fromtimestamp(int(epoch), tz=timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    except Exception:
        return ""


def _local_from_epoch(epoch: int) -> str:
    if not epoch:
        return ""
    try:
        return datetime.fromtimestamp(int(epoch)).astimezone().replace(microsecond=0).isoformat()
    except Exception:
        return ""


def _state_path(controller_output_root: str | Path) -> Path:
    return Path(controller_output_root) / "unattended_controller_state.json"


def _runs_path(controller_output_root: str | Path) -> Path:
    return Path(controller_output_root) / "unattended_controller_runs.jsonl"


def _events_path(controller_output_root: str | Path) -> Path:
    return Path(controller_output_root) / "unattended_controller_events.jsonl"


def _batch_state_path(batch_output_root: str | Path) -> Path:
    return Path(batch_output_root) / "batch_cycle_state.json"


def _compact_batch_state(batch_output_root: str | Path) -> dict[str, Any]:
    state = _read_json(_batch_state_path(batch_output_root))
    cooldown_epoch = _int(state.get("cooldown_until_epoch"), 0)
    return {
        "batch_output_root": str(batch_output_root),
        "cycle_count": _int(state.get("cycle_count"), 0),
        "latest_output_dir": str(state.get("latest_output_dir") or ""),
        "latest_pages_count": _int(state.get("latest_pages_count"), 0),
        "latest_entries_count": _int(state.get("latest_entries_count"), 0),
        "latest_unique_entries_count": _int(state.get("latest_unique_entries_count"), 0),
        "latest_stop_reason": str(state.get("latest_stop_reason") or ""),
        "latest_rate_limit_decision": str(state.get("latest_rate_limit_decision") or ""),
        "rate_limit_remaining": state.get("rate_limit_remaining"),
        "cooldown_until_epoch": cooldown_epoch,
        "cooldown_until_utc": str(state.get("cooldown_until_utc") or _utc_from_epoch(cooldown_epoch)),
        "cooldown_until_local": _local_from_epoch(cooldown_epoch),
        "status": str(state.get("status") or ""),
    }


def _compact_cycle_result(result: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": str(result.get("schema_version") or ""),
        "status": str(result.get("status") or ""),
        "stop_reason": str(result.get("stop_reason") or ""),
        "cycles_run_this_invocation": _int(result.get("cycles_run_this_invocation"), 0),
        "latest_output_dir": str(result.get("latest_output_dir") or ""),
        "latest_unique_entries_count": _int(result.get("latest_unique_entries_count"), 0),
        "cooldown_until_utc": str(result.get("cooldown_until_utc") or ""),
    }


def _build_controller_state(
    *,
    controller_output_root: str | Path,
    batch_output_root: str | Path,
    task_name: str,
    status: str,
    stop_reason: str,
    controller_cycles_run: int,
    max_controller_cycles: int,
    started_epoch: int,
    latest_batch_state: Mapping[str, Any],
    last_cycle_result: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    now = int(time.time())
    return {
        "schema_version": CONTROLLER_STATE_SCHEMA_VERSION,
        "status": status,
        "task_name": task_name,
        "controller_output_root": str(controller_output_root),
        "batch_output_root": str(batch_output_root),
        "stop_reason": stop_reason,
        "controller_cycles_run": int(controller_cycles_run),
        "max_controller_cycles": int(max_controller_cycles),
        "started_epoch": int(started_epoch),
        "updated_epoch": now,
        "elapsed_seconds": max(0, now - int(started_epoch)),
        "latest_batch_state": dict(latest_batch_state),
        "last_cycle_result": dict(last_cycle_result or {}),
        "latest_unique_entries_count": _int(latest_batch_state.get("latest_unique_entries_count"), 0),
        "latest_output_dir": str(latest_batch_state.get("latest_output_dir") or ""),
        "latest_stop_reason": str(latest_batch_state.get("latest_stop_reason") or ""),
        "cooldown_until_epoch": _int(latest_batch_state.get("cooldown_until_epoch"), 0),
        "cooldown_until_utc": str(latest_batch_state.get("cooldown_until_utc") or ""),
        "cooldown_until_local": str(latest_batch_state.get("cooldown_until_local") or ""),
    }


def _seconds_until_cooldown(batch_state: Mapping[str, Any], now_epoch: int, buffer_seconds: int) -> int:
    cooldown_epoch = _int(batch_state.get("cooldown_until_epoch"), 0)
    if cooldown_epoch <= 0:
        return 0
    return max(0, cooldown_epoch - int(now_epoch) + max(0, int(buffer_seconds)))


def run_unattended_controller(
    *,
    source_url: str,
    batch_output_root: str | Path,
    controller_output_root: str | Path = "",
    task_name: str = "twitter_cursor_batch",
    live: bool = True,
    browser_user_data_dir: str | Path = "",
    reuse_existing_profile: bool = False,
    seed_capture_dir: str | Path = "",
    har_path: str | Path = "",
    resume_from_output_dir: str | Path = "",
    profile_tab: str = "replies",
    headless: bool = False,
    timeout_ms: int = 120000,
    initial_wait_ms: int = 4500,
    max_controller_cycles: int = 3,
    cycle_live_page_budget: int = 1,
    initial_max_pages: int = 2,
    max_records: int = 0,
    page_delay_ms: int = 4500,
    page_jitter_ms: int = 1500,
    max_runtime_minutes: float = 60.0,
    max_sleep_seconds: int = 1200,
    cooldown_buffer_seconds: int = 10,
    rate_limit_safety_floor: int = 1,
    max_transient_retries: int = 2,
    transient_base_delay_ms: int = 15000,
    auth_probe_scroll_steps: int = 0,
    auth_probe_scroll_pixels: int = 900,
    auth_probe_wait_ms: int = 1500,
    wait_for_cooldown: bool = True,
    ignore_resume_cooldown: bool = False,
    clock: Callable[[], float] | None = None,
    sleeper: Callable[[float], None] | None = None,
    batch_runner: Callable[..., Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    clock = clock or time.time
    sleeper = sleeper or time.sleep
    batch_runner = batch_runner or batch_tool.run_batch_cycles
    root = Path(controller_output_root or batch_output_root)
    root.mkdir(parents=True, exist_ok=True)
    state_path = _state_path(root)
    runs_path = _runs_path(root)
    events_path = _events_path(root)
    started_epoch = int(clock())
    deadline_epoch = 0
    if _float(max_runtime_minutes, 0.0) > 0:
        deadline_epoch = started_epoch + int(float(max_runtime_minutes) * 60)

    max_controller_cycles = max(1, int(max_controller_cycles))
    controller_cycles_run = 0
    status = "success"
    stop_reason = "not_started"
    last_cycle_result: dict[str, Any] = {}
    latest_batch_state = _compact_batch_state(batch_output_root)

    while controller_cycles_run < max_controller_cycles:
        now_epoch = int(clock())
        latest_batch_state = _compact_batch_state(batch_output_root)
        wait_seconds = _seconds_until_cooldown(latest_batch_state, now_epoch, cooldown_buffer_seconds)
        if wait_seconds > 0 and not ignore_resume_cooldown:
            wait_event = {
                "schema_version": CONTROLLER_SCHEMA_VERSION,
                "event": "cooldown_pending",
                "now_epoch": now_epoch,
                "wait_seconds": wait_seconds,
                "cooldown_until_epoch": _int(latest_batch_state.get("cooldown_until_epoch"), 0),
                "cooldown_until_utc": str(latest_batch_state.get("cooldown_until_utc") or ""),
                "cooldown_until_local": str(latest_batch_state.get("cooldown_until_local") or ""),
            }
            _append_jsonl(events_path, wait_event)
            if not wait_for_cooldown:
                stop_reason = "cooldown_pending_no_wait"
                break
            if max_sleep_seconds > 0 and wait_seconds > int(max_sleep_seconds):
                stop_reason = "cooldown_wait_exceeds_cap"
                status = "needs_review"
                break
            if deadline_epoch and now_epoch + wait_seconds > deadline_epoch:
                stop_reason = "controller_runtime_cap_before_cooldown"
                status = "needs_review"
                break
            sleeper(float(wait_seconds))

        now_epoch = int(clock())
        if deadline_epoch and now_epoch >= deadline_epoch:
            stop_reason = "controller_runtime_cap_boundary"
            status = "needs_review"
            break

        result = batch_runner(
            source_url=source_url,
            batch_output_root=batch_output_root,
            task_name=task_name,
            live=live,
            browser_user_data_dir=browser_user_data_dir,
            reuse_existing_profile=reuse_existing_profile,
            seed_capture_dir=seed_capture_dir,
            har_path=har_path,
            resume_from_output_dir=resume_from_output_dir,
            profile_tab=profile_tab,
            headless=headless,
            timeout_ms=timeout_ms,
            initial_wait_ms=initial_wait_ms,
            max_cycles=1,
            cycle_live_page_budget=cycle_live_page_budget,
            initial_max_pages=initial_max_pages,
            max_records=max_records,
            page_delay_ms=page_delay_ms,
            page_jitter_ms=page_jitter_ms,
            max_runtime_minutes=0.0,
            rate_limit_safety_floor=rate_limit_safety_floor,
            max_transient_retries=max_transient_retries,
            transient_base_delay_ms=transient_base_delay_ms,
            auth_probe_scroll_steps=auth_probe_scroll_steps,
            auth_probe_scroll_pixels=auth_probe_scroll_pixels,
            auth_probe_wait_ms=auth_probe_wait_ms,
            ignore_resume_cooldown=ignore_resume_cooldown,
        )
        result_map = result.to_dict() if hasattr(result, "to_dict") else dict(result)  # type: ignore[arg-type]
        last_cycle_result = _compact_cycle_result(result_map)
        controller_cycles_run += 1
        stop_reason = str(result_map.get("stop_reason") or "")
        latest_batch_state = _compact_batch_state(batch_output_root)
        run_row = {
            "schema_version": CONTROLLER_SCHEMA_VERSION,
            "controller_cycle_number": controller_cycles_run,
            "stop_reason": stop_reason,
            "batch_result": last_cycle_result,
            "latest_batch_state": latest_batch_state,
            "timestamp_epoch": int(clock()),
        }
        _append_jsonl(runs_path, run_row)
        state = _build_controller_state(
            controller_output_root=root,
            batch_output_root=batch_output_root,
            task_name=task_name,
            status=status,
            stop_reason=stop_reason,
            controller_cycles_run=controller_cycles_run,
            max_controller_cycles=max_controller_cycles,
            started_epoch=started_epoch,
            latest_batch_state=latest_batch_state,
            last_cycle_result=last_cycle_result,
        )
        _write_json(state_path, state)

        if stop_reason in STOP_NOW_REASONS:
            if stop_reason != "max_records_reached":
                status = "needs_review"
            break
        if result_map.get("status") not in {"success", "needs_review", "planned"}:
            status = "needs_review"
            stop_reason = "batch_status_not_success"
            break
        if stop_reason not in CONTINUABLE_REASONS:
            break
        if controller_cycles_run >= max_controller_cycles:
            stop_reason = "controller_max_cycles_reached"
            break

    latest_batch_state = _compact_batch_state(batch_output_root)
    final_state = _build_controller_state(
        controller_output_root=root,
        batch_output_root=batch_output_root,
        task_name=task_name,
        status=status,
        stop_reason=stop_reason,
        controller_cycles_run=controller_cycles_run,
        max_controller_cycles=max_controller_cycles,
        started_epoch=started_epoch,
        latest_batch_state=latest_batch_state,
        last_cycle_result=last_cycle_result,
    )
    _write_json(state_path, final_state)
    return {
        "schema_version": CONTROLLER_SCHEMA_VERSION,
        "status": status,
        "controller_output_root": str(root),
        "state_path": str(state_path),
        "runs_path": str(runs_path),
        "events_path": str(events_path),
        "stop_reason": stop_reason,
        "controller_cycles_run": controller_cycles_run,
        "max_controller_cycles": max_controller_cycles,
        "latest_unique_entries_count": latest_batch_state.get("latest_unique_entries_count", 0),
        "latest_output_dir": latest_batch_state.get("latest_output_dir", ""),
        "latest_stop_reason": latest_batch_state.get("latest_stop_reason", ""),
        "cooldown_until_utc": latest_batch_state.get("cooldown_until_utc", ""),
        "cooldown_until_local": latest_batch_state.get("cooldown_until_local", ""),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run a capped unattended-safe Twitter/X cursor batch controller. "
            "It waits for saved cooldowns, runs one V74H budgeted cycle at a time, "
            "and stops on hard limits or unsafe boundaries."
        )
    )
    parser.add_argument("--source-url", required=True)
    parser.add_argument("--batch-output-root", required=True)
    parser.add_argument("--controller-output-root", default="")
    parser.add_argument("--task-name", default="twitter_cursor_batch")
    parser.add_argument("--live", action="store_true", default=True)
    parser.add_argument("--seed-capture-dir", default="")
    parser.add_argument("--har-path", default="")
    parser.add_argument("--resume-from-output-dir", default="")
    parser.add_argument("--browser-user-data-dir", default="")
    parser.add_argument("--reuse-existing-profile", action="store_true")
    parser.add_argument("--profile-tab", default="replies", choices=("default", "tweets", "replies", "tweets_replies", "tweets_and_replies", "media", "likes"))
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--timeout-ms", type=int, default=120000)
    parser.add_argument("--initial-wait-ms", type=int, default=4500)
    parser.add_argument("--max-controller-cycles", type=int, default=3)
    parser.add_argument("--cycle-live-page-budget", type=int, default=1)
    parser.add_argument("--initial-max-pages", type=int, default=2)
    parser.add_argument("--max-records", type=int, default=0)
    parser.add_argument("--page-delay-ms", type=int, default=4500)
    parser.add_argument("--page-jitter-ms", type=int, default=1500)
    parser.add_argument("--max-runtime-minutes", type=float, default=60.0)
    parser.add_argument("--max-sleep-seconds", type=int, default=1200)
    parser.add_argument("--cooldown-buffer-seconds", type=int, default=10)
    parser.add_argument("--rate-limit-safety-floor", type=int, default=1)
    parser.add_argument("--max-transient-retries", type=int, default=2)
    parser.add_argument("--transient-base-delay-ms", type=int, default=15000)
    parser.add_argument("--auth-probe-scroll-steps", type=int, default=0)
    parser.add_argument("--auth-probe-scroll-pixels", type=int, default=900)
    parser.add_argument("--auth-probe-wait-ms", type=int, default=1500)
    parser.add_argument("--no-wait", action="store_true", help="Do not sleep for cooldown; report cooldown_pending_no_wait instead.")
    parser.add_argument("--ignore-resume-cooldown", action="store_true")
    args = parser.parse_args(argv)

    result = run_unattended_controller(
        source_url=args.source_url,
        batch_output_root=args.batch_output_root,
        controller_output_root=args.controller_output_root,
        task_name=args.task_name,
        live=args.live,
        browser_user_data_dir=args.browser_user_data_dir,
        reuse_existing_profile=args.reuse_existing_profile,
        seed_capture_dir=args.seed_capture_dir,
        har_path=args.har_path,
        resume_from_output_dir=args.resume_from_output_dir,
        profile_tab=args.profile_tab,
        headless=args.headless,
        timeout_ms=args.timeout_ms,
        initial_wait_ms=args.initial_wait_ms,
        max_controller_cycles=args.max_controller_cycles,
        cycle_live_page_budget=args.cycle_live_page_budget,
        initial_max_pages=args.initial_max_pages,
        max_records=args.max_records,
        page_delay_ms=args.page_delay_ms,
        page_jitter_ms=args.page_jitter_ms,
        max_runtime_minutes=args.max_runtime_minutes,
        max_sleep_seconds=args.max_sleep_seconds,
        cooldown_buffer_seconds=args.cooldown_buffer_seconds,
        rate_limit_safety_floor=args.rate_limit_safety_floor,
        max_transient_retries=args.max_transient_retries,
        transient_base_delay_ms=args.transient_base_delay_ms,
        auth_probe_scroll_steps=args.auth_probe_scroll_steps,
        auth_probe_scroll_pixels=args.auth_probe_scroll_pixels,
        auth_probe_wait_ms=args.auth_probe_wait_ms,
        wait_for_cooldown=not args.no_wait,
        ignore_resume_cooldown=args.ignore_resume_cooldown,
    )
    print(json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True))
    return 0 if result.get("status") in {"success", "needs_review", "planned"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
