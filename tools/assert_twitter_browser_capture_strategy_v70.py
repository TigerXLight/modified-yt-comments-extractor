from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> None:
    for rel in (
        "twitter_browser_capture_strategy.py",
        "twitter_browser_capture_strategy_test.py",
        "tools/build_twitter_browser_capture_plan_v70.py",
        "tools/assert_twitter_browser_capture_strategy_v70.py",
    ):
        assert (ROOT / rel).exists(), rel

    source = (ROOT / "twitter_browser_capture_strategy.py").read_text(encoding="utf-8")
    assert "browser_session_network_responses" in source
    assert "UserTweets" in source
    assert "ListLatestTweetsTimeline" in source
    assert "next_page_requested_but_no_data_returned" in source
    assert "separate test account" in source
    assert "LIST_WORKAROUND_NOT_GUARANTEED" in source

    route_source = (ROOT / "twitter_route_strategy.py").read_text(encoding="utf-8")
    media_source = (ROOT / "twitter_media_backend.py").read_text(encoding="utf-8")
    assert "unwrap_twitter_input_url" in route_source
    assert "unwrap_twitter_media_input_url" in media_source

    from twitter_browser_capture_strategy import build_twitter_browser_capture_plan

    plan = build_twitter_browser_capture_plan(
        "https://x.com/example",
        list_workaround_url="https://x.com/i/lists/1234567890",
    )
    assert "list_workaround_not_guaranteed_complete" in plan.constraints
    assert plan.list_workaround_guarantees_full_export is False
    assert plan.list_workaround_url == "https://x.com/i/lists/1234567890"
    assert any(step.name == "optional_list_workaround" for step in plan.steps)
    print("assert_twitter_browser_capture_strategy_v70 OK")


if __name__ == "__main__":
    main()
