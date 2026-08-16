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


def test_main_content_creates_database_workbench_panel_between_progress_and_editors() -> None:
    source = _main_source()
    method = _method_source(source, "_create_main_content")
    assert "_create_profile_media_database_workbench_panel()" in method
    assert method.index("_create_progress_section()") < method.index("_create_profile_media_database_workbench_panel()")
    assert method.index("_create_profile_media_database_workbench_panel()") < method.index("_create_text_editor_section()")


def test_database_panel_is_main_content_not_sidebar_preview_or_filter() -> None:
    source = _main_source()
    method = _method_source(source, "_create_profile_media_database_workbench_panel")
    assert "self.main_frame" in method
    assert "DATABASE Workbench" in method
    assert "CTkFrame" in method
    assert "CTkLabel" in method
    assert "CTkButton" in method
    assert "Load batch JSON" in method
    assert "_select_profile_media_database_batch_json_files" in method
    assert "sidebar_scroll" not in method
    assert "CTkTextbox" not in method
    assert "filter" not in method.lower()
    assert "preview" not in method.lower()


def test_database_panel_refresh_and_batch_selection_are_safe() -> None:
    source = _main_source()
    combined = "\n".join(
        (
            _method_source(source, "_refresh_profile_media_database_workbench_panel"),
            _method_source(source, "_build_profile_media_database_workbench_payload_from_batches"),
            _method_source(source, "_select_profile_media_database_batch_json_files"),
        )
    )
    assert "askopenfilenames" in combined
    assert "build_batch_import_plan" in combined
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
        "unlink(",
        "download",
        "auto_class",
        "classify",
        "infer_sensitive",
    )
    lowered = combined.lower()
    for term in forbidden:
        assert term.lower() not in lowered


def test_database_toggle_refreshes_main_panel_without_adding_sidebar_preview() -> None:
    source = _main_source()
    setter = _method_source(source, "_set_profile_media_sidebar_mode")
    assert "_refresh_profile_media_database_workbench_panel" in setter
    assert "profile_media_database_preview_textbox" not in setter
    assert "_refresh_profile_media_database_sidebar_preview" not in setter


def main() -> int:
    test_main_content_creates_database_workbench_panel_between_progress_and_editors()
    test_database_panel_is_main_content_not_sidebar_preview_or_filter()
    test_database_panel_refresh_and_batch_selection_are_safe()
    test_database_toggle_refreshes_main_panel_without_adding_sidebar_preview()
    print("profile_media_database_gui_panel_main v76c OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
