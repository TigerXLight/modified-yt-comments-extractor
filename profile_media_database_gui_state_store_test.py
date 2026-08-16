from __future__ import annotations

import json
from pathlib import Path

from profile_media_database_gui_state_store import (
    PROFILE_MEDIA_DATABASE_GUI_STATE_CLEAR_CONFIRMATION,
    PROFILE_MEDIA_DATABASE_GUI_STATE_SAVE_CONFIRMATION,
    build_gui_state_config,
    clear_gui_state_config,
    gui_state_payload,
    load_gui_state_config,
    render_gui_state_text,
    save_gui_state_config,
)


def test_gui_state_config_is_explicit_and_inert() -> None:
    config = build_gui_state_config(database_root="Demo", batch_json_files=["case.json", "case.json"], source_chain_gap="true", limit="5")
    payload = gui_state_payload(config)
    assert payload["database_root"] == "Demo"
    assert payload["batch_json_files"] == ["case.json"]
    assert payload["source_chain_gap"] is True
    assert payload["limit"] == 5
    assert payload["folder_scan_performed"] is False
    assert payload["folder_creation_performed"] is False
    assert payload["folder_move_performed"] is False
    assert payload["folder_rename_performed"] is False
    assert payload["file_copy_performed"] is False
    assert payload["media_download_performed"] is False
    assert payload["automatic_classification_performed"] is False
    assert payload["sensitive_identifier_inference_performed"] is False
    assert "Profile/Media Database GUI State" in render_gui_state_text(config)


def test_save_is_dry_run_without_execute(tmp_path: Path) -> None:
    path = tmp_path / "state.json"
    config = build_gui_state_config(database_root="Demo", batch_json_files=["case.json"])
    result = save_gui_state_config(config, path)
    assert result.status == "planned_dry_run_no_state_written"
    assert result.file_write_performed is False
    assert result.config_file_write_performed is False
    assert not path.exists()


def test_save_load_and_clear_require_confirmation(tmp_path: Path) -> None:
    path = tmp_path / "state.json"
    config = build_gui_state_config(database_root="Demo", batch_json_files=["case.json"], profile_name="Example")
    blocked = save_gui_state_config(config, path, execute=True, confirmation_phrase="WRONG")
    assert blocked.status == "blocked_missing_save_confirmation"
    assert not path.exists()

    saved = save_gui_state_config(config, path, execute=True, confirmation_phrase=PROFILE_MEDIA_DATABASE_GUI_STATE_SAVE_CONFIRMATION)
    assert saved.status == "state_saved"
    assert saved.file_write_performed is True
    assert saved.config_file_write_performed is True
    loaded = load_gui_state_config(path)
    assert loaded.status == "success"
    assert loaded.config is not None
    assert loaded.config.database_root == "Demo"
    assert loaded.config.profile_name == "Example"

    dry_clear = clear_gui_state_config(path)
    assert dry_clear.status == "planned_dry_run_no_state_cleared"
    assert path.exists()
    cleared = clear_gui_state_config(path, execute=True, confirmation_phrase=PROFILE_MEDIA_DATABASE_GUI_STATE_CLEAR_CONFIRMATION)
    assert cleared.status == "state_cleared"
    assert not path.exists()


def main() -> int:
    import tempfile

    test_gui_state_config_is_explicit_and_inert()
    with tempfile.TemporaryDirectory() as directory:
        test_save_is_dry_run_without_execute(Path(directory))
    with tempfile.TemporaryDirectory() as directory:
        test_save_load_and_clear_require_confirmation(Path(directory))
    print("profile_media_database_gui_state_store v76d OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
