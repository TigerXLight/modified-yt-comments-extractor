from __future__ import annotations

import ast
import inspect
import sys
import types
from pathlib import Path

try:
    import customtkinter  # noqa: F401
except ModuleNotFoundError:
    customtkinter_stub = types.ModuleType("customtkinter")

    class _ImportOnlyCTk:
        pass

    customtkinter_stub.CTk = _ImportOnlyCTk
    customtkinter_stub.CTkToplevel = _ImportOnlyCTk
    customtkinter_stub.CTkFrame = _ImportOnlyCTk
    customtkinter_stub.CTkLabel = _ImportOnlyCTk
    customtkinter_stub.CTkButton = _ImportOnlyCTk
    customtkinter_stub.CTkEntry = _ImportOnlyCTk
    customtkinter_stub.CTkScrollableFrame = _ImportOnlyCTk
    customtkinter_stub.CTkFont = _ImportOnlyCTk
    customtkinter_stub.StringVar = _ImportOnlyCTk
    customtkinter_stub.set_appearance_mode = lambda *_args, **_kwargs: None
    customtkinter_stub.set_default_color_theme = (
        lambda *_args, **_kwargs: None
    )
    sys.modules["customtkinter"] = customtkinter_stub

import access_keys_dialog
from access_keys_catalog import build_default_access_keys_catalog_bundle
from access_keys_dialog import (
    ACCESS_KEYS_BUTTON_TEXT,
    ACCESS_KEYS_WINDOW_TITLE,
    ALL_FAMILIES_LABEL,
    AccessKeysDialogController,
    AccessKeysWindow,
    access_keys_detail_lines,
    build_default_access_keys_catalog,
    open_or_focus_access_keys_window,
)


class _FakeAccessKeysWindow:
    instances: list["_FakeAccessKeysWindow"] = []

    def __init__(self, *, on_close: object) -> None:
        self.on_close = on_close
        self.exists = True
        self.lift_count = 0
        self.focus_count = 0
        self.__class__.instances.append(self)

    def winfo_exists(self) -> bool:
        return self.exists

    def lift(self) -> None:
        self.lift_count += 1

    def focus_force(self) -> None:
        self.focus_count += 1

    def close(self) -> None:
        self.exists = False
        self.on_close()


def _function_source(module_source: str, name: str) -> str:
    tree = ast.parse(module_source)
    for node in ast.walk(tree):
        if (
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name == name
        ):
            source = ast.get_source_segment(module_source, node)
            assert source is not None
            return source
    raise AssertionError(f"Function not found: {name}")


def test_catalog_controller_and_details() -> None:
    bundle = build_default_access_keys_catalog_bundle()
    assert build_default_access_keys_catalog() == bundle.catalog

    controller = AccessKeysDialogController(
        bundle.catalog,
        bundle.layouts,
    )
    assert controller.family_options() == (
        "All families",
        "ASR Providers",
        "Social Media",
        "News Websites",
        "Professional, Jobs, Experts & Portfolios",
        "Workplace, Chat & Collaboration",
        "Archive Services",
        "Browser-Assisted Capture",
    )

    full_view = controller.view()
    assert full_view.visible_entry_count == len(bundle.catalog.entries)
    assert full_view.selected_entry_id
    first_id = full_view.selected_entry_id

    social = controller.set_family("Social Media")
    assert social.visible_entry_count > 40
    assert all(
        section.section_id == "social_media"
        for section in social.sections
    )
    assert social.selected_entry_id
    assert social.selected_entry_id != first_id or first_id.startswith(
        "source:"
    )

    flickr_search = controller.set_search("Flickr")
    assert flickr_search.visible_entry_count == 1
    assert flickr_search.selected_entry_id == "planned:source:flickr"
    selected = controller.selected_entry(flickr_search)
    assert selected is not None
    assert selected.display_name == "Flickr"
    assert selected.planned_only is True

    details = dict(access_keys_detail_lines(selected))
    assert details["Section"] == "Social Media"
    assert details["Subgroup"] == "Pure Photography & Creator Hubs"
    assert details["Implementation"] == "planned metadata only"
    assert details["Planned capabilities"] != "none"
    assert details["Enabled capabilities"] == "none"

    youtube_search = controller.set_search("YouTube")
    assert youtube_search.visible_entry_count >= 1
    assert youtube_search.selected_entry_id in {
        "source:youtube",
        "planned:source:youtube_live",
    }

    all_again = controller.set_family(ALL_FAMILIES_LABEL)
    controller.set_search("")
    all_again = controller.view()
    assert all_again.visible_entry_count == len(bundle.catalog.entries)

    no_match = controller.set_search("no such access entry")
    assert no_match.visible_entry_count == 0
    assert no_match.empty_message
    assert controller.selected_entry(no_match) is None


def test_sidebar_button_preserves_api_key_entry() -> None:
    main_source = Path("main.py").read_text(encoding="utf-8")
    api_section = _function_source(main_source, "_create_api_section")
    assert 'placeholder_text="Enter API key"' in api_section
    assert 'show="*"' in api_section
    assert "command=self._toggle_api_key_visibility" in api_section
    assert "text=ACCESS_KEYS_BUTTON_TEXT" in api_section
    assert "command=self.open_access_keys_window" in api_section

    open_method = _function_source(
        main_source,
        "open_access_keys_window",
    )
    assert "open_or_focus_access_keys_window" in open_method
    assert "AccessKeysWindow" in open_method
    assert "settings_manager" not in open_method
    assert "api_key_entry" not in open_method

    close_method = _function_source(
        main_source,
        "_on_access_keys_window_closed",
    )
    assert "self.access_keys_window = None" in close_method


def test_single_window_lifecycle() -> None:
    _FakeAccessKeysWindow.instances.clear()
    holder: dict[str, object] = {"window": None}

    def on_close() -> None:
        holder["window"] = None

    def factory() -> _FakeAccessKeysWindow:
        return _FakeAccessKeysWindow(on_close=on_close)

    first = open_or_focus_access_keys_window(None, factory)
    holder["window"] = first
    second = open_or_focus_access_keys_window(first, factory)
    assert first is second
    assert len(_FakeAccessKeysWindow.instances) == 1
    assert first.lift_count == 2
    assert first.focus_count == 2

    first.close()
    assert holder["window"] is None

    replacement = open_or_focus_access_keys_window(None, factory)
    assert replacement is not first
    assert len(_FakeAccessKeysWindow.instances) == 2



def test_fast_selection_path_updates_only_changed_controls() -> None:
    bundle = build_default_access_keys_catalog_bundle()
    controller = AccessKeysDialogController(
        bundle.catalog,
        bundle.layouts,
    )
    view = controller.view()
    entry_ids = [
        entry.entry_id
        for section in view.sections
        for entry in section.entries
    ]
    assert len(entry_ids) >= 2
    previous_id, selected_id = entry_ids[:2]

    window = AccessKeysWindow.__new__(AccessKeysWindow)
    window.controller = controller
    window.controller.selected_entry_id = previous_id
    window._visible_entry_ids = set(entry_ids)
    window._selected_entry_id = previous_id
    window._entry_buttons = {
        entry_id: object()
        for entry_id in entry_ids
    }
    window._entry_views = {
        entry.entry_id: entry
        for section in view.sections
        for entry in section.entries
    }

    button_updates: list[tuple[str, bool]] = []
    detail_updates: list[str] = []
    window._configure_entry_button = (
        lambda entry_id, *, selected: button_updates.append(
            (entry_id, selected)
        )
    )
    window._render_details = (
        lambda entry: detail_updates.append(
            "" if entry is None else entry.entry_id
        )
    )

    AccessKeysWindow._select_entry(window, selected_id)
    assert window.controller.selected_entry_id == selected_id
    assert window._selected_entry_id == selected_id
    assert button_updates == [
        (previous_id, False),
        (selected_id, True),
    ]
    assert detail_updates == [selected_id]

    # Re-selecting the active row is a no-op rather than a full rerender.
    AccessKeysWindow._select_entry(window, selected_id)
    assert button_updates == [
        (previous_id, False),
        (selected_id, True),
    ]
    assert detail_updates == [selected_id]


def test_static_selector_and_no_flicker_design() -> None:
    assert ACCESS_KEYS_WINDOW_TITLE == "Access & Keys"
    assert ACCESS_KEYS_BUTTON_TEXT == "KEYS"
    assert issubclass(
        AccessKeysWindow,
        access_keys_dialog.ctk.CTkToplevel,
    )

    source_path = Path(access_keys_dialog.__file__)
    source = source_path.read_text(encoding="utf-8")
    tree = ast.parse(source)

    imported_roots = {
        alias.name.split(".", 1)[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    imported_roots.update(
        node.module.split(".", 1)[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    )
    assert imported_roots.isdisjoint(
        {
            "requests",
            "urllib",
            "httpx",
            "aiohttp",
            "selenium",
            "playwright",
            "subprocess",
            "webbrowser",
            "keyring",
        }
    )

    # The entire selector remains one button. Its dropdown is a reusable
    # CustomTkinter overlay instead of native tk.Menu, avoiding the additional
    # native-menu flash seen in the screen recording.
    assert "ctk.CTkOptionMenu(" not in source
    assert "tk.Menu(" not in source
    assert "import tkinter as tk" not in source
    assert "self.family_button = ctk.CTkButton(" in source
    assert "command=self._toggle_family_menu" in source
    assert "self.family_popup = ctk.CTkFrame(" in source
    assert "width=280" in source
    assert "self.family_popup.place(x=x, y=y)" in source
    assert "self.family_popup.place(x=x, y=y, width=width)" not in source
    assert "self.family_popup.place_forget()" in source
    assert 'self.family_button.bind("<Return>"' in source
    assert 'self.family_button.bind("<space>"' in source
    assert 'self.family_button.bind("<Down>"' in source

    apply_view = inspect.getsource(AccessKeysWindow._apply_view)
    select_entry = inspect.getsource(AccessKeysWindow._select_entry)
    search_changed = inspect.getsource(
        AccessKeysWindow._on_search_changed
    )
    render_details = inspect.getsource(
        AccessKeysWindow._render_details
    )
    configure_button = inspect.getsource(
        AccessKeysWindow._configure_entry_button
    )

    # Entry selection has a fast path: two button colour updates and one
    # detail refresh, with no full view rebuild or list re-layout.
    assert "_apply_view" not in select_entry
    assert "controller.select_entry" not in select_entry
    assert select_entry.count("_configure_entry_button") == 2
    assert select_entry.count("_render_details") == 1
    assert ".grid(" not in select_entry
    assert ".grid_remove(" not in select_entry
    assert "destroy" not in select_entry

    # Search/family changes place the new layout before hiding stale widgets,
    # so there is no deliberate empty intermediate pass.
    assert "_hide_list_widgets" not in source
    assert "visible_entries.add" in apply_view
    assert "if entry_id not in visible_entries" in apply_view
    assert apply_view.index("visible_entries.add") < apply_view.index(
        "if entry_id not in visible_entries"
    )
    assert "destroy" not in apply_view
    assert "loading" not in apply_view.casefold()
    assert ".after(" not in apply_view
    assert ".update(" not in apply_view
    assert search_changed.count("_apply_view") == 1

    # Detail rows are created once and only their changed text is configured
    # during entry-to-entry selection.
    assert "_set_detail_rows_visible(True)" in render_details
    assert 'cget("text") != value' in render_details
    assert "configure(text=value)" in render_details
    assert "destroy" not in render_details
    assert "fg_color" in configure_button

    # Platform rows retain visible hover feedback. Selection updates remain
    # selective, so hover highlighting does not require a full catalog rebuild.
    assert 'hover_color=COLORS["accent_hover"]' in source
    assert "hover=False" not in source
    assert "_clear_children" not in source

    assert source.count("ctk.CTkEntry(") == 1
    assert 'placeholder_text="Search access metadata"' in source

    for forbidden_action in (
        "Reveal",
        "Copy key",
        "Save key",
        "Clear key",
        "Migrate",
        "Test connection",
    ):
        assert forbidden_action not in source

    lifecycle_source = inspect.getsource(
        open_or_focus_access_keys_window
    )
    assert "winfo_exists" in lifecycle_source
    assert "lift" in lifecycle_source
    assert "focus_force" in lifecycle_source


def run_self_test() -> None:
    test_catalog_controller_and_details()
    test_sidebar_button_preserves_api_key_entry()
    test_single_window_lifecycle()
    test_fast_selection_path_updates_only_changed_controls()
    test_static_selector_and_no_flicker_design()


if __name__ == "__main__":
    run_self_test()
    print("Access & Keys dialog self-test passed.")
