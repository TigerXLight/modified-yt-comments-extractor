from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> None:
    for rel in (
        "twitter_browser_capture_runner.py",
        "twitter_browser_capture_runner_test.py",
        "tools/run_twitter_browser_capture_v71.py",
        "tools/assert_twitter_browser_capture_runner_v71.py",
    ):
        assert (ROOT / rel).exists(), rel

    source = (ROOT / "twitter_browser_capture_runner.py").read_text(encoding="utf-8")
    assert "_playwright_browser_capture_executor" in source
    assert "page.on(\"response\"" in source
    assert "network_events.jsonl" in source
    assert "api_pages.jsonl" in source
    assert "cursor_boundaries.json" in source
    assert "media_inventory.json" in source
    assert "TweetDetail" in source
    assert "UserTweets" in source
    assert "ListLatestTweetsTimeline" in source
    assert "run_twitter_media_download_via_shared_backend" in source

    from twitter_browser_capture_runner import extract_twitter_api_query_name

    assert extract_twitter_api_query_name("https://x.com/i/api/graphql/abc/UserTweets") == "UserTweets"
    print("assert_twitter_browser_capture_runner_v71 OK")


if __name__ == "__main__":
    main()
