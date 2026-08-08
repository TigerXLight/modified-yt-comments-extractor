from __future__ import annotations

import json

from source_url_files_bridge import (
    accept_source_url_on_enter,
    build_default_source_url_files_bridge_state,
    clear_editor_transcript_without_deleting_file,
    inject_source_url_choice_to_files,
    replace_editor_transcript_without_deleting_previous,
    set_source_url_download_tick,
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


def test_enter_adds_source_url_without_network_execution() -> None:
    state = build_default_source_url_files_bridge_state()
    url = "local-fixture://second"
    updated = accept_source_url_on_enter(
        state,
        url=url,
        fixture_html_by_url={url: "<html><body><audio src='/clip.mp3'></audio></body></html>"},
    )
    data = updated.to_dict()
    assert data["source_row_count"] == 2
    assert data["url_enter_submit_supported"] is True
    assert data["network_performed"] is False


def test_download_tick_and_injection_are_independent_state_transitions() -> None:
    state = build_default_source_url_files_bridge_state()
    choice_id = state.source_rows[0]["resource_choices"][0]["choice_id"]
    unticked = set_source_url_download_tick(state, choice_id=choice_id, selected=False)
    assert choice_id not in unticked.selected_download_choice_ids
    injected = inject_source_url_choice_to_files(unticked, choice_id=choice_id)
    assert choice_id not in injected.selected_download_choice_ids
    assert choice_id in injected.injected_choice_ids
    assert any(row.resource_choice_id == choice_id for row in injected.files_rows)


def test_editor_clear_and_replace_preserve_stored_transcript_files() -> None:
    state = build_default_source_url_files_bridge_state()
    choice_id = state.source_rows[0]["resource_choices"][0]["choice_id"]
    cleared = clear_editor_transcript_without_deleting_file(state)
    assert cleared.editor_transcript_state == "cleared_editor_only_stored_file_preserved"
    assert validate_source_url_files_bridge_state(cleared) == ()
    replaced = replace_editor_transcript_without_deleting_previous(cleared, choice_id=choice_id)
    assert replaced.editor_transcript_state == "replaced_editor_only_previous_file_preserved"
    assert replaced.transcript_replacement_deletes_previous is False
    assert choice_id in replaced.injected_choice_ids


if __name__ == "__main__":
    test_default_bridge_has_source_rows_media_rows_and_files_rows()
    test_download_selection_is_separate_from_injection_and_files()
    test_files_preservation_guards_are_enforced()
    test_serialization_is_deterministic()
    test_enter_adds_source_url_without_network_execution()
    test_download_tick_and_injection_are_independent_state_transitions()
    test_editor_clear_and_replace_preserve_stored_transcript_files()
    print("source_url_files_bridge_test.py passed")
