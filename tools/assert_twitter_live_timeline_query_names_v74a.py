from __future__ import annotations

import json
import tempfile
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from twitter_browser_capture_runner import (
    TWITTER_API_QUERY_NAMES,
    TwitterCapturedNetworkEvent,
    build_api_pages_from_events,
    extract_twitter_api_query_name,
    is_twitter_timeline_api_query_name,
)
from twitter_browser_timeline_pagination import (
    TIMELINE_QUERY_NAMES,
    export_twitter_timeline_from_capture,
    is_timeline_query_name,
)


def fixture_body() -> dict:
    tweet = {
        "__typename": "Tweet",
        "rest_id": "2087999999999999999",
        "legacy": {
            "id_str": "2087999999999999999",
            "full_text": "UserRepliesTimeline fixture row",
            "created_at": "Sat Aug 15 08:00:00 +0000 2026",
            "reply_count": 1,
            "retweet_count": 2,
            "favorite_count": 3,
            "quote_count": 0,
            "bookmark_count": 4,
        },
        "core": {
            "user_results": {
                "result": {
                    "legacy": {"name": "Example", "screen_name": "examaddaorg"}
                }
            }
        },
    }
    entries = [
        {
            "entryId": "tweet-2087999999999999999",
            "sortIndex": "999",
            "content": {
                "entryType": "TimelineTimelineItem",
                "itemContent": {
                    "itemType": "TimelineTweet",
                    "tweet_results": {"result": tweet},
                },
            },
        },
        {
            "entryId": "cursor-bottom-0",
            "content": {"cursorType": "Bottom", "value": "NEXT_REPLY_CURSOR"},
        },
    ]
    return {
        "data": {
            "user": {
                "result": {
                    "timeline_v2": {
                        "timeline": {
                            "instructions": [
                                {"type": "TimelineAddEntries", "entries": entries}
                            ]
                        }
                    }
                }
            }
        }
    }


def main() -> None:
    assert "UserRepliesTimeline" in TWITTER_API_QUERY_NAMES
    assert "UserRepliesTimeline" in TIMELINE_QUERY_NAMES
    assert is_twitter_timeline_api_query_name("UserRepliesTimeline")
    assert is_twitter_timeline_api_query_name("UserSomethingRepliesTimeline")
    assert is_timeline_query_name("UserRepliesTimeline")
    assert is_timeline_query_name("UserSomethingTweetsTimeline")

    url = "https://api.x.com/graphql/abc/UserRepliesTimeline?variables=%7B%7D"
    assert extract_twitter_api_query_name(url) == "UserRepliesTimeline"
    event = TwitterCapturedNetworkEvent(
        url=url,
        status=200,
        content_type="application/json",
        query_name="UserRepliesTimeline",
        body_text=json.dumps(fixture_body()),
    )
    pages = build_api_pages_from_events(
        (event,), source_url="https://x.com/examaddaorg/with_replies"
    )
    assert len(pages) == 1
    assert pages[0].query_name == "UserRepliesTimeline"
    assert pages[0].cursor_out == "NEXT_REPLY_CURSOR"
    assert pages[0].returned_items_count >= 1

    with tempfile.TemporaryDirectory(prefix="ytce_v74a_user_replies_timeline_") as tmp:
        capture = Path(tmp) / "capture"
        out = Path(tmp) / "out"
        capture.mkdir()
        (capture / "browser_session_manifest.json").write_text(
            json.dumps(
                {
                    "status": "success",
                    "source_url": "https://x.com/examaddaorg/with_replies",
                    "canonical_url": "https://x.com/examaddaorg/with_replies",
                }
            ),
            encoding="utf-8",
        )
        (capture / "api_pages.jsonl").write_text(
            json.dumps(pages[0].to_dict()) + "\n", encoding="utf-8"
        )
        (capture / "network_events.jsonl").write_text("", encoding="utf-8")
        result = export_twitter_timeline_from_capture(
            capture_dir=capture,
            output_dir=out,
            source_url="https://x.com/examaddaorg",
            profile_tab="replies",
        )
        assert result.pages_count == 1
        assert result.entries_count == 1
        assert result.unique_entries_count == 1
        assert result.status == "success"
        state = json.loads(
            (out / "timeline_pagination_state.json").read_text(encoding="utf-8")
        )
        assert state["last_cursor_out"] == "NEXT_REPLY_CURSOR"

    print("assert_twitter_live_timeline_query_names_v74a OK")


if __name__ == "__main__":
    main()
