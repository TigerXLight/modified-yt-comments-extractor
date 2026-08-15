from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from twitter_browser_timeline_pagination import run_twitter_browser_timeline_pagination


def _slug(value: str) -> str:
    cleaned = re.sub(r"^https?://", "", str(value or "").strip(), flags=re.I)
    cleaned = cleaned.replace("/", "_").replace("?", "_").replace("&", "_")
    cleaned = re.sub(r"[^a-zA-Z0-9_.-]+", "_", cleaned).strip("._")
    return cleaned[:120] or "twitter_target"


def _read_targets(args: argparse.Namespace) -> list[str]:
    targets: list[str] = []
    if args.target_url:
        targets.extend(args.target_url)
    if args.targets_file:
        path = Path(args.targets_file)
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                targets.append(line)
    seen: set[str] = set()
    unique: list[str] = []
    for target in targets:
        if target not in seen:
            unique.append(target)
            seen.add(target)
    return unique


def _timeline_pages_rate_limited(output_dir: Path) -> bool:
    path = output_dir / "timeline_pages.jsonl"
    if not path.exists():
        return False
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except Exception:
            continue
        if bool(row.get("rate_limited")) or int(row.get("response_status") or 0) == 429:
            return True
    return False


def _write_manifest(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run conservative one-profile-at-a-time Twitter/X timeline exports with smart pacing, "
            "bounded batches, target delays, and stop-on-rate-limit behaviour."
        )
    )
    parser.add_argument("--target-url", action="append", default=[], help="Target profile/list URL. Can be repeated.")
    parser.add_argument("--targets-file", default="", help="Plain text file of target URLs, one per line; # comments are ignored.")
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--browser-user-data-dir", default="")
    parser.add_argument("--reuse-existing-profile", action="store_true")
    parser.add_argument("--profile-tab", default="replies", choices=("default", "tweets", "replies", "tweets_replies", "tweets_and_replies", "media", "likes"))
    parser.add_argument("--timeout-ms", type=int, default=180000)
    parser.add_argument("--scroll-steps", type=int, default=12)
    parser.add_argument("--scroll-delay-ms", type=int, default=3500)
    parser.add_argument("--scroll-jitter-ms", type=int, default=1200)
    parser.add_argument("--scroll-pixels", type=int, default=1700)
    parser.add_argument("--max-timeline-pages", type=int, default=4)
    parser.add_argument("--no-progress-scrolls", type=int, default=3)
    parser.add_argument("--target-delay-seconds", type=float, default=90.0)
    parser.add_argument("--max-targets", type=int, default=1, help="Safety default is one target per run. Use 0 for all targets in the supplied list.")
    parser.add_argument("--continue-on-needs-review", action="store_true")
    args = parser.parse_args(argv)

    targets = _read_targets(args)
    if args.max_targets > 0:
        targets = targets[: args.max_targets]
    output_root = Path(args.output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    manifest_path = output_root / "bulk_export_manifest.json"
    runs: list[dict[str, Any]] = []
    stopped_reason = ""

    for index, target in enumerate(targets, start=1):
        target_out = output_root / f"{index:03d}_{_slug(target)}_{args.profile_tab}"
        result = run_twitter_browser_timeline_pagination(
            source_url=target,
            output_dir=target_out,
            live=args.live,
            headless=args.headless,
            timeout_ms=args.timeout_ms,
            scroll_steps=args.scroll_steps,
            smart_rate_limit=True,
            scroll_delay_ms=args.scroll_delay_ms,
            scroll_jitter_ms=args.scroll_jitter_ms,
            scroll_pixels=args.scroll_pixels,
            max_timeline_pages=args.max_timeline_pages,
            no_progress_scrolls=args.no_progress_scrolls,
            stop_on_rate_limit=True,
            rate_limit_cooldown_ms=0,
            browser_user_data_dir=args.browser_user_data_dir,
            reuse_existing_profile=args.reuse_existing_profile,
            profile_tab=args.profile_tab,
        )
        row = result.to_dict()
        row["target_index"] = index
        row["rate_limited_detected"] = _timeline_pages_rate_limited(target_out)
        runs.append(row)
        _write_manifest(
            manifest_path,
            {
                "schema_version": "twitter_timeline_bulk_export.v74c",
                "status": "running",
                "output_root": str(output_root),
                "targets_requested": len(targets),
                "runs_completed": len(runs),
                "stopped_reason": stopped_reason,
                "safety_model": "sequential_one_profile_one_target_at_a_time_with_bounded_scroll_and_stop_on_429",
                "runs": runs,
            },
        )
        if row["rate_limited_detected"]:
            stopped_reason = "rate_limited_detected_stop_before_next_target"
            break
        if result.status == "failed" or (result.status == "needs_review" and not args.continue_on_needs_review):
            stopped_reason = f"stopped_on_status_{result.status}"
            break
        if index < len(targets) and args.target_delay_seconds > 0:
            time.sleep(max(0.0, float(args.target_delay_seconds)))

    status = "success" if runs and not stopped_reason else ("needs_review" if runs else "planned")
    _write_manifest(
        manifest_path,
        {
            "schema_version": "twitter_timeline_bulk_export.v74c",
            "status": status,
            "output_root": str(output_root),
            "targets_requested": len(targets),
            "runs_completed": len(runs),
            "stopped_reason": stopped_reason,
            "safety_model": "sequential_one_profile_one_target_at_a_time_with_bounded_scroll_and_stop_on_429",
            "runs": runs,
        },
    )
    print(manifest_path.read_text(encoding="utf-8"))
    return 0 if runs or not targets else 1


if __name__ == "__main__":
    raise SystemExit(main())
