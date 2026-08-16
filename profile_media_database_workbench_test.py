from __future__ import annotations

from profile_media_case_batch import write_demo_case_batch_json
from profile_media_database_session import ProfileMediaDatabaseSessionConfig
from profile_media_database_workbench import (
    PROFILE_MEDIA_DATABASE_WORKBENCH_EXPORT_CONFIRMATION,
    apply_workbench_export_plan,
    build_workbench_export_plan,
    build_workbench_state,
    render_workbench_text,
    workbench_payload,
)


def _config(batch_path: str) -> ProfileMediaDatabaseSessionConfig:
    return ProfileMediaDatabaseSessionConfig(
        database_root="Demo Database",
        batch_json_files=(batch_path,),
        source_chain_gap=True,
    )


def test_workbench_combines_dashboard_navigation_review_and_saved_views(tmp_path):
    batch = tmp_path / "batch.json"
    write_demo_case_batch_json(batch, database_root="Demo Database", case_title="Example Case")
    workbench = build_workbench_state(_config(str(batch)))
    payload = workbench_payload(workbench, include_text=True)
    assert payload["status"] == "success"
    assert payload["index_case_count"] == 1
    assert payload["index_source_count"] == 2
    assert payload["matched_source_count"] == 1
    assert payload["navigation_target_count"] == 5
    assert payload["saved_view_count"] >= 5
    assert payload["folder_scan_performed"] is False
    assert payload["folder_creation_performed"] is False
    assert payload["folder_move_performed"] is False
    assert payload["folder_rename_performed"] is False
    assert payload["file_copy_performed"] is False
    assert payload["media_download_performed"] is False
    assert payload["automatic_classification_performed"] is False
    assert payload["sensitive_identifier_inference_performed"] is False
    assert "Profile/Media Database Workbench" in render_workbench_text(workbench)


def test_workbench_export_is_guarded(tmp_path):
    batch = tmp_path / "batch.json"
    write_demo_case_batch_json(batch, database_root="Demo Database", case_title="Example Case")
    workbench = build_workbench_state(_config(str(batch)))
    dry_plan = build_workbench_export_plan(tmp_path / "exports")
    dry_result = apply_workbench_export_plan(dry_plan, workbench)
    assert dry_result.status == "planned_dry_run"
    assert dry_result.file_write_performed is False
    blocked = apply_workbench_export_plan(build_workbench_export_plan(tmp_path / "exports", execute=True, confirmation_phrase="WRONG"), workbench)
    assert blocked.status == "blocked_confirmation_required"
    confirmed = apply_workbench_export_plan(
        build_workbench_export_plan(
            tmp_path / "exports",
            execute=True,
            confirmation_phrase=PROFILE_MEDIA_DATABASE_WORKBENCH_EXPORT_CONFIRMATION,
        ),
        workbench,
    )
    assert confirmed.status == "success"
    assert confirmed.file_write_performed is True
    assert confirmed.folder_creation_performed is True
    assert confirmed.folder_scan_performed is False
    assert confirmed.folder_move_performed is False
    assert confirmed.folder_rename_performed is False
    assert confirmed.file_copy_performed is False
    assert confirmed.media_download_performed is False
    assert len(confirmed.written_files) == 6


def main() -> int:
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        test_workbench_combines_dashboard_navigation_review_and_saved_views(root)
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        test_workbench_export_is_guarded(root)
    print("profile_media_database_workbench v76a OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
