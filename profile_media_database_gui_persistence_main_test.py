from __future__ import annotations

from pathlib import Path


def _main_source() -> str:
    return Path("main.py").read_text(encoding="utf-8")


def _method_source(source: str, method_name: str) -> str:
    anchor = f"    def {method_name}"
    start = source.index(anchor)
    next_start = source.find("\n    def ", start + len(anchor))
    if next_start == -1:
        return source[start:]
    return source[start:next_start]


def test_main_loads_saved_database_gui_state_before_panel_creation() -> None:
    source = _main_source()
    assert "profile_media_database_gui_state_path" in source
    assert "_load_profile_media_database_saved_gui_state_for_startup()" in source
    loader = _method_source(source, "_load_profile_media_database_saved_gui_state_for_startup")
    assert "build_database_gui_selection_from_saved_state" in loader
    assert "profile_media_database_batch_json_files" in loader
    assert "profile_media_database_workbench_payload" in loader
    assert "os.walk" not in loader
    assert "rglob(" not in loader
    assert ".glob(" not in loader


def test_main_batch_selection_uses_controller_and_persists_explicit_state() -> None:
    source = _main_source()
    method = _method_source(source, "_select_profile_media_database_batch_json_files")
    assert "build_database_gui_selection_from_batch_json" in method
    assert "PROFILE_MEDIA_DATABASE_GUI_STATE_SAVE_CONFIRMATION" in method
    assert "persist_state=True" in method
    assert "askopenfilenames" in method
    forbidden = (
        "os.walk",
        ".glob(",
        "rglob(",
        "mkdir(",
        "os.rename",
        "os.replace",
        "shutil.move",
        "shutil.copy",
        "rmtree",
        "download_media",
        "auto_class",
        "infer_sensitive",
    )
    lowered = method.lower()
    for term in forbidden:
        assert term.lower() not in lowered


def test_main_has_clear_database_selection_action_without_sidebar_filter() -> None:
    source = _main_source()
    panel = _method_source(source, "_create_profile_media_database_workbench_panel")
    clearer = _method_source(source, "_clear_profile_media_database_batch_json_files")
    assert "Clear batch" in panel
    assert "_clear_profile_media_database_batch_json_files" in panel
    assert "build_database_gui_clear_selection" in clearer
    assert "PROFILE_MEDIA_DATABASE_GUI_STATE_CLEAR_CONFIRMATION" in clearer
    assert "sidebar_scroll" not in panel
    assert "preview" not in panel.lower()
    assert "filter" not in panel.lower()


def main() -> int:
    test_main_loads_saved_database_gui_state_before_panel_creation()
    test_main_batch_selection_uses_controller_and_persists_explicit_state()
    test_main_has_clear_database_selection_action_without_sidebar_filter()
    print("profile_media_database_gui_persistence_main v76d OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
