from urllib.request import urlopen

from capture_fixture_server import CaptureFixtureServer
from capture_media_discovery import (
    MEDIA_RESOURCE_KIND_BLOB,
    MEDIA_RESOURCE_KIND_IMAGE,
    MEDIA_RESOURCE_KIND_VIDEO,
    discover_media_resources_from_html,
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
    assert "playback-observation" in resource.warnings[0]


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
    test_media_discovery_marks_blob_media_as_playback_required()
    test_media_discovery_reports_empty_html()
    test_media_discovery_from_localhost_fixture()
    test_media_discovery_from_image_reference()


if __name__ == "__main__":
    run_self_test()
    print("Capture media discovery self-test passed.")
