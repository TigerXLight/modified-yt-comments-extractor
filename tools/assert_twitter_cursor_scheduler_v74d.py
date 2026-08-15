from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from twitter_timeline_cursor_scheduler import (
    _url_with_cursor,
    run_twitter_cursor_scheduler_from_records,
)


def _tweet(status_id: str, text: str, screen_name: str = "examaddaorg") -> dict:
    return {
        "__typename": "Tweet",
        "rest_id": status_id,
        "core": {"user_results": {"result": {"legacy": {"screen_name": screen_name, "name": "ExamAdda"}}}},
        "legacy": {
            "id_str": status_id,
            "full_text": text,
            "created_at": "Sat Aug 15 05:18:06 +0000 2026",
            "conversation_id_str": status_id,
            "reply_count": 1,
            "retweet_count": 2,
            "favorite_count": 3,
            "quote_count": 4,
            "bookmark_count": 5,
        },
        "views": {"count": "10"},
    }


def _timeline_body(status_id: str, text: str, cursor: str) -> dict:
    return {
        "data": {
            "user": {
                "result": {
                    "timeline_v2": {
                        "timeline": {
                            "instructions": [
                                {
                                    "type": "TimelineAddEntries",
                                    "entries": [
                                        {
                                            "entryId": f"tweet-{status_id}",
                                            "sortIndex": status_id,
                                            "content": {"itemContent": {"tweet_results": {"result": _tweet(status_id, text)}}},
                                        },
                                        {
                                            "entryId": "cursor-bottom-0",
                                            "content": {"cursorType": "Bottom", "value": cursor},
                                        },
                                    ],
                                }
                            ]
                        }
                    }
                }
            }
        }
    }


def main() -> int:
    base_url = (
        "https://api.x.com/graphql/query/UserRepliesTimeline?"
        "variables=%7B%22userId%22%3A%22123%22%2C%22count%22%3A20%7D&features=%7B%7D"
    )
    next_url = _url_with_cursor(base_url, "CURSOR_ONE")
    parsed_vars = json.loads(parse_qs(urlsplit(next_url).query)["variables"][0])
    assert parsed_vars["cursor"] == "CURSOR_ONE", next_url

    first_page = {
        "url": base_url,
        "query_name": "UserRepliesTimeline",
        "status": 200,
        "body_json": _timeline_body("100", "first page", "CURSOR_ONE"),
        "promotion_source": "network_response_bodies.jsonl",
    }
    duplicate_first_page = {
        "raw_event_url": "https://x.com/examaddaorg/with_replies",
        "query_name": "UserRepliesTimeline",
        "response_status": 200,
        "body_json": _timeline_body("100", "first page", "CURSOR_ONE"),
        "promotion_source": "api_pages.jsonl",
    }
    records = [
        first_page,
        duplicate_first_page,
        {
            "url": next_url,
            "query_name": "UserRepliesTimeline",
            "status": 200,
            "body_json": _timeline_body("101", "second page", "CURSOR_TWO"),
            "promotion_source": "unit_seed_page_2",
        },
    ]
    with tempfile.TemporaryDirectory() as tmp:
        result = run_twitter_cursor_scheduler_from_records(
            records=records,
            source_url="https://x.com/examaddaorg",
            profile_tab="replies",
            output_dir=tmp,
            max_pages=10,
        )
        assert result.status == "success", result
        assert result.pages_count == 2, result
        assert result.entries_count == 2, result
        assert result.unique_entries_count == 2, result
        assert any(str(w).startswith("deduped_seed_records:1") for w in result.warnings), result
        state = json.loads((Path(tmp) / "cursor_scheduler_state.json").read_text(encoding="utf-8"))
        assert state["last_cursor_out"] == "CURSOR_TWO", state
        assert state["read_only"] is True, state
        assert state["api_access_required"] is False, state
        pages = (Path(tmp) / "cursor_pages.jsonl").read_text(encoding="utf-8")
        assert "UserRepliesTimeline" in pages, pages
        entries = (Path(tmp) / "cursor_entries.jsonl").read_text(encoding="utf-8")
        assert "https://x.com/examaddaorg/status/100" in entries, entries
    print("assert_twitter_cursor_scheduler_v74d2 OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
