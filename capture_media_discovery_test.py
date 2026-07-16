from urllib.request import urlopen

from capture_fixture_server import CaptureFixtureServer, fixture_by_id
from capture_media_discovery import (
    MEDIA_DISCOVERY_PLAYBACK_EVENT,
    MEDIA_DISCOVERY_REQUEST_LOG,
    MEDIA_MANIFEST_DASH,
    MEDIA_MANIFEST_HLS,
    MEDIA_RESOURCE_KIND_AUDIO,
    MEDIA_RESOURCE_KIND_BLOB,
    MEDIA_RESOURCE_KIND_FRAME,
    MEDIA_RESOURCE_KIND_IMAGE,
    MEDIA_RESOURCE_KIND_MANIFEST,
    MEDIA_RESOURCE_KIND_VIDEO,
    discover_media_resources_from_html,
    discover_media_resources_from_playback_events,
    discover_media_resources_from_request_log,
)
from capture_status import DRM_NONE_DETECTED, DRM_UNKNOWN


def test_media_discovery_extracts_direct_media_references() -> None:
    result = discover_media_resources_from_html(
        """
        <video src="/media/movie.mp4" type="video/mp4"></video>
        <audio src="/media/audio.m4a" type="audio/mp4"></audio>
        <img src="/media/image.jpg" alt="Still">
        """,
        source_url="http://127.0.0.1:8000/media/page",
    )

    assert [resource.kind for resource in result.resources] == ["video", "audio", "image"]
    assert result.resources[0].url == "http://127.0.0.1:8000/media/movie.mp4"
    assert result.resources[0].mime_type == "video/mp4"
    assert result.resources[0].drm_status == DRM_NONE_DETECTED
    assert result.resources[2].display_name == "Still"
    assert "no fetch" in result.scope


def test_media_discovery_extracts_dom_poster_srcset_and_frame_candidates() -> None:
    result = discover_media_resources_from_html(
        fixture_by_id("media_basic").body + fixture_by_id("media_srcset").body + fixture_by_id("media_iframe").body,
        source_url="http://127.0.0.1:8000/page",
    )

    kinds = [resource.kind for resource in result.resources]
    assert MEDIA_RESOURCE_KIND_VIDEO in kinds
    assert MEDIA_RESOURCE_KIND_AUDIO in kinds
    assert MEDIA_RESOURCE_KIND_IMAGE in kinds
    assert MEDIA_RESOURCE_KIND_FRAME in kinds
    assert any(resource.source_tag == "poster" for resource in result.resources)
    assert any(resource.url.endswith("/media/still-large.webp") for resource in result.resources)
    assert any(resource.frame_reference == "fixture player" for resource in result.resources)


def test_media_discovery_detects_hls_and_dash_manifest_references() -> None:
    hls = discover_media_resources_from_html(fixture_by_id("media_hls").body, source_url="http://localhost:9000")
    dash = discover_media_resources_from_html(fixture_by_id("media_dash").body, source_url="http://localhost:9000")

    assert hls.resources[0].kind == MEDIA_RESOURCE_KIND_MANIFEST
    assert hls.resources[0].manifest_kind == MEDIA_MANIFEST_HLS
    assert hls.resources[0].downloadable is False
    assert dash.resources[0].manifest_kind == MEDIA_MANIFEST_DASH
    assert dash.resources[0].presentation_id == "dash-main"


def test_media_discovery_marks_blob_media_as_playback_required() -> None:
    result = discover_media_resources_from_html(
        '<video data-fixture="blob"></video>',
        source_url="http://127.0.0.1:8000/media/blob",
    )

    assert len(result.resources) == 1
    resource = result.resources[0]
    assert resource.kind == MEDIA_RESOURCE_KIND_BLOB
    assert resource.downloadable is False
    assert resource.requires_playback is True
    assert resource.drm_status == DRM_UNKNOWN
    assert "MediaSource" in resource.warnings[0]


def test_media_discovery_preserves_signed_url_fixture_metadata() -> None:
    result = discover_media_resources_from_html(fixture_by_id("media_signed").body, source_url="http://localhost:9000")

    assert result.resources[0].signed_url is True
    assert result.resources[0].expiry_hint == "2026-07-16T12:00:00Z"
    assert result.resources[0].url.endswith("/media/signed-video.mp4?sig=fixture")


def test_media_discovery_from_supplied_request_log_only() -> None:
    result = discover_media_resources_from_request_log(
        (
            {
                "request_id": "req-1",
                "url": "/media/video-track.mp4",
                "mime_type": "video/mp4",
                "component_role": "video",
                "presentation_id": "p1",
                "codec": "avc1",
            },
            {
                "request_id": "req-2",
                "url": "/media/audio-track.m4a",
                "mime_type": "audio/mp4",
                "component_role": "audio",
                "presentation_id": "p1",
                "language": "en",
            },
        ),
        source_url="http://127.0.0.1:8000/page",
    )

    assert [resource.kind for resource in result.resources] == [MEDIA_RESOURCE_KIND_VIDEO, MEDIA_RESOURCE_KIND_AUDIO]
    assert result.resources[0].discovery_methods == (MEDIA_DISCOVERY_REQUEST_LOG,)
    assert result.resources[0].component_role == "video"
    assert result.resources[1].language == "en"


def test_media_discovery_from_supplied_playback_events_only() -> None:
    result = discover_media_resources_from_playback_events(
        (
            {
                "event_id": "playback-1",
                "url": "/media/segment-1.m4s",
                "mime_type": "video/iso.segment",
                "component_role": "video",
            },
        ),
        source_url="http://127.0.0.1:8000/page",
    )

    assert len(result.resources) == 1
    assert result.resources[0].requires_playback is True
    assert result.resources[0].discovery_methods == (MEDIA_DISCOVERY_PLAYBACK_EVENT,)
    assert result.resources[0].request_reference == "playback-1"


def test_media_discovery_reports_empty_html() -> None:
    result = discover_media_resources_from_html("<html><body>No media</body></html>")

    assert result.resources == ()
    assert "No media resources found" in result.warnings[0]


def test_media_discovery_from_localhost_fixture() -> None:
    with CaptureFixtureServer() as server:
        url = server.url_for_fixture("media_playback")
        with urlopen(url, timeout=5) as response:
            html = response.read().decode("utf-8")

    result = discover_media_resources_from_html(html, source_url=url)
    assert len(result.resources) == 1
    assert result.resources[0].kind == MEDIA_RESOURCE_KIND_VIDEO
    assert result.resources[0].url.endswith("/media/sample-video.mp4")


def test_media_discovery_from_image_reference() -> None:
    result = discover_media_resources_from_html(
        '<img src="still.png" alt="Still frame">',
        source_url="http://localhost:9000/page",
    )

    assert result.resources[0].kind == MEDIA_RESOURCE_KIND_IMAGE
    assert result.resources[0].url == "http://localhost:9000/still.png"


def run_self_test() -> None:
    test_media_discovery_extracts_direct_media_references()
    test_media_discovery_extracts_dom_poster_srcset_and_frame_candidates()
    test_media_discovery_detects_hls_and_dash_manifest_references()
    test_media_discovery_marks_blob_media_as_playback_required()
    test_media_discovery_preserves_signed_url_fixture_metadata()
    test_media_discovery_from_supplied_request_log_only()
    test_media_discovery_from_supplied_playback_events_only()
    test_media_discovery_reports_empty_html()
    test_media_discovery_from_localhost_fixture()
    test_media_discovery_from_image_reference()


if __name__ == "__main__":
    run_self_test()
    print("Capture media discovery self-test passed.")
