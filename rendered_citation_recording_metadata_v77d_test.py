from __future__ import annotations

import hashlib
import json
import tempfile
from pathlib import Path

from rendered_citation_recording_metadata_v77d import (
    WRITE_RENDERED_CITATION_RECORDING_METADATA_V77D,
    build_rendered_citation_recording_metadata,
    render_rendered_citation_recording_summary,
    write_rendered_citation_recording_metadata,
)


def test_normal_manifest_hashes_local_file() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "frame.txt"
        data = b"visible frame placeholder\n"
        path.write_bytes(data)
        metadata = build_rendered_citation_recording_metadata(
            source_url="https://example.com/source",
            page_url="https://example.com/source",
            media_url="https://example.com/media.mp4",
            capture_kind="still_frame",
            capture_method="local_file_preservation",
            user_declared_purpose="criticism",
            media_position_start="00:01:02",
            media_position_end="00:01:03",
            local_file_path=str(path),
            source_unit_path="Sources/Social Media/Online/X/example",
            created_at_utc="2026-08-17T00:00:00Z",
        )
        assert metadata.schema_version == "rendered-citation-recording-metadata-v77d"
        assert metadata.local_file_size == len(data)
        assert metadata.local_file_sha256 == hashlib.sha256(data).hexdigest()
        assert metadata.safety_flags.media_download_performed is False
        assert metadata.safety_flags.recording_performed is False


def test_blocked_capture_and_human_challenge_are_recorded_without_solver() -> None:
    metadata = build_rendered_citation_recording_metadata(
        source_url="https://example.com/source",
        page_url="https://example.com/source",
        capture_kind="blocked_capture_state",
        capture_method="ordinary_browser_visible_capture",
        user_declared_purpose="source_preservation",
        capture_blocked=True,
        blocked_reason="captcha_or_challenge_required",
        human_mediated_access_required=True,
        human_mediated_access_completed_by_user=True,
        created_at_utc="2026-08-17T00:00:00Z",
    )
    assert metadata.capture_blocked is True
    assert metadata.blocked_reason == "captcha_or_challenge_required"
    assert metadata.human_mediated_access.required is True
    assert metadata.human_mediated_access.completed_by_user is True
    assert metadata.human_mediated_access.completion_recorded is True
    assert metadata.human_mediated_access.program_solved_challenge is False
    assert metadata.human_mediated_access.solver_service_used is False
    assert metadata.human_mediated_access.anti_detection_used is False
    assert metadata.safety_flags.drm_circumvention_performed is False
    assert metadata.safety_flags.proxy_or_evasion_performed is False
    assert metadata.safety_flags.forced_rate_limit_bypass_performed is False
    summary = render_rendered_citation_recording_summary(metadata)
    assert "capture_kind: blocked_capture_state" in summary
    assert "human_mediated_access.program_solved_challenge: False" in summary


def test_write_requires_confirmation_token() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        output = Path(tmp) / "metadata.json"
        metadata = build_rendered_citation_recording_metadata(
            source_url="https://example.com/source",
            page_url="https://example.com/source",
            capture_kind="subtitle_caption_capture",
            capture_method="source_reference_only",
            user_declared_purpose="review",
            created_at_utc="2026-08-17T00:00:00Z",
        )
        try:
            write_rendered_citation_recording_metadata(metadata, output, confirm_write="")
        except PermissionError:
            pass
        else:
            raise AssertionError("write without confirmation token should fail")
        assert not output.exists()
        write_rendered_citation_recording_metadata(
            metadata,
            output,
            confirm_write=WRITE_RENDERED_CITATION_RECORDING_METADATA_V77D,
        )
        payload = json.loads(output.read_text(encoding="utf-8"))
        assert payload["schema_version"] == "rendered-citation-recording-metadata-v77d"
        assert payload["safety_flags"]["captcha_solver_used"] is False


def test_invalid_capture_values_are_rejected() -> None:
    try:
        build_rendered_citation_recording_metadata(
            source_url="https://example.com/source",
            capture_kind="screen_scrape_everything",
            capture_method="source_reference_only",
            user_declared_purpose="review",
        )
    except ValueError as exc:
        assert "capture_kind must be one of" in str(exc)
    else:
        raise AssertionError("invalid capture kind should fail")


if __name__ == "__main__":
    test_normal_manifest_hashes_local_file()
    test_blocked_capture_and_human_challenge_are_recorded_without_solver()
    test_write_requires_confirmation_token()
    test_invalid_capture_values_are_rejected()
    print("rendered_citation_recording_metadata_v77d_test OK")
