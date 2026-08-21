from __future__ import annotations

from webpage_rendered_video_probe_backend import (
    RENDERED_VIDEO_PROBE_SCRIPT,
    VIDEO_DISCOVERY_METHOD_RENDERED_BROWSER,
    discover_rendered_webpage_video_candidates_from_probe_payload,
)
from webpage_video_candidate_backend import (
    VIDEO_CANDIDATE_KIND_EMBED,
    VIDEO_CANDIDATE_KIND_FILE,
    VIDEO_CANDIDATE_KIND_STREAM,
    summarize_webpage_video_candidate_kinds,
)


def _decision() -> dict[str, object]:
    return {
        "recommended_backend_id": "jdownloader_internal",
        "api3128_preferred": True,
        "decision_label": "try JDownloader API3128 first",
        "yt_dlp_role": "fallback_only_after_jdownloader_routes",
    }


def test_probe_payload_discovers_dom_performance_and_network_media() -> None:
    payload = {
        "location_href": "https://example.test/article",
        "document_title": "Rendered article",
        "records": [
            {
                "tag": "video",
                "attr": "currentSrc",
                "url": "/media/clip.mp4",
                "mime_type": "video/mp4",
                "width": 1920,
                "height": 1080,
                "detection_reason": "video currentSrc after render",
                "thumbnail_url": "/poster.jpg",
            },
            {
                "tag": "performance",
                "attr": "name",
                "url": "https://cdn.example.test/master.m3u8",
                "detection_reason": "performance resource fetch",
            },
            {
                "tag": "iframe",
                "attr": "src",
                "url": "https://x.com/i/videos/12345",
                "detection_reason": "rendered iframe embed",
            },
            {
                "tag": "a",
                "attr": "href",
                "url": "/plain-article.html",
            },
        ],
        "network_urls": [
            {
                "url": "https://cdn.example.test/manifest.mpd",
                "content_type": "application/dash+xml",
                "detection_reason": "browser network response",
            },
            "https://cdn.example.test/duplicate/master.m3u8",
        ],
    }
    result = discover_rendered_webpage_video_candidates_from_probe_payload(
        "https://example.test/article",
        payload,
        capability_decision=_decision(),
    )
    assert result.discovery_method == VIDEO_DISCOVERY_METHOD_RENDERED_BROWSER
    assert result.candidate_count == 5
    urls = {candidate.url for candidate in result.candidates}
    assert "https://example.test/media/clip.mp4" in urls
    assert any(candidate.thumbnail_url == "https://example.test/poster.jpg" for candidate in result.candidates if candidate.url.endswith("clip.mp4"))
    assert "https://cdn.example.test/master.m3u8" in urls
    assert "https://cdn.example.test/manifest.mpd" in urls
    assert "https://cdn.example.test/duplicate/master.m3u8" in urls
    assert "https://x.com/i/videos/12345" in urls
    kinds = summarize_webpage_video_candidate_kinds(result.candidates)
    assert kinds[VIDEO_CANDIDATE_KIND_FILE] == 1
    assert kinds[VIDEO_CANDIDATE_KIND_STREAM] == 3
    assert kinds[VIDEO_CANDIDATE_KIND_EMBED] == 1
    assert result.recommended_backend_id == "jdownloader_internal"
    assert result.to_dict()["jdownloader_capability_decision"]["yt_dlp_role"] == "fallback_only_after_jdownloader_routes"


def test_probe_payload_deduplicates_and_reports_json_warning() -> None:
    result = discover_rendered_webpage_video_candidates_from_probe_payload(
        "https://example.test/page",
        '{"records":[{"tag":"video","attr":"src","url":"/same.webm"},{"tag":"a","attr":"href","url":"/same.webm"}]}',
        capability_decision=_decision(),
    )
    assert result.candidate_count == 1
    assert result.candidates[0].url == "https://example.test/same.webm"
    bad = discover_rendered_webpage_video_candidates_from_probe_payload(
        "https://example.test/page",
        "{not json",
        capability_decision=_decision(),
    )
    assert bad.candidate_count == 0
    assert bad.warnings


def test_probe_script_contains_dom_and_resource_hooks() -> None:
    assert "querySelectorAll('video,audio')" in RENDERED_VIDEO_PROBE_SCRIPT
    assert "currentSrc" in RENDERED_VIDEO_PROBE_SCRIPT
    assert "performance.getEntriesByType('resource')" in RENDERED_VIDEO_PROBE_SCRIPT
    assert "pageThumbnailUrl" in RENDERED_VIDEO_PROBE_SCRIPT
    assert "parentPoster" in RENDERED_VIDEO_PROBE_SCRIPT
    assert "twitter:player:stream" in RENDERED_VIDEO_PROBE_SCRIPT



def test_probe_payload_rejects_social_share_links() -> None:
    payload = {
        "location_href": "https://example.test/article",
        "document_title": "Article",
        "records": [
            {"tag": "a", "attr": "href", "url": "https://x.com/intent/tweet?text=Share&url=https://example.test/article", "title": "Share this article via X"},
            {"tag": "a", "attr": "href", "url": "https://www.facebook.com/sharer/sharer.php?u=https://example.test/article", "title": "Share this article via Facebook"},
            {"tag": "iframe", "attr": "src", "url": "https://x.com/i/videos/12345", "title": "Embedded X video"},
        ],
    }
    result = discover_rendered_webpage_video_candidates_from_probe_payload(
        "https://example.test/article",
        payload,
        capability_decision=_decision(),
    )
    assert result.candidate_count == 1
    assert result.candidates[0].url == "https://x.com/i/videos/12345"


def test_payload_page_thumbnail_fills_network_candidates() -> None:
    payload = {
        "location_href": "https://metro.example/story",
        "document_title": "Metro style story",
        "page_thumbnail_url": "/article-thumb.jpg",
        "network_urls": [
            {
                "url": "https://videos.example.com/core.mp4",
                "content_type": "video/mp4",
                "detection_reason": "browser network response",
            }
        ],
    }
    result = discover_rendered_webpage_video_candidates_from_probe_payload(
        "https://metro.example/story",
        payload,
        capability_decision=_decision(),
    )
    assert result.candidate_count == 1
    assert result.candidates[0].thumbnail_url == "https://metro.example/article-thumb.jpg"

def main() -> None:
    test_probe_payload_discovers_dom_performance_and_network_media()
    test_probe_payload_deduplicates_and_reports_json_warning()
    test_probe_payload_rejects_social_share_links()
    test_payload_page_thumbnail_fills_network_candidates()
    test_probe_script_contains_dom_and_resource_hooks()
    print("webpage_rendered_video_probe_backend_test OK")


if __name__ == "__main__":
    main()



def test_bounded_direct_rendered_video_candidates_filters_and_caps() -> None:
    from webpage_rendered_video_probe_backend import bounded_direct_rendered_video_candidates

    records = []
    for index in range(18):
        records.append(
            {
                "tag": "performance",
                "attr": "name",
                "url": f"https://videos.example.test/path/{index:03d}_1024x576_MP4_clip.mp4",
                "mime_type": "video/mp4",
                "detection_reason": "performance resource fetch",
            }
        )
    records.extend(
        [
            {
                "tag": "performance",
                "attr": "name",
                "url": "https://videos.example.test/path/master.m3u8",
                "mime_type": "application/vnd.apple.mpegurl",
            },
            {
                "tag": "iframe",
                "attr": "src",
                "url": "https://player.example.test/embed/123",
            },
        ]
    )
    result = bounded_direct_rendered_video_candidates(
        "https://example.test/article",
        {"location_href": "https://example.test/article", "records": records},
        max_candidates=8,
        capability_decision=_decision(),
    )
    assert result.discovery_method == "fast_bounded_rendered_direct_media_probe"
    assert result.candidate_count == 8
    assert all(candidate.kind == VIDEO_CANDIDATE_KIND_FILE for candidate in result.candidates)
    assert all(candidate.extension == ".mp4" for candidate in result.candidates)
    assert not any(".m3u8" in candidate.url for candidate in result.candidates)
