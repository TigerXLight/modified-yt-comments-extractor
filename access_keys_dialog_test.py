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
    credential_detail_status_text,
    open_or_focus_access_keys_window,
    status_icon_key,
    user_status_text,
    _create_masked_credential_entry,
)
from access_keys_view_model import AccessKeysEntryView
from credential_store import InMemoryCredentialStore
from provider_key_validation import (
    KEY_VALIDATION_COULD_NOT_COMPLETE,
    KEY_VALIDATION_VALIDATED,
    KEY_STATUS_SAVED_NOT_VALIDATED,
    ProviderKeyValidationRecord,
)
from provider_official_links import official_link_buttons_for_entry


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


class _FakeActionButton:
    def __init__(self) -> None:
        self.options: dict[str, object] = {}

    def configure(self, **kwargs: object) -> None:
        self.options.update(kwargs)


class _FakeWrapWidget:
    def __init__(self) -> None:
        self.options: dict[str, object] = {}

    def configure(self, **kwargs: object) -> None:
        self.options.update(kwargs)

    def winfo_width(self) -> int:
        return 540


class _FakePanel:
    def __init__(self) -> None:
        self.visible = False

    def grid(self) -> None:
        self.visible = True

    def grid_remove(self) -> None:
        self.visible = False


class _FakePopup:
    def __init__(self) -> None:
        self.placed = False
        self.grid_options: dict[str, object] = {}
        self.lift_count = 0

    def grid(self, **kwargs: object) -> None:
        self.placed = True
        self.grid_options = dict(kwargs)

    def grid_remove(self) -> None:
        self.placed = False

    def lift(self) -> None:
        self.lift_count += 1

    def __str__(self) -> str:
        return ".popup"


class _FakeFocusButton:
    def __init__(self) -> None:
        self.focus_count = 0

    def focus_set(self) -> None:
        self.focus_count += 1

    def winfo_rootx(self) -> int:
        return 420

    def winfo_rooty(self) -> int:
        return 120

    def winfo_height(self) -> int:
        return 24


class _FakeResultButton:
    created: list["_FakeResultButton"] = []
    destroyed_count = 0

    def __init__(self, *_args: object, **kwargs: object) -> None:
        self.kwargs = kwargs
        _FakeResultButton.created.append(self)

    def grid(self, **_kwargs: object) -> None:
        pass

    def destroy(self) -> None:
        _FakeResultButton.destroyed_count += 1


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


def test_sidebar_uses_keys_section_without_api_key_block() -> None:
    main_source = Path("main.py").read_text(encoding="utf-8")
    sidebar = _function_source(main_source, "_create_sidebar")
    keys_section = _function_source(main_source, "_create_access_keys_section")
    updates_section = _function_source(main_source, "_create_updates_section")
    assert "_create_api_section" not in sidebar
    assert sidebar.index("_create_updates_section(first=True)") < sidebar.index(
        "_create_access_keys_section()"
    )
    assert sidebar.index("_create_access_keys_section()") < sidebar.index(
        "_create_export_section()"
    )
    assert 'text="UPDATES"' in updates_section
    assert "KEYS" in keys_section
    assert "_toggle_api_key_visibility" not in main_source
    assert "toggle_api_key_button" not in main_source
    assert "api_key_visible" not in main_source
    assert 'show=""' not in main_source
    assert 'text="KEYS/ACCOUNTS"' in keys_section
    assert "command=self.open_access_keys_window" in keys_section

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
    assert "youtube_migration_action=self._migrate_youtube_api_key" in open_method
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
    assert user_status_text(selected) == "No key configured"

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
    assert user_status_text(saved) == KEY_STATUS_SAVED_NOT_VALIDATED
    assert "incorrect" not in user_status_text(saved).casefold()
    assert (
        credential_detail_status_text(saved)
        == "Key saved securely. The key has not yet been checked with the provider. Existing keys are never displayed."
    )

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
    assert user_status_text(verified) == "Key validated successfully"

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


def test_provider_row_text_is_compact_and_status_sentence_stays_in_details() -> None:
    entry = AccessKeysEntryView(
        entry_id="asr:elevenlabs_scribe",
        display_name="ElevenLabs Scribe v2",
        entry_kind=AccessEntryKind.ASR_PROVIDER,
        platform_family="asr",
        implementation_state="provider metadata only",
        access_mode="API_KEY",
        credential_status="CONFIGURED_UNTESTED",
        last_test_status="TEST_NOT_RUN",
    )

    row_text = AccessKeysWindow._button_text(entry)

    assert row_text == "ElevenLabs Scribe v2"
    assert "\n" not in row_text
    assert "\\n" not in row_text
    assert KEY_STATUS_SAVED_NOT_VALIDATED not in row_text
    assert KEY_STATUS_SAVED_NOT_VALIDATED == user_status_text(entry)


def test_provider_links_use_injected_browser_opener_only_on_explicit_click() -> None:
    opened: list[str] = []
    window = AccessKeysWindow.__new__(AccessKeysWindow)
    window._browser_opener = lambda url: opened.append(url)
    window._selected_entry_id = "asr:elevenlabs_scribe"

    AccessKeysWindow._open_provider_link(window, "Provider website")
    AccessKeysWindow._open_provider_link(window, "Developer documentation")
    AccessKeysWindow._open_provider_link(window, "Get API key")
    AccessKeysWindow._open_provider_link(window, "View current pricing")
    AccessKeysWindow._open_provider_link(window, "Service status")
    AccessKeysWindow._open_provider_link(window, "Untrusted")

    assert opened == [
        url
        for _label, url in official_link_buttons_for_entry("asr:elevenlabs_scribe")
    ]

    window._selected_entry_id = "planned:source:nebula"
    AccessKeysWindow._open_provider_link(window, "Developer documentation")
    assert opened == [
        url
        for _label, url in official_link_buttons_for_entry("asr:elevenlabs_scribe")
    ]


def test_provider_links_render_only_applicable_user_facing_labels() -> None:
    def entry(entry_id: str, name: str) -> AccessKeysEntryView:
        return AccessKeysEntryView(
            entry_id=entry_id,
            display_name=name,
            entry_kind=AccessEntryKind.ASR_PROVIDER,
            platform_family="asr",
            implementation_state="provider metadata only",
            access_mode="API_KEY",
            credential_status="REQUIRED_MISSING",
        )

    assemblyai_links = dict(
        access_keys_dialog._provider_links(
            entry("asr:assemblyai_universal_3_5_pro", "AssemblyAI")
        )
    )
    assert {
        "Provider website",
        "Developer documentation",
        "Get API key",
        "View current pricing",
    } <= set(assemblyai_links)
    assert all("_" not in label for label in assemblyai_links)

    whisper_links = dict(
        access_keys_dialog._provider_links(
            entry(
                "asr:whisper_cpp_vulkan_large_v3_turbo",
                "whisper.cpp",
            )
        )
    )
    assert "Official repository" in whisper_links
    assert "Developer documentation" in whisper_links
    assert "Downloads / releases" in whisper_links
    assert "Get API key" not in whisper_links
    assert "View current pricing" not in whisper_links

    youtube = entry("source:youtube", "YouTube")
    youtube_links = dict(access_keys_dialog._provider_links(youtube))
    assert "Provider website" in youtube_links
    assert "Developer documentation" in youtube_links
    assert "Manage API keys" in youtube_links

    nebula = entry("planned:source:nebula", "Nebula")
    nebula_links = dict(access_keys_dialog._provider_links(nebula))
    assert nebula_links == {"Provider website": "https://nebula.tv/"}


def test_details_wraplength_tracks_available_width() -> None:
    window = AccessKeysWindow.__new__(AccessKeysWindow)
    window.details_panel = _FakeWrapWidget()
    window.detail_placeholder = _FakeWrapWidget()
    window.detail_title_label = _FakeWrapWidget()
    window.credential_action_status_label = _FakeWrapWidget()
    status_value = _FakeWrapWidget()
    data_use_value = _FakeWrapWidget()
    window._detail_rows = {
        "Status": (_FakeWrapWidget(), status_value),
        "Data use": (_FakeWrapWidget(), data_use_value),
    }

    wrap = AccessKeysWindow._update_details_wraplength(window, 360)

    assert wrap == 312
    assert status_value.options["wraplength"] == 312
    assert data_use_value.options["wraplength"] == 312
    assert window.detail_title_label.options["wraplength"] == 312


class _FakeScrollChild:
    def __init__(self, children: list[object] | None = None) -> None:
        self.bindings: list[str] = []
        self._children = children or []
        self.master = None
        for child in self._children:
            try:
                child.master = self
            except Exception:
                pass

    def bind(self, event: str, _callback: object, add: object = None) -> None:
        self.bindings.append(event)

    def winfo_children(self) -> list[object]:
        return list(self._children)


class _FakeDetailsCanvas(_FakeScrollChild):
    def __init__(self) -> None:
        super().__init__()
        self.view = (0.0, 0.5)
        self.scrolls: list[tuple[int, str]] = []
        self.moves: list[float] = []

    def configure(self, **_kwargs: object) -> None:
        pass

    def yview(self) -> tuple[float, float]:
        return self.view

    def yview_scroll(self, units: int, what: str) -> None:
        self.scrolls.append((units, what))
        top = max(0.0, min(1.0, self.view[0] + units * 0.05))
        self.view = (top, min(1.0, top + 0.5))

    def yview_moveto(self, value: float) -> None:
        self.moves.append(value)
        top = max(0.0, min(1.0, float(value)))
        self.view = (top, min(1.0, top + 0.5))


def test_details_scroll_routes_child_wheel_events_and_clamps_edges() -> None:
    link = _FakeScrollChild()
    label = _FakeScrollChild([link])
    canvas = _FakeDetailsCanvas()
    scrollbar = _FakeWrapWidget()
    window = AccessKeysWindow.__new__(AccessKeysWindow)
    window.details_panel = _FakeScrollChild([label])
    window.details_shell = _FakeScrollChild([window.details_panel])
    window.details_canvas = canvas
    window._details_mousewheel_remainder = 0.0
    window._details_scroll_canvas = lambda: canvas
    window._details_scrollbar = lambda: scrollbar
    window.bindings = []
    window.bind = lambda event, _callback, add=None: window.bindings.append(event)
    window.winfo_pointerx = lambda: 0
    window.winfo_pointery = lambda: 0
    window.winfo_containing = lambda _x, _y: link

    AccessKeysWindow._configure_details_scroll_surface(window)

    assert "<MouseWheel>" in window.bindings
    assert "<MouseWheel>" not in label.bindings
    assert "<MouseWheel>" not in link.bindings

    event = type("Event", (), {"delta": -120, "num": None})()
    AccessKeysWindow._on_access_keys_mousewheel(window, event)
    assert canvas.scrolls[-1] == (3, "units")

    canvas.view = (0.0, 0.5)
    AccessKeysWindow._scroll_details_canvas_units(window, -3)
    assert canvas.scrolls[-1] == (3, "units")

    canvas.view = (0.5, 1.0)
    AccessKeysWindow._scroll_details_canvas_units(window, 3)
    assert canvas.scrolls[-1] == (3, "units")

    AccessKeysWindow._reset_details_scroll_to_top(window)
    assert 0.0 in canvas.moves


def test_add_provider_popup_closes_on_escape_outside_click_and_same_plus() -> None:
    events: list[tuple[str, object]] = []
    origin = _FakeFocusButton()
    other = _FakeFocusButton()
    popup = _FakePopup()
    search = _FakeFocusButton()
    window = AccessKeysWindow.__new__(AccessKeysWindow)
    window._add_provider_popup_visible = False
    window._active_add_group_id = ""
    window._section_add_buttons = {"asr_providers": origin, "social_media": other}
    window.add_provider_popup = popup
    window.add_provider_search_entry = search
    window._add_provider_origin_button = None
    window._add_provider_click_bind_id = None
    window._add_provider_escape_bind_id = None
    window._add_provider_search_var = type(
        "Var",
        (),
        {"set": lambda self, value: events.append(("search", value))},
    )()
    window._refresh_add_provider_results = lambda: events.append(("refresh", ""))
    window._hide_family_menu = lambda: events.append(("hide_family", ""))
    window.update_idletasks = lambda: None
    window.bind = lambda event, callback, add=None: f"bind:{event}:{len(events)}"
    window.unbind = lambda event, token: events.append(("unbind", (event, token)))
    window._section_header_frames = {
        "asr_providers": type(
            "Header",
            (),
            {"grid_info": lambda self: {"row": 2}},
        )()
    }

    AccessKeysWindow._show_add_provider_popup(window, "asr_providers")
    assert popup.placed is True
    assert popup.grid_options["column"] == 1
    assert popup.grid_options["row"] == 2
    assert window._add_provider_popup_visible is True
    assert search.focus_count == 1

    AccessKeysWindow._show_add_provider_popup(window, "asr_providers")
    assert popup.placed is False
    assert window._add_provider_popup_visible is False
    assert origin.focus_count == 1
    assert any(event[0] == "unbind" for event in events)

    AccessKeysWindow._show_add_provider_popup(window, "asr_providers")
    inside_event = type("Event", (), {"widget": ".popup.search"})()
    AccessKeysWindow._on_add_provider_global_click(window, inside_event)
    assert window._add_provider_popup_visible is True

    outside_event = type("Event", (), {"widget": ".main.search"})()
    AccessKeysWindow._on_add_provider_global_click(window, outside_event)
    assert window._add_provider_popup_visible is False

    AccessKeysWindow._show_add_provider_popup(window, "asr_providers")
    AccessKeysWindow._hide_add_provider_popup_event(window, object())
    assert window._add_provider_popup_visible is False


def test_add_provider_search_uses_cached_metadata_and_skips_unchanged_render() -> None:
    original_button = access_keys_dialog.ctk.CTkButton
    bundle = build_default_access_keys_catalog_bundle()
    window = AccessKeysWindow.__new__(AccessKeysWindow)
    window._full_catalog = bundle.catalog
    window._full_layouts = tuple(bundle.layouts)
    window._added_entry_ids = ()
    window._active_add_group_id = "asr_providers"
    window._add_provider_buttons = {}
    window.add_provider_results = object()
    window._add_provider_search_var = type(
        "Var",
        (),
        {"get": lambda self: "eleven"},
    )()
    window._add_provider_search_index = (
        AccessKeysWindow._build_add_provider_search_index(window)
    )
    window._last_add_provider_render_key = ("", "", ())

    _FakeResultButton.created = []
    _FakeResultButton.destroyed_count = 0
    access_keys_dialog.ctk.CTkButton = _FakeResultButton
    try:
        AccessKeysWindow._refresh_add_provider_results(window)
        first_create_count = len(_FakeResultButton.created)
        AccessKeysWindow._refresh_add_provider_results(window)
    finally:
        access_keys_dialog.ctk.CTkButton = original_button

    assert first_create_count >= 1
    assert len(_FakeResultButton.created) == first_create_count
    assert _FakeResultButton.destroyed_count == 0
    assert "asr:elevenlabs_scribe" in window._add_provider_search_index
    assert "elevenlabs" in window._add_provider_search_index["asr:elevenlabs_scribe"]


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
    window.credential_validate_button = _FakeActionButton()
    window.credential_action_panel = _FakePanel()
    window._validate_provider_key = None
    window._validation_busy_provider_id = ""

    cloud_entry = AccessKeysEntryView(
        entry_id="asr:elevenlabs_scribe",
        display_name="ElevenLabs Scribe",
        entry_kind=AccessEntryKind.ASR_PROVIDER,
        platform_family="asr",
        implementation_state="provider metadata only",
        access_mode="API_KEY",
        credential_status="CONFIGURED_UNTESTED",
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
    window._current_credential_entry_id = "asr:elevenlabs_scribe"
    window._validation_records = {}
    window._base_catalog = build_default_access_keys_catalog()
    window._full_catalog = window._base_catalog
    window._on_validation_records_change = lambda _data: None
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


def test_validate_key_blocks_missing_key_before_dispatch() -> None:
    dispatch_calls: list[str] = []
    missing = AccessKeysEntryView(
        entry_id="asr:elevenlabs_scribe",
        display_name="ElevenLabs Scribe",
        entry_kind=AccessEntryKind.ASR_PROVIDER,
        platform_family="asr",
        implementation_state="provider metadata only",
        access_mode="API_KEY",
        credential_status="REQUIRED_MISSING",
    )
    window = AccessKeysWindow.__new__(AccessKeysWindow)
    window._current_validation_provider_id = "elevenlabs_scribe"
    window._current_credential_entry_id = "asr:elevenlabs_scribe"
    window._validation_busy_provider_id = ""
    window._validate_provider_key = lambda provider_id: dispatch_calls.append(provider_id)
    window._entry_views = {"asr:elevenlabs_scribe": missing}
    window.credential_action_status_label = _FakeStatusLabel()

    AccessKeysWindow._validate_selected_credential(window)

    assert dispatch_calls == []
    assert window.credential_action_status_label.text == "No key configured"


def test_validate_key_dispatches_once_and_records_safe_success() -> None:
    original_thread = access_keys_dialog.threading.Thread
    records: list[dict[str, dict[str, str]]] = []

    class ImmediateThread:
        created: list[object] = []

        def __init__(self, *, target: object, daemon: bool) -> None:
            self.target = target
            self.daemon = daemon
            self.__class__.created.append(self)

        def start(self) -> None:
            self.target()

    saved = AccessKeysEntryView(
        entry_id="asr:elevenlabs_scribe",
        display_name="ElevenLabs Scribe",
        entry_kind=AccessEntryKind.ASR_PROVIDER,
        platform_family="asr",
        implementation_state="provider metadata only",
        access_mode="API_KEY",
        credential_status="CONFIGURED_UNTESTED",
    )
    window = AccessKeysWindow.__new__(AccessKeysWindow)
    window._closed = False
    window._current_validation_provider_id = "elevenlabs_scribe"
    window._current_credential_entry_id = "asr:elevenlabs_scribe"
    window._validation_busy_provider_id = ""
    window._entry_views = {"asr:elevenlabs_scribe": saved}
    window._validation_records = {}
    window._base_catalog = build_default_access_keys_catalog()
    window._full_catalog = window._base_catalog
    window._on_validation_records_change = lambda data: records.append(data)
    window._refresh_runtime_statuses_after_credential_action = lambda: None
    window._validate_provider_key = lambda provider_id: ProviderKeyValidationRecord(
        provider_id=provider_id,
        state=KEY_VALIDATION_VALIDATED,
        safe_diagnostic="key_validation_succeeded",
    )
    window.after = lambda _delay, callback: callback()
    window.credential_validate_button = _FakeActionButton()
    window.credential_action_status_label = _FakeStatusLabel()

    access_keys_dialog.threading.Thread = ImmediateThread
    try:
        AccessKeysWindow._validate_selected_credential(window)
    finally:
        access_keys_dialog.threading.Thread = original_thread

    assert len(ImmediateThread.created) == 1
    assert window.credential_action_status_label.text == "Key validated successfully"
    assert records[-1]["elevenlabs_scribe"]["state"] == KEY_VALIDATION_VALIDATED
    assert window.credential_validate_button.options["state"] == "normal"


def test_validate_key_safe_failure_becomes_could_not_validate() -> None:
    window = AccessKeysWindow.__new__(AccessKeysWindow)
    record = AccessKeysWindow._record_from_validation_exception(
        "elevenlabs_scribe",
        RuntimeError("network timeout"),
    )

    assert record.provider_id == "elevenlabs_scribe"
    assert record.state == KEY_VALIDATION_COULD_NOT_COMPLETE


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
    assert "import tkinter as tk" in source
    assert "self.details_canvas = tk.Canvas(" in source
    assert "self.details_panel = ctk.CTkFrame(" in source
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
    assert "self.list_panel," in source
    assert "self.add_provider_popup.grid(" in source
    assert "column=1" in source
    assert "self.add_provider_results = ctk.CTkScrollableFrame(" in source
    assert "ADD_PROVIDER_SEARCH_PLACEHOLDER" in source
    assert "_show_add_provider_popup" in source
    assert "_refresh_add_provider_results" in source
    assert "_build_add_provider_search_index" in source
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
        "Test connection",
    ):
        assert forbidden_action not in source
    assert "Migrate legacy YouTube key" in source

    lifecycle_source = inspect.getsource(
        open_or_focus_access_keys_window
    )
    assert "winfo_exists" in lifecycle_source
    assert "lift" in lifecycle_source
    assert "focus_force" in lifecycle_source


def run_self_test() -> None:
    test_catalog_controller_and_details()
    test_sidebar_uses_keys_section_without_api_key_block()
    test_my_providers_subset_and_status_semantics()
    test_add_and_remove_provider_metadata_only()
    test_provider_row_text_is_compact_and_status_sentence_stays_in_details()
    test_provider_links_use_injected_browser_opener_only_on_explicit_click()
    test_provider_links_render_only_applicable_user_facing_labels()
    test_details_wraplength_tracks_available_width()
    test_details_scroll_routes_child_wheel_events_and_clamps_edges()
    test_add_provider_popup_closes_on_escape_outside_click_and_same_plus()
    test_add_provider_search_uses_cached_metadata_and_skips_unchanged_render()
    test_single_window_lifecycle()
    test_fast_selection_path_updates_only_changed_controls()
    test_filter_changes_reset_scroll_to_top()
    test_cloud_asr_credential_entry_mask_is_effective_on_creation()
    test_cloud_asr_credential_controls_are_scoped_and_masked()
    test_cloud_asr_save_and_clear_use_fake_store_without_retaining_value()
    test_validate_key_blocks_missing_key_before_dispatch()
    test_validate_key_dispatches_once_and_records_safe_success()
    test_validate_key_safe_failure_becomes_could_not_validate()
    test_cloud_asr_save_failure_clears_draft_and_uses_safe_message()
    test_static_selector_and_no_flicker_design()


if __name__ == "__main__":
    run_self_test()
    print("Access & Keys dialog self-test passed.")
