from tempfile import TemporaryDirectory
from urllib.request import urlopen

from capture_fixture_server import CaptureFixtureServer
from capture_media_discovery import MediaResource, discover_media_resources_from_html
from capture_media_download import (
    build_media_mux_plan,
    download_media_resource,
    is_allowed_media_download_url,
    safe_media_filename,
)
from capture_status import CAPTURE_STATUS_SUCCESS, CAPTURE_STATUS_UNSUPPORTED


def test_download_media_resource_from_localhost_fixture() -> None:
    with TemporaryDirectory() as tmpdir:
        # Keep the fixture server alive for the actual download.
        with CaptureFixtureServer() as server:
            page_url = server.url_for_fixture("media_playback")
            with urlopen(page_url, timeout=5) as response:
                html = response.read().decode("utf-8")
            resource = discover_media_resources_from_html(html, source_url=page_url).resources[0]
            result = download_media_resource(resource, output_folder=tmpdir)

        assert result.status == CAPTURE_STATUS_SUCCESS
        assert result.output_path.endswith("sample-video.mp4")
        assert result.size_bytes == len(b"fixture-video-bytes")
        assert result.sha256
        assert "external hosts" in result.scope


def test_download_media_resource_rejects_non_localhost_before_io() -> None:
    resource = MediaResource(
        resource_id="media_external",
        kind="video",
        url="https://example.com/video.mp4",
        source_tag="video",
    )

    with TemporaryDirectory() as tmpdir:
        result = download_media_resource(resource, output_folder=tmpdir)

    assert result.status == CAPTURE_STATUS_UNSUPPORTED
    assert result.output_path == ""
    assert "localhost fixture" in result.warnings[0]


def test_download_media_resource_rejects_blob_resource() -> None:
    resource = MediaResource(
        resource_id="media_blob",
        kind="blob",
        url="blob:fixture",
        source_tag="video",
        downloadable=False,
    )

    with TemporaryDirectory() as tmpdir:
        result = download_media_resource(resource, output_folder=tmpdir)

    assert result.status == CAPTURE_STATUS_UNSUPPORTED
    assert "not directly downloadable" in result.warnings[0]


def test_media_filename_and_allowed_url_helpers_are_strict() -> None:
    resource = MediaResource(
        resource_id="media_1",
        kind="video",
        url="http://127.0.0.1:1000/media/bad name.mp4?download=1",
        source_tag="video",
    )

    assert safe_media_filename(resource) == "bad_name.mp4"
    assert is_allowed_media_download_url("http://127.0.0.1:1/media.mp4")
    assert is_allowed_media_download_url("http://localhost:1/media.mp4")
    assert not is_allowed_media_download_url("https://example.com/media.mp4")
    assert not is_allowed_media_download_url("file:///tmp/media.mp4")


def test_media_mux_plan_is_plan_only_and_has_no_command() -> None:
    plan = build_media_mux_plan(
        video_resource_id="video_1",
        audio_resource_id="audio_1",
        output_filename="combined.mp4",
    )

    data = plan.to_dict()
    assert data["status"] == "plan_only"
    assert data["executable_command"] == []
    assert "muxing execution" in data["scope"]


def run_self_test() -> None:
    test_download_media_resource_from_localhost_fixture()
    test_download_media_resource_rejects_non_localhost_before_io()
    test_download_media_resource_rejects_blob_resource()
    test_media_filename_and_allowed_url_helpers_are_strict()
    test_media_mux_plan_is_plan_only_and_has_no_command()


if __name__ == "__main__":
    run_self_test()
    print("Capture media download self-test passed.")
