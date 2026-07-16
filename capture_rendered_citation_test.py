import hashlib
import json
from tempfile import TemporaryDirectory
from pathlib import Path

from capture_contracts import ARTIFACT_TYPE_RENDERED_RECORDING
from capture_rendered_citation import (
    RENDERED_CITATION_METHOD_GET_DISPLAY_MEDIA,
    RENDERED_CITATION_METHOD_OS_WINDOW_CAPTURE,
    RENDERED_CITATION_STATUS_COMPLETED,
    RENDERED_CITATION_STATUS_PLANNED,
    RENDERED_CITATION_STATUS_PROTECTED_OR_BLACK_OUTPUT,
    RENDERED_CITATION_STATUS_RECORDING_FIXTURE_RECEIVED,
    RENDERED_CITATION_STATUS_USER_AUTHORIZATION_REQUIRED,
    build_fixture_rendered_citation_segment,
    build_rendered_citation_artifacts,
    complete_rendered_citation_session,
    mark_protected_or_black_output,
    plan_rendered_citation_session,
    receive_fixture_recording_segments,
    require_user_authorization,
)


SOURCE_URL = "https://localhost.test/media/drm-simulated"


def test_planned_rendered_citation_session_is_user_mediated_metadata_only() -> None:
    session = plan_rendered_citation_session(
        source_url=SOURCE_URL,
        source_label="Fixture protected-media page",
        purpose="Record a short citation excerpt for review notes.",
        time_range_start_seconds=12.5,
        time_range_end_seconds=18.0,
        selected_display_label="Fixture browser tab",
        window_or_region_label="video region",
        subtitles_visible=True,
    )

    data = session.to_dict()
    assert data["status"] == RENDERED_CITATION_STATUS_PLANNED
    assert data["capture_method"] == RENDERED_CITATION_METHOD_GET_DISPLAY_MEDIA
    assert data["user_mediated"] is True
    assert data["user_authorization_required"] is True
    assert data["source_url"] == SOURCE_URL
    assert data["source_label"] == "Fixture protected-media page"
    assert data["purpose"] == "Record a short citation excerpt for review notes."
    assert data["time_range_start_seconds"] == 12.5
    assert data["time_range_end_seconds"] == 18.0
    assert "no real screen recording" in data["scope"]


def test_user_authorization_required_state_is_explicit() -> None:
    session = plan_rendered_citation_session(
        source_url=SOURCE_URL,
        source_label="Fixture",
        purpose="Citation",
        time_range_start_seconds=0,
        time_range_end_seconds=5,
    )

    authorization = require_user_authorization(session)

    assert authorization.status == RENDERED_CITATION_STATUS_USER_AUTHORIZATION_REQUIRED
    assert authorization.user_authorization_required is True
    assert authorization.session_id == session.session_id


def test_os_window_capture_fallback_is_metadata_only() -> None:
    session = plan_rendered_citation_session(
        source_url=SOURCE_URL,
        source_label="Fixture",
        purpose="Fallback citation",
        time_range_start_seconds=1,
        time_range_end_seconds=2,
        capture_method=RENDERED_CITATION_METHOD_OS_WINDOW_CAPTURE,
        selected_display_label="Fixture OS window",
    )

    assert session.capture_method == RENDERED_CITATION_METHOD_OS_WINDOW_CAPTURE
    assert session.user_mediated is True
    assert session.selected_display_label == "Fixture OS window"


def test_fixture_segment_manifest_hashes_supplied_temp_segment() -> None:
    with TemporaryDirectory() as tmpdir:
        segment_path = Path(tmpdir) / "segment-001.fixture"
        payload = b"synthetic rendered citation segment"
        segment_path.write_bytes(payload)

        segment = build_fixture_rendered_citation_segment(
            segment_path=str(segment_path),
            relative_path="segments/segment-001.fixture",
            start_seconds=0,
            end_seconds=3.25,
            frame_marker_count=2,
            audio_marker_count=1,
        )

    assert segment.relative_path == "segments/segment-001.fixture"
    assert segment.sha256 == hashlib.sha256(payload).hexdigest()
    assert segment.size_bytes == len(payload)
    assert segment.frame_marker_count == 2
    assert segment.audio_marker_count == 1


def test_fixture_recording_segments_and_completion_are_separate_states() -> None:
    segment = build_fixture_rendered_citation_segment(
        segment_path="missing.fixture",
        relative_path="segments/missing.fixture",
        start_seconds=4,
        end_seconds=8,
    )
    session = plan_rendered_citation_session(
        source_url=SOURCE_URL,
        source_label="Fixture",
        purpose="Citation",
        time_range_start_seconds=4,
        time_range_end_seconds=8,
    )

    received = receive_fixture_recording_segments(session, (segment,))
    completed = complete_rendered_citation_session(received)

    assert received.status == RENDERED_CITATION_STATUS_RECORDING_FIXTURE_RECEIVED
    assert received.user_authorization_required is False
    assert received.segments == (segment,)
    assert completed.status == RENDERED_CITATION_STATUS_COMPLETED
    assert completed.segments == (segment,)


def test_protected_or_black_output_is_blocked_not_success() -> None:
    session = plan_rendered_citation_session(
        source_url=SOURCE_URL,
        source_label="Fixture",
        purpose="Citation",
        time_range_start_seconds=0,
        time_range_end_seconds=10,
    )

    blocked = mark_protected_or_black_output(session, reason="fixture black output")
    completed_attempt = complete_rendered_citation_session(blocked)

    assert blocked.status == RENDERED_CITATION_STATUS_PROTECTED_OR_BLACK_OUTPUT
    assert blocked.failure_reason == "fixture black output"
    assert "not bypassed" in blocked.warnings[0]
    assert completed_attempt.status == RENDERED_CITATION_STATUS_PROTECTED_OR_BLACK_OUTPUT


def test_rendered_citation_artifact_declarations_are_deterministic() -> None:
    segment = build_fixture_rendered_citation_segment(
        segment_path="missing.fixture",
        relative_path="segments/missing.fixture",
        start_seconds=0,
        end_seconds=1,
    )
    session = receive_fixture_recording_segments(
        plan_rendered_citation_session(
            source_url=SOURCE_URL,
            source_label="Fixture",
            purpose="Citation",
            time_range_start_seconds=0,
            time_range_end_seconds=1,
        ),
        (segment,),
    )

    first = build_rendered_citation_artifacts(
        session=session,
        timestamp_utc="2026-07-16T00:00:00Z",
        source_id="source_1",
        adapter_id="fixture_adapter",
    )
    second = build_rendered_citation_artifacts(
        session=session,
        timestamp_utc="2026-07-16T00:00:00Z",
        source_id="source_1",
        adapter_id="fixture_adapter",
    )

    assert [artifact.artifact_type for artifact in first] == [
        ARTIFACT_TYPE_RENDERED_RECORDING,
        ARTIFACT_TYPE_RENDERED_RECORDING,
    ]
    assert first[0].sha256 == second[0].sha256
    assert first[1].metadata["artifact_role"] == "segment_manifest"
    assert first[1].metadata["segment_count"] == 1
    assert first[1].metadata["capture_execution"] == "not executed"
    assert first[1].metadata["user_authorization_required"] is False


def test_public_rendered_citation_data_contains_no_executable_capture_or_bypass_fields() -> None:
    session = mark_protected_or_black_output(
        plan_rendered_citation_session(
            source_url=SOURCE_URL,
            source_label="Fixture",
            purpose="Citation",
            time_range_start_seconds=0,
            time_range_end_seconds=1,
        ),
        reason="fixture blocked output",
    )
    data = session.to_dict()
    rendered = json.dumps(data, sort_keys=True)
    forbidden_keys = {
        "authorization_header",
        "bypass_command",
        "cdm_patch",
        "drm_key",
        "eme_patch",
        "executable_command",
        "hdcp_override",
        "license_server_impersonation",
        "proxy",
        "stealth",
    }

    assert forbidden_keys.isdisjoint(data)
    assert "executable_command" not in rendered
    assert "requests.get" not in rendered
    assert "playwright.chromium.launch" not in rendered


def run_self_test() -> None:
    test_planned_rendered_citation_session_is_user_mediated_metadata_only()
    test_user_authorization_required_state_is_explicit()
    test_os_window_capture_fallback_is_metadata_only()
    test_fixture_segment_manifest_hashes_supplied_temp_segment()
    test_fixture_recording_segments_and_completion_are_separate_states()
    test_protected_or_black_output_is_blocked_not_success()
    test_rendered_citation_artifact_declarations_are_deterministic()
    test_public_rendered_citation_data_contains_no_executable_capture_or_bypass_fields()


if __name__ == "__main__":
    run_self_test()
    print("Capture rendered citation self-test passed.")
