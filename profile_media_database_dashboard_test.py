from __future__ import annotations

from profile_media_case_batch import write_demo_case_batch_json
from profile_media_database_dashboard import (
    build_dashboard_from_batch_json_files,
    dashboard_payload,
    render_dashboard_text,
)


def test_dashboard_counts_and_safety(tmp_path):
    batch = tmp_path / "batch.json"
    write_demo_case_batch_json(batch, database_root="Demo Database", case_title="Example Case")
    dashboard = build_dashboard_from_batch_json_files([batch])
    payload = dashboard_payload(dashboard, include_text=True)
    assert payload["status"] == "success"
    assert payload["case_count"] == 1
    assert payload["unique_profile_count"] == 2
    assert any(metric["key"] == "sources" and metric["value"] == 2 for metric in payload["metrics"])
    assert any(facet["facet_type"] == "source_bucket" and facet["value"] == "Articles" for facet in payload["facets"])
    assert payload["folder_scan_performed"] is False
    assert payload["folder_move_performed"] is False
    assert payload["folder_rename_performed"] is False
    assert payload["file_copy_performed"] is False
    assert payload["media_download_performed"] is False
    assert payload["automatic_classification_performed"] is False
    assert payload["sensitive_identifier_inference_performed"] is False
    text = render_dashboard_text(dashboard)
    assert "Profile/Media Database Dashboard" in text
    assert "Source-chain gaps" in text


def main() -> int:
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as directory:
        test_dashboard_counts_and_safety(Path(directory))
    print("profile_media_database_dashboard v76a OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
