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
    parser.add_argument("--disable-smart-rate-limit", action="store_true", help="Disable conservative scroll pacing and stop-boundary checks. Not recommended for logged-in browser sessions.")
    parser.add_argument("--scroll-delay-ms", type=int, default=3500, help="Base wait after each scroll in live browser mode.")
    parser.add_argument("--scroll-jitter-ms", type=int, default=1200, help="Additional random wait after each scroll in live browser mode.")
    parser.add_argument("--scroll-pixels", type=int, default=1700, help="Mouse wheel distance for each browser scroll step.")
    parser.add_argument("--max-timeline-pages", type=int, default=4, help="Stop live scrolling after this many timeline GraphQL pages are observed. Use 0 for no page cap.")
    parser.add_argument("--no-progress-scrolls", type=int, default=3, help="Stop after this many scrolls produce no new timeline GraphQL page.")
    parser.add_argument("--stop-on-rate-limit", action="store_true", default=True, help="Stop when a 429/rate-limited response is observed.")
    parser.add_argument("--rate-limit-cooldown-ms", type=int, default=0, help="Optional bounded wait after a 429 before closing the browser capture.")
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
        smart_rate_limit=not args.disable_smart_rate_limit,
        scroll_delay_ms=args.scroll_delay_ms,
        scroll_jitter_ms=args.scroll_jitter_ms,
        scroll_pixels=args.scroll_pixels,
        max_timeline_pages=args.max_timeline_pages,
        no_progress_scrolls=args.no_progress_scrolls,
        stop_on_rate_limit=args.stop_on_rate_limit,
        rate_limit_cooldown_ms=args.rate_limit_cooldown_ms,
        browser_user_data_dir=args.browser_user_data_dir,
        reuse_existing_profile=args.reuse_existing_profile,
        profile_tab=args.profile_tab,
        max_pages=args.max_pages,
    )
    print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False, sort_keys=True))
    return 0 if result.status in {"success", "needs_review", "planned"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
