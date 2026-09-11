from __future__ import annotations

import json
import tempfile
from pathlib import Path

from webpage_video_api3128_route_r42fx import (
    API3128_ROUTE_USED,
    STATUS_PLAN_ONLY,
    STATUS_SUCCESS,
    STATUS_UNSUPPORTED,
    build_webpage_video_api3128_handoff_plan,
    is_public_web_media_candidate,
    run_webpage_video_api3128_handoff,
    should_attempt_webpage_video_api3128_first,
)


def test_public_media_route_decision() -> None:
    assert is_public_web_media_candidate("https://cdn.example.test/video.mp4")
    assert not is_public_web_media_candidate("http://127.0.0.1:8765/video.mp4")
    assert should_attempt_webpage_video_api3128_first("https://cdn.example.test/video.mp4")
    assert should_attempt_webpage_video_api3128_first("https://cdn.example.test/master.m3u8")
    assert should_attempt_webpage_video_api3128_first(
        "https://player.example.test/embed/123",
        kind="embed",
        source_url="https://news.example.test/story",
    )
    assert not should_attempt_webpage_video_api3128_first("blob:https://example.test/abc")


def test_plan_is_side_effect_free_and_serializable() -> None:
    plan = build_webpage_video_api3128_handoff_plan(
        media_url="https://cdn.example.test/video.mp4",
        source_url="https://metro.co.uk/story",
        output_dir="out",
        resource_id="resource 1",
        display_name="Metro video",
    )
    payload = plan.to_dict()
    assert plan.status == STATUS_PLAN_ONLY
    assert plan.route_used == API3128_ROUTE_USED
    assert payload["side_effects_performed"] is False
    assert payload["yt_dlp_role"] == "fallback_only_after_jdownloader_api3128"
    json.dumps(payload)


def test_injected_backend_reports_completed_file() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        output = Path(tmp)
        completed = output / "downloaded.mp4"
        completed.write_bytes(b"media")
        manifest = output / "manifest.json"
        manifest.write_text(json.dumps({"files": [{"path": str(completed)}]}), encoding="utf-8")
        plan = build_webpage_video_api3128_handoff_plan(
            media_url="https://cdn.example.test/video.mp4",
            output_dir=str(output),
            source_url="https://metro.co.uk/story",
            resource_id="metro-video",
        )

        def fake_builder(**kwargs):
            assert kwargs["source_url"] == "https://cdn.example.test/video.mp4"
            assert kwargs["source_adapter_id"] == "webpage"
            assert kwargs["video"] is True
            assert kwargs["audio"] is True
            return {"manifest_path": str(manifest)}

        def fake_runner(request, internal_job_runner=None):
            return {"status": "success", "manifest_path": str(manifest), "message": "ok"}

        result = run_webpage_video_api3128_handoff(
            plan,
            request_builder=fake_builder,
            backend_runner=fake_runner,
        )
        assert result.status == STATUS_SUCCESS
        assert result.local_file_paths == (str(completed),)
        assert result.side_effects_performed is True


def test_unsupported_localhost_candidate_remains_direct_path() -> None:
    plan = build_webpage_video_api3128_handoff_plan(
        media_url="http://127.0.0.1:8765/video.mp4",
        output_dir="out",
        resource_id="local-fixture",
    )
    assert plan.status == STATUS_UNSUPPORTED


if __name__ == "__main__":
    test_public_media_route_decision()
    test_plan_is_side_effect_free_and_serializable()
    test_injected_backend_reports_completed_file()
    test_unsupported_localhost_candidate_remains_direct_path()
    print("webpage_video_api3128_route_r42fx_test OK")
