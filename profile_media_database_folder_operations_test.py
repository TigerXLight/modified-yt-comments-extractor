from __future__ import annotations

import tempfile
from pathlib import Path

from profile_media_database_folder_operations import (
    PROFILE_MEDIA_DATABASE_FOLDER_OPERATIONS_CONFIRMATION,
    apply_folder_operations_plan,
    build_demo_folder_operations_payload,
    build_folder_operations_plan,
    folder_operations_payload,
    render_folder_operations_plan_text,
)


def _make_tree(root: Path) -> None:
    (root / "Cases" / "Demo Case" / "Sources" / "Articles" / "Old Article Folder").mkdir(parents=True)
    (root / "Cases" / "Demo Case" / "Sources" / "Social Media" / "Online" / "Misfiled Offline Bundle").mkdir(parents=True)
    (root / "Cases" / "Demo Case" / "Sources" / "Social Media" / "Offline").mkdir(parents=True)


def test_dry_run_never_moves_or_renames() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _make_tree(root)
        plan = build_folder_operations_plan(database_root=root, operations_payload=build_demo_folder_operations_payload())
        result = apply_folder_operations_plan(plan)
        payload = folder_operations_payload(result, plan=plan)
        assert result.status == "planned_dry_run"
        assert payload["folder_scan_performed"] is False
        assert payload["folder_creation_performed"] is False
        assert payload["folder_move_performed"] is False
        assert payload["folder_rename_performed"] is False
        assert payload["file_copy_performed"] is False
        assert payload["file_write_performed"] is False
        assert payload["media_download_performed"] is False
        assert payload["automatic_classification_performed"] is False
        assert payload["sensitive_identifier_inference_performed"] is False
        assert (root / "Cases" / "Demo Case" / "Sources" / "Articles" / "Old Article Folder").exists()
        assert "Profile/Media Reviewed Folder Operations Plan" in render_folder_operations_plan_text(plan)


def test_confirmation_required_before_execution() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _make_tree(root)
        plan = build_folder_operations_plan(
            database_root=root,
            operations_payload=build_demo_folder_operations_payload(),
            execute=True,
            confirmation_phrase="WRONG",
        )
        result = apply_folder_operations_plan(plan)
        assert result.status == "blocked_confirmation_required"
        assert result.folder_move_performed is False
        assert result.folder_rename_performed is False
        assert (root / "Cases" / "Demo Case" / "Sources" / "Articles" / "Old Article Folder").exists()


def test_confirmed_execution_moves_and_renames_known_folders_only() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _make_tree(root)
        plan = build_folder_operations_plan(
            database_root=root,
            operations_payload=build_demo_folder_operations_payload(),
            execute=True,
            confirmation_phrase=PROFILE_MEDIA_DATABASE_FOLDER_OPERATIONS_CONFIRMATION,
        )
        result = apply_folder_operations_plan(plan)
        payload = folder_operations_payload(result, plan=plan)
        assert result.status == "operations_applied"
        assert payload["folder_scan_performed"] is False
        assert payload["folder_creation_performed"] is False
        assert payload["file_copy_performed"] is False
        assert payload["file_write_performed"] is False
        assert payload["media_download_performed"] is False
        assert payload["automatic_classification_performed"] is False
        assert payload["sensitive_identifier_inference_performed"] is False
        assert payload["folder_move_performed"] is True
        assert payload["folder_rename_performed"] is True
        assert not (root / "Cases" / "Demo Case" / "Sources" / "Articles" / "Old Article Folder").exists()
        assert (root / "Cases" / "Demo Case" / "Sources" / "Articles" / "Renamed Article Folder").is_dir()
        assert (root / "Cases" / "Demo Case" / "Sources" / "Social Media" / "Offline" / "Misfiled Offline Bundle").is_dir()


def test_block_outside_or_missing_paths() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _make_tree(root)
        payload = {
            "operations": [
                {"operation_type": "rename_folder", "source_path": "../escape", "new_name": "Nope"},
                {"operation_type": "move_folder", "source_path": "Cases/Demo Case/Missing", "destination_path": "Cases/Demo Case/Sources/Articles/Missing"},
            ]
        }
        plan = build_folder_operations_plan(database_root=root, operations_payload=payload, execute=True, confirmation_phrase=PROFILE_MEDIA_DATABASE_FOLDER_OPERATIONS_CONFIRMATION)
        result = apply_folder_operations_plan(plan)
        assert result.status == "blocked_review_required"
        assert result.folder_move_performed is False
        assert result.folder_rename_performed is False
        assert any("parent_path_segments_not_allowed" in warning for warning in result.warnings)
        assert any("source_directory_missing" in warning for warning in result.warnings)


def main() -> int:
    test_dry_run_never_moves_or_renames()
    test_confirmation_required_before_execution()
    test_confirmed_execution_moves_and_renames_known_folders_only()
    test_block_outside_or_missing_paths()
    print("profile_media_database_folder_operations v76g OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
