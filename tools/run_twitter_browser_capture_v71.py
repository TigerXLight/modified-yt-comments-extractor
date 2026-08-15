from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from twitter_browser_capture_runner import run_twitter_browser_capture


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run or plan a Twitter/X browser-session capture.")
    parser.add_argument("--source-url", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--capture-goal", default="")
    parser.add_argument("--list-workaround-url", default="")
    parser.add_argument("--live", action="store_true", help="Actually launch Playwright/Chromium and capture the browser session.")
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--timeout-ms", type=int, default=60000)
    parser.add_argument("--scroll-steps", type=int, default=3)
    parser.add_argument("--browser-user-data-dir", default="", help="Optional isolated/persistent Chromium user-data directory for login/session reuse.")
    parser.add_argument("--reuse-existing-profile", action="store_true", help="Mark the supplied browser user-data directory as an intentional reusable profile.")
    parser.add_argument("--download-media", action="store_true", help="After browser capture discovers media, run the shared media backend.")
    args = parser.parse_args(argv)

    result = run_twitter_browser_capture(
        source_url=args.source_url,
        output_dir=args.output_dir,
        capture_goal=args.capture_goal,
        list_workaround_url=args.list_workaround_url,
        live=args.live,
        headless=args.headless,
        timeout_ms=args.timeout_ms,
        scroll_steps=args.scroll_steps,
        browser_user_data_dir=args.browser_user_data_dir,
        reuse_existing_profile=args.reuse_existing_profile,
        download_media=args.download_media,
    )
    print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False, sort_keys=True))
    if result.status in {"success", "planned"}:
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
