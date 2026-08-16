from __future__ import annotations

from profile_media_case_batch import write_demo_case_batch_json
from profile_media_database_navigation import (
    build_navigation_index_from_batch_json_files,
    filter_navigation_targets,
    navigation_payload,
    render_navigation_text,
)


def test_navigation_targets_and_filtering(tmp_path):
    batch = tmp_path / "batch.json"
    write_demo_case_batch_json(batch, database_root="Demo Database", case_title="Example Case")
    navigation = build_navigation_index_from_batch_json_files([batch])
    payload = navigation_payload(navigation, include_text=True)
    assert payload["status"] == "success"
    assert payload["case_target_count"] == 1
    assert payload["source_target_count"] == 2
    assert payload["profile_target_count"] == 2
    assert payload["folder_scan_performed"] is False
    assert payload["folder_creation_performed"] is False
    assert payload["folder_move_performed"] is False
    assert payload["folder_rename_performed"] is False
    assert payload["file_copy_performed"] is False
    assert payload["media_download_performed"] is False
    social = filter_navigation_targets(navigation, text="social media", target_type="source")
    assert len(social) == 1
    assert social[0].target_type == "source"
    assert "Social Media" in " > ".join(social[0].breadcrumb)
    text = render_navigation_text(navigation, text="Second", target_type="profile")
    assert "Second Example" in text
    assert "Folder scan performed: false" in text


def main() -> int:
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as directory:
        test_navigation_targets_and_filtering(Path(directory))
    print("profile_media_database_navigation v76a OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
