"""Source assertions for the Text Editor spell correction overlay.

This protects the compact reference-style spell menu from regressing into
orphaned desktop Toplevel popups or the broad embedded spelling bar.
"""

from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MAIN = ROOT / "main.py"
SOURCE = MAIN.read_text(encoding="utf-8")


def _method(name: str) -> str:
    pattern = re.compile(rf"^    def {re.escape(name)}\(.*?(?=^    def |\Z)", re.M | re.S)
    match = pattern.search(SOURCE)
    assert match, f"Missing method {name}"
    return match.group(0)


def test_no_broad_spelling_bar_or_wrong_label() -> None:
    text_editor_section = _method("_create_text_editor_section")
    assert "Spelling:" not in text_editor_section
    assert "(wrong text)" not in SOURCE


def test_popup_is_app_owned_overlay_not_toplevel() -> None:
    show = _method("_show_text_editor_spell_popup")
    assert "tk.Toplevel" not in show
    assert "overrideredirect" not in show
    assert "-topmost" not in show
    assert 'parent = getattr(self, "text_editor_card", None)' in show
    assert "tk.Frame(" in show
    assert "popup.place(" in show
    assert "popup.lift()" in show


def test_single_instance_cleanup_before_showing_new_overlay() -> None:
    show = _method("_show_text_editor_spell_popup")
    hide = _method("_hide_text_editor_spell_popup")
    assert "self._hide_text_editor_spell_popup()" in show
    assert "existing_popup is not None" in show
    assert "popup.destroy()" in hide
    assert "self.text_editor_spell_popup = None" in hide
    assert "self.text_editor_spell_popup_bridge_bounds = None" in hide


def test_lifecycle_closes_overlay() -> None:
    bind = _method("_bind_text_editor_spellcheck")
    hide_panel = _method("_hide_text_editor_panel")
    assert '"<Escape>"' in bind
    assert '"<MouseWheel>"' in bind
    assert '"<Button-4>"' in bind
    assert '"<Button-5>"' in bind
    assert '"<Unmap>"' in bind
    assert '"<FocusOut>"' in bind
    assert "self._hide_text_editor_spell_popup()" in hide_panel
    assert "_handle_text_editor_key_press" in SOURCE
    assert "self._hide_text_editor_spell_popup()" in _method("_handle_text_editor_key_press")


def test_click_away_actions_and_hover_rows_remain() -> None:
    click = _method("_handle_text_editor_spell_click")
    show = _method("_show_text_editor_spell_popup")
    assert "self._hide_text_editor_spell_popup()" in click
    assert "Add to Dictionary" in show
    assert "_replace_text_editor_misspelling" in show
    assert 'activebackground=COLORS["accent"]' in show
    assert "_add_text_editor_spelling_word" in SOURCE


def test_url_path_skip_rules_remain() -> None:
    skip = _method("_text_editor_line_is_spellcheck_exempt")
    should = _method("_should_spellcheck_word")
    assert "https?://|www\\." in skip
    assert "source:" in skip
    assert "selected quality:" in skip
    assert "plan files:" in skip
    assert "[a-zA-Z]:[\\\\/]" in skip
    assert '"/?=&:._-\\\\"' in should


def test_undo_redo_and_panel_open_behaviour_remain() -> None:
    undo = _method("_configure_text_editor_undo_redo")
    assert '"<Control-z>"' in undo
    assert '"<Control-y>"' in undo
    load = _method("_load_session_text_editor_file")
    assert "self._show_text_editor_panel()" in load
    add_file_block = SOURCE[SOURCE.find("def add_file_to_list"): SOURCE.find("def add_folder_to_list")]
    assert "_show_text_editor_panel()" not in add_file_block
    assert "_show_transcript_panel()" not in add_file_block


if __name__ == "__main__":
    tests = [
        test_no_broad_spelling_bar_or_wrong_label,
        test_popup_is_app_owned_overlay_not_toplevel,
        test_single_instance_cleanup_before_showing_new_overlay,
        test_lifecycle_closes_overlay,
        test_click_away_actions_and_hover_rows_remain,
        test_url_path_skip_rules_remain,
        test_undo_redo_and_panel_open_behaviour_remain,
    ]
    for test in tests:
        test()
    print("spellcheck owned overlay assertions passed")
