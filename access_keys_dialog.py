from __future__ import annotations

from typing import Callable, Mapping, Optional, Sequence

import customtkinter as ctk

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
)
from access_keys_view_model import (
    AccessKeysEntryView,
    AccessKeysManagerView,
    build_access_keys_manager_view,
)
from core.constants import COLORS


ACCESS_KEYS_WINDOW_TITLE = "Access & Keys"
ACCESS_KEYS_BUTTON_TEXT = "KEYS"
ALL_FAMILIES_LABEL = "All families"

_DETAIL_LABELS = (
    "Name",
    "Section",
    "Subgroup",
    "Entry kind",
    "Platform family",
    "Implementation",
    "Access mode",
    "Credential status",
    "Credential type",
    "Project status",
    "Test status",
    "Enabled capabilities",
    "Planned capabilities",
    "Setup hint",
    "Privacy",
    "Cost / rate limits",
    "Access limitations",
)


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
    enabled_capabilities = ", ".join(entry.enabled_capabilities) or "none"
    planned_capabilities = ", ".join(entry.planned_capabilities) or "none"
    return (
        ("Name", entry.display_name),
        ("Section", entry.section_label or entry.section_id or "other"),
        ("Subgroup", entry.subgroup_label or "none"),
        ("Entry kind", entry.entry_kind.value),
        ("Platform family", entry.platform_family or "other"),
        ("Implementation", entry.implementation_state or "not stated"),
        ("Access mode", entry.access_mode),
        ("Credential status", entry.credential_status),
        ("Credential type", entry.credential_type or "not stated"),
        ("Project status", entry.project_status or "not stated"),
        ("Test status", entry.last_test_status or "not stated"),
        ("Enabled capabilities", enabled_capabilities),
        ("Planned capabilities", planned_capabilities),
        ("Setup hint", entry.setup_hint or "none"),
        ("Privacy", entry.privacy_notes or "none"),
        ("Cost / rate limits", entry.cost_or_rate_limit_notes or "none"),
        ("Access limitations", entry.access_limitations or "none"),
    )


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
        on_close: Optional[Callable[[], None]] = None,
    ) -> None:
        super().__init__(parent)
        self._on_close_callback = on_close
        self._closed = False
        self._render_count = 0
        self._selected_entry_id = ""
        self._visible_entry_ids: set[str] = set()
        self._detail_rows_visible = False
        self._family_popup_visible = False
        self._list_scroll_reset_after_id: Optional[str] = None

        if catalog is None:
            bundle = build_default_access_keys_catalog_bundle()
        else:
            bundle = AccessKeysCatalogBundle(
                catalog=catalog,
                layouts=tuple(layouts),
            )
        bundle = AccessKeysCatalogBundle(
            catalog=apply_runtime_credential_statuses(
                bundle.catalog,
                credential_statuses or {},
            ),
            layouts=bundle.layouts,
        )
        self.controller = AccessKeysDialogController(
            bundle.catalog,
            bundle.layouts,
        )

        self.title(ACCESS_KEYS_WINDOW_TITLE)
        self.geometry("1100x720")
        self.minsize(900, 600)
        self.configure(fg_color=COLORS["bg_dark"])
        self.transient(parent)
        self.protocol("WM_DELETE_WINDOW", self.close)

        self._search_var = ctk.StringVar(value="")
        self._family_var = ctk.StringVar(value=ALL_FAMILIES_LABEL)

        self._section_labels: dict[str, ctk.CTkLabel] = {}
        self._subgroup_labels: dict[tuple[str, str], ctk.CTkLabel] = {}
        self._entry_buttons: dict[str, ctk.CTkButton] = {}
        self._entry_views: dict[str, AccessKeysEntryView] = {}
        self._detail_rows: dict[
            str,
            tuple[ctk.CTkLabel, ctk.CTkLabel],
        ] = {}

        self._build_widgets()
        initial_view = self.controller.view()
        self._build_catalog_widgets(initial_view)
        self._build_detail_widgets()
        self._search_var.trace_add("write", self._on_search_changed)
        self._apply_view(initial_view)

    def _build_widgets(self) -> None:
        header = ctk.CTkFrame(
            self,
            fg_color=COLORS["bg_card"],
            corner_radius=0,
        )
        header.pack(fill="x")

        ctk.CTkLabel(
            header,
            text=ACCESS_KEYS_WINDOW_TITLE,
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=COLORS["text_primary"],
        ).pack(anchor="w", padx=20, pady=(16, 2))

        ctk.CTkLabel(
            header,
            text=(
                "Read-only local credential presence/provenance status. This "
                "window does not display values, store, migrate, clear, test, "
                "or call providers."
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
            placeholder_text="Search access metadata",
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
            text="Select an access entry to review its non-secret metadata.",
            text_color=COLORS["text_secondary"],
            wraplength=520,
            justify="left",
        )

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

    def _build_catalog_widgets(
        self,
        view: AccessKeysManagerView,
    ) -> None:
        for section in view.sections:
            self._section_labels[section.section_id] = ctk.CTkLabel(
                self.list_panel,
                text=section.display_name,
                font=ctk.CTkFont(size=14, weight="bold"),
                text_color=COLORS["text_primary"],
            )
            for subgroup in section.subgroups:
                key = (section.section_id, subgroup.subgroup_id)
                self._subgroup_labels[key] = ctk.CTkLabel(
                    self.list_panel,
                    text=subgroup.display_name,
                    font=ctk.CTkFont(size=11, weight="bold"),
                    text_color=COLORS["text_secondary"],
                )
            for entry in section.entries:
                self._entry_views[entry.entry_id] = entry
                self._entry_buttons[entry.entry_id] = ctk.CTkButton(
                    self.list_panel,
                    text=self._button_text(entry),
                    anchor="w",
                    command=lambda entry_id=entry.entry_id: (
                        self._select_entry(entry_id)
                    ),
                    fg_color=self._base_entry_color(entry),
                    hover_color=COLORS["accent_hover"],
                    text_color=self._base_entry_text_color(entry),
                )

    def _build_detail_widgets(self) -> None:
        row = 0
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
                pady=(10, 1),
            )
            row += 1
            value_widget.grid(
                row=row,
                column=0,
                sticky="ew",
                padx=14,
            )
            row += 1
            label_widget.grid_remove()
            value_widget.grid_remove()
            self._detail_rows[label] = (label_widget, value_widget)

    @staticmethod
    def _button_text(entry: AccessKeysEntryView) -> str:
        return (
            f"{entry.display_name}  · Planned"
            if entry.planned_only
            else entry.display_name
        )

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

    def _select_entry(self, entry_id: str) -> None:
        if (
            entry_id not in self._visible_entry_ids
            or entry_id == self._selected_entry_id
        ):
            return

        previous_entry_id = self._selected_entry_id
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
        visible_subgroups: set[tuple[str, str]] = set()
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
            self.empty_label.grid(
                row=row,
                column=0,
                sticky="ew",
                padx=12,
                pady=20,
            )
        else:
            self.empty_label.grid_remove()
            for section in view.sections:
                visible_sections.add(section.section_id)
                section_label = self._section_labels[section.section_id]
                section_label.grid(
                    row=row,
                    column=0,
                    sticky="w",
                    padx=10,
                    pady=(14, 5),
                )
                row += 1

                if section.subgroups:
                    for subgroup in section.subgroups:
                        subgroup_key = (
                            section.section_id,
                            subgroup.subgroup_id,
                        )
                        visible_subgroups.add(subgroup_key)
                        subgroup_label = self._subgroup_labels[subgroup_key]
                        subgroup_label.grid(
                            row=row,
                            column=0,
                            sticky="w",
                            padx=(20, 10),
                            pady=(8, 3),
                        )
                        row += 1
                        for entry in subgroup.entries:
                            visible_entries.add(entry.entry_id)
                            row = self._place_entry_button(entry, row)
                else:
                    for entry in section.entries:
                        visible_entries.add(entry.entry_id)
                        row = self._place_entry_button(entry, row)

        for section_id, label in self._section_labels.items():
            if section_id not in visible_sections:
                label.grid_remove()
        for subgroup_key, label in self._subgroup_labels.items():
            if subgroup_key not in visible_subgroups:
                label.grid_remove()
        for entry_id, button in self._entry_buttons.items():
            if entry_id not in visible_entries:
                button.grid_remove()

        self._visible_entry_ids = visible_entries
        self._selected_entry_id = view.selected_entry_id
        selected = self.controller.selected_entry(view)
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
            self._set_detail_rows_visible(False)
            self.detail_placeholder.grid(
                row=0,
                column=0,
                sticky="w",
                padx=14,
                pady=18,
            )
            return

        self.detail_placeholder.grid_remove()
        self._set_detail_rows_visible(True)
        for label, value in access_keys_detail_lines(entry):
            _label_widget, value_widget = self._detail_rows[label]
            if value_widget.cget("text") != value:
                value_widget.configure(text=value)

    def close(self) -> None:
        if self._closed:
            return
        self._hide_family_menu()
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
