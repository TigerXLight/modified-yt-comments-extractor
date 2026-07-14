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
from access_keys_metadata import AccessEntryKind
from access_keys_dialog import (
    ACCESS_KEYS_BUTTON_TEXT,
    ACCESS_KEYS_WINDOW_TITLE,
    ALL_FAMILIES_LABEL,
    CREDENTIAL_ENTRY_MASK,
    MY_PROVIDERS_HEADING,
    STATUS_ICON_ASSETS,
    VIDEO_SOCIAL_CATEGORY_LABEL,
    AccessKeysDialogController,
    AccessKeysWindow,
    access_keys_detail_lines,
    build_default_access_keys_catalog,
    open_or_focus_access_keys_window,
    status_icon_key,
    user_status_text,
    _create_masked_credential_entry,
)
from access_keys_view_model import AccessKeysEntryView
from credential_store import InMemoryCredentialStore


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


class _FakeInnerEntry:
    def __init__(self) -> None:
        self.options: dict[str, object] = {}

    def configure(self, **kwargs: object) -> None:
        self.options.update(kwargs)

    def cget(self, key: str) -> object:
        return self.options.get(key, "")


class _FakeCredentialEntry:
    instances: list["_FakeCredentialEntry"] = []

    def __init__(self, value: str = "", **kwargs: object) -> None:
        self.value = value
        self.options: dict[str, object] = dict(kwargs)
        self._entry = _FakeInnerEntry()
        self.__class__.instances.append(self)

    def get(self) -> str:
        return self.value

    def delete(self, _start: object, _end: object) -> None:
        self.value = ""

    def configure(self, **kwargs: object) -> None:
        self.options.update(kwargs)

    def cget(self, key: str) -> object:
        return self.options.get(key, "")


def _assert_entry_masked(entry: _FakeCredentialEntry) -> None:
    assert entry.cget("show") == CREDENTIAL_ENTRY_MASK
    assert entry._entry.cget("show") == CREDENTIAL_ENTRY_MASK


class _FakeStatusLabel:
    def __init__(self) -> None:
        self.text = ""

    def configure(self, *, text: str) -> None:
        self.text = text


class _FakePanel:
    def __init__(self) -> None:
        self.visible = False

    def grid(self) -> None:
        self.visible = True

    def grid_remove(self) -> None:
        self.visible = False


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
        VIDEO_SOCIAL_CATEGORY_LABEL,
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

    social = controller.set_family(VIDEO_SOCIAL_CATEGORY_LABEL)
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
    assert set(details) == {"Status", "Use", "Model", "Data use"}
    assert "Subgroup" not in details
    assert "Implementation" not in details
    assert "Credential status" not in details

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
    assert "command=self._save_youtube_api_key_secure" in api_section
    assert "command=self._migrate_youtube_api_key" in api_section
    assert "command=self._clear_youtube_api_key" in api_section
    assert "_toggle_api_key_visibility" not in main_source
    assert "toggle_api_key_button" not in main_source
    assert "api_key_visible" not in main_source
    assert 'show=""' not in main_source
    assert "text=ACCESS_KEYS_BUTTON_TEXT" in api_section
    assert "command=self.open_access_keys_window" in api_section

    open_method = _function_source(
        main_source,
        "open_access_keys_window",
    )
    assert "open_or_focus_access_keys_window" in open_method
    assert "AccessKeysWindow" in open_method
    assert "build_runtime_credential_statuses" in open_method
    assert "SystemKeyringCredentialStore" in open_method
    assert "settings_manager=self.settings_manager" in open_method
    assert "youtube_configured=bool(" in open_method
    assert "credential_store=credential_store" in open_method
    assert "self.api_key_entry.get().strip()" in open_method
    assert "get_api_key" not in open_method
    assert "set_api_key" not in open_method
    assert "delete_api_key" not in open_method

    close_method = _function_source(
        main_source,
        "_on_access_keys_window_closed",
    )
    assert "self.access_keys_window = None" in close_method


def test_my_providers_subset_and_status_semantics() -> None:
    bundle = build_default_access_keys_catalog_bundle()
    subset = access_keys_dialog._catalog_subset(
        bundle.catalog,
        bundle.layouts,
        ("asr:elevenlabs_scribe",),
    )
    controller = AccessKeysDialogController(subset.catalog, subset.layouts)
    view = controller.view()

    assert view.visible_entry_count == 1
    assert view.sections[0].display_name == "ASR Providers"
    selected = controller.selected_entry(view)
    assert selected is not None
    assert selected.display_name == "ElevenLabs Scribe v2"
    assert "source:youtube" not in {
        entry.entry_id
        for section in view.sections
        for entry in section.entries
    }
    assert status_icon_key(selected) == "missing"
    assert user_status_text(selected) == "No key saved"

    saved = AccessKeysEntryView(
        entry_id="asr:elevenlabs_scribe",
        display_name="ElevenLabs Scribe v2",
        entry_kind=AccessEntryKind.ASR_PROVIDER,
        platform_family="asr",
        implementation_state="provider metadata only",
        access_mode="API_KEY",
        credential_status="CONFIGURED_UNTESTED",
        last_test_status="TEST_NOT_RUN",
    )
    assert status_icon_key(saved) == "saved"
    assert user_status_text(saved) == "Key saved — not yet validated"
    assert "incorrect" not in user_status_text(saved).casefold()

    verified = AccessKeysEntryView(
        entry_id="asr:elevenlabs_scribe",
        display_name="ElevenLabs Scribe v2",
        entry_kind=AccessEntryKind.ASR_PROVIDER,
        platform_family="asr",
        implementation_state="provider metadata only",
        access_mode="API_KEY",
        credential_status="CONFIGURED_TEST_PASSED",
        last_test_status="TEST_PASSED",
    )
    assert status_icon_key(verified) == "verified"
    assert user_status_text(verified) == "Verified"

    rejected = AccessKeysEntryView(
        entry_id="asr:elevenlabs_scribe",
        display_name="ElevenLabs Scribe v2",
        entry_kind=AccessEntryKind.ASR_PROVIDER,
        platform_family="asr",
        implementation_state="provider metadata only",
        access_mode="API_KEY",
        credential_status="CONFIGURED_TEST_FAILED",
        last_test_status="TEST_FAILED",
        access_limitations="Authentication rejected by provider.",
    )
    assert status_icon_key(rejected) == "warning"
    assert user_status_text(rejected) == "Key validation failed"

    transient = AccessKeysEntryView(
        entry_id="asr:elevenlabs_scribe",
        display_name="ElevenLabs Scribe v2",
        entry_kind=AccessEntryKind.ASR_PROVIDER,
        platform_family="asr",
        implementation_state="provider metadata only",
        access_mode="API_KEY",
        credential_status="STATUS_ERROR",
        last_test_status="TEST_FAILED",
        access_limitations="Provider outage or network timeout.",
    )
    assert status_icon_key(transient) == "warning"
    assert user_status_text(transient) == "Key could not be validated"


def test_add_and_remove_provider_metadata_only() -> None:
    events: list[tuple[str, ...]] = []
    window = AccessKeysWindow.__new__(AccessKeysWindow)
    bundle = build_default_access_keys_catalog_bundle()
    window._full_catalog = bundle.catalog
    window._base_catalog = bundle.catalog
    window._full_layouts = bundle.layouts
    window._added_entry_ids = ()
    window._selected_entry_id = ""
    window._on_added_entry_ids_change = lambda ids: events.append(ids)
    window._hide_add_provider_popup = lambda: None

    applied: list[int] = []
    window._apply_view = lambda view: applied.append(view.visible_entry_count)

    AccessKeysWindow._add_provider(
        window,
        "asr:elevenlabs_scribe",
        select=True,
    )
    assert window._added_entry_ids == ("asr:elevenlabs_scribe",)
    assert events == [("asr:elevenlabs_scribe",)]
    assert applied == [1]

    AccessKeysWindow._add_provider(
        window,
        "asr:elevenlabs_scribe",
        select=True,
    )
    assert window._added_entry_ids == ("asr:elevenlabs_scribe",)
    assert events == [("asr:elevenlabs_scribe",)]

    window._selected_entry_id = "asr:elevenlabs_scribe"
    AccessKeysWindow._remove_selected_provider(window)
    assert window._added_entry_ids == ()
    assert events[-1] == ()


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
    window._runtime_status_checked_entry_ids = set()
    window._credential_status_provider = None
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


def test_filter_changes_reset_scroll_to_top() -> None:
    events: list[tuple[str, object]] = []

    class _FakeCanvas:
        def yview_moveto(self, value: float) -> None:
            events.append(("scroll", value))

    class _FakePanel:
        _parent_canvas = _FakeCanvas()

    window = AccessKeysWindow.__new__(AccessKeysWindow)
    window.list_panel = _FakePanel()
    window._closed = False
    window._list_scroll_reset_after_id = "old-reset"
    window._apply_view = lambda view: events.append(("apply", view))
    window.after_cancel = lambda token: events.append(("cancel", token))

    def after_idle(callback: object) -> str:
        events.append(("after_idle", getattr(callback, "__name__", "")))
        return "new-reset"

    window.after_idle = after_idle

    AccessKeysWindow._apply_filtered_view(window, "filtered-view")
    assert events == [
        ("scroll", 0.0),
        ("apply", "filtered-view"),
        ("cancel", "old-reset"),
        ("after_idle", "_finish_list_scroll_reset"),
    ]
    assert window._list_scroll_reset_after_id == "new-reset"

    AccessKeysWindow._finish_list_scroll_reset(window)
    assert events[-1] == ("scroll", 0.0)
    assert window._list_scroll_reset_after_id is None

    # Missing internal canvas support is a safe no-op rather than a crash.
    window.list_panel = object()
    AccessKeysWindow._reset_list_scroll_to_top(window)


def test_cloud_asr_credential_entry_mask_is_effective_on_creation() -> None:
    original_entry_class = access_keys_dialog.ctk.CTkEntry
    _FakeCredentialEntry.instances = []
    access_keys_dialog.ctk.CTkEntry = _FakeCredentialEntry
    try:
        entry = _create_masked_credential_entry(
            "parent",
            placeholder_text="Enter credential to save",
        )
    finally:
        access_keys_dialog.ctk.CTkEntry = original_entry_class

    assert isinstance(entry, _FakeCredentialEntry)
    assert _FakeCredentialEntry.instances == [entry]
    _assert_entry_masked(entry)


def test_cloud_asr_credential_controls_are_scoped_and_masked() -> None:
    window = AccessKeysWindow.__new__(AccessKeysWindow)
    window._credential_store = InMemoryCredentialStore()
    window.credential_entry = _FakeCredentialEntry("old draft")
    window.credential_action_status_label = _FakeStatusLabel()
    window.credential_action_panel = _FakePanel()

    cloud_entry = AccessKeysEntryView(
        entry_id="asr:elevenlabs_scribe",
        display_name="ElevenLabs Scribe",
        entry_kind=AccessEntryKind.ASR_PROVIDER,
        platform_family="asr",
        implementation_state="provider metadata only",
        access_mode="API_KEY",
        credential_status="REQUIRED_MISSING",
    )
    AccessKeysWindow._render_credential_controls(window, cloud_entry)
    assert window._current_credential_id == "elevenlabs_scribe_api_key"
    assert window.credential_entry.get() == ""
    _assert_entry_masked(window.credential_entry)
    assert window.credential_action_panel.visible is True
    assert (
        "Key saved securely. The key has not yet been checked with the provider."
        in window.credential_action_status_label.text
    )
    assert "never displayed" in window.credential_action_status_label.text
    assert "provenance" not in window.credential_action_status_label.text.casefold()

    window.credential_entry.value = "new draft"

    youtube_entry = AccessKeysEntryView(
        entry_id="source:youtube",
        display_name="YouTube",
        entry_kind=AccessEntryKind.SOURCE_ADAPTER,
        platform_family="source",
        implementation_state="registered source adapter metadata",
        access_mode="API_KEY",
        credential_status="REQUIRED_MISSING",
    )
    AccessKeysWindow._render_credential_controls(window, youtube_entry)
    assert window._current_credential_id == ""
    assert window.credential_entry.get() == ""
    _assert_entry_masked(window.credential_entry)
    assert window.credential_action_panel.visible is False


def test_cloud_asr_save_and_clear_use_fake_store_without_retaining_value() -> None:
    secret = "ROW2C2-SECRET-MUST-NOT-APPEAR"
    store = InMemoryCredentialStore()
    refresh_events: list[str] = []

    window = AccessKeysWindow.__new__(AccessKeysWindow)
    window._credential_store = store
    window._current_credential_id = "elevenlabs_scribe_api_key"
    window.credential_entry = _FakeCredentialEntry(secret)
    window.credential_action_status_label = _FakeStatusLabel()
    window._refresh_runtime_statuses_after_credential_action = (
        lambda: refresh_events.append("refresh")
    )

    AccessKeysWindow._save_selected_credential(window)
    assert window.credential_entry.get() == ""
    _assert_entry_masked(window.credential_entry)
    assert "saved" in window.credential_action_status_label.text.casefold()
    assert refresh_events == ["refresh"]
    if store._test_only_stored_credential("elevenlabs_scribe_api_key") != secret:
        raise AssertionError("credential was not saved in the fake store")
    assert secret not in window.credential_action_status_label.text
    assert secret not in repr(window.__dict__)

    AccessKeysWindow._clear_selected_credential(window)
    assert store._test_only_stored_credential("elevenlabs_scribe_api_key") is None
    assert window.credential_entry.get() == ""
    _assert_entry_masked(window.credential_entry)
    assert "cleared" in window.credential_action_status_label.text.casefold()
    assert refresh_events == ["refresh", "refresh"]


def test_cloud_asr_save_failure_clears_draft_and_uses_safe_message() -> None:
    secret = "ROW2C2-SECRET-MUST-NOT-APPEAR"
    window = AccessKeysWindow.__new__(AccessKeysWindow)
    window._credential_store = InMemoryCredentialStore(fail_save=True)
    window._current_credential_id = "elevenlabs_scribe_api_key"
    window.credential_entry = _FakeCredentialEntry(secret)
    window.credential_action_status_label = _FakeStatusLabel()
    window._refresh_runtime_statuses_after_credential_action = lambda: None

    AccessKeysWindow._save_selected_credential(window)
    assert window.credential_entry.get() == ""
    _assert_entry_masked(window.credential_entry)
    assert "safe error" in window.credential_action_status_label.text
    assert secret not in window.credential_action_status_label.text

    window.credential_entry = _FakeCredentialEntry("   ")
    AccessKeysWindow._save_selected_credential(window)
    _assert_entry_masked(window.credential_entry)
    assert "empty input" in window.credential_action_status_label.text


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
    assert MY_PROVIDERS_HEADING in source
    assert VIDEO_SOCIAL_CATEGORY_LABEL in source
    assert "Local credential presence/provenance status" not in source
    assert "Cloud ASR secure credential" not in source
    assert "Subgroup" not in source
    assert "self.family_button = ctk.CTkButton(" in source
    assert "command=self._toggle_family_menu" in source
    assert "self.family_popup = ctk.CTkFrame(" in source
    assert "width=280" in source
    assert "self.family_popup.place(x=x, y=y)" in source
    assert "self.family_popup.place(x=x, y=y, width=width)" not in source
    assert "self.family_popup.place_forget()" in source
    assert "self.add_provider_popup = ctk.CTkFrame(" in source
    assert "self.add_provider_results = ctk.CTkScrollableFrame(" in source
    assert "ADD_PROVIDER_SEARCH_PLACEHOLDER" in source
    assert "_show_add_provider_popup" in source
    assert "_refresh_add_provider_results" in source
    assert "_add_provider(" in source
    assert "_remove_selected_provider" in source
    assert "compound=\"left\"" in source
    assert "status_icon_labels" not in source
    assert 'self.family_button.bind("<Return>"' in source
    assert 'self.family_button.bind("<space>"' in source
    assert 'self.family_button.bind("<Down>"' in source

    apply_view = inspect.getsource(AccessKeysWindow._apply_view)
    select_entry = inspect.getsource(AccessKeysWindow._select_entry)
    search_changed = inspect.getsource(
        AccessKeysWindow._on_search_changed
    )
    choose_family = inspect.getsource(
        AccessKeysWindow._choose_family
    )
    apply_filtered_view = inspect.getsource(
        AccessKeysWindow._apply_filtered_view
    )
    reset_scroll = inspect.getsource(
        AccessKeysWindow._reset_list_scroll_to_top
    )
    queue_scroll_reset = inspect.getsource(
        AccessKeysWindow._queue_list_scroll_reset
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
    assert search_changed.count("_apply_filtered_view") == 1
    assert "_apply_view" not in search_changed
    assert choose_family.count("_apply_filtered_view") == 1
    assert "_apply_view" not in choose_family

    # Family/search filters reset the scroll position before layout and once
    # after idle. This prevents a short family such as ASR Providers from
    # inheriting a lower scroll offset and appearing blank.
    assert apply_filtered_view.index("_reset_list_scroll_to_top") < (
        apply_filtered_view.index("_apply_view")
    )
    assert "_queue_list_scroll_reset" in apply_filtered_view
    assert "_parent_canvas" in reset_scroll
    assert "yview_moveto(0.0)" in reset_scroll
    assert "after_idle" in queue_scroll_reset
    assert "after_cancel" in queue_scroll_reset

    # Detail rows are created once and only their changed text is configured
    # during entry-to-entry selection.
    assert "_set_detail_rows_visible(True)" in render_details
    assert "detail_title_label.configure" in render_details
    assert 'cget("text") != value' in render_details
    assert "configure(text=value)" in render_details
    assert "destroy" not in render_details
    assert "fg_color" in configure_button

    # Platform rows retain visible hover feedback. Selection updates remain
    # selective, so hover highlighting does not require a full catalog rebuild.
    assert 'hover_color=COLORS["accent_hover"]' in source
    assert "hover=False" not in source
    assert "_clear_children" not in source

    assert source.count("ctk.CTkEntry(") == 3
    assert 'placeholder_text="Search My Providers"' in source
    assert "placeholder_text=ADD_PROVIDER_SEARCH_PLACEHOLDER" in source
    assert "CREDENTIAL_ENTRY_MASK" in source
    assert "show=CREDENTIAL_ENTRY_MASK" in source
    assert 'show=""' not in source
    assert 'placeholder_text="Enter key to save"' in source
    assert "clipboard" not in source
    for asset_name in STATUS_ICON_ASSETS.values():
        assert Path("assets", asset_name).exists()

    refresh_status = inspect.getsource(
        AccessKeysWindow._refresh_runtime_statuses_after_credential_action
    )
    assert "_apply_view" not in refresh_status
    assert "_build_widgets" not in refresh_status
    assert "_build_catalog_widgets" not in refresh_status

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
    test_my_providers_subset_and_status_semantics()
    test_add_and_remove_provider_metadata_only()
    test_single_window_lifecycle()
    test_fast_selection_path_updates_only_changed_controls()
    test_filter_changes_reset_scroll_to_top()
    test_cloud_asr_credential_entry_mask_is_effective_on_creation()
    test_cloud_asr_credential_controls_are_scoped_and_masked()
    test_cloud_asr_save_and_clear_use_fake_store_without_retaining_value()
    test_cloud_asr_save_failure_clears_draft_and_uses_safe_message()
    test_static_selector_and_no_flicker_design()


if __name__ == "__main__":
    run_self_test()
    print("Access & Keys dialog self-test passed.")
