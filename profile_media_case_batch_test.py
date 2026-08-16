from __future__ import annotations

import tempfile
from pathlib import Path

from profile_media_case_batch import (
    PROFILE_MEDIA_CASE_BATCH_CONFIRMATION,
    apply_case_batch_plan,
    build_case_batch_plan,
    build_demo_case_batch_payload,
    load_case_batch_json,
    write_demo_case_batch_json,
)


def test_batch_dry_run_keeps_filesystem_untouched() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = str(Path(tmp) / "Database")
        payload = build_demo_case_batch_payload(database_root=root, case_title="Example Case")
        plan = build_case_batch_plan(payload=payload)
        result = apply_case_batch_plan(plan)
        assert result.status == "planned_dry_run"
        assert result.folder_creation_performed is False
        assert result.file_write_performed is False
        assert result.folder_scan_performed is False
        assert result.folder_move_performed is False
        assert result.folder_rename_performed is False
        assert result.file_copy_performed is False
        assert result.media_download_performed is False
        assert result.automatic_classification_performed is False
        assert result.sensitive_identifier_inference_performed is False
        assert not Path(root).exists()
        assert len(plan.source_specs) == 2
        assert len(plan.profile_specs) == 2


def test_batch_blocks_forbidden_scan_request() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = str(Path(tmp) / "Database")
        payload = build_demo_case_batch_payload(database_root=root, case_title="Example Case")
        payload["scan_folders"] = True
        plan = build_case_batch_plan(payload=payload, execute=True, confirmation_phrase=PROFILE_MEDIA_CASE_BATCH_CONFIRMATION)
        result = apply_case_batch_plan(plan)
        assert result.status == "blocked_forbidden_operation_requested"
        assert "forbidden_operation_requested:scan_folders" in result.warnings
        assert not Path(root).exists()


def test_batch_execute_requires_batch_confirmation() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = str(Path(tmp) / "Database")
        payload = build_demo_case_batch_payload(database_root=root, case_title="Example Case")
        plan = build_case_batch_plan(payload=payload, execute=True, confirmation_phrase="WRONG")
        result = apply_case_batch_plan(plan)
        assert result.status == "blocked_confirmation_required"
        assert not Path(root).exists()


def test_batch_execute_materializes_known_metadata_only() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = str(Path(tmp) / "Database")
        payload = build_demo_case_batch_payload(database_root=root, case_title="Example Case")
        plan = build_case_batch_plan(payload=payload, execute=True, confirmation_phrase=PROFILE_MEDIA_CASE_BATCH_CONFIRMATION)
        result = apply_case_batch_plan(plan)
        assert result.status == "batch_materialized"
        assert result.folder_creation_performed is True
        assert result.file_write_performed is True
        assert result.folder_scan_performed is False
        assert result.folder_move_performed is False
        assert result.folder_rename_performed is False
        assert result.file_copy_performed is False
        assert result.media_download_performed is False
        assert result.automatic_classification_performed is False
        assert result.sensitive_identifier_inference_performed is False
        assert (Path(root) / "Profiles").is_dir()
        assert (Path(root) / "Cases" / "Example Case" / "case_manifest.json").is_file()
        assert any(path.endswith("source_claim_evaluation.json") for path in result.written_files)
        assert any(path.endswith("profile_record.json") for path in result.written_files)


def test_demo_batch_json_round_trip() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "batch.json"
        root = str(Path(tmp) / "Database")
        written = write_demo_case_batch_json(path, database_root=root, case_title="Example Case")
        payload = load_case_batch_json(written)
        assert payload["database_root"] == root
        assert payload["case_title"] == "Example Case"
        assert len(payload["sources"]) == 2
        assert len(payload["profiles"]) == 2


if __name__ == "__main__":
    test_batch_dry_run_keeps_filesystem_untouched()
    test_batch_blocks_forbidden_scan_request()
    test_batch_execute_requires_batch_confirmation()
    test_batch_execute_materializes_known_metadata_only()
    test_demo_batch_json_round_trip()
    print("profile_media_case_batch v75v OK")
