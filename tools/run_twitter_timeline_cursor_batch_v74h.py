from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from twitter_timeline_cursor_scheduler import run_twitter_cursor_scheduler

BATCH_SCHEMA_VERSION = "twitter_timeline_cursor_batch_cycle.v74h"
BATCH_STATE_SCHEMA_VERSION = "twitter_timeline_cursor_batch_state.v74h"

PAUSE_OR_TERMINAL_REASONS = {
    "resume_cooldown_not_elapsed",
    "soft_page_budget_pause_boundary",
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


def _load_output_counts(output_dir: str | Path) -> dict[str, Any]:
    root = Path(output_dir)
    state = _read_json(root / "cursor_scheduler_state.json")
    rate = _read_json(root / "cursor_rate_limit_state.json")
    templates = _read_json(root / "cursor_request_templates.json")
    return {
        "pages_count": _int(state.get("pages_count"), 0),
        "entries_count": _int(state.get("entries_count"), 0),
        "unique_entries_count": _int(state.get("unique_entries_count"), 0),
        "stop_reason": str(state.get("stop_reason") or ""),
        "next_cursor_url": str(templates.get("next_cursor_url") or state.get("next_cursor_url") or ""),
        "cooldown_until_epoch": _int(rate.get("cooldown_until_epoch"), 0),
        "cooldown_until_utc": str(rate.get("cooldown_until_utc") or ""),
        "rate_limit_remaining": rate.get("rate_limit_remaining"),
        "latest_rate_limit_decision": str(rate.get("latest_decision") or state.get("latest_rate_limit_decision") or ""),
    }


def _state_path(batch_output_root: str | Path) -> Path:
    return Path(batch_output_root) / "batch_cycle_state.json"


def _runs_path(batch_output_root: str | Path) -> Path:
    return Path(batch_output_root) / "batch_cycle_runs.jsonl"


def _latest_resume_dir(
    *,
    batch_output_root: str | Path,
    resume_from_output_dir: str | Path = "",
) -> str:
    state = _read_json(_state_path(batch_output_root))
    latest = str(state.get("latest_output_dir") or "")
    if latest:
        return latest
    return str(resume_from_output_dir or "")


def _cycle_output_dir(batch_output_root: str | Path, task_name: str, cycle_number: int) -> Path:
    safe_name = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in str(task_name or "twitter_cursor_batch")).strip("_")
    return Path(batch_output_root) / f"{safe_name}_cycle_{cycle_number:04d}"


def _next_cycle_number(batch_output_root: str | Path) -> int:
    state = _read_json(_state_path(batch_output_root))
    return _int(state.get("cycle_count"), 0) + 1


def _build_batch_state(
    *,
    batch_output_root: str | Path,
    task_name: str,
    latest_output_dir: str,
    latest_result: Mapping[str, Any] | None,
    stop_reason: str,
    cycle_count: int,
    status: str,
) -> dict[str, Any]:
    counts = _load_output_counts(latest_output_dir) if latest_output_dir else {}
    now = int(time.time())
    return {
        "schema_version": BATCH_STATE_SCHEMA_VERSION,
        "status": status,
        "task_name": task_name,
        "batch_output_root": str(batch_output_root),
        "cycle_count": int(cycle_count),
        "latest_output_dir": str(latest_output_dir or ""),
        "latest_result": dict(latest_result or {}),
        "latest_stop_reason": stop_reason,
        "latest_pages_count": counts.get("pages_count", 0),
        "latest_entries_count": counts.get("entries_count", 0),
        "latest_unique_entries_count": counts.get("unique_entries_count", 0),
        "latest_next_cursor_url": counts.get("next_cursor_url", ""),
        "cooldown_until_epoch": counts.get("cooldown_until_epoch", 0),
        "cooldown_until_utc": counts.get("cooldown_until_utc", ""),
        "rate_limit_remaining": counts.get("rate_limit_remaining"),
        "latest_rate_limit_decision": counts.get("latest_rate_limit_decision", ""),
        "updated_epoch": now,
    }


def run_batch_cycles(
    *,
    source_url: str,
    batch_output_root: str | Path,
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
    max_cycles: int = 1,
    cycle_live_page_budget: int = 1,
    initial_max_pages: int = 2,
    max_records: int = 0,
    page_delay_ms: int = 4500,
    page_jitter_ms: int = 1500,
    max_runtime_minutes: float = 0.0,
    rate_limit_safety_floor: int = 1,
    max_transient_retries: int = 2,
    transient_base_delay_ms: int = 15000,
    auth_probe_scroll_steps: int = 0,
    auth_probe_scroll_pixels: int = 900,
    auth_probe_wait_ms: int = 1500,
    ignore_resume_cooldown: bool = False,
) -> dict[str, Any]:
    root = Path(batch_output_root)
    root.mkdir(parents=True, exist_ok=True)
    runs_path = _runs_path(root)
    state_path = _state_path(root)

    latest_output_dir = _latest_resume_dir(batch_output_root=root, resume_from_output_dir=resume_from_output_dir)
    cycle_number = _next_cycle_number(root)
    max_cycles = max(1, int(max_cycles))
    cycle_live_page_budget = max(1, int(cycle_live_page_budget))
    results: list[dict[str, Any]] = []
    final_stop_reason = "not_started"
    status = "success"

    for _ in range(max_cycles):
        output_dir = _cycle_output_dir(root, task_name, cycle_number)
        previous_counts = _load_output_counts(latest_output_dir) if latest_output_dir else {}
        previous_pages = _int(previous_counts.get("pages_count"), 0)
        if latest_output_dir:
            resume_arg = latest_output_dir
            seed_arg = ""
            har_arg = ""
            target_max_pages = previous_pages + cycle_live_page_budget
            cycle_mode = "resume_from_previous_output"
        else:
            resume_arg = ""
            seed_arg = str(seed_capture_dir or "")
            har_arg = str(har_path or "") if not seed_arg else ""
            target_max_pages = max(1, int(initial_max_pages))
            cycle_mode = "seed_capture_start" if seed_arg else ("har_start" if har_arg else "live_scroll_start")

        result = run_twitter_cursor_scheduler(
            source_url=source_url,
            output_dir=output_dir,
            live=live,
            browser_user_data_dir=browser_user_data_dir,
            reuse_existing_profile=reuse_existing_profile,
            seed_capture_dir=seed_arg,
            har_path=har_arg,
            resume_from_output_dir=resume_arg,
            profile_tab=profile_tab,
            headless=headless,
            timeout_ms=timeout_ms,
            initial_wait_ms=initial_wait_ms,
            max_pages=target_max_pages,
            max_records=max_records,
            page_delay_ms=page_delay_ms,
            page_jitter_ms=page_jitter_ms,
            max_runtime_minutes=max_runtime_minutes,
            rate_limit_safety_floor=rate_limit_safety_floor,
            soft_page_budget=cycle_live_page_budget,
            max_transient_retries=max_transient_retries,
            transient_base_delay_ms=transient_base_delay_ms,
            auth_probe_scroll_steps=auth_probe_scroll_steps,
            auth_probe_scroll_pixels=auth_probe_scroll_pixels,
            auth_probe_wait_ms=auth_probe_wait_ms,
            ignore_resume_cooldown=ignore_resume_cooldown,
        )
        result_map = result.to_dict() if hasattr(result, "to_dict") else dict(result)  # type: ignore[arg-type]
        final_stop_reason = str(result_map.get("stop_reason") or "")
        latest_output_dir = str(output_dir)
        run_row = {
            "schema_version": BATCH_SCHEMA_VERSION,
            "cycle_number": cycle_number,
            "cycle_mode": cycle_mode,
            "previous_output_dir": str(resume_arg or ""),
            "output_dir": str(output_dir),
            "target_max_pages": target_max_pages,
            "cycle_live_page_budget": cycle_live_page_budget,
            "result": result_map,
        }
        _append_jsonl(runs_path, run_row)
        results.append(run_row)
        batch_state = _build_batch_state(
            batch_output_root=root,
            task_name=task_name,
            latest_output_dir=latest_output_dir,
            latest_result=result_map,
            stop_reason=final_stop_reason,
            cycle_count=cycle_number,
            status=status,
        )
        _write_json(state_path, batch_state)
        cycle_number += 1

        if final_stop_reason in PAUSE_OR_TERMINAL_REASONS:
            break
        if result_map.get("status") not in {"success", "needs_review", "planned"}:
            status = "needs_review"
            break

    final_state = _read_json(state_path)
    return {
        "schema_version": BATCH_SCHEMA_VERSION,
        "status": status,
        "batch_output_root": str(root),
        "state_path": str(state_path),
        "runs_path": str(runs_path),
        "cycles_run_this_invocation": len(results),
        "latest_output_dir": str(latest_output_dir or ""),
        "stop_reason": final_stop_reason,
        "latest_unique_entries_count": final_state.get("latest_unique_entries_count", 0),
        "cooldown_until_utc": final_state.get("cooldown_until_utc", ""),
        "results": results,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run one or more conservative Twitter/X cursor resume cycles. "
            "The tool writes durable batch state and is safe to rerun after cooldown."
        )
    )
    parser.add_argument("--source-url", required=True)
    parser.add_argument("--batch-output-root", required=True)
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
    parser.add_argument("--max-cycles", type=int, default=1)
    parser.add_argument("--cycle-live-page-budget", type=int, default=1)
    parser.add_argument("--initial-max-pages", type=int, default=2)
    parser.add_argument("--max-records", type=int, default=0)
    parser.add_argument("--page-delay-ms", type=int, default=4500)
    parser.add_argument("--page-jitter-ms", type=int, default=1500)
    parser.add_argument("--max-runtime-minutes", type=float, default=0.0)
    parser.add_argument("--rate-limit-safety-floor", type=int, default=1)
    parser.add_argument("--max-transient-retries", type=int, default=2)
    parser.add_argument("--transient-base-delay-ms", type=int, default=15000)
    parser.add_argument("--auth-probe-scroll-steps", type=int, default=0)
    parser.add_argument("--auth-probe-scroll-pixels", type=int, default=900)
    parser.add_argument("--auth-probe-wait-ms", type=int, default=1500)
    parser.add_argument("--ignore-resume-cooldown", action="store_true")
    args = parser.parse_args(argv)

    result = run_batch_cycles(
        source_url=args.source_url,
        batch_output_root=args.batch_output_root,
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
        max_cycles=args.max_cycles,
        cycle_live_page_budget=args.cycle_live_page_budget,
        initial_max_pages=args.initial_max_pages,
        max_records=args.max_records,
        page_delay_ms=args.page_delay_ms,
        page_jitter_ms=args.page_jitter_ms,
        max_runtime_minutes=args.max_runtime_minutes,
        rate_limit_safety_floor=args.rate_limit_safety_floor,
        max_transient_retries=args.max_transient_retries,
        transient_base_delay_ms=args.transient_base_delay_ms,
        auth_probe_scroll_steps=args.auth_probe_scroll_steps,
        auth_probe_scroll_pixels=args.auth_probe_scroll_pixels,
        auth_probe_wait_ms=args.auth_probe_wait_ms,
        ignore_resume_cooldown=args.ignore_resume_cooldown,
    )
    print(json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True))
    return 0 if result.get("status") in {"success", "needs_review", "planned"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
