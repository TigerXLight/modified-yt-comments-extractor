from __future__ import annotations

import hashlib
import json
import tempfile
from pathlib import Path

from rendered_citation_media_intake_v77e import (
    WRITE_RENDERED_CITATION_MEDIA_INTAKE_V77E,
    build_rendered_citation_media_intake_manifest,
    render_rendered_citation_media_intake_summary,
    write_rendered_citation_media_intake_manifest,
)


def test_ingest_existing_text_fixture_as_transcript() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "transcript.txt"
        data = b"Speaker: visible local transcript text\n"
        path.write_bytes(data)
        manifest = build_rendered_citation_media_intake_manifest(
            source_url="https://x.com/example/status/123",
            page_url="https://x.com/example/status/123",
            media_url="https://video.example/media.mp4",
            source_unit_path="Sources/Social Media/Online/X/example",
            user_declared_purpose="source_preservation",
            capture_kind="subtitle_caption_capture",
            capture_method="local_file_preservation",
            media_position_start="00:00:05",
            media_position_end="00:00:10",
            local_file_path=str(path),
            local_file_role="transcript",
            created_at_utc="2026-08-17T00:00:00Z",
        )
        assert manifest.schema_version == "rendered-citation-media-intake-v77e"
        assert manifest.local_file_present is True
        assert manifest.local_file_size == len(data)
        assert manifest.local_file_sha256 == hashlib.sha256(data).hexdigest()
        assert manifest.local_file_role == "transcript"
        assert manifest.source_unit_attachment.attached_to_source_unit is True
        assert manifest.source_unit_attachment.attachment_scope == "twitter_x_source_unit"
        assert manifest.rendered_citation_metadata["schema_version"] == "rendered-citation-recording-metadata-v77d"


def test_fake_screenshot_fixture_is_classified_without_pixel_open() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "screenshot.png"
        data = b"not a real png but an existing local placeholder"
        path.write_bytes(data)
        manifest = build_rendered_citation_media_intake_manifest(
            source_url="https://example.com/article",
            page_url="https://example.com/article",
            source_unit_path="Sources/Articles/Example/17 August",
            user_declared_purpose="review",
            capture_kind="still_frame",
            capture_method="ordinary_windows_screen_capture",
            local_file_path=str(path),
            local_file_role="screenshot",
            created_at_utc="2026-08-17T00:00:00Z",
        )
        assert manifest.local_file_name == "screenshot.png"
        assert manifest.local_file_extension == ".png"
        assert manifest.local_file_mime_type == "image/png"
        assert manifest.local_file_role == "screenshot"
        assert manifest.source_unit_attachment.attachment_scope == "article_source_unit"


def test_blocked_capture_placeholder_without_local_file() -> None:
    manifest = build_rendered_citation_media_intake_manifest(
        source_url="https://example.com/source",
        page_url="https://example.com/source",
        source_unit_path="Sources/Social Media/Online/YouTube/example",
        user_declared_purpose="source_preservation",
        capture_kind="blocked_capture_state",
        capture_method="ordinary_browser_visible_capture",
        local_file_role="blocked_capture_placeholder",
        capture_blocked=True,
        blocked_reason="captcha_or_challenge_required",
        human_mediated_access_required=True,
        human_mediated_access_completed_by_user=True,
        created_at_utc="2026-08-17T00:00:00Z",
    )
    assert manifest.local_file_present is False
    assert manifest.blocked_capture["blocked"] is True
    assert manifest.blocked_capture["reason"] == "captcha_or_challenge_required"
    assert manifest.human_mediated_access["required"] is True
    assert manifest.human_mediated_access["completed_by_user"] is True
    assert manifest.human_mediated_access["program_solved_challenge"] is False
    assert manifest.human_mediated_access["solver_service_used"] is False
    assert manifest.human_mediated_access["anti_detection_used"] is False
    assert manifest.source_unit_attachment.attachment_scope == "social_video_source_unit"


def test_safety_flags_remain_false() -> None:
    manifest = build_rendered_citation_media_intake_manifest(
        source_url="https://example.com/source",
        page_url="https://example.com/source",
        user_declared_purpose="research",
        capture_kind="source_reference_only" if False else "still_frame",
        capture_method="source_reference_only",
        local_file_role="source_reference_only",
        created_at_utc="2026-08-17T00:00:00Z",
    )
    flags = manifest.safety_flags
    assert flags.browser_launch_performed is False
    assert flags.web_download_performed is False
    assert flags.media_download_performed is False
    assert flags.recording_performed is False
    assert flags.drm_circumvention_performed is False
    assert flags.hidden_protected_stream_extraction_performed is False
    assert flags.captcha_solver_used is False
    assert flags.credential_automation_performed is False
    assert flags.proxy_or_evasion_performed is False
    assert flags.forced_rate_limit_bypass_performed is False
    assert flags.write_actions_performed is False


def test_write_requires_confirmation_token() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        output = Path(tmp) / "intake.json"
        manifest = build_rendered_citation_media_intake_manifest(
            source_url="https://example.com/source",
            page_url="https://example.com/source",
            user_declared_purpose="quotation",
            capture_kind="still_frame",
            capture_method="source_reference_only",
            local_file_role="source_reference_only",
            created_at_utc="2026-08-17T00:00:00Z",
        )
        try:
            write_rendered_citation_media_intake_manifest(manifest, output, confirm_write="")
        except PermissionError:
            pass
        else:
            raise AssertionError("write without confirmation token should fail")
        assert not output.exists()
        write_rendered_citation_media_intake_manifest(
            manifest,
            output,
            confirm_write=WRITE_RENDERED_CITATION_MEDIA_INTAKE_V77E,
        )
        payload = json.loads(output.read_text(encoding="utf-8"))
        assert payload["schema_version"] == "rendered-citation-media-intake-v77e"
        assert payload["safety_flags"]["media_download_performed"] is False


def test_summary_contains_expected_markers() -> None:
    manifest = build_rendered_citation_media_intake_manifest(
        source_url="https://example.com/source",
        page_url="https://example.com/source",
        source_unit_path="Reference Extants/example",
        user_declared_purpose="source_preservation",
        capture_kind="blocked_capture_state",
        capture_method="source_reference_only",
        local_file_role="blocked_capture_placeholder",
        capture_blocked=True,
        blocked_reason="access_boundary",
        created_at_utc="2026-08-17T00:00:00Z",
    )
    text = render_rendered_citation_media_intake_summary(manifest)
    assert "schema_version: rendered-citation-media-intake-v77e" in text
    assert "local_file_role: blocked_capture_placeholder" in text
    assert "source_unit_attachment.attachment_scope: reference_extant" in text
    assert "safety_flags.browser_launch_performed: False" in text


if __name__ == "__main__":
    test_ingest_existing_text_fixture_as_transcript()
    test_fake_screenshot_fixture_is_classified_without_pixel_open()
    test_blocked_capture_placeholder_without_local_file()
    test_safety_flags_remain_false()
    test_write_requires_confirmation_token()
    test_summary_contains_expected_markers()
    print("rendered_citation_media_intake_v77e_test OK")
