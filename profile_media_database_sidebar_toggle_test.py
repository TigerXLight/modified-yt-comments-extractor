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


def test_profile_media_sidebar_toggle_has_required_state_fields() -> None:
    source = _main_source()

    assert 'self.profile_media_sidebar_mode: str = "FILES"' in source
    assert "self.profile_media_database_mode_var = None" in source
    assert "self.profile_media_mode_status_label = None" in source


def test_profile_media_sidebar_toggle_uses_database_on_off_control() -> None:
    source = _main_source()
    method = _method_source(source, "_create_profile_media_database_mode_toggle_section")

    assert 'text="DATABASE"' in method
    assert 'text="On / Off"' in method
    assert "CTkSwitch" in method
    assert "profile_media_database_mode_var" in method
    assert "_on_profile_media_database_mode_toggled" in method
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
    test_profile_media_sidebar_toggle_has_required_state_fields()
    test_profile_media_sidebar_toggle_uses_database_on_off_control()
    test_profile_media_sidebar_mode_uses_v75h_view_model_coercion()
    test_profile_media_sidebar_toggle_source_is_guarded()
    print("profile_media_database_sidebar_toggle v75i OK")
