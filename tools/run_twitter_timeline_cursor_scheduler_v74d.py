from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from twitter_timeline_cursor_scheduler import run_twitter_cursor_scheduler


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run a read-only, cursor-driven Twitter/X timeline scheduler. "
            "Login must be done manually in the browser profile before this tool runs."
        )
    )
    parser.add_argument("--source-url", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--live", action="store_true", help="Use Playwright with a pre-logged-in browser profile.")
    parser.add_argument("--seed-capture-dir", default="", help="Build scheduler state from an existing V74 capture without live requests.")
    parser.add_argument("--har-path", default="", help="Build scheduler state from a Firefox/Chrome HAR export without live requests.")
    parser.add_argument("--browser-user-data-dir", default="")
    parser.add_argument("--reuse-existing-profile", action="store_true")
    parser.add_argument("--profile-tab", default="replies", choices=("default", "tweets", "replies", "tweets_replies", "tweets_and_replies", "media", "likes"))
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--timeout-ms", type=int, default=120000)
    parser.add_argument("--initial-scroll-steps", type=int, default=1)
    parser.add_argument("--initial-wait-ms", type=int, default=4500)
    parser.add_argument("--scroll-pixels", type=int, default=1700)
    parser.add_argument("--scroll-delay-ms", type=int, default=2500)
    parser.add_argument("--max-pages", type=int, default=10)
    parser.add_argument("--max-records", type=int, default=0)
    parser.add_argument("--page-delay-ms", type=int, default=4500)
    parser.add_argument("--page-jitter-ms", type=int, default=1500)
    parser.add_argument("--cooldown-ms", type=int, default=180000)
    parser.add_argument("--max-runtime-minutes", type=float, default=0.0)
    parser.add_argument("--disable-stop-on-rate-limit", action="store_true")
    parser.add_argument("--max-no-new-pages", type=int, default=2)
    parser.add_argument("--rate-limit-safety-floor", type=int, default=1)
    parser.add_argument("--soft-page-budget", type=int, default=0)
    parser.add_argument("--max-transient-retries", type=int, default=2)
    parser.add_argument("--transient-base-delay-ms", type=int, default=15000)
    parser.add_argument("--sleep-on-rate-limit", action="store_true", help="Sleep up to the capped cooldown in the browser instead of writing a pause/resume state and exiting.")
    args = parser.parse_args(argv)

    result = run_twitter_cursor_scheduler(
        source_url=args.source_url,
        output_dir=args.output_dir,
        live=args.live,
        browser_user_data_dir=args.browser_user_data_dir,
        reuse_existing_profile=args.reuse_existing_profile,
        seed_capture_dir=args.seed_capture_dir,
        har_path=args.har_path,
        profile_tab=args.profile_tab,
        headless=args.headless,
        timeout_ms=args.timeout_ms,
        initial_scroll_steps=args.initial_scroll_steps,
        initial_wait_ms=args.initial_wait_ms,
        scroll_pixels=args.scroll_pixels,
        scroll_delay_ms=args.scroll_delay_ms,
        max_pages=args.max_pages,
        max_records=args.max_records,
        page_delay_ms=args.page_delay_ms,
        page_jitter_ms=args.page_jitter_ms,
        cooldown_ms=args.cooldown_ms,
        max_runtime_minutes=args.max_runtime_minutes,
        stop_on_rate_limit=not args.disable_stop_on_rate_limit,
        max_no_new_pages=args.max_no_new_pages,
        rate_limit_safety_floor=args.rate_limit_safety_floor,
        soft_page_budget=args.soft_page_budget,
        max_transient_retries=args.max_transient_retries,
        transient_base_delay_ms=args.transient_base_delay_ms,
        sleep_on_rate_limit=args.sleep_on_rate_limit,
    )
    print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False, sort_keys=True))
    return 0 if result.status in {"success", "needs_review", "planned"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
