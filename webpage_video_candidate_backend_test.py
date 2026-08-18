from __future__ import annotations

from webpage_video_candidate_backend import (
    VIDEO_CANDIDATE_KIND_EMBED,
    VIDEO_CANDIDATE_KIND_FILE,
    VIDEO_CANDIDATE_KIND_STREAM,
    classify_video_candidate_url,
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


def test_classifies_video_file_and_stream_urls() -> None:
    assert classify_video_candidate_url("https://cdn.example/video.mp4")[0] == VIDEO_CANDIDATE_KIND_FILE
    assert classify_video_candidate_url("https://cdn.example/master.m3u8")[0] == VIDEO_CANDIDATE_KIND_STREAM
    assert classify_video_candidate_url("https://player.vimeo.com/video/123")[0] == VIDEO_CANDIDATE_KIND_EMBED


def test_discovers_static_video_sources_and_meta() -> None:
    html = """
    <html><head>
      <meta property="og:video" content="/share/preview.mp4">
    </head><body>
      <video width="1280" height="720" poster="poster.jpg">
        <source src="https://cdn.example.com/video-720.mp4" type="video/mp4">
        <source src="https://cdn.example.com/master.m3u8" type="application/vnd.apple.mpegurl">
      </video>
      <iframe src="https://player.vimeo.com/video/12345"></iframe>
      <a href="/not-video.html">ignore</a>
    </body></html>
    """
    result = discover_webpage_video_candidates_from_html(
        "https://news.example/article",
        html,
        capability_decision=_decision(),
    )
    assert result.candidate_count == 4
    urls = {item.url for item in result.candidates}
    assert "https://news.example/share/preview.mp4" in urls
    assert "https://cdn.example.com/video-720.mp4" in urls
    assert "https://cdn.example.com/master.m3u8" in urls
    assert "https://player.vimeo.com/video/12345" in urls
    kinds = summarize_webpage_video_candidate_kinds(result.candidates)
    assert kinds[VIDEO_CANDIDATE_KIND_FILE] == 2
    assert kinds[VIDEO_CANDIDATE_KIND_STREAM] == 1
    assert kinds[VIDEO_CANDIDATE_KIND_EMBED] == 1
    assert result.recommended_backend_id == "jdownloader_internal"
    assert result.to_dict()["jdownloader_capability_decision"]["yt_dlp_role"] == "fallback_only_after_jdownloader_routes"


def test_deduplicates_repeated_urls() -> None:
    html = """
    <video src="https://cdn.example.com/same.mp4"></video>
    <a href="https://cdn.example.com/same.mp4">same</a>
    """
    result = discover_webpage_video_candidates_from_html(
        "https://example.com/page",
        html,
        capability_decision=_decision(),
    )
    assert result.candidate_count == 1
    assert result.candidates[0].selected_by_default is True


def main() -> None:
    test_classifies_video_file_and_stream_urls()
    test_discovers_static_video_sources_and_meta()
    test_deduplicates_repeated_urls()
    print("webpage_video_candidate_backend_test OK")


if __name__ == "__main__":
    main()
