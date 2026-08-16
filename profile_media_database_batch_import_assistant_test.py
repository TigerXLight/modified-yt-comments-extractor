from __future__ import annotations

import json

from profile_media_database_batch_import_assistant import (
    apply_batch_import_plan,
    batch_import_result_payload,
    build_batch_import_plan,
    validate_batch_json_file,
)


def test_batch_import_accepts_explicit_valid_file_without_scanning(tmp_path):
    batch = tmp_path / "case.json"
    batch.write_text(
        json.dumps(
            {
                "database_root": "Demo Database",
                "case_title": "Example Case",
                "sources": [{"source_title": "Example source"}],
                "profiles": [{"profile_text": "Name: Example Person"}],
            }
        ),
        encoding="utf-8",
    )
    plan = build_batch_import_plan([batch])
    result = apply_batch_import_plan(plan)
    payload = batch_import_result_payload(result, include_text=True)
    assert payload["status"] == "success"
    assert payload["accepted_file_count"] == 1
    assert payload["rejected_file_count"] == 0
    assert payload["database_root"] == "Demo Database"
    assert payload["folder_scan_performed"] is False
    assert payload["folder_creation_performed"] is False
    assert payload["folder_move_performed"] is False
    assert payload["folder_rename_performed"] is False
    assert payload["file_copy_performed"] is False
    assert payload["file_write_performed"] is False
    assert payload["media_download_performed"] is False
    assert payload["automatic_classification_performed"] is False
    assert payload["sensitive_identifier_inference_performed"] is False
    assert "Profile/Media Database Batch Import" in payload["import_text"]


def test_batch_import_rejects_missing_and_non_json_without_discovery(tmp_path):
    txt = tmp_path / "case.txt"
    txt.write_text("not json", encoding="utf-8")
    plan = build_batch_import_plan([txt, tmp_path / "missing.json"], database_root="Chosen Root")
    result = apply_batch_import_plan(plan)
    payload = batch_import_result_payload(result)
    assert payload["status"] == "blocked_no_valid_batch_json"
    assert payload["accepted_file_count"] == 0
    assert payload["rejected_file_count"] == 2
    assert payload["database_root"] == "Chosen Root"
    assert "not_json_file" in payload["warnings"]
    assert "missing_file" in payload["warnings"]


def test_validate_batch_json_warns_for_missing_case_title(tmp_path):
    batch = tmp_path / "case.json"
    batch.write_text(json.dumps({"sources": [{"source_title": "x"}], "profiles": []}), encoding="utf-8")
    item = validate_batch_json_file(batch)
    assert item.status == "accepted_with_warnings"
    assert item.source_count == 1
    assert item.profile_count == 0
    assert "missing_case_title" in item.warnings


def main() -> int:
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as directory:
        test_batch_import_accepts_explicit_valid_file_without_scanning(Path(directory))
    with tempfile.TemporaryDirectory() as directory:
        test_batch_import_rejects_missing_and_non_json_without_discovery(Path(directory))
    with tempfile.TemporaryDirectory() as directory:
        test_validate_batch_json_warns_for_missing_case_title(Path(directory))
    print("profile_media_database_batch_import_assistant v76c OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
