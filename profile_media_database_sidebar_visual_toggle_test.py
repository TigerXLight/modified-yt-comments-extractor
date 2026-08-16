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


def test_database_toggle_uses_square_check_handle_x_labels() -> None:
    source = _main_source()
    text_method = _method_source(source, "_profile_media_database_toggle_text")

    assert "✓        ◻" in text_method
    assert "◻        ✕" in text_method
    assert "DATABASE" in text_method


def test_database_toggle_uses_green_on_and_red_off_button_colours() -> None:
    source = _main_source()
    refresh_method = _method_source(source, "_refresh_profile_media_database_mode_switch_visual")
    create_method = _method_source(source, "_create_profile_media_database_mode_toggle_section")

    combined = refresh_method + "\n" + create_method
    assert "CTkButton" in combined
    assert "#7ac943" in combined
    assert "#e84b6a" in combined
    assert "#4d9b29" in combined
    assert "#b92d4d" in combined
    assert "hover_color" in combined
    assert "border_color" in combined
    assert "button_color" not in combined
    assert "progress_color" not in combined


def test_database_toggle_click_flips_existing_mode_without_preview_or_file_operations() -> None:
    source = _main_source()
    combined = "\n".join(
        (
            _method_source(source, "_profile_media_database_toggle_text"),
            _method_source(source, "_refresh_profile_media_database_mode_switch_visual"),
            _method_source(source, "_on_profile_media_database_mode_toggled"),
            _method_source(source, "_create_profile_media_database_mode_toggle_section"),
        )
    )

    assert 'requested_mode = "FILES" if current_mode == "DATABASE" else "DATABASE"' in combined
    forbidden = (
        "CTkTextbox",
        "CTkEntry",
        "Filter Database preview",
        "preview only",
        "os.rename",
        "os.replace",
        "shutil.move",
        "shutil.copy",
        "rmtree",
        "unlink(",
        "mkdir(",
        "classify",
    )
    lowered = combined.lower()
    for term in forbidden:
        assert term.lower() not in lowered


if __name__ == "__main__":
    test_database_toggle_uses_square_check_handle_x_labels()
    test_database_toggle_uses_green_on_and_red_off_button_colours()
    test_database_toggle_click_flips_existing_mode_without_preview_or_file_operations()
    print("profile_media_database_sidebar_visual_toggle v75n OK")
