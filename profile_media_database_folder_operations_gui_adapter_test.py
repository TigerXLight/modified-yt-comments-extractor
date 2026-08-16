from __future__ import annotations

import tempfile
from pathlib import Path

from profile_media_database_folder_operations import PROFILE_MEDIA_DATABASE_FOLDER_OPERATIONS_CONFIRMATION, build_demo_folder_operations_payload
from profile_media_database_folder_operations_gui_adapter import build_folder_operations_gui_payload


def _make_tree(root: Path) -> None:
    (root / "Cases" / "Demo Case" / "Sources" / "Articles" / "Old Article Folder").mkdir(parents=True)
    (root / "Cases" / "Demo Case" / "Sources" / "Social Media" / "Online" / "Misfiled Offline Bundle").mkdir(parents=True)
    (root / "Cases" / "Demo Case" / "Sources" / "Social Media" / "Offline").mkdir(parents=True)


def test_gui_payload_dry_run_is_guarded() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _make_tree(root)
        payload = build_folder_operations_gui_payload(database_root=str(root), operations_payload=build_demo_folder_operations_payload())
        assert payload["status"] == "planned_dry_run"
        assert payload["confirmation_phrase"] == PROFILE_MEDIA_DATABASE_FOLDER_OPERATIONS_CONFIRMATION
        assert payload["folder_scan_performed"] is False
        assert payload["folder_creation_performed"] is False
        assert payload["folder_move_performed"] is False
        assert payload["folder_rename_performed"] is False
        assert payload["file_copy_performed"] is False
        assert payload["file_write_performed"] is False
        assert payload["media_download_performed"] is False
        assert payload["automatic_classification_performed"] is False
        assert payload["sensitive_identifier_inference_performed"] is False
        assert any(action["action_id"] == "execute_folder_operations_plan" for action in payload["actions"])


def test_gui_payload_confirmed_execution_reports_changes() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _make_tree(root)
        payload = build_folder_operations_gui_payload(
            database_root=str(root),
            operations_payload=build_demo_folder_operations_payload(),
            execute=True,
            confirmation_phrase=PROFILE_MEDIA_DATABASE_FOLDER_OPERATIONS_CONFIRMATION,
        )
        assert payload["status"] == "operations_applied"
        assert payload["folder_move_performed"] is True
        assert payload["folder_rename_performed"] is True
        assert payload["file_copy_performed"] is False
        assert payload["media_download_performed"] is False


def main() -> int:
    test_gui_payload_dry_run_is_guarded()
    test_gui_payload_confirmed_execution_reports_changes()
    print("profile_media_database_folder_operations_gui_adapter v76g OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
