from __future__ import annotations

import json
import tempfile
from pathlib import Path

from profile_media_database_end_to_end_workflow import (
    ProfileMediaDatabaseEndToEndConfig,
    confirmation_phrases,
    end_to_end_workflow_payload,
    render_end_to_end_workflow_text,
    run_profile_media_database_end_to_end_workflow,
)


def _tree_lines(case_title: str = "V76H Case") -> tuple[str, ...]:
    return (
        "Database/Profiles/Global Header Person",
        f"Cases/{case_title}/Sources/Articles/Old Article Folder/source_claim_evaluation.json",
        f"Cases/{case_title}/Sources/Social Media/Online/Misfiled Offline Bundle/capture.html",
        f"Cases/{case_title}/Sources/Internal Media/Creator Original Clip/internal_media_note.txt",
        f"Cases/{case_title}/Profiles/Example Person/profile.txt",
        f"Cases/{case_title}/Profiles/Second Example/profile.txt",
        f"Cases/{case_title}/People/Readable person note.txt",
        f"Cases/{case_title}/Reference Extants/Timeline.txt",
    )


def _operations(case_title: str = "V76H Case") -> dict[str, object]:
    return {
        "operations": [
            {
                "operation_type": "rename_folder",
                "source_path": f"Cases/{case_title}/Sources/Articles/Old Article Folder",
                "new_name": "Renamed Article Folder",
                "reason": "Reviewed title normalization.",
            },
            {
                "operation_type": "move_folder",
                "source_path": f"Cases/{case_title}/Sources/Social Media/Online/Misfiled Offline Bundle",
                "destination_path": f"Cases/{case_title}/Sources/Social Media/Offline/Misfiled Offline Bundle",
                "reason": "Reviewed source bucket correction.",
            },
        ]
    }


def test_dry_run_preview_never_mutates() -> None:
    result = run_profile_media_database_end_to_end_workflow(
        ProfileMediaDatabaseEndToEndConfig(
            folder_tree_lines=_tree_lines(),
            database_root="Demo Database",
        )
    )
    payload = end_to_end_workflow_payload(result, include_text=True)
    assert payload["status"] == "workflow_dry_run_preview"
    assert payload["existing_folder_plan"]["source_candidate_count"] == 3
    assert payload["existing_folder_plan"]["profile_candidate_count"] == 2
    assert payload["folder_scan_performed"] is False
    assert payload["folder_creation_performed"] is False
    assert payload["folder_move_performed"] is False
    assert payload["folder_rename_performed"] is False
    assert payload["file_copy_performed"] is False
    assert payload["file_write_performed"] is False
    assert payload["media_download_performed"] is False
    assert payload["automatic_classification_performed"] is False
    assert payload["sensitive_identifier_inference_performed"] is False
    assert "Profile/Media Database End-to-End Workflow" in payload["workflow_text"]


def test_confirmed_preview_write_then_gui_refresh() -> None:
    phrases = confirmation_phrases()
    with tempfile.TemporaryDirectory() as tmp:
        preview = Path(tmp) / "preview.json"
        result = run_profile_media_database_end_to_end_workflow(
            ProfileMediaDatabaseEndToEndConfig(
                folder_tree_lines=_tree_lines(),
                database_root=str(Path(tmp) / "Database"),
                batch_preview_path=str(preview),
                write_batch_preview=True,
                batch_write_confirmation=phrases["write_batch_preview"],
            )
        )
        payload = end_to_end_workflow_payload(result)
        assert result.status == "workflow_batch_preview_written"
        assert preview.exists()
        assert payload["batch_preview_write_result"]["status"] == "batch_preview_written"
        assert payload["gui_selection_result"]["status"] == "success"
        assert payload["folder_creation_performed"] is False
        assert payload["folder_move_performed"] is False
        assert payload["folder_rename_performed"] is False
        assert payload["file_copy_performed"] is False
        assert payload["media_download_performed"] is False


def test_full_confirmed_temp_workflow_materializes_and_applies_reviewed_ops() -> None:
    phrases = confirmation_phrases()
    case_title = "V76H Case"
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "Database"
        preview = Path(tmp) / "preview.json"
        result = run_profile_media_database_end_to_end_workflow(
            ProfileMediaDatabaseEndToEndConfig(
                folder_tree_lines=_tree_lines(case_title),
                database_root=str(root),
                batch_preview_path=str(preview),
                write_batch_preview=True,
                batch_write_confirmation=phrases["write_batch_preview"],
                materialize_database=True,
                materialize_confirmation=phrases["materialize_database"],
                operations_payload=_operations(case_title),
                execute_folder_operations=True,
                folder_operations_confirmation=phrases["folder_operations"],
            )
        )
        payload = end_to_end_workflow_payload(result, include_text=True)
        assert payload["status"] == "workflow_operations_applied"
        assert payload["materialize_result"]["status"] == "materialized"
        assert payload["folder_operations_result"]["status"] == "operations_applied"
        assert (root / "Cases" / case_title / "Sources" / "Articles" / "Renamed Article Folder").is_dir()
        assert (root / "Cases" / case_title / "Sources" / "Social Media" / "Offline" / "Misfiled Offline Bundle").is_dir()
        assert payload["folder_scan_performed"] is False
        assert payload["folder_creation_performed"] is True
        assert payload["folder_move_performed"] is True
        assert payload["folder_rename_performed"] is True
        assert payload["file_copy_performed"] is False
        assert payload["media_download_performed"] is False
        assert payload["automatic_classification_performed"] is False
        assert payload["sensitive_identifier_inference_performed"] is False
        assert "Refreshed sources" in payload["workflow_text"]


def test_blocked_confirmations_remain_safe() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        preview = Path(tmp) / "preview.json"
        result = run_profile_media_database_end_to_end_workflow(
            ProfileMediaDatabaseEndToEndConfig(
                folder_tree_lines=_tree_lines(),
                database_root=str(Path(tmp) / "Database"),
                batch_preview_path=str(preview),
                write_batch_preview=True,
                batch_write_confirmation="wrong phrase",
                materialize_database=True,
                materialize_confirmation="wrong phrase",
                operations_payload=_operations(),
                execute_folder_operations=True,
                folder_operations_confirmation="wrong phrase",
            )
        )
        payload = end_to_end_workflow_payload(result)
        assert payload["status"] == "blocked_confirmation_required"
        assert preview.exists() is False
        assert payload["folder_creation_performed"] is False
        assert payload["folder_move_performed"] is False
        assert payload["folder_rename_performed"] is False
        assert payload["file_copy_performed"] is False
        assert payload["media_download_performed"] is False


def main() -> int:
    test_dry_run_preview_never_mutates()
    test_confirmed_preview_write_then_gui_refresh()
    test_full_confirmed_temp_workflow_materializes_and_applies_reviewed_ops()
    test_blocked_confirmations_remain_safe()
    print("profile_media_database_end_to_end_workflow v76h OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
