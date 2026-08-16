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


def test_profile_media_sidebar_preview_panel_is_removed() -> None:
    source = _main_source()
    assert "self.profile_media_database_preview_textbox" not in source
    assert "_build_profile_media_database_sidebar_preview_manifest" not in source
    assert "_profile_media_database_sidebar_preview_text" not in source
    assert "_refresh_profile_media_database_sidebar_preview" not in source


def test_profile_media_sidebar_has_no_preview_only_text_or_filter() -> None:
    source = _main_source()
    assert "Preview only" not in source
    assert "preview only" not in source.lower()
    assert "Filter Database preview" not in source
    assert "profile_media_database_filter" not in source
    assert "CTkEntry" not in _method_source(source, "_create_profile_media_database_mode_toggle_section")


def test_profile_media_sidebar_mode_only_toggle_remains_guarded() -> None:
    source = _main_source()
    method = _method_source(source, "_create_profile_media_database_mode_toggle_section")
    assert "CTkSwitch" in method
    assert 'text="On / Off"' in method
    assert "CTkTextbox" not in method
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
        "scan_folders",
        "classify(",
    )
    lowered = method.lower()
    for term in forbidden:
        assert term.lower() not in lowered


if __name__ == "__main__":
    test_profile_media_sidebar_preview_panel_is_removed()
    test_profile_media_sidebar_has_no_preview_only_text_or_filter()
    test_profile_media_sidebar_mode_only_toggle_remains_guarded()
    print("profile_media_database_sidebar_preview_removed v75l OK")
