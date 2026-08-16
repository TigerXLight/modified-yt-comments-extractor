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


def test_profile_media_sidebar_preview_state_field_exists() -> None:
    source = _main_source()
    assert "self.profile_media_database_preview_textbox = None" in source


def test_profile_media_sidebar_preview_has_required_hierarchy() -> None:
    source = _main_source()
    method = _method_source(source, "_profile_media_database_sidebar_preview_text")

    expected = (
        "Database",
        "Profiles",
        "Case Folder",
        "People",
        "Sources",
        "Articles",
        "Social Media",
        "Offline",
        "Online",
        "Internal Media",
        "Reference Extants",
    )
    for label in expected:
        assert label in method
    assert method.index("Sources") < method.index("Articles")
    assert method.index("Social Media") < method.index("Offline")
    assert method.index("Social Media") < method.index("Online")
    assert "Preview only" in method


def test_profile_media_sidebar_preview_is_only_visible_in_database_mode() -> None:
    source = _main_source()
    method = _method_source(source, "_refresh_profile_media_database_sidebar_preview")

    assert "profile_media_database_preview_textbox" in method
    assert 'mode != "DATABASE"' in method
    assert "grid_remove" in method
    assert 'preview_box.grid(row=3' in method
    assert "_profile_media_database_sidebar_preview_text" in method


def test_profile_media_sidebar_toggle_creates_preview_textbox() -> None:
    source = _main_source()
    method = _method_source(source, "_create_profile_media_database_mode_toggle_section")

    assert "ctk.CTkTextbox" in method
    assert "profile_media_database_preview_textbox" in method
    assert "_refresh_profile_media_database_sidebar_preview" in method
    assert 'height=156' in method


def test_profile_media_sidebar_mode_updates_preview() -> None:
    source = _main_source()
    method = _method_source(source, "_set_profile_media_sidebar_mode")
    assert "_refresh_profile_media_database_sidebar_preview" in method
    assert "profile_media_database_mode_var" in method
    assert "profile_media_mode_status_label" in method


def test_profile_media_sidebar_preview_source_is_guarded() -> None:
    source = _main_source()
    combined_source = "\n".join(
        (
            _method_source(source, "_profile_media_database_sidebar_preview_text"),
            _method_source(source, "_refresh_profile_media_database_sidebar_preview"),
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
        "glob(",
        "rglob(",
        "os.walk",
    )
    lowered = combined_source.lower()
    for term in forbidden:
        assert term.lower() not in lowered
    assert "classify(" not in lowered


if __name__ == "__main__":
    test_profile_media_sidebar_preview_state_field_exists()
    test_profile_media_sidebar_preview_has_required_hierarchy()
    test_profile_media_sidebar_preview_is_only_visible_in_database_mode()
    test_profile_media_sidebar_toggle_creates_preview_textbox()
    test_profile_media_sidebar_mode_updates_preview()
    test_profile_media_sidebar_preview_source_is_guarded()
    print("profile_media_database_sidebar_preview v75j OK")
