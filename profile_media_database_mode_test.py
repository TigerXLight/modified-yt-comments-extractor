from __future__ import annotations

import tempfile
from pathlib import Path

from profile_media_case_batch import build_demo_case_batch_payload, write_demo_case_batch_json
from profile_media_database_mode import (
    PROFILE_MEDIA_DATABASE_MODE_SCHEMA_VERSION,
    build_database_mode_view_from_batch_json_files,
    build_database_mode_view_from_payloads,
    database_mode_payload,
    render_database_mode_view_text,
)


def _demo_payload():
    return build_demo_case_batch_payload(database_root="C:/DB", case_title="Example Case")


def test_database_mode_view_builds_main_panel_sections_without_filesystem_work() -> None:
    view = build_database_mode_view_from_payloads([_demo_payload()])
    data = view.to_dict()
    assert data["schema_version"] == PROFILE_MEDIA_DATABASE_MODE_SCHEMA_VERSION
    assert data["mode"] == "DATABASE"
    assert data["index_case_count"] == 1
    assert data["index_source_count"] == 2
    assert data["index_profile_row_count"] == 2
    assert data["section_count"] == 3
    assert [section["section_id"] for section in data["sections"]] == ["cases", "sources", "profiles"]
    assert data["folder_scan_performed"] is False
    assert data["folder_creation_performed"] is False
    assert data["folder_move_performed"] is False
    assert data["folder_rename_performed"] is False
    assert data["file_copy_performed"] is False
    assert data["file_write_performed"] is False
    assert data["media_download_performed"] is False
    assert data["automatic_classification_performed"] is False
    assert data["sensitive_identifier_inference_performed"] is False


def test_profile_search_view_keeps_cases_visible_and_filters_profiles() -> None:
    view = build_database_mode_view_from_payloads([_demo_payload()], profile_name="Second")
    data = view.to_dict()
    cases = data["sections"][0]
    sources = data["sections"][1]
    profiles = data["sections"][2]
    assert cases["row_count"] == 1
    assert sources["row_count"] == 0
    assert profiles["row_count"] == 1
    assert profiles["rows"][0]["title"] == "Second Example"
    assert profiles["rows"][0]["source_bucket"] == "Social Media/Online"


def test_source_gap_and_disputed_rows_are_tagged() -> None:
    gap_view = build_database_mode_view_from_payloads([_demo_payload()], source_chain_gap=True)
    gap_sources = gap_view.to_dict()["sections"][1]["rows"]
    assert len(gap_sources) == 1
    assert "source-chain gap" in gap_sources[0]["tags"]
    disputed_view = build_database_mode_view_from_payloads([_demo_payload()], disputed_framing=True)
    disputed_sources = disputed_view.to_dict()["sections"][1]["rows"]
    assert len(disputed_sources) == 1
    assert "disputed framing" in disputed_sources[0]["tags"]


def test_rendered_view_text_and_payload() -> None:
    view = build_database_mode_view_from_payloads([_demo_payload()], text="BelfastLive")
    payload = database_mode_payload(view, include_text=True)
    assert payload["status"] == "success"
    assert "Profile/Media Database Mode View" in payload["view_text"]
    assert "Folder scan performed: false" in payload["view_text"]
    assert "Sensitive identifier inference performed: false" in payload["view_text"]
    assert "BelfastLive" in render_database_mode_view_text(view)


def test_explicit_batch_file_view_without_folder_scan() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        batch_path = Path(tmp) / "batch.json"
        write_demo_case_batch_json(batch_path, database_root=str(Path(tmp) / "DB"), case_title="Example Case")
        view = build_database_mode_view_from_batch_json_files([batch_path], source_bucket="Articles")
        data = view.to_dict()
        assert data["matched_source_count"] == 1
        assert data["matched_profile_count"] == 1
        assert data["folder_scan_performed"] is False
        assert data["file_write_performed"] is False


def main() -> None:
    test_database_mode_view_builds_main_panel_sections_without_filesystem_work()
    test_profile_search_view_keeps_cases_visible_and_filters_profiles()
    test_source_gap_and_disputed_rows_are_tagged()
    test_rendered_view_text_and_payload()
    test_explicit_batch_file_view_without_folder_scan()
    print("profile_media_database_mode v75y OK")


if __name__ == "__main__":
    main()
