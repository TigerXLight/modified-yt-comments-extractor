from __future__ import annotations

import json
import tempfile
from pathlib import Path

from profile_media_case_batch import write_demo_case_batch_json
from profile_media_database_session import (
    PROFILE_MEDIA_DATABASE_EXPORT_CONFIRMATION,
    ProfileMediaDatabaseSessionConfig,
    apply_database_export_plan,
    build_database_export_plan,
    build_database_session_snapshot,
    database_session_config_from_mapping,
    load_database_session_config,
    render_database_session_text,
    write_database_session_config,
)


def test_session_snapshot_database_mode_searches_explicit_batch_only() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        batch_path = root / "case_batch.json"
        write_demo_case_batch_json(batch_path, database_root=str(root / "db"), case_title="Example Case")
        config = ProfileMediaDatabaseSessionConfig(
            database_root=str(root / "db"),
            batch_json_files=(str(batch_path),),
            mode="DATABASE",
            profile_name="Second",
        )
        snapshot = build_database_session_snapshot(config)
        payload = snapshot.to_dict(include_view_text=True)
        assert payload["status"] == "success"
        assert payload["index_case_count"] == 1
        assert payload["index_source_count"] == 2
        assert payload["index_profile_row_count"] == 2
        assert payload["matched_profile_count"] == 1
        assert payload["matched_source_count"] == 0
        assert payload["folder_scan_performed"] is False
        assert payload["folder_creation_performed"] is False
        assert payload["folder_move_performed"] is False
        assert payload["folder_rename_performed"] is False
        assert payload["file_copy_performed"] is False
        assert payload["file_write_performed"] is False
        assert payload["media_download_performed"] is False
        assert payload["automatic_classification_performed"] is False
        assert payload["sensitive_identifier_inference_performed"] is False
        text = render_database_session_text(snapshot)
        assert "Profile/Media Database Session" in text
        assert "Second Example" in text
        assert "Folder scan performed: false" in text


def test_files_mode_does_not_build_database_view() -> None:
    config = ProfileMediaDatabaseSessionConfig(mode="FILES", batch_json_files=("not-read.json",))
    snapshot = build_database_session_snapshot(config)
    payload = snapshot.to_dict(include_view_text=True)
    assert payload["status"] == "files_mode_passthrough"
    assert payload["mode_view"] is None
    assert payload["index_case_count"] == 0
    assert "database_view_not_built_in_files_mode" in payload["warnings"]
    assert payload["folder_scan_performed"] is False


def test_config_round_trip_and_mapping_coercion() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "session.json"
        config = database_session_config_from_mapping(
            {
                "database_root": "Database",
                "batch_json": "batch.json",
                "mode": "database",
                "profile_name": "Example",
                "source_chain_gap": "true",
                "disputed_framing": "false",
                "has_parser_warnings": "any",
                "limit": "5",
            }
        )
        assert config.mode == "DATABASE"
        assert config.batch_json_files == ("batch.json",)
        assert config.source_chain_gap is True
        assert config.disputed_framing is False
        assert config.has_parser_warnings is None
        assert config.limit == 5
        write_database_session_config(path, config)
        loaded = load_database_session_config(path)
        assert loaded == config


def test_export_plan_is_dry_run_by_default_and_guarded_when_executed() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        batch_path = root / "case_batch.json"
        write_demo_case_batch_json(batch_path, database_root=str(root / "db"), case_title="Example Case")
        snapshot = build_database_session_snapshot(
            ProfileMediaDatabaseSessionConfig(
                database_root=str(root / "db"),
                batch_json_files=(str(batch_path),),
                mode="DATABASE",
                source_chain_gap=True,
            )
        )
        plan = build_database_export_plan(root / "exports")
        dry = apply_database_export_plan(plan, snapshot)
        assert dry.status == "planned_dry_run"
        assert dry.file_write_performed is False
        assert not (root / "exports").exists()

        blocked_plan = build_database_export_plan(root / "exports", execute=True, confirmation_phrase="WRONG")
        blocked = apply_database_export_plan(blocked_plan, snapshot)
        assert blocked.status == "blocked_confirmation_required"
        assert blocked.file_write_performed is False
        assert not (root / "exports").exists()

        good_plan = build_database_export_plan(
            root / "exports",
            execute=True,
            confirmation_phrase=PROFILE_MEDIA_DATABASE_EXPORT_CONFIRMATION,
        )
        result = apply_database_export_plan(good_plan, snapshot)
        assert result.status == "success"
        assert result.file_write_performed is True
        assert result.folder_creation_performed is True
        assert result.folder_scan_performed is False
        assert result.folder_move_performed is False
        assert result.folder_rename_performed is False
        assert result.file_copy_performed is False
        assert result.media_download_performed is False
        assert len(result.written_files) == 3
        for written in result.written_files:
            assert Path(written).exists()
        exported = json.loads(Path(good_plan.json_path).read_text(encoding="utf-8"))
        assert exported["index_source_count"] == 2
        assert exported["matched_source_count"] == 1


def main() -> int:
    test_session_snapshot_database_mode_searches_explicit_batch_only()
    test_files_mode_does_not_build_database_view()
    test_config_round_trip_and_mapping_coercion()
    test_export_plan_is_dry_run_by_default_and_guarded_when_executed()
    print("profile_media_database_session v75z OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
