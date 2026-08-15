from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _assert_contains(path: Path, needles: tuple[str, ...]) -> None:
    text = path.read_text(encoding="utf-8")
    missing = [needle for needle in needles if needle not in text]
    assert not missing, f"{path} missing {missing}"


def main() -> None:
    expected_terms = (
        "smart_rate_limit",
        "scroll_delay_ms",
        "scroll_jitter_ms",
        "scroll_pixels",
        "max_timeline_pages",
        "no_progress_scrolls",
        "stop_on_rate_limit",
        "rate_limit_cooldown_ms",
    )
    _assert_contains(ROOT / "twitter_browser_capture_runner.py", expected_terms + ("ACCOUNT_TIMELINE_QUERY_NAMES", "smart_rate_limit_observed_429_stopping"))
    _assert_contains(ROOT / "twitter_browser_timeline_pagination.py", expected_terms)
    _assert_contains(ROOT / "tools" / "run_twitter_timeline_bulk_v74c.py", ("target-delay-seconds", "max-targets", "sequential_one_profile_one_target_at_a_time", "stop_on_rate_limit=True"))

    help_text = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "run_twitter_browser_timeline_pagination_v74.py"), "--help"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    bulk_help = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "run_twitter_timeline_bulk_v74c.py"), "--help"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    for bulk_flag in ("--target-delay-seconds", "--max-targets", "--target-url", "--targets-file"):
        assert bulk_flag in bulk_help, bulk_flag

    for flag in (
        "--disable-smart-rate-limit",
        "--scroll-delay-ms",
        "--scroll-jitter-ms",
        "--scroll-pixels",
        "--max-timeline-pages",
        "--no-progress-scrolls",
        "--stop-on-rate-limit",
        "--rate-limit-cooldown-ms",
    ):
        assert flag in help_text, flag

    print("assert_twitter_smart_rate_limit_v74c OK")


if __name__ == "__main__":
    main()
