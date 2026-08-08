from __future__ import annotations

import json

from source_url_files_bridge import (
    build_default_source_url_files_bridge_state,
    source_url_files_bridge_state_to_json,
    validate_source_url_files_bridge_state,
)


def test_default_bridge_has_source_rows_media_rows_and_files_rows() -> None:
    state = build_default_source_url_files_bridge_state()
    data = state.to_dict()
    assert data["source_row_count"] == 1
    assert data["source_rows"][0]["source_url_enter_submits"] is True
    assert data["source_rows"][0]["no_youtube_specific_button"] is True
    assert data["source_rows"][0]["resource_choice_count"] >= 3
    assert data["files_row_count"] >= 1


def test_download_selection_is_separate_from_injection_and_files() -> None:
    data = build_default_source_url_files_bridge_state().to_dict()
    assert data["selected_download_count"] >= 1
    assert data["injected_choice_count"] >= 1
    download_ids = set(data["selected_download_choice_ids"])
    injected_ids = set(data["injected_choice_ids"])
    assert download_ids != injected_ids
    assert all(row["resource_choice_id"] in injected_ids for row in data["files_rows"])


def test_files_preservation_guards_are_enforced() -> None:
    state = build_default_source_url_files_bridge_state()
    assert validate_source_url_files_bridge_state(state) == ()
    unsafe = json.loads(source_url_files_bridge_state_to_json(state))
    unsafe["clear_editor_deletes_file"] = True
    unsafe["transcript_replacement_deletes_previous"] = True
    unsafe["audio_playback_requires_transcript"] = True
    errors = validate_source_url_files_bridge_state(unsafe)
    assert "clear_editor_must_not_delete_file" in errors
    assert "transcript_replacement_must_preserve_previous_file" in errors
    assert "audio_playback_must_not_require_transcript" in errors


def test_serialization_is_deterministic() -> None:
    assert source_url_files_bridge_state_to_json(build_default_source_url_files_bridge_state()) == (
        source_url_files_bridge_state_to_json(build_default_source_url_files_bridge_state())
    )


if __name__ == "__main__":
    test_default_bridge_has_source_rows_media_rows_and_files_rows()
    test_download_selection_is_separate_from_injection_and_files()
    test_files_preservation_guards_are_enforced()
    test_serialization_is_deterministic()
    print("source_url_files_bridge_test.py passed")
