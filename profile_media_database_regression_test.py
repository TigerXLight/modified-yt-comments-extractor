from __future__ import annotations

from profile_media_database_regression import (
    build_integration_batch_payload,
    render_full_regression_text,
    run_full_profile_media_regression,
    write_integration_batch_json,
)


def test_integration_batch_fixture_has_review_coverage():
    payload = build_integration_batch_payload(database_root="Demo Database", case_title="V76B Test Case")
    assert len(payload["sources"]) >= 40
    assert len(payload["profiles"]) >= 40
    assert any(item.get("source_chain_gap") for item in payload["sources"])
    assert any(item.get("disputed_framing") for item in payload["sources"])
    assert any(item.get("source_role") == "UNKNOWN_SOURCE_ROLE" for item in payload["sources"])


def test_full_regression_passes_without_mutating_filesystem(tmp_path):
    batch_path = tmp_path / "v76b_batch.json"
    write_integration_batch_json(batch_path, database_root="Demo Database", case_title="V76B Test Case")
    result = run_full_profile_media_regression([batch_path], database_root="Demo Database", include_text=True)
    payload = result.to_dict(include_text=True)
    assert payload["status"] == "success"
    assert payload["safety_audit"]["status"] == "passed"
    assert payload["readiness_report"]["ready_for_gui_panel"] is True
    assert payload["folder_scan_performed"] is False
    assert payload["folder_creation_performed"] is False
    assert payload["folder_move_performed"] is False
    assert payload["folder_rename_performed"] is False
    assert payload["file_copy_performed"] is False
    assert payload["file_write_performed"] is False
    assert payload["media_download_performed"] is False
    assert payload["automatic_classification_performed"] is False
    assert payload["sensitive_identifier_inference_performed"] is False
    assert "Profile/Media Database Full Regression" in render_full_regression_text(result)
    assert payload["payloads"]["workbench"]["index_source_count"] >= 40
    assert payload["payloads"]["workbench"]["workbench_export_result"]["status"] == "planned_dry_run"
    assert payload["payloads"]["workbench_blocked_export_result"]["status"] == "blocked_confirmation_required"


def main() -> int:
    import tempfile
    from pathlib import Path

    test_integration_batch_fixture_has_review_coverage()
    with tempfile.TemporaryDirectory() as directory:
        test_full_regression_passes_without_mutating_filesystem(Path(directory))
    print("profile_media_database_regression v76b OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
