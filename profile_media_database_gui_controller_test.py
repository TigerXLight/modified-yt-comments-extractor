from __future__ import annotations

import json
from pathlib import Path

from profile_media_database_gui_controller import (
    build_database_gui_clear_selection,
    build_database_gui_selection_from_batch_json,
    build_database_gui_selection_from_saved_state,
    database_gui_selection_result_payload,
    render_database_gui_selection_text,
)
from profile_media_database_gui_state_store import (
    PROFILE_MEDIA_DATABASE_GUI_STATE_CLEAR_CONFIRMATION,
    PROFILE_MEDIA_DATABASE_GUI_STATE_SAVE_CONFIRMATION,
)


def _write_batch(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "database_root": "Demo Database",
                "case_title": "Controller Case",
                "sources": [
                    {
                        "source_page": "Controller Source",
                        "source_title": "Controller Article",
                        "source_bucket": "Articles",
                        "source_role": "TERTIARY_PROPAGATED_SOURCE",
                        "claim_basis": "AGENCY_OR_OUTSIDE_RETELLING",
                        "source_chain_gap": True,
                    }
                ],
                "profiles": [
                    {
                        "profile_text": "Name: Controller Person\nDate: 2026-08-16\nText: Mentioned in controller batch.\nAddress: Cases/Controller Case/Sources/Articles/Controller Article\nSource: Controller Source",
                        "source_bucket": "Articles",
                        "source_role": "TERTIARY_PROPAGATED_SOURCE",
                        "claim_basis": "AGENCY_OR_OUTSIDE_RETELLING",
                        "currentness_status": "CURRENT",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )


def test_controller_loads_explicit_batch_and_builds_panel(tmp_path: Path) -> None:
    batch = tmp_path / "controller_case.json"
    _write_batch(batch)
    result = build_database_gui_selection_from_batch_json([batch], database_root="Demo Database")
    payload = database_gui_selection_result_payload(result, include_text=True)
    assert payload["status"] == "success"
    assert payload["batch_json_file_count"] == 1
    assert payload["panel_state"]["status"] == "success"
    assert payload["panel_state"]["mode"] == "DATABASE"
    assert payload["folder_scan_performed"] is False
    assert payload["folder_creation_performed"] is False
    assert payload["folder_move_performed"] is False
    assert payload["folder_rename_performed"] is False
    assert payload["file_copy_performed"] is False
    assert payload["media_download_performed"] is False
    assert payload["automatic_classification_performed"] is False
    assert payload["sensitive_identifier_inference_performed"] is False
    assert "Profile/Media Database GUI Selection" in render_database_gui_selection_text(result)


def test_controller_persists_and_restores_explicit_selection(tmp_path: Path) -> None:
    batch = tmp_path / "controller_case.json"
    state_path = tmp_path / "gui_state.json"
    _write_batch(batch)
    saved = build_database_gui_selection_from_batch_json(
        [batch],
        database_root="Demo Database",
        state_path=state_path,
        persist_state=True,
        confirmation_phrase=PROFILE_MEDIA_DATABASE_GUI_STATE_SAVE_CONFIRMATION,
    )
    assert saved.state_io_result is not None
    assert saved.state_io_result.status == "state_saved"
    assert state_path.exists()

    restored = build_database_gui_selection_from_saved_state(state_path=state_path)
    payload = database_gui_selection_result_payload(restored)
    assert payload["status"] == "success"
    assert payload["database_root"] == "Demo Database"
    assert payload["batch_json_file_count"] == 1
    assert payload["panel_state"]["status"] == "success"

    cleared = build_database_gui_clear_selection(
        state_path=state_path,
        clear_persisted_state=True,
        confirmation_phrase=PROFILE_MEDIA_DATABASE_GUI_STATE_CLEAR_CONFIRMATION,
    )
    assert cleared.status == "cleared"
    assert cleared.state_io_result is not None
    assert cleared.state_io_result.status == "state_cleared"
    assert not state_path.exists()


def main() -> int:
    import tempfile

    with tempfile.TemporaryDirectory() as directory:
        test_controller_loads_explicit_batch_and_builds_panel(Path(directory))
    with tempfile.TemporaryDirectory() as directory:
        test_controller_persists_and_restores_explicit_selection(Path(directory))
    print("profile_media_database_gui_controller v76d OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
