from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
for path in (str(ROOT), str(TOOLS)):
    if path not in sys.path:
        sys.path.insert(0, path)

import run_twitter_timeline_cursor_unattended_controller_v74i as controller


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _make_batch_state(root: Path, *, cycle: int, unique: int, cooldown_epoch: int = 0, stop_reason: str = "soft_page_budget_pause_boundary") -> None:
    out = root / f"examaddaorg_replies_cycle_{cycle:04d}"
    out.mkdir(parents=True, exist_ok=True)
    _write_json(root / "batch_cycle_state.json", {
        "schema_version": "twitter_timeline_cursor_batch_state.v74h",
        "status": "success",
        "task_name": "examaddaorg_replies",
        "batch_output_root": str(root),
        "cycle_count": cycle,
        "latest_output_dir": str(out),
        "latest_pages_count": cycle + 2,
        "latest_entries_count": unique,
        "latest_unique_entries_count": unique,
        "latest_stop_reason": stop_reason,
        "cooldown_until_epoch": cooldown_epoch,
        "cooldown_until_utc": controller._utc_from_epoch(cooldown_epoch),
        "latest_rate_limit_decision": "soft_page_budget_pause",
        "rate_limit_remaining": 48,
    })


def main() -> int:
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        batch_root = tmp / "batch"
        ctrl_root = tmp / "controller"

        # no-wait mode should not call the batch runner while cooldown is active.
        _make_batch_state(batch_root, cycle=3, unique=213, cooldown_epoch=110)
        called = []
        result = controller.run_unattended_controller(
            source_url="https://x.com/examaddaorg",
            batch_output_root=batch_root,
            controller_output_root=ctrl_root,
            task_name="examaddaorg_replies",
            max_controller_cycles=2,
            cycle_live_page_budget=1,
            wait_for_cooldown=False,
            clock=lambda: 100,
            sleeper=lambda seconds: (_ for _ in ()).throw(AssertionError("sleep should not be called")),
            batch_runner=lambda **kwargs: called.append(kwargs) or {},
        )
        assert result["stop_reason"] == "cooldown_pending_no_wait", result
        assert result["controller_cycles_run"] == 0, result
        assert not called, called

        # wait mode should sleep until cooldown, then run one compact V74H cycle.
        sleeps: list[float] = []
        now = {"value": 100.0}

        def fake_sleep(seconds: float) -> None:
            sleeps.append(seconds)
            now["value"] += seconds

        def fake_batch_runner(**kwargs):
            assert kwargs["max_cycles"] == 1, kwargs
            assert kwargs["cycle_live_page_budget"] == 1, kwargs
            assert kwargs["resume_from_output_dir"] == "", kwargs
            _make_batch_state(batch_root, cycle=4, unique=257, cooldown_epoch=int(now["value"] + 900))
            return {
                "schema_version": "twitter_timeline_cursor_batch_cycle.v74h",
                "status": "success",
                "stop_reason": "soft_page_budget_pause_boundary",
                "cycles_run_this_invocation": 1,
                "latest_output_dir": str(batch_root / "examaddaorg_replies_cycle_0004"),
                "latest_unique_entries_count": 257,
                "cooldown_until_utc": controller._utc_from_epoch(int(now["value"] + 900)),
            }

        _make_batch_state(batch_root, cycle=3, unique=213, cooldown_epoch=110)
        result2 = controller.run_unattended_controller(
            source_url="https://x.com/examaddaorg",
            batch_output_root=batch_root,
            controller_output_root=ctrl_root,
            task_name="examaddaorg_replies",
            max_controller_cycles=1,
            cycle_live_page_budget=1,
            max_sleep_seconds=60,
            cooldown_buffer_seconds=5,
            clock=lambda: now["value"],
            sleeper=fake_sleep,
            batch_runner=fake_batch_runner,
        )
        assert sleeps == [15.0], sleeps
        assert result2["controller_cycles_run"] == 1, result2
        assert result2["latest_unique_entries_count"] == 257, result2
        assert result2["stop_reason"] == "controller_max_cycles_reached", result2
        state = json.loads((ctrl_root / "unattended_controller_state.json").read_text(encoding="utf-8"))
        assert state["latest_unique_entries_count"] == 257, state
        assert state["controller_cycles_run"] == 1, state
        runs = (ctrl_root / "unattended_controller_runs.jsonl").read_text(encoding="utf-8")
        assert "soft_page_budget_pause_boundary" in runs, runs
        events = (ctrl_root / "unattended_controller_events.jsonl").read_text(encoding="utf-8")
        assert "cooldown_pending" in events, events

        # sleep cap should refuse unattended waiting if the wait is too large.
        _make_batch_state(batch_root, cycle=4, unique=257, cooldown_epoch=500)
        result3 = controller.run_unattended_controller(
            source_url="https://x.com/examaddaorg",
            batch_output_root=batch_root,
            controller_output_root=ctrl_root,
            task_name="examaddaorg_replies",
            max_controller_cycles=1,
            max_sleep_seconds=30,
            cooldown_buffer_seconds=0,
            clock=lambda: 100,
            sleeper=lambda seconds: (_ for _ in ()).throw(AssertionError("sleep should not be called")),
            batch_runner=lambda **kwargs: (_ for _ in ()).throw(AssertionError("batch should not be called")),
        )
        assert result3["stop_reason"] == "cooldown_wait_exceeds_cap", result3
        assert result3["status"] == "needs_review", result3

    print("assert_twitter_cursor_unattended_controller_v74i OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
