from __future__ import annotations

import json
import tempfile
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from twitter_browser_timeline_pagination import (
    RXLIULI_BROWSER_SESSION_LIMITATION_NOTE,
    TIMELINE_QUERY_NAMES,
    export_twitter_timeline_from_capture,
    extract_timeline_cursors,
    extract_timeline_entries_from_body,
    run_twitter_browser_timeline_pagination,
)


def _fixture_body() -> dict:
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
                                            "entryId": "tweet-2087000000000000001",
                                            "sortIndex": "999",
                                            "content": {
                                                "entryType": "TimelineTimelineItem",
                                                "itemContent": {
                                                    "itemType": "TimelineTweet",
                                                    "tweet_results": {
                                                        "result": {
                                                            "__typename": "Tweet",
                                                            "rest_id": "2087000000000000001",
                                                            "views": {"count": "1234"},
                                                            "core": {
                                                                "user_results": {
                                                                    "result": {
                                                                        "legacy": {
                                                                            "name": "Temp Done",
                                                                            "screen_name": "TempDone365",
                                                                        }
                                                                    }
                                                                }
                                                            },
                                                            "legacy": {
                                                                "id_str": "2087000000000000001",
                                                                "full_text": "Fixture account timeline reply row https://t.co/example",
                                                                "created_at": "Sat Aug 15 07:00:00 +0000 2026",
                                                                "conversation_id_str": "2086999999999999999",
                                                                "in_reply_to_status_id_str": "2086999999999999999",
                                                                "in_reply_to_screen_name": "Somebody",
                                                                "reply_count": 2,
                                                                "retweet_count": 3,
                                                                "favorite_count": 4,
                                                                "quote_count": 5,
                                                                "bookmark_count": 6,
                                                                "entities": {
                                                                    "urls": [
                                                                        {
                                                                            "url": "https://t.co/example",
                                                                            "expanded_url": "https://example.com/article",
                                                                        }
                                                                    ]
                                                                },
                                                            },
                                                        }
                                                    },
                                                },
                                            },
                                        },
                                        {
                                            "entryId": "cursor-bottom-0",
                                            "content": {"cursorType": "Bottom", "value": "CURSOR_NEXT"},
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


def _write_fixture_capture(capture: Path) -> None:
    source_url = "https://x.com/TempDone365/with_replies"
    body = _fixture_body()
    (capture / "browser_session_manifest.json").write_text(
        json.dumps(
            {
                "status": "success",
                "source_url": source_url,
                "canonical_url": source_url,
                "completion_state": "cursor_bounded_partial_browser_session_timeline_export",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (capture / "api_pages.jsonl").write_text(
        json.dumps(
            {
                "query_name": "UserTweetsAndReplies",
                "source_url": "https://x.com/i/api/graphql/abc/UserTweetsAndReplies",
                "page_number": 1,
                "response_status": 200,
                "cursor_in": "",
                "body_json": body,
                "body_sha256": "fixture",
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    (capture / "network_events.jsonl").write_text("", encoding="utf-8")


def main() -> None:
    assert "UserTweetsAndReplies" in TIMELINE_QUERY_NAMES
    body = _fixture_body()
    cursors = extract_timeline_cursors(body)
    assert cursors["bottom_cursor"] == "CURSOR_NEXT"
    entries = extract_timeline_entries_from_body(
        body,
        source_url="https://x.com/TempDone365/with_replies",
        query_name="UserTweetsAndReplies",
        page_number=1,
    )
    assert len(entries) == 1
    assert entries[0].status_id == "2087000000000000001"
    assert entries[0].screen_name == "TempDone365"
    assert entries[0].in_reply_to_screen_name == "Somebody"
    assert entries[0].bookmark_count == 6
    assert "https://example.com/article" in entries[0].links
    assert entries[0].canonical_url == "https://x.com/TempDone365/status/2087000000000000001"

    with tempfile.TemporaryDirectory(prefix="ytce_v74_timeline_pagination_") as tmp:
        capture = Path(tmp) / "capture"
        out = Path(tmp) / "out"
        capture.mkdir()
        _write_fixture_capture(capture)
        result = export_twitter_timeline_from_capture(
            capture_dir=capture,
            output_dir=out,
            source_url="https://x.com/TempDone365",
            profile_tab="replies",
        )
        assert result.status == "success"
        assert result.pages_count == 1
        assert result.entries_count == 1
        assert result.unique_entries_count == 1
        assert (out / "timeline_pages.jsonl").exists()
        assert (out / "timeline_entries.jsonl").exists()
        assert (out / "timeline_pagination_state.json").exists()
        assert (out / "timeline_export_manifest.json").exists()
        state = json.loads((out / "timeline_pagination_state.json").read_text(encoding="utf-8"))
        assert state["api_access_required"] is False
        assert state["live_browser_session_required"] is True
        assert state["requested_profile_tab"] == "replies"
        assert state["last_cursor_out"] == "CURSOR_NEXT"
        assert RXLIULI_BROWSER_SESSION_LIMITATION_NOTE in state["limitation_notes"]
        text = (out / "timeline_entries.jsonl").read_text(encoding="utf-8")
        assert "Fixture account timeline reply row" in text

    with tempfile.TemporaryDirectory(prefix="ytce_v74_timeline_run_") as tmp:
        capture = Path(tmp) / "capture"
        out = Path(tmp) / "out"
        capture.mkdir()
        _write_fixture_capture(capture)
        result = run_twitter_browser_timeline_pagination(
            source_url="https://x.com/TempDone365",
            output_dir=out,
            capture_dir=capture,
            live=False,
            profile_tab="replies",
        )
        assert result.status == "success"
        assert result.canonical_url == "https://x.com/TempDone365/with_replies"
    print("assert_twitter_browser_timeline_pagination_v74 OK")


if __name__ == "__main__":
    main()
