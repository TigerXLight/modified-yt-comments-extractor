from pathlib import Path

from profile_media_database_view_model import (
    ProfileMediaViewMode,
    coerce_profile_media_view_mode,
    toggle_profile_media_view_mode,
)


def _main_source() -> str:
    return Path("main.py").read_text(encoding="utf-8")


def _method_source(source: str, method_name: str) -> str:
    anchor = f"    def {method_name}"
    start = source.index(anchor)
    next_start = source.find("\n    def ", start + len(anchor))
    if next_start == -1:
        return source[start:]
    return source[start:next_start]


def test_profile_media_sidebar_toggle_is_directly_above_files() -> None:
    source = _main_source()
    sidebar = _method_source(source, "_create_sidebar")

    assert sidebar.index("_create_export_section") < sidebar.index(
        "_create_profile_media_database_mode_toggle_section"
    )
    assert sidebar.index("_create_profile_media_database_mode_toggle_section") < sidebar.index(
        "_create_files_section"
    )
    assert "Profile/media Database mode toggle sits directly above FILES" in sidebar


def test_profile_media_sidebar_toggle_has_mode_only_state_fields() -> None:
    source = _main_source()

    assert 'self.profile_media_sidebar_mode: str = "FILES"' in source
    assert "self.profile_media_database_mode_var = None" in source
    assert "self.profile_media_mode_status_label = None" not in source
    assert "self.profile_media_database_preview_textbox = None" not in source


def test_profile_media_sidebar_toggle_uses_database_visual_on_off_control_only() -> None:
    source = _main_source()
    method = _method_source(source, "_create_profile_media_database_mode_toggle_section")

    assert 'text="DATABASE"' in method
    assert "CTkSwitch" in method
    assert "profile_media_database_mode_var" in method
    assert "_on_profile_media_database_mode_toggled" in method
    assert "_profile_media_database_toggle_text" in method
    assert "_refresh_profile_media_database_mode_switch_visual" in method
    assert 'fg_color="#e84b6a"' in method
    assert 'progress_color="#7ac943"' in method
    assert "CTkTextbox" not in method
    assert "CTkEntry" not in method
    assert "Filter Database preview" not in method
    assert "preview only" not in method.lower()
    assert "profile_media_mode_status_label" not in method
    assert "profile_media_database_preview_textbox" not in method
    assert "_create_files_section" not in method
    assert "os.rename" not in method
    assert "shutil.move" not in method
    assert "mkdir" not in method
    assert "classify" not in method.lower()


def test_profile_media_sidebar_mode_uses_v75h_view_model_coercion() -> None:
    assert coerce_profile_media_view_mode("FILES") == ProfileMediaViewMode.FILES
    assert coerce_profile_media_view_mode("db") == ProfileMediaViewMode.DATABASE
    assert coerce_profile_media_view_mode("file_browser") == ProfileMediaViewMode.FILES
    assert toggle_profile_media_view_mode("FILES") == ProfileMediaViewMode.DATABASE
    assert toggle_profile_media_view_mode("DATABASE") == ProfileMediaViewMode.FILES


def test_profile_media_sidebar_toggle_source_is_guarded() -> None:
    source = _main_source()
    combined_source = "\n".join(
        (
            _method_source(source, "_coerce_profile_media_sidebar_mode"),
            _method_source(source, "_set_profile_media_sidebar_mode"),
            _method_source(source, "_profile_media_database_toggle_text"),
            _method_source(source, "_refresh_profile_media_database_mode_switch_visual"),
            _method_source(source, "_on_profile_media_database_mode_toggled"),
            _method_source(source, "_create_profile_media_database_mode_toggle_section"),
        )
    )

    forbidden = (
        "os.rename",
        "os.replace",
        "shutil.move",
        "shutil.copy",
        "rmtree",
        "unlink(",
        "mkdir(",
    )
    lowered = combined_source.lower()
    for term in forbidden:
        assert term.lower() not in lowered
    assert "coerce_profile_media_view_mode" in combined_source
    assert "No folder scan, move, rename, or classification was performed" in combined_source


if __name__ == "__main__":
    test_profile_media_sidebar_toggle_is_directly_above_files()
    test_profile_media_sidebar_toggle_has_mode_only_state_fields()
    test_profile_media_sidebar_toggle_uses_database_visual_on_off_control_only()
    test_profile_media_sidebar_mode_uses_v75h_view_model_coercion()
    test_profile_media_sidebar_toggle_source_is_guarded()
    print("profile_media_database_sidebar_toggle v75m OK")
