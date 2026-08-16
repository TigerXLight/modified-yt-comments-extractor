from __future__ import annotations

from profile_media_database_end_to_end_workflow import ProfileMediaDatabaseEndToEndConfig, run_profile_media_database_end_to_end_workflow
from profile_media_database_implementation_closeout import (
    build_implementation_closeout_report,
    implementation_closeout_payload,
    render_implementation_closeout_text,
)


def test_closeout_without_workflow_result_is_readiness_only() -> None:
    closeout = build_implementation_closeout_report()
    payload = implementation_closeout_payload(closeout, include_text=True)
    assert payload["status"] == "implementation_ready_for_end_to_end_proof"
    assert payload["implemented_count"] >= 13
    assert payload["remaining_count"] == 3
    assert payload["folder_scan_performed"] is False
    assert payload["folder_creation_performed"] is False
    assert payload["folder_move_performed"] is False
    assert payload["folder_rename_performed"] is False
    assert payload["file_copy_performed"] is False
    assert payload["media_download_performed"] is False
    assert "Profile/Media Database Implementation Closeout" in payload["closeout_text"]


def test_closeout_accepts_workflow_status() -> None:
    workflow = run_profile_media_database_end_to_end_workflow(
        ProfileMediaDatabaseEndToEndConfig(
            folder_tree_lines=(
                "Cases/Closeout Case/Sources/Articles/Article One/source_claim_evaluation.json",
                "Cases/Closeout Case/Profiles/Person One/profile.txt",
            ),
            database_root="Demo Database",
        )
    )
    closeout = build_implementation_closeout_report(workflow)
    text = render_implementation_closeout_text(closeout)
    payload = implementation_closeout_payload(closeout)
    assert payload["workflow_status"] == "workflow_dry_run_preview"
    assert payload["status"] == "implementation_ready_for_end_to_end_proof"
    assert "End-to-end workflow" in text


def test_closeout_marks_full_workflow_status_ready_for_gui_smoke() -> None:
    closeout = build_implementation_closeout_report({"status": "workflow_operations_applied"})
    payload = implementation_closeout_payload(closeout)
    capabilities = {item["key"]: item["status"] for item in payload["capabilities"]}
    assert payload["status"] == "implementation_ready_for_gui_smoke"
    assert capabilities["end_to_end_workflow"] == "implemented"
    assert capabilities["temp_execution_proof"] == "implemented"


def main() -> int:
    test_closeout_without_workflow_result_is_readiness_only()
    test_closeout_accepts_workflow_status()
    test_closeout_marks_full_workflow_status_ready_for_gui_smoke()
    print("profile_media_database_implementation_closeout v76h OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
