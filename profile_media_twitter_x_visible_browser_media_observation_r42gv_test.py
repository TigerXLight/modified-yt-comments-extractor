from __future__ import annotations

import json
import tempfile
from pathlib import Path

from profile_media_twitter_x_media_extraction_r42gt import LOCAL_FIXTURE_COPIED, REMOTE_NOT_DOWNLOADED
from profile_media_twitter_x_visible_browser_media_observation_r42gv import (
    BYTE_STATUS_REMOTE,
    R42GV_MARKER,
    R42GV_PASS_STATUS,
    build_report,
    build_review_window_database_projection,
    build_visible_browser_media_observation_store,
    project_visible_browser_observations_to_source_resources,
    write_r42gt_package_from_visible_browser_observations,
    write_report,
    write_visible_browser_media_observation_store,
)


def _events():
    return (
        {"url": "https://pbs.twimg.com/media/example.jpg?format=jpg&name=large", "content_type": "image/jpeg", "resource_type": "image"},
        {"url": "https://video.twimg.com/ext_tw_video/123/pu/pl/manifest.m3u8?tag=16", "content_type": "application/x-mpegURL", "resource_type": "media"},
        {"url": "https://video.twimg.com/ext_tw_video/123/pu/seg/00001.ts", "content_type": "video/mp2t", "resource_type": "media"},
        {"url": "https://video.twimg.com/ext_tw_video/123/pu/seg/00002.ts", "content_type": "video/mp2t", "resource_type": "media"},
        {"url": "https://video.twimg.com/ext_tw_video/123/pu/vid/720x720/example.mp4", "content_type": "video/mp4", "resource_type": "media"},
        {"url": "https://example.com/not-twitter.mp4", "content_type": "video/mp4", "resource_type": "media"},
    )


def test_build_store_from_visible_browser_events_and_segments() -> None:
    store = build_visible_browser_media_observation_store(
        source_url="https://x.com/user/status/123",
        events=_events(),
        capture_timestamp="20260914T000000Z",
    )
    assert store.marker == R42GV_MARKER
    assert store.status == R42GV_PASS_STATUS
    assert store.observation_count == 5
    assert store.segment_count == 2
    assert all(row.playlist_manifest_url for row in store.segment_rows)
    assert any(item.media_kind == "manifest" for item in store.observations)
    assert all(item.byte_status == BYTE_STATUS_REMOTE for item in store.observations)
    flags = store.to_dict()["side_effect_flags"]
    assert flags["visible_browser_session_observation_enabled"] is True
    assert flags["hidden_x_api_scraping_performed"] is False
    assert flags["remote_x_media_download_performed_by_r42gv"] is False


def test_projection_feeds_image_and_video_windows_without_segment_spam() -> None:
    store = build_visible_browser_media_observation_store(
        source_url="https://x.com/user/status/123",
        events=_events(),
        final_dom='<html><body><img src="https://pbs.twimg.com/media/dom.jpg?format=jpg&name=large"></body></html>',
        capture_timestamp="20260914T000000Z",
    )
    images, videos = project_visible_browser_observations_to_source_resources(store, source_row_id="row-1")
    assert images
    assert all(item.resource_kind == "image" for item in images)
    assert any(item.media_type == "stream" for item in videos)
    segment_summaries = [item for item in videos if item.status == "observed_segment_table"]
    assert len(segment_summaries) == 1
    assert segment_summaries[0].selectable is False
    assert "segment table" in segment_summaries[0].warning


def test_review_projection_and_writer_outputs() -> None:
    with tempfile.TemporaryDirectory(prefix="ytce_r42gv_store_") as tmp:
        store = build_visible_browser_media_observation_store(
            source_url="https://x.com/user/status/123",
            events=_events(),
            capture_timestamp="20260914T000000Z",
        )
        result = write_visible_browser_media_observation_store(store, tmp)
        assert Path(result.observation_store_path).exists()
        assert Path(result.observation_ndjson_path).read_text(encoding="utf-8").count("\n") == store.observation_count
        assert Path(result.segment_table_path).read_text(encoding="utf-8").count("\n") == store.segment_count
        projection = build_review_window_database_projection(store)
        assert projection["table_name"] == "twitter_x_visible_browser_media_observations"
        assert projection["segment_table_name"] == "twitter_x_visible_browser_media_segments"
        assert projection["review_window_rewrite_performed"] is False


def test_r42gt_bridge_metadata_only_and_session_local_hash() -> None:
    with tempfile.TemporaryDirectory(prefix="ytce_r42gv_r42gt_") as tmp:
        fixture = Path(tmp) / "frame.jpg"
        fixture.write_bytes(b"local session image bytes")
        store = build_visible_browser_media_observation_store(
            source_url="https://x.com/user/status/123",
            events=_events(),
            session_local_files=(
                {
                    "local_path": str(fixture),
                    "media_url": "https://pbs.twimg.com/media/frame.jpg?format=jpg&name=large",
                    "content_type": "image/jpeg",
                    "media_id": "frame-local",
                },
            ),
            capture_timestamp="20260914T000000Z",
        )
        package = write_r42gt_package_from_visible_browser_observations(store, Path(tmp) / "pkg", account_or_unknown="user")
        media_index = json.loads(Path(package.media_index_path).read_text(encoding="utf-8"))["media"]
        assert any(row["media_file_status"] == REMOTE_NOT_DOWNLOADED and not row.get("sha256") for row in media_index)
        assert any(row["media_file_status"] == LOCAL_FIXTURE_COPIED and row.get("sha256") for row in media_index)
        assert all(row.get("promotion_status") == "not_promoted_review_bridge_only" for row in media_index)


def test_runner_hook_writes_observation_store_with_injected_visible_session() -> None:
    from twitter_browser_capture_runner import BrowserCapturePayload, TwitterCapturedNetworkEvent, run_twitter_browser_capture

    def fake_executor(plan):
        return BrowserCapturePayload(
            events=(
                TwitterCapturedNetworkEvent(
                    url="https://pbs.twimg.com/media/hook.jpg?format=jpg&name=large",
                    status=200,
                    resource_type="image",
                    content_type="image/jpeg",
                ),
                TwitterCapturedNetworkEvent(
                    url="https://video.twimg.com/ext_tw_video/123/pu/pl/hook.m3u8",
                    status=200,
                    resource_type="media",
                    content_type="application/x-mpegURL",
                ),
                TwitterCapturedNetworkEvent(
                    url="https://video.twimg.com/ext_tw_video/123/pu/seg/hook00001.ts",
                    status=200,
                    resource_type="media",
                    content_type="video/mp2t",
                ),
            ),
            final_url=plan.canonical_url,
            final_dom="<html><body>visible X session</body></html>",
        )

    with tempfile.TemporaryDirectory(prefix="ytce_r42gv_runner_") as tmp:
        result = run_twitter_browser_capture(
            source_url="https://x.com/user/status/123",
            output_dir=tmp,
            browser_executor=fake_executor,
        )
        assert Path(result.visible_browser_media_observation_store_path).exists()
        assert Path(result.visible_browser_media_observation_ndjson_path).exists()
        assert Path(result.visible_browser_media_segment_table_path).exists()
        assert result.visible_browser_media_observation_count >= 3
        manifest = json.loads(Path(result.manifest_path).read_text(encoding="utf-8"))
        assert manifest["visible_browser_media_observation_count"] >= 3
        assert manifest["visible_browser_media_observation_store_path"].endswith("visible_browser_media_observations.json")


def test_report_green() -> None:
    with tempfile.TemporaryDirectory(prefix="ytce_r42gv_report_") as tmp:
        report = build_report(".", tmp)
        write_report(report, tmp)
        payload = report.to_dict()
        assert payload["marker"] == R42GV_MARKER
        assert payload["status"] == R42GV_PASS_STATUS
        assert payload["image_resource_count"] >= 2
        assert payload["video_audio_resource_count"] >= 2
        assert payload["side_effect_flags"]["hidden_x_api_scraping_performed"] is False
        assert Path(tmp, "R42GV_TWITTER_X_VISIBLE_BROWSER_MEDIA_OBSERVATION_STORE_REPORT.json").exists()


def run_self_test() -> None:
    test_build_store_from_visible_browser_events_and_segments()
    test_projection_feeds_image_and_video_windows_without_segment_spam()
    test_review_projection_and_writer_outputs()
    test_r42gt_bridge_metadata_only_and_session_local_hash()
    test_runner_hook_writes_observation_store_with_injected_visible_session()
    test_report_green()
    print("profile_media_twitter_x_visible_browser_media_observation_r42gv_test: PASS")


if __name__ == "__main__":
    run_self_test()
