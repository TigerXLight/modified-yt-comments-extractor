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
    extract_rendered_dom_media_inventory,
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


def test_runner_unwraps_markdown_source_url_and_records_profile_dir() -> None:
    def fake_executor(plan):
        assert plan.canonical_url == "https://x.com/user/status/123"
        assert plan.browser_session.user_data_dir.endswith("ytce-twitter-test-profile")
        return BrowserCapturePayload(events=())

    with tempfile.TemporaryDirectory(prefix="ytce_v72_twitter_capture_") as tmp:
        result = run_twitter_browser_capture(
            source_url="[https://x.com/user/status/123](https://x.com/user/status/123)",
            output_dir=Path(tmp) / "out",
            browser_user_data_dir=Path(tmp) / "ytce-twitter-test-profile",
            reuse_existing_profile=True,
            browser_executor=fake_executor,
        )
        assert result.source_url == "https://x.com/user/status/123"
        assert result.canonical_url == "https://x.com/user/status/123"



def test_runner_marks_http_404_zero_item_capture_not_completed() -> None:
    def fake_executor(plan):
        return BrowserCapturePayload(
            events=(
                BrowserNetworkEvent(
                    url="https://x.com/i/api/graphql/TweetDetail",
                    method="GET",
                    status=404,
                    resource_type="xhr",
                    query_name="twitter_api",
                    response_json={"errors": [{"message": "not found"}]},
                ),
            )
        )

    with tempfile.TemporaryDirectory(prefix="ytce_v72b_twitter_capture_") as tmp:
        result = run_twitter_browser_capture(
            source_url="[https://x.com/user/status/404](https://x.com/user/status/404)",
            output_dir=tmp,
            browser_executor=fake_executor,
        )
        assert result.source_url == "https://x.com/user/status/404"
        assert result.canonical_url == "https://x.com/user/status/404"
        assert result.status == "needs_review"
        assert result.evidence_completion_claim == "not_completed"
        assert "twitter_live_capture_http_404_zero_items_not_completed" in result.warnings
        manifest = json.loads(Path(result.manifest_path).read_text(encoding="utf-8"))
        assert manifest["source_url"] == "https://x.com/user/status/404"
        assert manifest["evidence_completion_claim"] == "not_completed"




def _rendered_status_dom(status_id: str = "2085760210359267524") -> str:
    return f"""<html><head>
<meta property="og:url" content="https://x.com/DuvalMagic/status/{status_id}" nonce="">
<meta property="og:title" content="Randy Pitchford (@DuvalMagic) on X" nonce="">
<meta property="og:description" content="Use this SHiFT code for free Golden Keys in Borderlands 4:" nonce="">
<meta property="og:image" content="https://pbs.twimg.com/media/HPIb1teawAEGqVL.png:large" nonce="">
<link rel="canonical" href="https://x.com/DuvalMagic/status/{status_id}" nonce="">
</head><body>
<article data-tweet-id="{status_id}" itemid="https://x.com/i/status/{status_id}"></article>
</body></html>"""


def test_extract_rendered_dom_media_inventory_from_status_dom() -> None:
    items = extract_rendered_dom_media_inventory(
        _rendered_status_dom(),
        source_url="https://x.com/DuvalMagic/status/2085760210359267524",
    )
    assert len(items) == 1
    assert items[0].media_url == "https://pbs.twimg.com/media/HPIb1teawAEGqVL.png:large"
    assert items[0].from_query_name == "rendered_dom"
    assert items[0].source_kind == "rendered_dom_og_image"
    assert items[0].status_id == "2085760210359267524"


def test_rendered_dom_fallback_does_not_activate_for_wrong_tweet_id() -> None:
    items = extract_rendered_dom_media_inventory(
        _rendered_status_dom("1111111111111111111"),
        source_url="https://x.com/DuvalMagic/status/2085760210359267524",
    )
    assert items == ()


def test_run_browser_capture_uses_rendered_dom_fallback_for_api_404() -> None:
    def fake_executor(plan):
        return BrowserCapturePayload(
            events=(
                TwitterCapturedNetworkEvent(
                    url="https://x.com/i/api/graphql/abc/TweetDetail",
                    status=404,
                    content_type="application/json",
                    query_name="twitter_api",
                    body_text=json.dumps({"errors": [{"message": "not found"}]}),
                ),
            ),
            final_url=plan.canonical_url,
            final_dom=_rendered_status_dom(),
        )

    with tempfile.TemporaryDirectory(prefix="ytce_v72d_twitter_capture_") as tmp:
        result = run_twitter_browser_capture(
            source_url="https://x.com/DuvalMagic/status/2085760210359267524",
            output_dir=tmp,
            browser_executor=fake_executor,
        )
        assert result.status == "needs_review"
        assert result.api_completion_state == "needs_review_http_404_no_items"
        assert result.rendered_dom_status_available is True
        assert result.rendered_dom_fallback_used is True
        assert result.rendered_dom_media_item_count == 1
        assert result.media_item_count == 1
        assert result.evidence_completion_claim == "rendered_status_media_metadata_captured"
        manifest = json.loads(Path(result.manifest_path).read_text(encoding="utf-8"))
        media = json.loads(Path(result.media_inventory_path).read_text(encoding="utf-8"))
        assert manifest["rendered_dom_fallback_used"] is True
        assert media[0]["media_url"] == "https://pbs.twimg.com/media/HPIb1teawAEGqVL.png:large"
        assert media[0]["provenance"] == "rendered_dom_status_metadata"


def test_run_browser_capture_with_rendered_dom_metadata_only_is_not_completed() -> None:
    def fake_executor(plan):
        return BrowserCapturePayload(
            events=(
                TwitterCapturedNetworkEvent(
                    url="https://x.com/i/api/graphql/abc/TweetDetail",
                    status=200,
                    content_type="application/json",
                    query_name="twitter_api",
                    body_text=json.dumps({"data": {"threaded_conversation_with_injections_v2": {"instructions": []}}}),
                ),
            ),
            final_url=plan.canonical_url,
            final_dom=_rendered_status_dom(),
        )

    with tempfile.TemporaryDirectory(prefix="ytce_v72e_twitter_capture_") as tmp:
        result = run_twitter_browser_capture(
            source_url="https://x.com/DuvalMagic/status/2085760210359267524",
            output_dir=tmp,
            browser_executor=fake_executor,
        )
        assert result.status == "needs_review"
        assert result.rendered_dom_status_available is True
        assert result.rendered_dom_media_item_count == 1
        assert result.rendered_dom_fallback_used is False
        assert result.media_item_count == 1
        assert result.evidence_completion_claim == "rendered_status_media_metadata_captured"
        manifest = json.loads(Path(result.manifest_path).read_text(encoding="utf-8"))
        assert manifest["status"] == "needs_review"
        assert manifest["evidence_completion_claim"] == "rendered_status_media_metadata_captured"
        assert manifest["media_backend_result_paths"] == []

def main() -> None:
    test_extract_query_name_from_graphql_url()
    test_api_pages_boundaries_and_media_inventory()
    test_run_browser_capture_with_fake_executor_writes_artifacts()
    test_plan_only_run_without_live_is_not_completed()
    test_extract_rendered_dom_media_inventory_from_status_dom()
    test_rendered_dom_fallback_does_not_activate_for_wrong_tweet_id()
    test_run_browser_capture_uses_rendered_dom_fallback_for_api_404()
    test_run_browser_capture_with_rendered_dom_metadata_only_is_not_completed()
    print("twitter_browser_capture_runner_test OK")


if __name__ == "__main__":
    main()
