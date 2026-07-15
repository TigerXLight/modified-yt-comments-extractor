from __future__ import annotations

import os
import sys
import threading
from typing import Callable, Mapping, Optional, Sequence

import customtkinter as ctk
from PIL import Image, ImageTk

from access_keys_catalog import (
    AccessKeysCatalogBundle,
    AccessKeysEntryLayout,
    build_default_access_keys_catalog,
    build_default_access_keys_catalog_bundle,
)
from access_keys_metadata import AccessKeysCatalog
from credential_runtime_status import (
    CredentialRuntimeStatus,
    apply_runtime_credential_statuses,
    cloud_asr_credential_id_for_entry_id,
)
from credential_store import (
    CredentialStore,
    CredentialStoreStatus,
)
from access_keys_view_model import (
    AccessKeysEntryView,
    AccessKeysManagerView,
    build_access_keys_manager_view,
)
from core.constants import COLORS
from provider_key_validation import (
    KEY_VALIDATION_COULD_NOT_COMPLETE,
    KEY_VALIDATION_FAILED,
    KEY_VALIDATION_NOT_CONFIGURED,
    KEY_VALIDATION_NOT_YET_VALIDATED,
    KEY_VALIDATION_VALIDATED,
    KEY_STATUS_NO_KEY_CONFIGURED,
    KEY_STATUS_NO_KEY_NEEDED,
    KEY_STATUS_SAVED_NOT_VALIDATED,
    KEY_STATUS_VALIDATED,
    ProviderKeyValidationRecord,
    access_entry_id_for_provider_id,
    apply_provider_key_validation_records,
    current_utc_timestamp,
    normalize_provider_id,
    normalize_validation_records,
    provider_id_for_access_entry_id,
    validation_icon_key_for_state,
    validation_record_for_cleared_key,
    validation_record_for_saved_key,
    validation_records_to_settings_dict,
    validation_status_text_for_state,
)


ACCESS_KEYS_WINDOW_TITLE = "Access & Keys"
ACCESS_KEYS_BUTTON_TEXT = "KEYS"
ALL_FAMILIES_LABEL = "All families"
CREDENTIAL_ENTRY_MASK = "*"
MY_PROVIDERS_HEADING = "My Providers"
ADD_PROVIDER_SEARCH_PLACEHOLDER = "Search providers to add"
VIDEO_SOCIAL_CATEGORY_LABEL = "Video & Social Platforms"
STATUS_ICON_SIZE = (16, 16)
STATUS_ICON_ASSETS = {
    "missing": "status_x.png",
    "saved": "status_dash.png",
    "verified": "status_check.png",
    "warning": "status_warning.png",
}
DEFAULT_ACCESS_KEYS_GROUPS = (
    ("asr_providers", "ASR Providers"),
    ("social_media", VIDEO_SOCIAL_CATEGORY_LABEL),
)
ELEVENLABS_LINKS = {
    "Provider website": "https://elevenlabs.io/",
    "Get API key": "https://elevenlabs.io/app/settings/api-keys",
    "View current pricing": "https://elevenlabs.io/pricing",
}

_DETAIL_LABELS = (
    "Status",
    "Use",
    "Model",
    "Data use",
)


def _set_entry_masked(entry: object) -> None:
    configure = getattr(entry, "configure", None)
    if callable(configure):
        configure(show=CREDENTIAL_ENTRY_MASK)

    # CustomTkinter wraps a tkinter Entry internally. Configure it directly
    # too so masking is effective from widget creation onward on all runtimes.
    internal_entry = getattr(entry, "_entry", None)
    internal_configure = getattr(internal_entry, "configure", None)
    if callable(internal_configure):
        internal_configure(show=CREDENTIAL_ENTRY_MASK)


def _create_masked_credential_entry(parent: object, **kwargs: object) -> object:
    entry = ctk.CTkEntry(parent, show=CREDENTIAL_ENTRY_MASK, **kwargs)
    _set_entry_masked(entry)
    return entry


class AccessKeysDialogController:
    def __init__(
        self,
        catalog: AccessKeysCatalog,
        layouts: Sequence[AccessKeysEntryLayout] = (),
    ) -> None:
        self.catalog = catalog
        self.layouts = tuple(layouts)
        self.search_query = ""
        self.platform_family = ""
        self.selected_entry_id = ""

    def _section_options(self) -> tuple[tuple[str, str, int], ...]:
        by_id: dict[str, tuple[str, str, int]] = {}
        for position, layout in enumerate(self.layouts):
            by_id.setdefault(
                layout.section_id,
                (
                    layout.section_id,
                    layout.section_label or layout.section_id,
                    layout.section_order,
                ),
            )
        if not by_id:
            for position, entry in enumerate(self.catalog.entries):
                family = (entry.platform_family or "other").strip() or "other"
                by_id.setdefault(family, (family, family, position))
        return tuple(
            sorted(
                by_id.values(),
                key=lambda item: (item[2], item[1].casefold()),
            )
        )

    def family_options(self) -> tuple[str, ...]:
        return (
            ALL_FAMILIES_LABEL,
            *(label for _section_id, label, _order in self._section_options()),
        )

    def _section_id_for_label(self, value: str) -> str:
        if value == ALL_FAMILIES_LABEL:
            return ""
        for section_id, label, _order in self._section_options():
            if value.casefold() in {section_id.casefold(), label.casefold()}:
                return section_id
        return value

    def set_search(self, value: str) -> AccessKeysManagerView:
        self.search_query = value
        return self.view()

    def set_family(self, value: str) -> AccessKeysManagerView:
        self.platform_family = self._section_id_for_label(value)
        return self.view()

    def select_entry(self, entry_id: str) -> AccessKeysManagerView:
        self.selected_entry_id = entry_id
        return self.view()

    def view(self) -> AccessKeysManagerView:
        view = build_access_keys_manager_view(
            self.catalog,
            search_query=self.search_query,
            platform_family=self.platform_family,
            selected_entry_id=self.selected_entry_id,
            layouts=self.layouts,
        )
        if view.visible_entry_count and not view.selected_entry_id:
            first_entry_id = view.sections[0].entries[0].entry_id
            self.selected_entry_id = first_entry_id
            view = build_access_keys_manager_view(
                self.catalog,
                search_query=self.search_query,
                platform_family=self.platform_family,
                selected_entry_id=first_entry_id,
                layouts=self.layouts,
            )
        else:
            self.selected_entry_id = view.selected_entry_id
        return view

    def selected_entry(
        self,
        view: Optional[AccessKeysManagerView] = None,
    ) -> Optional[AccessKeysEntryView]:
        current_view = view or self.view()
        for section in current_view.sections:
            for entry in section.entries:
                if entry.selected:
                    return entry
        return None


def access_keys_detail_lines(
    entry: AccessKeysEntryView,
) -> tuple[tuple[str, str], ...]:
    return (
        ("Status", user_status_text(entry)),
        ("Use", provider_use_summary(entry)),
        ("Model", provider_model_label(entry)),
        ("Data use", provider_data_use_note(entry)),
    )


def _normalised_entry_ids(values: Sequence[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        entry_id = " ".join(str(value or "").split())
        if not entry_id or entry_id in seen:
            continue
        seen.add(entry_id)
        result.append(entry_id)
    return tuple(result)


def _catalog_entry_ids(catalog: AccessKeysCatalog) -> set[str]:
    return {entry.entry_id for entry in catalog.entries}


def _entry_by_id(catalog: AccessKeysCatalog) -> dict[str, object]:
    return {entry.entry_id: entry for entry in catalog.entries}


def _layout_by_id(layouts: Sequence[AccessKeysEntryLayout]) -> dict[str, AccessKeysEntryLayout]:
    return {layout.entry_id: layout for layout in layouts}


def _catalog_subset(
    catalog: AccessKeysCatalog,
    layouts: Sequence[AccessKeysEntryLayout],
    entry_ids: Sequence[str],
) -> AccessKeysCatalogBundle:
    wanted = set(_normalised_entry_ids(entry_ids))
    entries = tuple(entry for entry in catalog.entries if entry.entry_id in wanted)
    layout_lookup = _layout_by_id(layouts)
    subset_layouts = tuple(
        layout_lookup[entry.entry_id]
        for entry in entries
        if entry.entry_id in layout_lookup
    )
    return AccessKeysCatalogBundle(
        catalog=AccessKeysCatalog(entries=entries, test_results=catalog.test_results),
        layouts=subset_layouts,
    )


def _entries_for_section(
    catalog: AccessKeysCatalog,
    layouts: Sequence[AccessKeysEntryLayout],
    section_id: str,
) -> tuple[str, ...]:
    entry_ids = _catalog_entry_ids(catalog)
    return tuple(
        layout.entry_id
        for layout in layouts
        if layout.section_id == section_id and layout.entry_id in entry_ids
    )


def _provider_links(entry: AccessKeysEntryView) -> tuple[tuple[str, str], ...]:
    if entry.entry_id == "asr:elevenlabs_scribe":
        return tuple(ELEVENLABS_LINKS.items())
    return ()


def provider_model_label(entry: AccessKeysEntryView) -> str:
    if entry.entry_id == "asr:elevenlabs_scribe":
        return "Scribe v2"
    return "Not applicable"


def provider_use_summary(entry: AccessKeysEntryView) -> str:
    if entry.entry_kind.value == "ASR_PROVIDER":
        return "Online speech-to-text"
    if entry.entry_kind.value == "SOURCE_ADAPTER":
        return "Source access / source evidence"
    return "Provider metadata"


def provider_data_use_note(entry: AccessKeysEntryView) -> str:
    if entry.entry_id == "asr:elevenlabs_scribe":
        return (
            "Audio is sent to this provider only when you explicitly start an "
            "online transcription."
        )
    return "No provider request is made from this window."


def status_icon_key(entry: AccessKeysEntryView) -> str:
    status = (entry.credential_status or "").casefold()
    test_status = (entry.last_test_status or "").casefold()
    if "test_passed" in status or test_status == "test_passed":
        return "verified"
    if (
        "test_failed" in status
        or "expired" in status
        or "revoked" in status
        or "status_error" in status
        or test_status == "test_failed"
    ):
        return "warning"
    if "configured" in status:
        return "saved"
    return "missing"


def _validation_failure_text(entry: AccessKeysEntryView) -> str:
    combined = " ".join(
        (
            entry.credential_status,
            entry.last_test_status,
            entry.project_status,
            entry.access_limitations,
        )
    ).casefold()
    if any(
        token in combined
        for token in (
            "timeout",
            "network",
            "rate limit",
            "rate-limit",
            "outage",
            "unavailable",
            "could not complete",
            "provider error",
        )
    ):
        return "Key could not be validated"
    return "Key validation failed"


def user_status_text(entry: AccessKeysEntryView) -> str:
    key = status_icon_key(entry)
    if key == "verified":
        return KEY_STATUS_VALIDATED
    if key == "warning":
        return _validation_failure_text(entry)
    if key == "saved":
        return KEY_STATUS_SAVED_NOT_VALIDATED
    if entry.credential_status == "NOT_NEEDED":
        return KEY_STATUS_NO_KEY_NEEDED
    return KEY_STATUS_NO_KEY_CONFIGURED


def credential_detail_status_text(entry: AccessKeysEntryView) -> str:
    status_text = user_status_text(entry)
    if status_icon_key(entry) == "saved":
        return (
            "Key saved securely. The key has not yet been checked with the provider. "
            "Existing keys are never displayed."
        )
    return f"{status_text}. Existing keys are never displayed."


class AccessKeysWindow(ctk.CTkToplevel):
    def __init__(
        self,
        parent: ctk.CTk,
        *,
        catalog: Optional[AccessKeysCatalog] = None,
        layouts: Sequence[AccessKeysEntryLayout] = (),
        credential_statuses: Optional[
            Mapping[str, CredentialRuntimeStatus]
        ] = None,
        credential_store: Optional[CredentialStore] = None,
        credential_status_provider: Optional[
            Callable[[], Mapping[str, CredentialRuntimeStatus]]
        ] = None,
        validation_records: Optional[Mapping[str, object]] = None,
        on_validation_records_change: Optional[
            Callable[[dict[str, dict[str, str]]], None]
        ] = None,
        validate_provider_key: Optional[
            Callable[[str], ProviderKeyValidationRecord]
        ] = None,
        browser_opener: Optional[Callable[[str], object]] = None,
        added_entry_ids: Sequence[str] = (),
        on_added_entry_ids_change: Optional[Callable[[tuple[str, ...]], None]] = None,
        on_close: Optional[Callable[[], None]] = None,
    ) -> None:
        super().__init__(parent)
        self._on_close_callback = on_close
        self._on_added_entry_ids_change = on_added_entry_ids_change
        self._closed = False
        self._render_count = 0
        self._selected_entry_id = ""
        self._visible_entry_ids: set[str] = set()
        self._detail_rows_visible = False
        self._family_popup_visible = False
        self._add_provider_popup_visible = False
        self._active_add_group_id = ""
        self._list_scroll_reset_after_id: Optional[str] = None
        self._credential_store = credential_store
        self._credential_status_provider = credential_status_provider
        self._validation_records = normalize_validation_records(validation_records)
        self._on_validation_records_change = on_validation_records_change
        self._validate_provider_key = validate_provider_key
        self._browser_opener = browser_opener
        self._validation_busy_provider_id = ""
        self._current_credential_entry_id = ""
        self._current_credential_id = ""
        self._current_validation_provider_id = ""
        self._runtime_status_checked_entry_ids: set[str] = set()
        self._add_provider_click_bind_id: Optional[str] = None
        self._add_provider_escape_bind_id: Optional[str] = None
        self._add_provider_origin_button: Optional[object] = None

        if catalog is None:
            bundle = build_default_access_keys_catalog_bundle()
        else:
            bundle = AccessKeysCatalogBundle(
                catalog=catalog,
                layouts=tuple(layouts),
            )
        self._full_catalog = bundle.catalog
        self._full_layouts = tuple(bundle.layouts)
        self._base_catalog = bundle.catalog
        self._layouts = tuple(bundle.layouts)
        valid_ids = _catalog_entry_ids(self._full_catalog)
        self._added_entry_ids = tuple(
            entry_id
            for entry_id in _normalised_entry_ids(added_entry_ids)
            if entry_id in valid_ids
        )
        if credential_statuses:
            self._base_catalog = apply_runtime_credential_statuses(
                self._base_catalog,
                credential_statuses,
            )
            self._full_catalog = apply_runtime_credential_statuses(
                self._full_catalog,
                credential_statuses,
            )
        self._apply_validation_records_to_catalogs()
        my_bundle = self._my_provider_bundle()
        self.controller = AccessKeysDialogController(
            my_bundle.catalog,
            my_bundle.layouts,
        )

        self.title(ACCESS_KEYS_WINDOW_TITLE)
        self.geometry("1100x720")
        self.minsize(900, 600)
        self.configure(fg_color=COLORS["bg_dark"])
        self.transient(parent)
        self.protocol("WM_DELETE_WINDOW", self.close)

        self._search_var = ctk.StringVar(value="")
        self._family_var = ctk.StringVar(value=ALL_FAMILIES_LABEL)
        self._add_provider_search_var = ctk.StringVar(value="")

        self._section_labels: dict[str, ctk.CTkLabel] = {}
        self._section_header_frames: dict[str, ctk.CTkFrame] = {}
        self._section_add_buttons: dict[str, ctk.CTkButton] = {}
        self._entry_buttons: dict[str, ctk.CTkButton] = {}
        self._entry_views: dict[str, AccessKeysEntryView] = {}
        self._detail_rows: dict[
            str,
            tuple[ctk.CTkLabel, ctk.CTkLabel],
        ] = {}
        self._status_icon_images: dict[str, object] = self._load_status_icons()
        self._add_provider_buttons: dict[str, ctk.CTkButton] = {}
        self._link_widgets: dict[str, ctk.CTkButton] = {}

        self._build_widgets()
        initial_view = self.controller.view()
        self._build_my_provider_widgets()
        self._build_detail_widgets()
        self._add_provider_search_var.trace_add(
            "write",
            self._on_add_provider_search_changed,
        )
        self._apply_view(initial_view)

    def _my_provider_bundle(self) -> AccessKeysCatalogBundle:
        return _catalog_subset(
            self._base_catalog,
            self._full_layouts,
            self._added_entry_ids,
        )

    def _replace_my_provider_controller(self) -> AccessKeysManagerView:
        bundle = self._my_provider_bundle()
        selected_id = (
            self._selected_entry_id
            if self._selected_entry_id in set(self._added_entry_ids)
            else ""
        )
        self.controller = AccessKeysDialogController(
            bundle.catalog,
            bundle.layouts,
        )
        self.controller.selected_entry_id = selected_id
        return self.controller.view()

    def _notify_added_entry_ids_changed(self) -> None:
        if self._on_added_entry_ids_change is not None:
            self._on_added_entry_ids_change(tuple(self._added_entry_ids))

    def _apply_validation_records_to_catalogs(self) -> None:
        if not self._validation_records:
            return
        self._base_catalog = apply_provider_key_validation_records(
            self._base_catalog,
            self._validation_records,
        )
        self._full_catalog = apply_provider_key_validation_records(
            self._full_catalog,
            self._validation_records,
        )

    def _set_validation_record(self, record: ProviderKeyValidationRecord) -> None:
        provider_id = normalize_provider_id(record.provider_id)
        if not provider_id:
            return
        self._validation_records[provider_id] = record
        self._apply_validation_records_to_catalogs()
        if self._on_validation_records_change is not None:
            self._on_validation_records_change(
                validation_records_to_settings_dict(self._validation_records)
            )

    def _asset_base_dir(self) -> str:
        if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
            return str(sys._MEIPASS)
        return os.path.dirname(os.path.abspath(__file__))

    def _load_status_icons(self) -> dict[str, object]:
        images: dict[str, object] = {}
        try:
            for key, filename in STATUS_ICON_ASSETS.items():
                path = os.path.join(self._asset_base_dir(), "assets", filename)
                image = Image.open(path).convert("RGBA").resize(
                    STATUS_ICON_SIZE,
                    Image.LANCZOS,
                )
                images[key] = ImageTk.PhotoImage(image)
        except Exception:
            images = {}
        return images

    def _build_widgets(self) -> None:
        header = ctk.CTkFrame(
            self,
            fg_color=COLORS["bg_card"],
            corner_radius=0,
        )
        header.pack(fill="x")

        ctk.CTkLabel(
            header,
            text=MY_PROVIDERS_HEADING,
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=COLORS["text_primary"],
        ).pack(anchor="w", padx=20, pady=(16, 2))

        ctk.CTkLabel(
            header,
            text=(
                "Add the services you use, then save or clear keys explicitly. "
                "Existing keys are never displayed, and this window does not "
                "test credentials or call providers."
            ),
            font=ctk.CTkFont(size=11),
            text_color=COLORS["text_secondary"],
        ).pack(anchor="w", padx=20, pady=(0, 14))

        filters = ctk.CTkFrame(self, fg_color="transparent")
        filters.pack(fill="x", padx=16, pady=(14, 8))
        filters.grid_columnconfigure(0, weight=1)

        self.search_entry = ctk.CTkEntry(
            filters,
            textvariable=self._search_var,
            placeholder_text="Search My Providers",
            height=36,
            fg_color=COLORS["bg_input"],
            border_color=COLORS["border"],
        )
        self.search_entry.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=(0, 8),
        )

        self.family_button = ctk.CTkButton(
            filters,
            text=f"{ALL_FAMILIES_LABEL}  ▾",
            command=self._toggle_family_menu,
            width=280,
            height=36,
            anchor="w",
            fg_color=COLORS["accent_secondary"],
            hover_color=COLORS["accent_hover"],
            text_color=COLORS["text_primary"],
        )
        self.family_button.grid(row=0, column=1, sticky="ew")
        self.family_button.bind("<Return>", self._toggle_family_menu_event)
        self.family_button.bind("<space>", self._toggle_family_menu_event)
        self.family_button.bind("<Down>", self._show_family_menu_event)
        self.bind("<Escape>", self._hide_family_menu_event, add="+")

        # A CustomTkinter overlay avoids the native tk.Menu repaint flash while
        # keeping the whole selector surface clickable.
        self.family_popup = ctk.CTkFrame(
            self,
            width=280,
            fg_color=COLORS["bg_card"],
            border_width=1,
            border_color=COLORS["border"],
            corner_radius=6,
        )
        self.family_option_buttons: dict[str, ctk.CTkButton] = {}
        for option in self.controller.family_options():
            button = ctk.CTkButton(
                self.family_popup,
                text=option,
                anchor="w",
                height=30,
                command=lambda value=option: self._choose_family(value),
                fg_color="transparent",
                hover_color=COLORS["accent_hover"],
                text_color=COLORS["text_primary"],
            )
            button.pack(fill="x", padx=4, pady=2)
            self.family_option_buttons[option] = button
        self.family_popup.place_forget()

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(
            fill="both",
            expand=True,
            padx=16,
            pady=(0, 12),
        )
        body.grid_columnconfigure(0, weight=2)
        body.grid_columnconfigure(1, weight=3)
        body.grid_rowconfigure(0, weight=1)

        self.list_panel = ctk.CTkScrollableFrame(
            body,
            fg_color=COLORS["bg_card"],
            corner_radius=8,
        )
        self.list_panel.grid(
            row=0,
            column=0,
            sticky="nsew",
            padx=(0, 8),
        )
        self.list_panel.grid_columnconfigure(0, weight=1)

        self.details_panel = ctk.CTkScrollableFrame(
            body,
            fg_color=COLORS["bg_card"],
            corner_radius=8,
        )
        self.details_panel.grid(
            row=0,
            column=1,
            sticky="nsew",
            padx=(8, 0),
        )
        self.details_panel.grid_columnconfigure(0, weight=1)

        self.warning_label = ctk.CTkLabel(
            self.list_panel,
            text="",
            text_color=COLORS["warning"],
            wraplength=360,
            justify="left",
        )
        self.empty_label = ctk.CTkLabel(
            self.list_panel,
            text="",
            text_color=COLORS["text_secondary"],
            wraplength=360,
            justify="left",
        )

        self.detail_placeholder = ctk.CTkLabel(
            self.details_panel,
            text="Add or select a provider to manage its key.",
            text_color=COLORS["text_secondary"],
            wraplength=520,
            justify="left",
        )

        self.add_provider_popup = ctk.CTkFrame(
            self,
            width=360,
            fg_color=COLORS["bg_card"],
            border_width=1,
            border_color=COLORS["border"],
            corner_radius=8,
        )
        self.add_provider_popup.grid_columnconfigure(0, weight=1)
        self.add_provider_search_entry = ctk.CTkEntry(
            self.add_provider_popup,
            textvariable=self._add_provider_search_var,
            placeholder_text=ADD_PROVIDER_SEARCH_PLACEHOLDER,
            height=32,
            fg_color=COLORS["bg_input"],
            border_color=COLORS["border"],
        )
        self.add_provider_search_entry.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=8,
            pady=(8, 6),
        )
        self.add_provider_results = ctk.CTkScrollableFrame(
            self.add_provider_popup,
            height=260,
            fg_color="transparent",
        )
        self.add_provider_results.grid(
            row=1,
            column=0,
            sticky="nsew",
            padx=8,
            pady=(0, 8),
        )
        self.add_provider_popup.place_forget()

        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.pack(fill="x", padx=16, pady=(0, 14))
        ctk.CTkButton(
            footer,
            text="Close",
            width=100,
            command=self.close,
            fg_color=COLORS["accent_secondary"],
            hover_color=COLORS["border"],
        ).pack(side="right")

    def _build_my_provider_widgets(self) -> None:
        for section_id, label in DEFAULT_ACCESS_KEYS_GROUPS:
            header = ctk.CTkFrame(self.list_panel, fg_color="transparent")
            header.grid_columnconfigure(0, weight=1)
            self._section_header_frames[section_id] = header
            self._section_labels[section_id] = ctk.CTkLabel(
                header,
                text=label,
                font=ctk.CTkFont(size=14, weight="bold"),
                text_color=COLORS["text_primary"],
            )
            self._section_labels[section_id].grid(
                row=0,
                column=0,
                sticky="w",
            )
            add_button = ctk.CTkButton(
                header,
                text="+",
                width=28,
                height=24,
                command=lambda section_id=section_id: (
                    self._show_add_provider_popup(section_id)
                ),
                fg_color=COLORS["accent_secondary"],
                hover_color=COLORS["accent_hover"],
                text_color=COLORS["text_primary"],
                corner_radius=6,
            )
            add_button.grid(row=0, column=1, sticky="e")
            self._section_add_buttons[section_id] = add_button

        for section in self.controller.view().sections:
            for entry in section.entries:
                self._create_entry_button(entry)

    def _create_entry_button(self, entry: AccessKeysEntryView) -> None:
        if entry.entry_id in self._entry_buttons:
            self._entry_views[entry.entry_id] = entry
            return
        self._entry_views[entry.entry_id] = entry
        self._entry_buttons[entry.entry_id] = ctk.CTkButton(
            self.list_panel,
            text=self._button_text(entry),
            image=self._status_icon_images.get(status_icon_key(entry)),
            compound="left",
            anchor="w",
            command=lambda entry_id=entry.entry_id: self._select_entry(entry_id),
            fg_color=self._base_entry_color(entry),
            hover_color=COLORS["accent_hover"],
            text_color=self._base_entry_text_color(entry),
        )

    def _build_detail_widgets(self) -> None:
        row = 0
        self.detail_title_label = ctk.CTkLabel(
            self.details_panel,
            text="",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=COLORS["text_primary"],
            wraplength=520,
            justify="left",
        )
        self.detail_title_label.grid(
            row=row,
            column=0,
            sticky="w",
            padx=14,
            pady=(14, 4),
        )
        self.detail_title_label.grid_remove()
        row += 1

        for label in _DETAIL_LABELS:
            label_widget = ctk.CTkLabel(
                self.details_panel,
                text=label,
                font=ctk.CTkFont(size=11, weight="bold"),
                text_color=COLORS["text_secondary"],
            )
            value_widget = ctk.CTkLabel(
                self.details_panel,
                text="",
                font=ctk.CTkFont(size=12),
                text_color=COLORS["text_primary"],
                wraplength=520,
                justify="left",
            )
            label_widget.grid(
                row=row,
                column=0,
                sticky="w",
                padx=14,
                pady=(7, 0),
            )
            row += 1
            value_widget.grid(
                row=row,
                column=0,
                sticky="ew",
                padx=14,
                pady=(0, 2),
            )
            row += 1
            label_widget.grid_remove()
            value_widget.grid_remove()
            self._detail_rows[label] = (label_widget, value_widget)

        self.detail_links_frame = ctk.CTkFrame(
            self.details_panel,
            fg_color="transparent",
        )
        self.detail_links_frame.grid(
            row=row,
            column=0,
            sticky="ew",
            padx=14,
            pady=(8, 2),
        )
        self.detail_links_frame.grid_columnconfigure(0, weight=1)
        self.detail_link_labels: dict[str, ctk.CTkButton] = {}
        for link_index, label in enumerate(ELEVENLABS_LINKS):
            link_label = ctk.CTkButton(
                self.detail_links_frame,
                text=label,
                command=lambda label=label: self._open_provider_link(label),
                anchor="w",
                height=28,
                font=ctk.CTkFont(size=11, weight="bold"),
                fg_color="transparent",
                hover_color=COLORS["accent_hover"],
                text_color=COLORS["accent_hover"],
            )
            link_label.grid(
                row=link_index,
                column=0,
                sticky="ew",
                pady=(0, 3),
            )
            link_label.grid_remove()
            self.detail_link_labels[label] = link_label
        self.detail_links_frame.grid_remove()
        row += 1

        self.credential_action_panel = ctk.CTkFrame(
            self.details_panel,
            fg_color=COLORS["bg_input"],
            border_width=1,
            border_color=COLORS["border"],
            corner_radius=6,
        )
        self.credential_action_panel.grid(
            row=row,
            column=0,
            sticky="ew",
            padx=14,
            pady=(16, 8),
        )
        self.credential_action_panel.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            self.credential_action_panel,
            text="Key input",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=COLORS["text_secondary"],
        ).grid(row=0, column=0, columnspan=3, sticky="w", padx=10, pady=(8, 2))

        self.credential_entry = _create_masked_credential_entry(
            self.credential_action_panel,
            placeholder_text="Enter key to save",
            fg_color=COLORS["bg_card"],
            border_color=COLORS["border"],
        )
        self.credential_entry.grid(
            row=1,
            column=0,
            sticky="ew",
            padx=(10, 6),
            pady=(4, 8),
        )
        self.credential_save_button = ctk.CTkButton(
            self.credential_action_panel,
            text="Save",
            width=72,
            command=self._save_selected_credential,
            fg_color=COLORS["accent_secondary"],
            hover_color=COLORS["accent_hover"],
        )
        self.credential_save_button.grid(
            row=1,
            column=1,
            padx=(0, 6),
            pady=(4, 8),
        )
        self.credential_clear_button = ctk.CTkButton(
            self.credential_action_panel,
            text="Clear",
            width=72,
            command=self._clear_selected_credential,
            fg_color=COLORS["accent_secondary"],
            hover_color=COLORS["border"],
        )
        self.credential_clear_button.grid(
            row=1,
            column=2,
            padx=(0, 10),
            pady=(4, 8),
        )
        self.credential_validate_button = ctk.CTkButton(
            self.credential_action_panel,
            text="Validate key",
            command=self._validate_selected_credential,
            height=30,
            fg_color=COLORS["accent_secondary"],
            hover_color=COLORS["accent_hover"],
        )
        self.credential_validate_button.grid(
            row=2,
            column=0,
            columnspan=3,
            sticky="ew",
            padx=10,
            pady=(0, 8),
        )
        self.credential_action_status_label = ctk.CTkLabel(
            self.credential_action_panel,
            text="",
            text_color=COLORS["text_secondary"],
            wraplength=500,
            justify="left",
        )
        self.credential_action_status_label.grid(
            row=3,
            column=0,
            columnspan=3,
            sticky="ew",
            padx=10,
            pady=(0, 8),
        )
        self.credential_action_panel.grid_remove()

        self.hide_provider_button = ctk.CTkButton(
            self.details_panel,
            text="Remove from My Providers",
            command=self._remove_selected_provider,
            height=30,
            fg_color=COLORS["accent_secondary"],
            hover_color=COLORS["border"],
            text_color=COLORS["text_primary"],
        )
        self.hide_provider_button.grid(
            row=row + 1,
            column=0,
            sticky="w",
            padx=14,
            pady=(4, 14),
        )
        self.hide_provider_button.grid_remove()

    @staticmethod
    def _button_text(entry: AccessKeysEntryView) -> str:
        suffix = " - Planned" if entry.planned_only else ""
        return f"{entry.display_name}{suffix}"

    @staticmethod
    def _base_entry_color(entry: AccessKeysEntryView) -> str:
        return (
            COLORS["bg_input"]
            if entry.planned_only
            else COLORS["accent_secondary"]
        )

    @staticmethod
    def _base_entry_text_color(entry: AccessKeysEntryView) -> str:
        return (
            COLORS["text_secondary"]
            if entry.planned_only
            else COLORS["text_primary"]
        )

    def _toggle_family_menu_event(self, _event: object) -> str:
        self._toggle_family_menu()
        return "break"

    def _show_family_menu_event(self, _event: object) -> str:
        self._show_family_menu()
        return "break"

    def _hide_family_menu_event(self, _event: object) -> str:
        self._hide_family_menu()
        return "break"

    def _toggle_family_menu(self) -> None:
        if self._family_popup_visible:
            self._hide_family_menu()
        else:
            self._show_family_menu()

    def _show_family_menu(self) -> None:
        if self._family_popup_visible:
            return
        self.family_button.focus_set()
        self.update_idletasks()
        x = self.family_button.winfo_rootx() - self.winfo_rootx()
        y = (
            self.family_button.winfo_rooty()
            - self.winfo_rooty()
            + self.family_button.winfo_height()
            + 2
        )
        self.family_popup.place(x=x, y=y)
        self.family_popup.lift()
        self._family_popup_visible = True

    def _hide_family_menu(self) -> None:
        if not self._family_popup_visible:
            return
        self.family_popup.place_forget()
        self._family_popup_visible = False

    def _reset_list_scroll_to_top(self) -> None:
        # CTkScrollableFrame does not expose a public yview API. Guard the
        # internal canvas lookup so older/newer CustomTkinter builds degrade
        # safely instead of leaving a filtered short list below the old scroll
        # offset.
        canvas = getattr(self.list_panel, "_parent_canvas", None)
        yview_moveto = getattr(canvas, "yview_moveto", None)
        if callable(yview_moveto):
            yview_moveto(0.0)

    def _finish_list_scroll_reset(self) -> None:
        self._list_scroll_reset_after_id = None
        if self._closed:
            return
        self._reset_list_scroll_to_top()

    def _queue_list_scroll_reset(self) -> None:
        if self._list_scroll_reset_after_id is not None:
            self.after_cancel(self._list_scroll_reset_after_id)
        self._list_scroll_reset_after_id = self.after_idle(
            self._finish_list_scroll_reset
        )

    def _apply_filtered_view(self, view: AccessKeysManagerView) -> None:
        # Reset immediately so a short filtered family does not inherit the
        # previous long list's lower scroll position. Repeat after idle once
        # geometry and the canvas scrollregion have caught up.
        self._reset_list_scroll_to_top()
        self._apply_view(view)
        self._queue_list_scroll_reset()

    def _choose_family(self, value: str) -> None:
        self._hide_family_menu()
        self._family_var.set(value)
        self.family_button.configure(text=f"{value}  ▾")
        self._apply_filtered_view(self.controller.set_family(value))

    def _on_search_changed(self, *_args: object) -> None:
        self._apply_filtered_view(
            self.controller.set_search(self._search_var.get())
        )

    def _hide_add_provider_popup_event(self, _event: object) -> str:
        self._hide_add_provider_popup()
        return "break"

    def _bind_add_provider_popup_events(self) -> None:
        if self._add_provider_click_bind_id is None:
            self._add_provider_click_bind_id = self.bind(
                "<Button-1>",
                self._on_add_provider_global_click,
                add="+",
            )
        if self._add_provider_escape_bind_id is None:
            self._add_provider_escape_bind_id = self.bind(
                "<Escape>",
                self._hide_add_provider_popup_event,
                add="+",
            )

    def _unbind_add_provider_popup_events(self) -> None:
        if self._add_provider_click_bind_id is not None:
            try:
                self.unbind("<Button-1>", self._add_provider_click_bind_id)
            except Exception:
                pass
            self._add_provider_click_bind_id = None
        if self._add_provider_escape_bind_id is not None:
            try:
                self.unbind("<Escape>", self._add_provider_escape_bind_id)
            except Exception:
                pass
            self._add_provider_escape_bind_id = None

    def _widget_is_inside_add_provider_popup(self, widget: object) -> bool:
        popup_name = str(getattr(self, "add_provider_popup", ""))
        widget_name = str(widget or "")
        return bool(popup_name and widget_name.startswith(popup_name))

    def _on_add_provider_global_click(self, event: object) -> None:
        if not self._add_provider_popup_visible:
            return
        widget = getattr(event, "widget", None)
        if self._widget_is_inside_add_provider_popup(widget):
            return
        if widget in self._section_add_buttons.values():
            return
        self._hide_add_provider_popup()

    def _show_add_provider_popup(self, section_id: str) -> None:
        self._hide_family_menu()
        if (
            self._add_provider_popup_visible
            and self._active_add_group_id == section_id
        ):
            self._hide_add_provider_popup()
            return
        if self._add_provider_popup_visible:
            self._hide_add_provider_popup()
        self._active_add_group_id = section_id
        self._add_provider_search_var.set("")
        self._refresh_add_provider_results()
        button = self._section_add_buttons[section_id]
        self._add_provider_origin_button = button
        self.update_idletasks()
        x = button.winfo_rootx() - self.winfo_rootx() - 320
        y = button.winfo_rooty() - self.winfo_rooty() + button.winfo_height() + 2
        self.add_provider_popup.place(x=max(8, x), y=max(8, y))
        self.add_provider_popup.lift()
        self._add_provider_popup_visible = True
        self._bind_add_provider_popup_events()
        try:
            self.add_provider_search_entry.focus_set()
        except Exception:
            pass

    def _hide_add_provider_popup(self) -> None:
        if not self._add_provider_popup_visible:
            return
        self.add_provider_popup.place_forget()
        self._add_provider_popup_visible = False
        self._active_add_group_id = ""
        self._unbind_add_provider_popup_events()
        origin = self._add_provider_origin_button
        self._add_provider_origin_button = None
        try:
            if origin is not None:
                origin.focus_set()
        except Exception:
            pass

    def _on_add_provider_search_changed(self, *_args: object) -> None:
        if self._add_provider_popup_visible:
            self._refresh_add_provider_results()

    def _refresh_add_provider_results(self) -> None:
        for button in self._add_provider_buttons.values():
            button.destroy()
        self._add_provider_buttons = {}

        query = " ".join(self._add_provider_search_var.get().split()).casefold()
        section_ids = _entries_for_section(
            self._full_catalog,
            self._full_layouts,
            self._active_add_group_id,
        )
        entry_lookup = _entry_by_id(self._full_catalog)
        layout_lookup = _layout_by_id(self._full_layouts)
        row = 0
        for entry_id in section_ids:
            if entry_id in self._added_entry_ids:
                continue
            entry = entry_lookup.get(entry_id)
            layout = layout_lookup.get(entry_id)
            if entry is None or layout is None:
                continue
            search_text = " ".join(
                (
                    getattr(entry, "display_name", ""),
                    getattr(entry, "entry_id", ""),
                    layout.canonical_name,
                    *layout.aliases,
                    *layout.tags,
                )
            ).casefold()
            if query and query not in search_text:
                continue
            disabled = getattr(entry, "implementation_state", "") == "planned metadata only"
            label = (
                f"{entry.display_name} - planned"
                if disabled
                else entry.display_name
            )
            button = ctk.CTkButton(
                self.add_provider_results,
                text=label,
                anchor="w",
                height=30,
                command=lambda entry_id=entry_id, disabled=disabled: (
                    None if disabled else self._add_provider(entry_id, select=True)
                ),
                fg_color="transparent" if disabled else COLORS["accent_secondary"],
                hover_color=COLORS["accent_hover"],
                text_color=(
                    COLORS["text_secondary"]
                    if disabled
                    else COLORS["text_primary"]
                ),
            )
            button.grid(row=row, column=0, sticky="ew", padx=4, pady=2)
            self._add_provider_buttons[entry_id] = button
            row += 1

    def _add_provider(self, entry_id: str, *, select: bool = False) -> None:
        entry_id = " ".join(str(entry_id or "").split())
        if entry_id not in _catalog_entry_ids(self._full_catalog):
            return
        if entry_id not in self._added_entry_ids:
            self._added_entry_ids = (*self._added_entry_ids, entry_id)
            self._notify_added_entry_ids_changed()
        if select:
            self._selected_entry_id = entry_id
        view = self._replace_my_provider_controller()
        if select:
            self.controller.selected_entry_id = entry_id
            view = self.controller.view()
        self._apply_view(view)
        self._hide_add_provider_popup()

    def _remove_selected_provider(self) -> None:
        entry_id = self._selected_entry_id
        if not entry_id:
            return
        self._added_entry_ids = tuple(
            candidate
            for candidate in self._added_entry_ids
            if candidate != entry_id
        )
        self._notify_added_entry_ids_changed()
        self._selected_entry_id = ""
        view = self._replace_my_provider_controller()
        self._apply_view(view)

    def _refresh_runtime_status_for_entry(self, entry_id: str) -> None:
        if (
            not entry_id
            or entry_id in self._runtime_status_checked_entry_ids
            or self._credential_status_provider is None
        ):
            return
        self._runtime_status_checked_entry_ids.add(entry_id)
        statuses = self._credential_status_provider()
        status = statuses.get(entry_id)
        if status is None:
            return
        self._base_catalog = apply_runtime_credential_statuses(
            self._base_catalog,
            {entry_id: status},
        )
        self._full_catalog = apply_runtime_credential_statuses(
            self._full_catalog,
            {entry_id: status},
        )
        self._apply_validation_records_to_catalogs()
        view = self._replace_my_provider_controller()
        self.controller.selected_entry_id = entry_id
        view = self.controller.view()
        self._entry_views = {
            entry.entry_id: entry
            for section in view.sections
            for entry in section.entries
        }
        if entry_id in self._entry_buttons and entry_id in self._entry_views:
            self._configure_entry_button(
                entry_id,
                selected=entry_id == self._selected_entry_id,
            )

    def _select_entry(self, entry_id: str) -> None:
        if entry_id not in self._visible_entry_ids:
            if entry_id in _catalog_entry_ids(self._full_catalog):
                self._add_provider(entry_id, select=True)
            return
        if (
            entry_id == self._selected_entry_id
        ):
            return

        previous_entry_id = self._selected_entry_id
        self._refresh_runtime_status_for_entry(entry_id)
        self.controller.selected_entry_id = entry_id
        self._selected_entry_id = entry_id

        if previous_entry_id in self._entry_buttons:
            self._configure_entry_button(
                previous_entry_id,
                selected=False,
            )
        self._configure_entry_button(entry_id, selected=True)
        self._render_details(self._entry_views.get(entry_id))

    def _apply_view(self, view: AccessKeysManagerView) -> None:
        # Build the new layout before hiding stale widgets. This avoids an
        # empty intermediate frame during synchronous search/family changes.
        self._render_count += 1
        visible_sections: set[str] = set()
        visible_entries: set[str] = set()

        row = 0
        if view.warnings:
            self.warning_label.configure(text="\n".join(view.warnings))
            self.warning_label.grid(
                row=row,
                column=0,
                sticky="ew",
                padx=10,
                pady=(8, 4),
            )
            row += 1
        else:
            self.warning_label.grid_remove()

        if view.empty_message:
            self.empty_label.configure(text=view.empty_message)
        else:
            self.empty_label.grid_remove()

        for section_id, _label in DEFAULT_ACCESS_KEYS_GROUPS:
            visible_sections.add(section_id)
            header = self._section_header_frames[section_id]
            header.grid(
                row=row,
                column=0,
                sticky="ew",
                padx=10,
                pady=(14, 5),
            )
            row += 1
            matching_section = next(
                (
                    section
                    for section in view.sections
                    if section.section_id == section_id
                ),
                None,
            )
            if matching_section is None:
                continue
            for entry in matching_section.entries:
                self._create_entry_button(entry)
                visible_entries.add(entry.entry_id)
                row = self._place_entry_button(entry, row)

        if view.empty_message:
            self.empty_label.grid(
                row=row,
                column=0,
                sticky="ew",
                padx=12,
                pady=20,
            )

        for section_id, header in self._section_header_frames.items():
            if section_id not in visible_sections:
                header.grid_remove()
        for entry_id, button in self._entry_buttons.items():
            if entry_id not in visible_entries:
                button.grid_remove()

        self._visible_entry_ids = visible_entries
        self._selected_entry_id = view.selected_entry_id
        selected = self.controller.selected_entry(view)
        if selected is not None:
            self._refresh_runtime_status_for_entry(selected.entry_id)
            selected = self._entry_views.get(selected.entry_id, selected)
        self._render_details(selected)

    def _configure_entry_button(
        self,
        entry_id: str,
        *,
        selected: bool,
    ) -> None:
        entry = self._entry_views[entry_id]
        self._entry_buttons[entry_id].configure(
            text=self._button_text(entry),
            image=self._status_icon_images.get(status_icon_key(entry)),
            fg_color=(
                COLORS["accent"]
                if selected
                else self._base_entry_color(entry)
            ),
            text_color=(
                COLORS["text_primary"]
                if selected
                else self._base_entry_text_color(entry)
            ),
        )

    def _place_entry_button(
        self,
        entry: AccessKeysEntryView,
        row: int,
    ) -> int:
        self._configure_entry_button(
            entry.entry_id,
            selected=entry.selected,
        )
        self._entry_buttons[entry.entry_id].grid(
            row=row,
            column=0,
            sticky="ew",
            padx=(28, 10),
            pady=2,
        )
        return row + 1

    def _set_detail_rows_visible(self, visible: bool) -> None:
        if visible == self._detail_rows_visible:
            return
        self._detail_rows_visible = visible
        if visible:
            for label_widget, value_widget in self._detail_rows.values():
                label_widget.grid()
                value_widget.grid()
        else:
            for label_widget, value_widget in self._detail_rows.values():
                label_widget.grid_remove()
                value_widget.grid_remove()

    def _render_details(
        self,
        entry: Optional[AccessKeysEntryView],
    ) -> None:
        if entry is None:
            self.detail_title_label.grid_remove()
            self.detail_links_frame.grid_remove()
            self.hide_provider_button.grid_remove()
            self._set_detail_rows_visible(False)
            self._render_credential_controls(None)
            self.detail_placeholder.grid(
                row=0,
                column=0,
                sticky="w",
                padx=14,
                pady=18,
            )
            return

        self.detail_placeholder.grid_remove()
        self.detail_title_label.configure(text=entry.display_name)
        self.detail_title_label.grid()
        self._set_detail_rows_visible(True)
        for label, value in access_keys_detail_lines(entry):
            _label_widget, value_widget = self._detail_rows[label]
            if value_widget.cget("text") != value:
                value_widget.configure(text=value)
        links = dict(_provider_links(entry))
        if links:
            self.detail_links_frame.grid()
        else:
            self.detail_links_frame.grid_remove()
        for label, widget in self.detail_link_labels.items():
            url = links.get(label, "")
            if url:
                widget.configure(text=label)
                widget.grid()
            else:
                widget.grid_remove()
        self.hide_provider_button.grid()
        self._render_credential_controls(entry)

    def _open_provider_link(self, label: str) -> None:
        links = dict(ELEVENLABS_LINKS)
        url = links.get(label, "")
        if not url.startswith("https://") or url not in set(links.values()):
            return
        if self._browser_opener is not None:
            self._browser_opener(url)

    def _render_credential_controls(
        self,
        entry: Optional[AccessKeysEntryView],
    ) -> None:
        credential_id = (
            cloud_asr_credential_id_for_entry_id(entry.entry_id)
            if entry is not None and self._credential_store is not None
            else ""
        )
        self._current_credential_entry_id = entry.entry_id if entry else ""
        self._current_credential_id = credential_id
        self._current_validation_provider_id = (
            provider_id_for_access_entry_id(entry.entry_id)
            if entry is not None
            else ""
        )
        _set_entry_masked(self.credential_entry)
        if not credential_id:
            self.credential_entry.delete(0, "end")
            _set_entry_masked(self.credential_entry)
            self.credential_action_status_label.configure(text="")
            self.credential_validate_button.configure(state="disabled")
            self.credential_action_panel.grid_remove()
            return

        self.credential_action_panel.grid()
        self.credential_entry.delete(0, "end")
        _set_entry_masked(self.credential_entry)
        self.credential_validate_button.configure(
            state=(
                "normal"
                if status_icon_key(entry) in {"saved", "verified", "warning"}
                and self._validate_provider_key is not None
                and self._validation_busy_provider_id != self._current_validation_provider_id
                else "disabled"
            )
        )
        self.credential_action_status_label.configure(
            text=credential_detail_status_text(entry)
        )

    @staticmethod
    def _credential_result_message(status: CredentialStoreStatus) -> str:
        messages = {
            CredentialStoreStatus.SAVED: "Credential saved.",
            CredentialStoreStatus.UPDATED: "Credential updated.",
            CredentialStoreStatus.CLEARED: "Credential cleared.",
            CredentialStoreStatus.NOT_FOUND: "Credential was already missing.",
            CredentialStoreStatus.EMPTY_CREDENTIAL_REJECTED: "Nothing was saved; empty input is not accepted.",
            CredentialStoreStatus.BACKEND_UNAVAILABLE: "Secure credential store is unavailable.",
            CredentialStoreStatus.BACKEND_ERROR: "Secure credential store returned a safe error.",
            CredentialStoreStatus.UNSUPPORTED_CREDENTIAL: "This credential is not supported by the secure store.",
            CredentialStoreStatus.YOUTUBE_CREDENTIAL_EXCLUDED: "The existing YouTube credential is excluded here.",
        }
        return messages.get(status, "Credential action finished.")

    def _refresh_runtime_statuses_after_credential_action(self) -> None:
        if self._credential_status_provider is None:
            return
        statuses = self._credential_status_provider()
        self._runtime_status_checked_entry_ids.clear()
        self._base_catalog = apply_runtime_credential_statuses(
            self._base_catalog,
            statuses,
        )
        self._full_catalog = apply_runtime_credential_statuses(
            self._full_catalog,
            statuses,
        )
        self._apply_validation_records_to_catalogs()
        view = self._replace_my_provider_controller()
        if self._selected_entry_id:
            self.controller.selected_entry_id = self._selected_entry_id
            view = self.controller.view()
        self._entry_views = {
            entry.entry_id: entry
            for section in view.sections
            for entry in section.entries
        }
        for entry_id in tuple(self._visible_entry_ids):
            if entry_id in self._entry_buttons and entry_id in self._entry_views:
                self._configure_entry_button(
                    entry_id,
                    selected=entry_id == view.selected_entry_id,
                )
        self._selected_entry_id = view.selected_entry_id
        self._render_details(self.controller.selected_entry(view))

    def _save_selected_credential(self) -> None:
        credential_id = self._current_credential_id
        store = self._credential_store
        credential = self.credential_entry.get()
        self.credential_entry.delete(0, "end")
        _set_entry_masked(self.credential_entry)
        if not credential_id or store is None:
            self.credential_action_status_label.configure(
                text="No supported cloud-ASR credential is selected."
            )
            return
        if not str(credential).strip():
            self.credential_action_status_label.configure(
                text=self._credential_result_message(
                    CredentialStoreStatus.EMPTY_CREDENTIAL_REJECTED
                )
            )
            return
        result = store.save_credential(credential_id, str(credential).strip())
        message = self._credential_result_message(result.status)
        if result.status in {CredentialStoreStatus.SAVED, CredentialStoreStatus.UPDATED}:
            provider_id = provider_id_for_access_entry_id(
                self._current_credential_entry_id
            )
            self._set_validation_record(
                validation_record_for_saved_key(provider_id)
            )
        self._refresh_runtime_statuses_after_credential_action()
        self.credential_action_status_label.configure(text=message)

    def _clear_selected_credential(self) -> None:
        credential_id = self._current_credential_id
        store = self._credential_store
        self.credential_entry.delete(0, "end")
        _set_entry_masked(self.credential_entry)
        if not credential_id or store is None:
            self.credential_action_status_label.configure(
                text="No supported cloud-ASR credential is selected."
            )
            return
        result = store.clear_credential(credential_id)
        message = self._credential_result_message(result.status)
        if result.status in {CredentialStoreStatus.CLEARED, CredentialStoreStatus.NOT_FOUND}:
            provider_id = provider_id_for_access_entry_id(
                self._current_credential_entry_id
            )
            self._set_validation_record(
                validation_record_for_cleared_key(provider_id)
            )
        self._refresh_runtime_statuses_after_credential_action()
        self.credential_action_status_label.configure(text=message)

    @staticmethod
    def _record_from_validation_exception(
        provider_id: str,
        exc: Exception,
    ) -> ProviderKeyValidationRecord:
        category = str(getattr(exc, "category", "") or exc)
        state = (
            KEY_VALIDATION_FAILED
            if "validation_failed" in category
            or "authentication" in category.casefold()
            else KEY_VALIDATION_COULD_NOT_COMPLETE
        )
        return ProviderKeyValidationRecord(
            provider_id=provider_id,
            state=state,
            checked_at_utc=current_utc_timestamp(),
            safe_diagnostic=category or "validation_could_not_complete",
        )

    def _finish_validation_record(
        self,
        record: ProviderKeyValidationRecord,
    ) -> None:
        if self._closed:
            return
        self._validation_busy_provider_id = ""
        self._set_validation_record(record)
        self._refresh_runtime_statuses_after_credential_action()
        if self._current_validation_provider_id == record.provider_id:
            self.credential_validate_button.configure(state="normal")
            self.credential_action_status_label.configure(
                text=validation_status_text_for_state(record.state)
            )

    def _validate_selected_credential(self) -> None:
        provider_id = self._current_validation_provider_id
        if (
            not provider_id
            or self._validate_provider_key is None
            or self._validation_busy_provider_id
        ):
            return
        entry = self._entry_views.get(self._current_credential_entry_id)
        if entry is None or status_icon_key(entry) == "missing":
            self.credential_action_status_label.configure(
                text=KEY_STATUS_NO_KEY_CONFIGURED
            )
            return
        self._validation_busy_provider_id = provider_id
        self.credential_validate_button.configure(state="disabled")
        self.credential_action_status_label.configure(text="Validating...")

        def worker() -> None:
            try:
                record = self._validate_provider_key(provider_id)
            except (KeyboardInterrupt, SystemExit, GeneratorExit):
                raise
            except Exception as exc:
                record = self._record_from_validation_exception(provider_id, exc)
            if self._closed:
                return
            try:
                self.after(0, lambda: self._finish_validation_record(record))
            except Exception:
                return

        threading.Thread(target=worker, daemon=True).start()

    def close(self) -> None:
        if self._closed:
            return
        self._hide_family_menu()
        self._hide_add_provider_popup()
        if self._list_scroll_reset_after_id is not None:
            self.after_cancel(self._list_scroll_reset_after_id)
            self._list_scroll_reset_after_id = None
        self._closed = True
        callback = self._on_close_callback
        self._on_close_callback = None
        if callback is not None:
            callback()
        self.destroy()


def open_or_focus_access_keys_window(
    existing: Optional[AccessKeysWindow],
    factory: Callable[[], AccessKeysWindow],
) -> AccessKeysWindow:
    if existing is not None and existing.winfo_exists():
        window = existing
    else:
        window = factory()
    window.lift()
    window.focus_force()
    return window
