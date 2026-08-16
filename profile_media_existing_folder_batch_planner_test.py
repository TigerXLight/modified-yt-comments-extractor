from __future__ import annotations

import json
import tempfile
from pathlib import Path

from profile_media_existing_folder_batch_planner import (
    PROFILE_MEDIA_EXISTING_FOLDER_BATCH_WRITE_CONFIRMATION,
    build_existing_folder_to_batch_plan,
    load_folder_tree_lines,
    render_existing_folder_plan_text,
    write_batch_preview_if_confirmed,
)
from profile_media_existing_folder_gui_adapter import build_existing_folder_gui_payload
from profile_media_database_workbench_panel import build_profile_media_database_gui_panel_state, gui_panel_payload


def _fixture_lines() -> tuple[str, ...]:
    return load_folder_tree_lines("testdata/profile_media_database_v76e_existing_tree_fixture.txt")


def test_existing_folder_tree_builds_dry_run_batch_preview() -> None:
    plan = build_existing_folder_to_batch_plan(_fixture_lines(), database_root="Demo Database")
    payload = plan.to_dict()
    assert payload["folder_scan_performed"] is False
    assert payload["folder_creation_performed"] is False
    assert payload["folder_move_performed"] is False
    assert payload["folder_rename_performed"] is False
    assert payload["file_copy_performed"] is False
    assert payload["media_download_performed"] is False
    assert payload["automatic_classification_performed"] is False
    assert payload["sensitive_identifier_inference_performed"] is False
    assert payload["source_candidate_count"] >= 4
    assert payload["profile_candidate_count"] >= 3
    assert payload["global_profile_candidate_count"] >= 2
    assert payload["batch_preview_source_count"] >= 4
    assert payload["batch_preview_profile_count"] >= 3
    roles = {source["source_role"] for source in payload["batch_preview"]["sources"]}
    assert roles == {"UNKNOWN_SOURCE_ROLE"}
    assert "Profile/Media Existing Folder Import Plan" in render_existing_folder_plan_text(plan)


def test_existing_folder_preview_write_is_guarded() -> None:
    plan = build_existing_folder_to_batch_plan(_fixture_lines(), database_root="Demo Database")
    with tempfile.TemporaryDirectory() as tmp:
        output = Path(tmp) / "preview.json"
        blocked = write_batch_preview_if_confirmed(plan, output)
        assert blocked.status == "blocked_confirmation_required"
        assert blocked.file_write_performed is False
        assert not output.exists()
        written = write_batch_preview_if_confirmed(
            plan,
            output,
            confirmation_phrase=PROFILE_MEDIA_EXISTING_FOLDER_BATCH_WRITE_CONFIRMATION,
        )
        assert written.status == "batch_preview_written"
        assert written.file_write_performed is True
        data = json.loads(output.read_text(encoding="utf-8"))
        assert data["sources"]
        assert data["profiles"]


def test_existing_folder_gui_adapter_and_panel_action_are_safe() -> None:
    plan = build_existing_folder_to_batch_plan(_fixture_lines(), database_root="Demo Database")
    payload = build_existing_folder_gui_payload(plan).to_dict()
    assert payload["status"] == "dry_run_preview"
    assert payload["folder_scan_performed"] is False
    assert payload["file_copy_performed"] is False
    assert any(action["action_id"] == "write_batch_preview" and action["status"] == "guarded" for action in payload["actions"])
    panel = gui_panel_payload(build_profile_media_database_gui_panel_state(mode="DATABASE", database_root="Demo Database"))
    assert any(action["action_id"] == "plan_existing_folder_import" for action in panel["actions"])


def main() -> int:
    test_existing_folder_tree_builds_dry_run_batch_preview()
    test_existing_folder_preview_write_is_guarded()
    test_existing_folder_gui_adapter_and_panel_action_are_safe()
    print("profile_media_existing_folder_batch_planner v76e OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
