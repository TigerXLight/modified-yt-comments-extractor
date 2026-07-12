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
    customtkinter_stub.set_appearance_mode = lambda *_args, **_kwargs: None
    customtkinter_stub.set_default_color_theme = lambda *_args, **_kwargs: None
    sys.modules["customtkinter"] = customtkinter_stub

import access_keys_dialog
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
from access_keys_metadata import (
    AccessEntryKind,
    AccessEntryMetadata,
    AccessKeysCatalog,
    AccessMode,
    CredentialStatus,
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


def _duplicate_catalog() -> AccessKeysCatalog:
    entry = AccessEntryMetadata(
        entry_id="duplicate",
        entry_kind=AccessEntryKind.SOURCE_ADAPTER,
        display_name="Duplicate",
        platform_family="Example family",
        access_mode=AccessMode.NO_CREDENTIALS_REQUIRED,
        credential_status=CredentialStatus.NOT_NEEDED,
    )
    return AccessKeysCatalog(entries=(entry, entry))


def test_catalog_and_controller() -> None:
    catalog = build_default_access_keys_catalog()
    assert catalog.entries
    assert any(entry.entry_kind is AccessEntryKind.ASR_PROVIDER for entry in catalog.entries)
    assert any(entry.entry_id == "source:youtube" for entry in catalog.entries)
    news_entry = next(
        entry for entry in catalog.entries if entry.entry_id == "source:news_website"
    )
    assert news_entry.access_mode is AccessMode.NO_CREDENTIALS_REQUIRED
    local_asr = next(
        entry
        for entry in catalog.entries
        if entry.entry_id == "asr:whisper_cpp_vulkan_large_v3_turbo"
    )
    assert local_asr.access_mode is AccessMode.LOCAL_ONLY
    assert all(not hasattr(entry, "api_key") for entry in catalog.entries)
    assert all(not hasattr(entry, "token") for entry in catalog.entries)

    controller = AccessKeysDialogController(catalog)
    assert controller.family_options()[0] == ALL_FAMILIES_LABEL
    full_view = controller.view()
    assert full_view.visible_entry_count == len(catalog.entries)

    search_view = controller.set_search("YouTube")
    assert [
        entry.entry_id
        for section in search_view.sections
        for entry in section.entries
    ] == ["source:youtube"]

    controller.set_search("")
    family = next(
        option
        for option in controller.family_options()
        if option != ALL_FAMILIES_LABEL
    )
    family_view = controller.set_family(family)
    assert family_view.visible_entry_count > 0
    assert all(section.section_id == family for section in family_view.sections)

    selected_id = family_view.sections[0].entries[0].entry_id
    selected_view = controller.select_entry(selected_id)
    assert selected_view.selected_entry_id == selected_id
    selected = controller.selected_entry()
    assert selected is not None
    assert selected.entry_id == selected_id
    detail_labels = dict(access_keys_detail_lines(selected))
    assert detail_labels["Access mode"]
    assert detail_labels["Credential status"]
    assert detail_labels["Test status"]
    assert detail_labels["Capabilities"]

    empty_view = controller.set_search("no such access entry")
    assert empty_view.visible_entry_count == 0
    assert empty_view.empty_message

    duplicate_view = AccessKeysDialogController(_duplicate_catalog()).view()
    assert duplicate_view.warnings == ("Duplicate access entry ID: duplicate",)


def _function_source(module_source: str, name: str) -> str:
    tree = ast.parse(module_source)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            source = ast.get_source_segment(module_source, node)
            assert source is not None
            return source
    raise AssertionError(f"Function not found: {name}")


def test_sidebar_button_preserves_api_key_entry() -> None:
    main_source = Path("main.py").read_text(encoding="utf-8")
    api_section = _function_source(main_source, "_create_api_section")
    assert 'placeholder_text="Enter API key"' in api_section
    assert 'show="*"' in api_section
    assert "command=self._toggle_api_key_visibility" in api_section
    assert "text=ACCESS_KEYS_BUTTON_TEXT" in api_section
    assert "command=self.open_access_keys_window" in api_section

    open_method = _function_source(main_source, "open_access_keys_window")
    assert "open_or_focus_access_keys_window" in open_method
    assert "AccessKeysWindow" in open_method
    assert "settings_manager" not in open_method
    assert "api_key_entry" not in open_method

    close_method = _function_source(main_source, "_on_access_keys_window_closed")
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


def test_static_gui_safety() -> None:
    assert ACCESS_KEYS_WINDOW_TITLE == "Access & Keys"
    assert issubclass(AccessKeysWindow, access_keys_dialog.ctk.CTkToplevel)

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

    lifecycle_source = inspect.getsource(open_or_focus_access_keys_window)
    assert "winfo_exists" in lifecycle_source
    assert "lift" in lifecycle_source
    assert "focus_force" in lifecycle_source


def run_self_test() -> None:
    test_catalog_and_controller()
    test_sidebar_button_preserves_api_key_entry()
    test_single_window_lifecycle()
    test_static_gui_safety()


if __name__ == "__main__":
    run_self_test()
    print("Access & Keys dialog self-test passed.")
