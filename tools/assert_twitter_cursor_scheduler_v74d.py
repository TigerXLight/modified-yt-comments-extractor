from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from twitter_rate_limit_policy import decide_rate_limit_action, observe_rate_limit
from twitter_timeline_cursor_scheduler import (
    _merge_replay_headers,
    _redacted_headers_for_output,
    _request_headers_are_authenticated,
    _seed_state_from_records,
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
    prepared = _seed_state_from_records(
        records=records,
        source_url="https://x.com/examaddaorg",
        profile_tab="replies",
        max_pages=10,
    )
    assert len(prepared["pages"]) == 2, prepared
    assert len(prepared["entries"]) == 2, prepared
    assert prepared["cursor_history"][-1] == "CURSOR_TWO", prepared
    assert "cursor" in prepared["next_cursor_url"], prepared
    assert any(str(w).startswith("deduped_seed_records:1") for w in prepared["warnings"]), prepared

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
        rate_state = json.loads((Path(tmp) / "cursor_rate_limit_state.json").read_text(encoding="utf-8"))
        assert rate_state["schema_version"] == "twitter_rate_limit_state.v74e", rate_state
        assert (Path(tmp) / "cursor_errors.jsonl").exists(), tmp

    merged_headers = _merge_replay_headers(
        {"accept": "application/json", "authorization": "Bearer SECRET"},
        {"x-csrf-token": "CT0SECRET", "x-twitter-active-user": "yes"},
    )
    assert _request_headers_are_authenticated(merged_headers), merged_headers
    redacted_headers = _redacted_headers_for_output(merged_headers)
    assert redacted_headers["authorization"] == "[redacted]", redacted_headers
    assert redacted_headers["x-csrf-token"] == "[redacted]", redacted_headers
    assert redacted_headers["x-twitter-active-user"] == "yes", redacted_headers
    assert "SECRET" not in json.dumps(redacted_headers), redacted_headers

    obs = observe_rate_limit(
        response_status=429,
        headers={"x-rate-limit-limit": "50", "x-rate-limit-remaining": "0", "x-rate-limit-reset": "2000000000"},
        body={"errors": [{"code": 88, "message": "Rate limit exceeded"}]},
    )
    decision = decide_rate_limit_action(observation=obs, normal_delay_ms=1000, safety_floor=1)
    assert obs.rate_limit_remaining == 0, obs
    assert "88" in obs.body_error_codes, obs
    assert decision.decision == "pause_until_reset", decision
    assert decision.rate_limited is True, decision

    obs2 = observe_rate_limit(response_status=200, headers={"x-rate-limit-remaining": "1", "x-rate-limit-reset": "2000000000"})
    decision2 = decide_rate_limit_action(observation=obs2, normal_delay_ms=1000, safety_floor=1)
    assert decision2.decision == "pause_until_reset", decision2
    assert decision2.reason == "rate_limit_remaining_safety_floor", decision2
    print("assert_twitter_cursor_scheduler_v74f2 OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
