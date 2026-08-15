from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from twitter_browser_capture_strategy import (
    build_twitter_browser_capture_plan,
    build_twitter_browser_session_config,
    write_twitter_browser_capture_plan,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build a Twitter/X browser-session capture plan.")
    parser.add_argument("--source-url", required=True)
    parser.add_argument("--capture-goal", default="")
    parser.add_argument("--list-workaround-url", default="")
    parser.add_argument("--profile-label", default="ytce_twitter_isolated_test_profile")
    parser.add_argument("--user-data-dir", default="")
    parser.add_argument("--reuse-existing-profile", action="store_true")
    parser.add_argument("--output", default="")
    args = parser.parse_args(argv)

    session = build_twitter_browser_session_config(
        profile_label=args.profile_label,
        user_data_dir=args.user_data_dir,
        reuse_existing_profile=args.reuse_existing_profile,
    )
    plan = build_twitter_browser_capture_plan(
        args.source_url,
        capture_goal=args.capture_goal,
        list_workaround_url=args.list_workaround_url,
        session_config=session,
    )
    if args.output:
        write_twitter_browser_capture_plan(args.output, plan)
        print(f"WROTE {args.output}")
    print(json.dumps(plan.to_dict(), indent=2, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
