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

import run_twitter_timeline_cursor_batch_v74h as batch_tool


class FakeResult:
    def __init__(self, **values):
        self.values = values

    def to_dict(self):
        return dict(self.values)


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def _make_output(root: Path, *, pages: int, unique: int, cursor: str, cooldown_epoch: int = 0, cooldown_utc: str = "") -> None:
    _write_json(root / "cursor_scheduler_state.json", {
        "schema_version": "twitter_timeline_cursor_state.v74g",
        "source_url": "https://x.com/examaddaorg",
        "canonical_url": "https://x.com/examaddaorg/with_replies",
        "requested_profile_tab": "replies",
        "pages_count": pages,
        "entries_count": unique,
        "unique_entries_count": unique,
        "stop_reason": "soft_page_budget_pause_boundary",
        "next_cursor_url": f"https://x.com/i/api/graphql/q/UserRepliesTimeline?variables={{\"cursor\":\"{cursor}\"}}",
        "latest_rate_limit_decision": "soft_page_budget_pause",
    })
    _write_json(root / "cursor_request_templates.json", {
        "next_cursor_url": f"https://x.com/i/api/graphql/q/UserRepliesTimeline?variables={{\"cursor\":\"{cursor}\"}}",
        "request_templates": [],
    })
    _write_json(root / "cursor_rate_limit_state.json", {
        "schema_version": "twitter_rate_limit_state.v74e",
        "cooldown_until_epoch": cooldown_epoch,
        "cooldown_until_utc": cooldown_utc,
        "latest_decision": "soft_page_budget_pause",
        "rate_limit_remaining": 48,
    })
    _write_jsonl(root / "cursor_pages.jsonl", [{"page_number": i + 1, "cursor_out": f"CURSOR_{i+1}"} for i in range(pages)])
    _write_jsonl(root / "cursor_entries.jsonl", [{"status_id": str(1000 + i)} for i in range(unique)])
    _write_jsonl(root / "cursor_errors.jsonl", [])
    _write_json(root / "cursor_export_manifest.json", {"canonical_url": "https://x.com/examaddaorg/with_replies"})


def main() -> int:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        previous = root / "previous_v74g"
        batch_root = root / "batch"
        _make_output(previous, pages=3, unique=124, cursor="CURSOR_THREE")

        calls: list[dict] = []

        def fake_scheduler(**kwargs):
            calls.append(dict(kwargs))
            out = Path(kwargs["output_dir"])
            resume = Path(kwargs["resume_from_output_dir"])
            prev_state = json.loads((resume / "cursor_scheduler_state.json").read_text(encoding="utf-8"))
            assert kwargs["max_pages"] == int(prev_state["pages_count"]) + 1, kwargs
            assert kwargs["soft_page_budget"] == 1, kwargs
            _make_output(out, pages=int(prev_state["pages_count"]) + 1, unique=int(prev_state["unique_entries_count"]) + 40, cursor="CURSOR_NEXT")
            return FakeResult(
                schema_version="twitter_timeline_cursor_scheduler.v74g",
                status="success",
                source_url=kwargs["source_url"],
                canonical_url="https://x.com/examaddaorg/with_replies",
                output_dir=str(out),
                pages_count=int(prev_state["pages_count"]) + 1,
                entries_count=int(prev_state["unique_entries_count"]) + 40,
                unique_entries_count=int(prev_state["unique_entries_count"]) + 40,
                stop_reason="soft_page_budget_pause_boundary",
                next_cursor_url="https://x.com/i/api/graphql/q/UserRepliesTimeline?variables={\"cursor\":\"CURSOR_NEXT\"}",
                warnings=["rate_limit_decision:soft_page_budget_pause"],
                errors=[],
            )

        original = batch_tool.run_twitter_cursor_scheduler
        batch_tool.run_twitter_cursor_scheduler = fake_scheduler
        try:
            result = batch_tool.run_batch_cycles(
                source_url="https://x.com/examaddaorg",
                batch_output_root=batch_root,
                task_name="examaddaorg_replies",
                live=True,
                browser_user_data_dir="C:/fake/profile",
                reuse_existing_profile=True,
                resume_from_output_dir=previous,
                max_cycles=3,
                cycle_live_page_budget=1,
                profile_tab="replies",
            )
        finally:
            batch_tool.run_twitter_cursor_scheduler = original

        assert result["status"] == "success", result
        assert result["cycles_run_this_invocation"] == 1, result
        assert result["latest_unique_entries_count"] == 164, result
        assert result["stop_reason"] == "soft_page_budget_pause_boundary", result
        assert calls and calls[0]["resume_from_output_dir"] == str(previous), calls
        assert calls[0]["max_pages"] == 4, calls
        state = json.loads((batch_root / "batch_cycle_state.json").read_text(encoding="utf-8"))
        assert state["cycle_count"] == 1, state
        assert state["latest_unique_entries_count"] == 164, state
        assert Path(state["latest_output_dir"]).name == "examaddaorg_replies_cycle_0001", state
        runs = (batch_root / "batch_cycle_runs.jsonl").read_text(encoding="utf-8")
        assert "resume_from_previous_output" in runs, runs

        # Second invocation should discover the latest output from batch state
        # and use it as the resume input without the caller repeating it.
        calls.clear()
        batch_tool.run_twitter_cursor_scheduler = fake_scheduler
        try:
            result2 = batch_tool.run_batch_cycles(
                source_url="https://x.com/examaddaorg",
                batch_output_root=batch_root,
                task_name="examaddaorg_replies",
                live=True,
                browser_user_data_dir="C:/fake/profile",
                reuse_existing_profile=True,
                max_cycles=1,
                cycle_live_page_budget=1,
                profile_tab="replies",
            )
        finally:
            batch_tool.run_twitter_cursor_scheduler = original
        assert result2["latest_unique_entries_count"] == 204, result2
        assert calls and Path(calls[0]["resume_from_output_dir"]).name == "examaddaorg_replies_cycle_0001", calls
        assert calls[0]["max_pages"] == 5, calls
        state2 = json.loads((batch_root / "batch_cycle_state.json").read_text(encoding="utf-8"))
        assert state2["cycle_count"] == 2, state2
        assert Path(state2["latest_output_dir"]).name == "examaddaorg_replies_cycle_0002", state2

    print("assert_twitter_cursor_batch_cycle_v74h OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
