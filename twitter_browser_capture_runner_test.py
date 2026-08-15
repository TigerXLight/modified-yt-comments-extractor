from __future__ import annotations

import json
import tempfile
from pathlib import Path

from twitter_browser_capture_runner import (
    BrowserCapturePayload,
    TwitterCapturedNetworkEvent,
    build_api_pages_from_events,
    build_boundaries_from_api_pages,
    extract_media_inventory_from_api_pages,
    extract_twitter_api_query_name,
    run_twitter_browser_capture,
)


def _tweet_detail_json() -> str:
    return json.dumps(
        {
            "data": {
                "threaded_conversation_with_injections_v2": {
                    "instructions": [
                        {
                            "entries": [
                                {
                                    "entryId": "tweet-123",
                                    "content": {
                                        "itemContent": {
                                            "tweet_results": {
                                                "result": {
                                                    "__typename": "Tweet",
                                                    "legacy": {
                                                        "entities": {
                                                            "media": [
                                                                {
                                                                    "id_str": "m1",
                                                                    "type": "video",
                                                                    "media_url_https": "https://pbs.twimg.com/media/preview.jpg",
                                                                    "video_info": {
                                                                        "variants": [
                                                                            {"content_type": "application/x-mpegURL", "url": "https://video.twimg.com/ext_tw_video/pl/master.m3u8"},
                                                                            {"bitrate": 832000, "content_type": "video/mp4", "url": "https://video.twimg.com/ext_tw_video/pl/vid/720x720/video.mp4"},
                                                                        ]
                                                                    },
                                                                }
                                                            ]
                                                        }
                                                    },
                                                }
                                            }
                                        }
                                    },
                                },
                                {"entryId": "cursor-bottom-0", "content": {"cursorType": "Bottom", "value": "cursor-two"}},
                            ]
                        }
                    ]
                }
            }
        }
    )


def test_extract_query_name_from_graphql_url() -> None:
    assert extract_twitter_api_query_name("https://x.com/i/api/graphql/abc/TweetDetail?variables=x") == "TweetDetail"


def test_api_pages_boundaries_and_media_inventory() -> None:
    events = (
        TwitterCapturedNetworkEvent(
            url="https://x.com/i/api/graphql/abc/TweetDetail",
            status=200,
            content_type="application/json",
            query_name="TweetDetail",
            body_text=_tweet_detail_json(),
        ),
    )
    pages = build_api_pages_from_events(events, source_url="https://x.com/user/status/123")
    boundaries = build_boundaries_from_api_pages(pages)
    media = extract_media_inventory_from_api_pages(pages)
    assert len(pages) == 1
    assert pages[0].cursor_out == "cursor-two"
    assert boundaries[0].completeness_state == "partial_api_boundary"
    assert any(item.media_url.endswith("video.mp4") for item in media)
    assert any(item.preview_url.endswith("preview.jpg") for item in media)


def test_run_browser_capture_with_fake_executor_writes_artifacts() -> None:
    def fake_executor(plan):
        return BrowserCapturePayload(
            events=(
                TwitterCapturedNetworkEvent(
                    url="https://x.com/i/api/graphql/abc/TweetDetail",
                    status=200,
                    content_type="application/json",
                    query_name="TweetDetail",
                    body_text=_tweet_detail_json(),
                ),
            ),
            final_url=plan.canonical_url,
            final_dom="<html><body>tweet</body></html>",
        )

    with tempfile.TemporaryDirectory(prefix="ytce_v71_twitter_capture_") as tmp:
        result = run_twitter_browser_capture(
            source_url="https://x.com/user/status/123",
            output_dir=tmp,
            browser_executor=fake_executor,
        )
        manifest = Path(result.manifest_path)
        media = Path(result.media_inventory_path)
        network = Path(result.network_events_path)
        assert result.status == "success"
        assert result.api_page_count == 1
        assert result.media_item_count >= 2
        assert manifest.exists()
        assert media.exists()
        assert network.exists()


def test_plan_only_run_without_live_is_not_completed() -> None:
    with tempfile.TemporaryDirectory(prefix="ytce_v71_twitter_capture_plan_") as tmp:
        result = run_twitter_browser_capture(source_url="https://x.com/user/status/123", output_dir=tmp)
    assert result.status == "planned"
    assert result.evidence_completion_claim == "not_completed"
    assert "live_browser_capture_not_requested" in result.warnings


def main() -> None:
    test_extract_query_name_from_graphql_url()
    test_api_pages_boundaries_and_media_inventory()
    test_run_browser_capture_with_fake_executor_writes_artifacts()
    test_plan_only_run_without_live_is_not_completed()
    print("twitter_browser_capture_runner_test OK")


if __name__ == "__main__":
    main()
