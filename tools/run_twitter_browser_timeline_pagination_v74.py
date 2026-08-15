from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from twitter_browser_timeline_pagination import run_twitter_browser_timeline_pagination


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run rxliuli-style Twitter/X browser-session timeline pagination. "
            "This uses the logged-in browser session/network responses; it never accepts passwords."
        )
    )
    parser.add_argument("--source-url", required=True, help="Profile, list, or timeline URL. For replies use --profile-tab replies.")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--capture-dir", default="", help="Existing browser capture directory to parse instead of launching a live browser.")
    parser.add_argument("--har-path", default="", help="Import Firefox/Chrome DevTools HAR containing X web GraphQL timeline responses.")
    parser.add_argument("--live", action="store_true", help="Launch Playwright/Chromium and scroll the logged-in browser session.")
    parser.add_argument("--headless", action="store_true", help="Use headless browser. For first login, omit this.")
    parser.add_argument("--timeout-ms", type=int, default=90000)
    parser.add_argument("--scroll-steps", type=int, default=8)
    parser.add_argument("--browser-user-data-dir", default="", help="Persistent browser profile directory. Login manually here; do not pass credentials.")
    parser.add_argument("--reuse-existing-profile", action="store_true", help="Intentional reuse of the supplied profile directory.")
    parser.add_argument("--profile-tab", default="replies", choices=("default", "tweets", "replies", "tweets_replies", "tweets_and_replies", "media", "likes"))
    parser.add_argument("--max-pages", type=int, default=0)
    args = parser.parse_args(argv)

    result = run_twitter_browser_timeline_pagination(
        source_url=args.source_url,
        output_dir=args.output_dir,
        capture_dir=args.capture_dir,
        har_path=args.har_path,
        live=args.live,
        headless=args.headless,
        timeout_ms=args.timeout_ms,
        scroll_steps=args.scroll_steps,
        browser_user_data_dir=args.browser_user_data_dir,
        reuse_existing_profile=args.reuse_existing_profile,
        profile_tab=args.profile_tab,
        max_pages=args.max_pages,
    )
    print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False, sort_keys=True))
    return 0 if result.status in {"success", "needs_review", "planned"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
