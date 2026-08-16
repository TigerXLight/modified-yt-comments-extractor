from __future__ import annotations

from profile_media_database_gui_smoke_readiness import (
    build_gui_smoke_readiness_report,
    gui_smoke_readiness_payload,
    render_gui_smoke_readiness_text,
)
from profile_media_database_materialize_workflow import PROFILE_MEDIA_DATABASE_MATERIALIZE_CONFIRMATION
from profile_media_database_folder_operations import PROFILE_MEDIA_DATABASE_FOLDER_OPERATIONS_CONFIRMATION
from profile_media_database_operation_reconciliation import PROFILE_MEDIA_DATABASE_RECONCILIATION_WRITE_CONFIRMATION


def test_gui_smoke_readiness_contains_complete_manual_chain() -> None:
    report = build_gui_smoke_readiness_report(manual_test_database_root="Demo Root")
    payload = gui_smoke_readiness_payload(report, include_text=True)
    step_ids = [step["step_id"] for step in payload["steps"]]
    assert payload["status"] == "ready_for_manual_gui_smoke"
    assert step_ids == [
        "start_clean",
        "toggle_database_mode",
        "plan_existing_folder_import",
        "write_batch_preview",
        "load_batch_json",
        "materialize_selection",
        "reviewed_folder_operations",
        "reconcile_batch_preview",
        "refresh_database_panel",
        "confirm_safety_flags",
    ]
    assert payload["guarded_step_count"] == 4
    assert PROFILE_MEDIA_DATABASE_MATERIALIZE_CONFIRMATION in payload["readiness_text"]
    assert PROFILE_MEDIA_DATABASE_FOLDER_OPERATIONS_CONFIRMATION in payload["readiness_text"]
    assert PROFILE_MEDIA_DATABASE_RECONCILIATION_WRITE_CONFIRMATION in payload["readiness_text"]


def test_gui_smoke_readiness_is_read_only() -> None:
    payload = gui_smoke_readiness_payload(build_gui_smoke_readiness_report())
    assert payload["folder_scan_performed"] is False
    assert payload["folder_creation_performed"] is False
    assert payload["folder_move_performed"] is False
    assert payload["folder_rename_performed"] is False
    assert payload["file_copy_performed"] is False
    assert payload["file_write_performed"] is False
    assert payload["media_download_performed"] is False
    assert payload["automatic_classification_performed"] is False
    assert payload["sensitive_identifier_inference_performed"] is False


def test_gui_smoke_readiness_text_renders() -> None:
    text = render_gui_smoke_readiness_text(build_gui_smoke_readiness_report())
    assert "Profile/Media Database Manual GUI Smoke Readiness" in text
    assert "Turn DATABASE mode on" in text
    assert "Refresh Database panel" in text
    assert "Folder scan performed: False" in text


def main() -> int:
    test_gui_smoke_readiness_contains_complete_manual_chain()
    test_gui_smoke_readiness_is_read_only()
    test_gui_smoke_readiness_text_renders()
    print("profile_media_database_gui_smoke_readiness v76j OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
