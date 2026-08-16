from __future__ import annotations

import json
import tempfile
from pathlib import Path

from profile_media_case_batch import build_demo_case_batch_payload, write_demo_case_batch_json
from profile_media_database_index import (
    PROFILE_MEDIA_DATABASE_INDEX_SCHEMA_VERSION,
    build_database_index_from_batch_json_files,
    build_database_index_from_payloads,
    render_database_index_text,
    result_payload,
)


def test_build_index_from_demo_payload() -> None:
    payload = build_demo_case_batch_payload(database_root="C:/ExampleDB", case_title="Example Case")
    index = build_database_index_from_payloads([payload])
    data = index.to_dict()
    assert data["schema_version"] == PROFILE_MEDIA_DATABASE_INDEX_SCHEMA_VERSION
    assert data["case_count"] == 1
    assert data["source_count"] == 2
    assert data["profile_row_count"] == 2
    assert data["unique_profile_count"] == 2
    assert data["source_chain_gap_count"] == 1
    assert data["disputed_framing_count"] == 1
    assert data["sensitive_identifier_inference_performed"] is False
    assert data["folder_scan_performed"] is False
    assert "Example Person" in data["unique_profile_names"]
    assert data["profile_case_map"]["Second Example"] == ["Example Case"]


def test_build_index_from_two_explicit_files_without_scanning() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        first = Path(tmp) / "first.json"
        second = Path(tmp) / "second.json"
        write_demo_case_batch_json(first, database_root=str(Path(tmp) / "Database"), case_title="First Case")
        payload = build_demo_case_batch_payload(database_root=str(Path(tmp) / "Database"), case_title="Second Case")
        payload["profiles"][0]["profile_text"] = payload["profiles"][0]["profile_text"].replace("Example Person", "Shared Person")
        payload["profiles"][1]["profile_text"] = payload["profiles"][1]["profile_text"].replace("Second Example", "Shared Person")
        second.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        index = build_database_index_from_batch_json_files([first, second])
        data = index.to_dict()
        assert data["case_count"] == 2
        assert data["source_count"] == 4
        assert data["profile_row_count"] == 4
        assert data["folder_scan_performed"] is False
        assert "First Case" in data["cases"]
        assert "Second Case" in data["cases"]
        assert "Shared Person" in data["profile_case_map"]


def test_render_and_payload_expose_safety_flags() -> None:
    index = build_database_index_from_payloads([build_demo_case_batch_payload(database_root="C:/DB", case_title="Example Case")])
    text = render_database_index_text(index)
    assert "Profile/Media Database Index" in text
    assert "Folder scan performed: false" in text
    assert "Sensitive identifier inference performed: false" in text
    assert "source-chain gap" in text
    payload = result_payload(index, include_text=True)
    assert payload["status"] == "success"
    assert payload["folder_scan_performed"] is False
    assert payload["index"]["automatic_classification_performed"] is False
    assert "index_text" in payload


def main() -> None:
    test_build_index_from_demo_payload()
    test_build_index_from_two_explicit_files_without_scanning()
    test_render_and_payload_expose_safety_flags()
    print("profile_media_database_index v75w OK")


if __name__ == "__main__":
    main()
