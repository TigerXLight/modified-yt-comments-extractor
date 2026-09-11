from __future__ import annotations

import json
import tempfile
from pathlib import Path

from webpage_video_api3128_route_validation_r42gb import (
    STATUS_PLAN_ONLY,
    STATUS_UNSUPPORTED,
    build_route_decision_sample,
    validate_selected_webpage_media_api3128_route,
    write_r42gb_validation_report,
)


def test_public_selected_webpage_media_prefers_api3128() -> None:
    file_decision = build_route_decision_sample(
        media_url="https://cdn.example.test/1024x576_MP4_clip.mp4",
        source_url="https://metro.co.uk/story",
        kind="file",
        extension=".mp4",
        mime_type="video/mp4",
    )
    assert file_decision.should_attempt_api3128_first is True
    assert file_decision.plan_status == STATUS_PLAN_ONLY
    assert file_decision.route_used == "api3128"
    assert file_decision.backend_id == "jdownloader_internal"
    assert file_decision.yt_dlp_role == "fallback_only_after_jdownloader_api3128"


def test_stream_and_embed_candidates_prefer_api3128() -> None:
    stream = build_route_decision_sample(
        media_url="https://cdn.example.test/master.m3u8",
        source_url="https://metro.co.uk/story",
        kind="stream",
        extension=".m3u8",
        mime_type="application/vnd.apple.mpegurl",
    )
    embed = build_route_decision_sample(
        media_url="https://player.vimeo.com/video/12345",
        source_url="https://metro.co.uk/story",
        kind="embed",
    )
    assert stream.should_attempt_api3128_first is True
    assert stream.plan_status == STATUS_PLAN_ONLY
    assert embed.should_attempt_api3128_first is True
    assert embed.plan_status == STATUS_PLAN_ONLY


def test_localhost_fixture_stays_direct_local_path() -> None:
    local = build_route_decision_sample(
        media_url="http://127.0.0.1:8765/video.mp4",
        source_url="http://127.0.0.1:8765/page.html",
        kind="file",
        extension=".mp4",
        mime_type="video/mp4",
    )
    assert local.should_attempt_api3128_first is False
    assert local.plan_status == STATUS_UNSUPPORTED
    assert "direct/local" in local.warning


def test_current_source_tree_static_route_order() -> None:
    report = validate_selected_webpage_media_api3128_route(Path(__file__).resolve().parent)
    assert report.passed, json.dumps(report.to_dict(), indent=2)
    check_ids = {check.check_id for check in report.checks}
    assert "api3128_decision_before_direct_fetch" in check_ids
    assert "api3128_handoff_before_direct_fetch" in check_ids
    assert "stream_candidates_do_not_silently_fall_back_to_direct_fetch" in check_ids


def test_report_writer_outputs_json_and_markdown() -> None:
    report = validate_selected_webpage_media_api3128_route(Path(__file__).resolve().parent)
    with tempfile.TemporaryDirectory() as tmp:
        json_path, md_path = write_r42gb_validation_report(report, tmp)
        payload = json.loads(json_path.read_text(encoding="utf-8"))
        markdown = md_path.read_text(encoding="utf-8")
    assert payload["passed"] is True
    assert "R42GB selected webpage media API3128/JDownloader route validation" in markdown
    assert "no network fetch" in markdown


def run_self_test() -> None:
    test_public_selected_webpage_media_prefers_api3128()
    test_stream_and_embed_candidates_prefer_api3128()
    test_localhost_fixture_stays_direct_local_path()
    test_current_source_tree_static_route_order()
    test_report_writer_outputs_json_and_markdown()


if __name__ == "__main__":
    run_self_test()
    print("webpage_video_api3128_route_validation_r42gb_test OK")
