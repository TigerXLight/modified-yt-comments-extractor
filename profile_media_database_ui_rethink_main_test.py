from __future__ import annotations

from pathlib import Path


def test_main_database_toggle_uses_clear_home_slider_and_save_button() -> None:
    source = Path("main.py").read_text(encoding="utf-8")
    assert "SAVE" in source
    assert "✓  ON" in source
    assert "OFF" in source
    assert "profile_media_database_home_save_button" in source
    assert "profile_media_database_sidebar_summary_labels" in source


def test_main_hides_backend_terms_from_common_user_buttons() -> None:
    source = Path("main.py").read_text(encoding="utf-8")
    assert "Add / Import" in source
    assert "Unload" in source
    assert "Save to HOME" in source
    assert "Load batch JSON" not in source
    assert 'text="Materialize"' not in source
    assert 'text="Clear batch"' not in source
    assert 'text="Refresh"' not in source


def test_main_uses_home_import_dialog_wording() -> None:
    source = Path("main.py").read_text(encoding="utf-8")
    assert "Add / Import Profile-Media source package" in source
    assert "Profile-Media import files" in source
    assert "Database import" in source


if __name__ == "__main__":
    test_main_database_toggle_uses_clear_home_slider_and_save_button()
    test_main_hides_backend_terms_from_common_user_buttons()
    test_main_uses_home_import_dialog_wording()
    print("profile_media_database_ui_rethink_main v76k2 OK")
