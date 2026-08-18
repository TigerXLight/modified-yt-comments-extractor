from __future__ import annotations

from source_resource_state import RESOURCE_KIND_VIDEO_AUDIO, build_source_resource_row
from webpage_video_candidate_backend import WebpageVideoCandidate, WebpageVideoDiscoveryResult
from webpage_video_resource_bridge import webpage_video_resources_from_discovery


def test_webpage_video_candidates_convert_to_source_resources_with_jd_first_provenance() -> None:
    row = build_source_resource_row("https://example.com/article")
    discovery = WebpageVideoDiscoveryResult(
        source_url=row.canonical_url,
        canonical_url=row.canonical_url,
        discovery_method="static_html_plus_rendered_browser_video_probe",
        candidates=(
            WebpageVideoCandidate(
                candidate_id="c1",
                url="https://cdn.example.com/video/master.m3u8",
                kind="stream",
                mime_type="application/vnd.apple.mpegurl",
                extension=".m3u8",
                title="Main clip",
                thumbnail_url="https://cdn.example.com/poster.jpg",
                width=1280,
                height=720,
                source_tag="video",
                source_attr="src",
                detection_reason="video currentSrc after render",
                selected_by_default=True,
            ),
        ),
        recommended_backend_id="jdownloader_api3128_fast",
        route_preference="try_jdownloader_api3128_before_yt_dlp",
    )

    resources = webpage_video_resources_from_discovery(row, discovery)

    assert len(resources) == 1
    item = resources[0]
    assert item.resource_kind == RESOURCE_KIND_VIDEO_AUDIO
    assert item.reference_url.endswith("master.m3u8")
    assert item.display_name == "Main clip"
    assert item.media_type == "stream"
    assert item.extension == ".m3u8"
    assert item.thumbnail_reference == "https://cdn.example.com/poster.jpg"
    assert item.width == 1280
    assert item.height == 720
    assert item.selectable is True
    assert "route_preference=try_jdownloader_api3128_before_yt_dlp" in item.provenance
    assert "recommended_backend=jdownloader_api3128_fast" in item.provenance


def test_embedded_player_resource_is_kept_but_warns_about_jdownloader_crawler() -> None:
    row = build_source_resource_row("https://example.com/post")
    discovery = WebpageVideoDiscoveryResult(
        source_url=row.canonical_url,
        canonical_url=row.canonical_url,
        candidates=(
            WebpageVideoCandidate(
                candidate_id="embed",
                url="https://player.vimeo.com/video/123",
                kind="embed",
                source_tag="iframe",
                source_attr="src",
                selected_by_default=False,
            ),
        ),
        recommended_backend_id="jdownloader_api3128_fast",
    )

    resources = webpage_video_resources_from_discovery(row, discovery)

    assert len(resources) == 1
    assert resources[0].media_type == "embedded_player"
    assert "JDownloader crawler/API3128" in resources[0].warning


def run_self_test() -> None:
    test_webpage_video_candidates_convert_to_source_resources_with_jd_first_provenance()
    test_embedded_player_resource_is_kept_but_warns_about_jdownloader_crawler()


if __name__ == "__main__":
    run_self_test()
    print("webpage_video_resource_bridge_test OK")
