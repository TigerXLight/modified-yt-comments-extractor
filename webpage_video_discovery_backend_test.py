from __future__ import annotations

from webpage_video_discovery_backend import (
    VIDEO_DISCOVERY_METHOD_MERGED,
    discover_webpage_video_candidates,
    merge_webpage_video_discovery_results,
    summarize_merged_webpage_video_discovery,
)
from webpage_rendered_video_probe_backend import discover_rendered_webpage_video_candidates_from_probe_payload
from webpage_video_candidate_backend import (
    VIDEO_CANDIDATE_KIND_EMBED,
    VIDEO_CANDIDATE_KIND_FILE,
    VIDEO_CANDIDATE_KIND_STREAM,
    discover_webpage_video_candidates_from_html,
    summarize_webpage_video_candidate_kinds,
)


def _decision() -> dict[str, object]:
    return {
        "recommended_backend_id": "jdownloader_internal",
        "api3128_preferred": True,
        "decision_label": "try JDownloader API3128 first",
        "yt_dlp_role": "fallback_only_after_jdownloader_routes",
    }


def test_merges_static_and_rendered_candidates_and_deduplicates() -> None:
    html = """
    <video src="/media/clip.mp4"></video>
    <iframe src="https://player.vimeo.com/video/12345"></iframe>
    """
    payload = {
        "location_href": "https://example.test/article",
        "document_title": "Rendered title",
        "records": [
            {
                "tag": "video",
                "attr": "currentSrc",
                "url": "/media/clip.mp4#t=0",
                "mime_type": "video/mp4",
                "width": 1920,
                "height": 1080,
                "detection_reason": "rendered video currentSrc after render",
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
        ],
    }
    result = discover_webpage_video_candidates(
        "https://example.test/article",
        html_text=html,
        rendered_probe_payload=payload,
        capability_decision=_decision(),
    )
    assert result.discovery_method == VIDEO_DISCOVERY_METHOD_MERGED
    assert result.candidate_count == 4
    urls = {candidate.url for candidate in result.candidates}
    assert "https://example.test/media/clip.mp4#t=0" in urls
    assert "https://player.vimeo.com/video/12345" in urls
    assert "https://cdn.example.test/master.m3u8" in urls
    assert "https://x.com/i/videos/12345" in urls
    clip = [candidate for candidate in result.candidates if "clip.mp4" in candidate.url][0]
    assert clip.width == 1920
    assert clip.height == 1080
    kinds = summarize_webpage_video_candidate_kinds(result.candidates)
    assert kinds[VIDEO_CANDIDATE_KIND_FILE] == 1
    assert kinds[VIDEO_CANDIDATE_KIND_STREAM] == 1
    assert kinds[VIDEO_CANDIDATE_KIND_EMBED] == 2
    assert result.to_dict()["jdownloader_capability_decision"]["yt_dlp_role"] == "fallback_only_after_jdownloader_routes"


def test_merge_result_prefers_existing_decision_and_preserves_warnings() -> None:
    static = discover_webpage_video_candidates_from_html(
        "https://example.test/page",
        '<meta property="og:video" content="/preview.mp4">',
        capability_decision=_decision(),
    )
    rendered = discover_rendered_webpage_video_candidates_from_probe_payload(
        "https://example.test/page",
        "{not json",
        capability_decision=_decision(),
    )
    result = merge_webpage_video_discovery_results("https://example.test/page", [static, rendered])
    assert result.candidate_count == 1
    assert result.warnings
    assert result.recommended_backend_id == "jdownloader_internal"


def test_summary_is_activity_log_safe_and_no_input_warns() -> None:
    result = discover_webpage_video_candidates(
        "https://example.test/empty",
        capability_decision=_decision(),
    )
    assert result.candidate_count == 0
    assert result.warnings
    summary = summarize_merged_webpage_video_discovery(result)
    assert summary["discovery_method"] == VIDEO_DISCOVERY_METHOD_MERGED
    assert summary["api3128_preferred"] is True
    assert summary["yt_dlp_role"] == "fallback_only_after_jdownloader_routes"
    assert summary["warning_count"] == 1


def main() -> None:
    test_merges_static_and_rendered_candidates_and_deduplicates()
    test_merge_result_prefers_existing_decision_and_preserves_warnings()
    test_summary_is_activity_log_safe_and_no_input_warns()
    print("webpage_video_discovery_backend_test OK")


if __name__ == "__main__":
    main()
