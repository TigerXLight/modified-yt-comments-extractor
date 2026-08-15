from __future__ import annotations

import json
import tempfile
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from twitter_browser_timeline_pagination import (
    export_twitter_timeline_from_capture,
    export_twitter_timeline_from_har,
    timeline_rows_from_har,
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
                                            "entryId": "tweet-2088000000000000001",
                                            "sortIndex": "777",
                                            "content": {
                                                "entryType": "TimelineTimelineItem",
                                                "itemContent": {
                                                    "itemType": "TimelineTweet",
                                                    "tweet_results": {
                                                        "result": {
                                                            "__typename": "Tweet",
                                                            "rest_id": "2088000000000000001",
                                                            "views": {"count": "55"},
                                                            "core": {
                                                                "user_results": {
                                                                    "result": {
                                                                        "legacy": {
                                                                            "name": "Exam Adda",
                                                                            "screen_name": "examaddaorg",
                                                                        }
                                                                    }
                                                                }
                                                            },
                                                            "legacy": {
                                                                "id_str": "2088000000000000001",
                                                                "full_text": "V74B promoted UserRepliesTimeline row",
                                                                "created_at": "Sat Aug 15 08:30:00 +0000 2026",
                                                                "conversation_id_str": "2087999999999999999",
                                                                "in_reply_to_status_id_str": "2087999999999999999",
                                                                "in_reply_to_screen_name": "Somebody",
                                                                "reply_count": 1,
                                                                "retweet_count": 2,
                                                                "favorite_count": 3,
                                                                "quote_count": 4,
                                                                "bookmark_count": 5,
                                                            },
                                                        }
                                                    },
                                                },
                                            },
                                        },
                                        {"entryId": "cursor-bottom-0", "content": {"cursorType": "Bottom", "value": "V74B_CURSOR"}},
                                    ],
                                }
                            ]
                        }
                    }
                }
            }
        }
    }


def _url() -> str:
    return "https://api.x.com/graphql/abc/UserRepliesTimeline?variables=%7B%22cursor%22%3A%22IN%22%7D"


def _write_hashflag_only_api_pages(path: Path) -> None:
    path.write_text(
        json.dumps({"query_name": "twitter_api", "source_url": "https://api.x.com/hashflags", "body_json": [{"hashtag": "Noise"}]}) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    body = _fixture_body()
    with tempfile.TemporaryDirectory(prefix="ytce_v74b_promotion_") as tmp:
        root = Path(tmp)
        capture = root / "capture"
        out = root / "out"
        capture.mkdir()
        _write_hashflag_only_api_pages(capture / "api_pages.jsonl")
        (capture / "network_events.jsonl").write_text(
            json.dumps(
                {
                    "query_name": "UserRepliesTimeline",
                    "url": _url(),
                    "status": 200,
                    "body_text": json.dumps(body),
                    "body_sha256": "fixture",
                },
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )
        result = export_twitter_timeline_from_capture(
            capture_dir=capture,
            output_dir=out,
            source_url="https://x.com/examaddaorg",
            profile_tab="replies",
        )
        assert result.status == "success"
        assert result.pages_count == 1
        assert result.entries_count == 1
        assert "V74B promoted UserRepliesTimeline row" in (out / "timeline_entries.jsonl").read_text(encoding="utf-8")

    with tempfile.TemporaryDirectory(prefix="ytce_v74b_bodyfile_") as tmp:
        root = Path(tmp)
        capture = root / "capture"
        out = root / "out"
        capture.mkdir()
        _write_hashflag_only_api_pages(capture / "api_pages.jsonl")
        (capture / "network_events.jsonl").write_text("", encoding="utf-8")
        (capture / "network_response_bodies.jsonl").write_text(
            json.dumps(
                {
                    "schema_version": "twitter_network_response_body.v74b",
                    "query_name": "UserRepliesTimeline",
                    "url": _url(),
                    "status": 200,
                    "body_text": json.dumps(body),
                    "body_sha256": "fixture",
                },
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )
        result = export_twitter_timeline_from_capture(
            capture_dir=capture,
            output_dir=out,
            source_url="https://x.com/examaddaorg",
            profile_tab="replies",
        )
        assert result.status == "success"
        assert result.entries_count == 1

    with tempfile.TemporaryDirectory(prefix="ytce_v74b_har_") as tmp:
        root = Path(tmp)
        har = root / "twitter.har"
        out = root / "out"
        har.write_text(
            json.dumps(
                {
                    "log": {
                        "entries": [
                            {
                                "request": {"url": _url(), "method": "GET"},
                                "response": {"status": 200, "content": {"mimeType": "application/json", "text": json.dumps(body)}},
                            }
                        ]
                    }
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        rows = timeline_rows_from_har(har)
        assert len(rows) == 1
        result = export_twitter_timeline_from_har(
            har_path=har,
            output_dir=out,
            source_url="https://x.com/examaddaorg",
            profile_tab="replies",
        )
        assert result.status == "success"
        assert result.pages_count == 1
        assert result.entries_count == 1
        state = json.loads((out / "timeline_pagination_state.json").read_text(encoding="utf-8"))
        assert state["api_access_required"] is False
        assert state["live_browser_session_required"] is True
    print("assert_twitter_response_promotion_and_har_v74b OK")


if __name__ == "__main__":
    main()
