from __future__ import annotations

import tempfile
from pathlib import Path

from profile_media_case_batch import build_demo_case_batch_payload, write_demo_case_batch_json
from profile_media_database_index import build_database_index_from_payloads
from profile_media_database_search import (
    PROFILE_MEDIA_DATABASE_SEARCH_SCHEMA_VERSION,
    render_database_search_text,
    result_payload,
    search_database_batch_json_files,
    search_database_index,
)


def _demo_index():
    return build_database_index_from_payloads([build_demo_case_batch_payload(database_root="C:/DB", case_title="Example Case")])


def test_profile_name_query_keeps_database_mode_safe() -> None:
    result = search_database_index(_demo_index(), profile_name="Second")
    data = result.to_dict()
    assert data["schema_version"] == PROFILE_MEDIA_DATABASE_SEARCH_SCHEMA_VERSION
    assert data["matched_profile_count"] == 1
    assert data["matched_source_count"] == 0
    assert data["matched_profiles"][0]["canonical_name"] == "Second Example"
    assert data["folder_scan_performed"] is False
    assert data["folder_move_performed"] is False
    assert data["folder_rename_performed"] is False
    assert data["file_copy_performed"] is False
    assert data["media_download_performed"] is False
    assert data["automatic_classification_performed"] is False
    assert data["sensitive_identifier_inference_performed"] is False


def test_source_chain_gap_and_disputed_framing_queries() -> None:
    index = _demo_index()
    gap = search_database_index(index, source_chain_gap=True)
    assert gap.to_dict()["matched_source_count"] == 1
    assert gap.to_dict()["matched_profile_count"] == 0
    assert gap.to_dict()["matched_sources"][0]["source_chain_gap"] is True
    disputed = search_database_index(index, disputed_framing=True)
    assert disputed.to_dict()["matched_source_count"] == 1
    assert disputed.to_dict()["matched_sources"][0]["disputed_framing"] is True


def test_text_query_and_rendered_report() -> None:
    result = search_database_index(_demo_index(), text="BelfastLive")
    payload = result_payload(result, include_text=True)
    assert payload["status"] == "success"
    assert payload["matched_source_count"] >= 1
    assert payload["matched_profile_count"] >= 1
    assert "Profile/Media Database Search" in payload["search_text"]
    assert "Folder scan performed: false" in payload["search_text"]
    assert "Sensitive identifier inference performed: false" in payload["search_text"]
    rendered = render_database_search_text(result)
    assert "BelfastLive" in rendered


def test_explicit_batch_json_file_query_without_folder_scan() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        batch_path = Path(tmp) / "batch.json"
        write_demo_case_batch_json(batch_path, database_root=str(Path(tmp) / "DB"), case_title="Example Case")
        result = search_database_batch_json_files([batch_path], source_bucket="Social Media/Online")
        data = result.to_dict()
        assert data["matched_source_count"] == 1
        assert data["matched_profile_count"] == 1
        assert data["folder_scan_performed"] is False
        assert data["file_write_performed"] is False


def main() -> None:
    test_profile_name_query_keeps_database_mode_safe()
    test_source_chain_gap_and_disputed_framing_queries()
    test_text_query_and_rendered_report()
    test_explicit_batch_json_file_query_without_folder_scan()
    print("profile_media_database_search v75x OK")


if __name__ == "__main__":
    main()
