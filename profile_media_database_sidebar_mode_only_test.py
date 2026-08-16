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


def test_database_sidebar_section_is_visual_mode_on_off_only() -> None:
    source = _main_source()
    method = _method_source(source, "_create_profile_media_database_mode_toggle_section")

    assert 'text="DATABASE"' in method
    assert "_profile_media_database_toggle_text" in method
    assert "CTkButton" in method
    assert "CTkSwitch" not in method
    assert "CTkLabel" in method
    assert "#7ac943" in method
    assert "#e84b6a" in method
    assert "CTkTextbox" not in method
    assert "CTkEntry" not in method
    assert "preview" not in method.lower()
    assert "filter" not in method.lower()
    assert "status" not in method.lower()


def test_database_sidebar_mode_setter_does_not_update_preview_or_status_widgets() -> None:
    source = _main_source()
    method = _method_source(source, "_set_profile_media_sidebar_mode")

    assert "profile_media_database_mode_var" in method
    assert "_refresh_profile_media_database_mode_switch_visual" in method
    assert "profile_media_mode_status_label" not in method
    assert "profile_media_database_preview_textbox" not in method
    assert "_refresh_profile_media_database_sidebar_preview" not in method


if __name__ == "__main__":
    test_database_sidebar_section_is_visual_mode_on_off_only()
    test_database_sidebar_mode_setter_does_not_update_preview_or_status_widgets()
    print("profile_media_database_sidebar_mode_only v75n OK")
