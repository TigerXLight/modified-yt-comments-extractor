from __future__ import annotations

from typing import Callable, Optional

import customtkinter as ctk

from access_keys_metadata import (
    AccessEntryKind,
    AccessEntryMetadata,
    AccessKeysCatalog,
    AccessMode,
    ConnectionTestStatus,
    CredentialStatus,
)
from access_keys_view_model import (
    AccessKeysEntryView,
    AccessKeysManagerView,
    build_access_keys_manager_view,
)
from asr_provider_metadata import (
    CREDENTIAL_API_KEY,
    CREDENTIAL_LOCAL_BINARY,
    CREDENTIAL_NONE,
    CREDENTIAL_OAUTH,
    PROVIDER_STATUS_BLOCKED,
    available_asr_provider_metadata,
)
from core.constants import COLORS
from source_adapters import AVAILABLE_SOURCE_ADAPTERS


ACCESS_KEYS_WINDOW_TITLE = "Access & Keys"
ACCESS_KEYS_BUTTON_TEXT = "KEYS"
ALL_FAMILIES_LABEL = "All families"


def _access_mode(
    credential_type: str,
    *,
    local_runtime: bool = False,
) -> AccessMode:
    if local_runtime or credential_type == CREDENTIAL_LOCAL_BINARY:
        return AccessMode.LOCAL_ONLY
    if credential_type == CREDENTIAL_NONE:
        return AccessMode.NO_CREDENTIALS_REQUIRED
    if credential_type == CREDENTIAL_API_KEY:
        return AccessMode.API_KEY
    if credential_type == CREDENTIAL_OAUTH:
        return AccessMode.OAUTH_OR_BROWSER_LOGIN
    return AccessMode.BLOCKED_OR_NOT_CONFIGURED


def _credential_status(
    *,
    credentials_required: bool,
    credentials_optional: bool = False,
    local_runtime: bool = False,
    blocked: bool = False,
) -> CredentialStatus:
    if local_runtime or (not credentials_required and not credentials_optional):
        return CredentialStatus.NOT_NEEDED
    if blocked:
        return CredentialStatus.UNSUPPORTED
    if credentials_required:
        return CredentialStatus.REQUIRED_MISSING
    return CredentialStatus.OPTIONAL


def build_default_access_keys_catalog() -> AccessKeysCatalog:
    entries: list[AccessEntryMetadata] = []

    for provider in available_asr_provider_metadata():
        entries.append(
            AccessEntryMetadata(
                entry_id=f"asr:{provider.provider_id}",
                entry_kind=AccessEntryKind.ASR_PROVIDER,
                display_name=provider.display_name,
                platform_family="ASR providers",
                access_mode=_access_mode(
                    provider.credential_type,
                    local_runtime=provider.local_runtime,
                ),
                credential_status=_credential_status(
                    credentials_required=provider.credentials_required,
                    local_runtime=provider.local_runtime,
                    blocked=provider.access_limitations != ""
                    and provider.status == PROVIDER_STATUS_BLOCKED,
                ),
                implementation_state=(
                    "local runtime metadata"
                    if provider.local_runtime
                    else "provider metadata only"
                ),
                credential_type=provider.credential_type,
                credentials_required=provider.credentials_required,
                supports_connection_test=provider.test_connection_supported,
                project_status=provider.status,
                setup_hint=provider.setup_hint,
                privacy_notes=provider.privacy_notes,
                cost_or_rate_limit_notes=provider.cost_or_rate_limit_notes,
                access_limitations=provider.access_limitations,
                last_test_status=ConnectionTestStatus.TEST_NOT_SUPPORTED,
            )
        )

    for adapter in AVAILABLE_SOURCE_ADAPTERS:
        metadata = adapter.metadata
        capabilities = adapter.capabilities
        entries.append(
            AccessEntryMetadata(
                entry_id=f"source:{adapter.source_name}",
                entry_kind=AccessEntryKind.SOURCE_ADAPTER,
                display_name=metadata.display_name or adapter.source_name,
                platform_family=metadata.platform_family,
                access_mode=_access_mode(metadata.credential_type),
                credential_status=_credential_status(
                    credentials_required=metadata.credentials_required,
                    credentials_optional=metadata.credentials_optional,
                ),
                implementation_state="registered source adapter metadata",
                credential_type=metadata.credential_type,
                credentials_required=metadata.credentials_required,
                credentials_optional=metadata.credentials_optional,
                supports_browser_capture=metadata.supports_browser_capture,
                supports_manual_import=metadata.supports_manual_import,
                supports_connection_test=metadata.test_connection_supported,
                supports_comments=capabilities.supports_comments,
                supports_replies=capabilities.supports_replies,
                supports_live_chat=capabilities.supports_livechat,
                supports_captions_or_transcripts=capabilities.supports_transcripts,
                setup_hint=metadata.setup_hint,
                privacy_notes=metadata.privacy_notes,
                cost_or_rate_limit_notes=metadata.cost_or_rate_limit_notes,
                access_limitations=metadata.access_limitations,
                last_test_status=ConnectionTestStatus.TEST_NOT_SUPPORTED,
            )
        )

    return AccessKeysCatalog(entries=tuple(entries))


class AccessKeysDialogController:
    def __init__(self, catalog: AccessKeysCatalog) -> None:
        self.catalog = catalog
        self.search_query = ""
        self.platform_family = ""
        self.selected_entry_id = ""

    def family_options(self) -> tuple[str, ...]:
        families: list[str] = []
        for entry in self.catalog.entries:
            family = (entry.platform_family or "other").strip() or "other"
            if family not in families:
                families.append(family)
        return (ALL_FAMILIES_LABEL, *families)

    def set_search(self, value: str) -> AccessKeysManagerView:
        self.search_query = value
        return self.view()

    def set_family(self, value: str) -> AccessKeysManagerView:
        self.platform_family = "" if value == ALL_FAMILIES_LABEL else value
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
        )
        self.selected_entry_id = view.selected_entry_id
        return view

    def selected_entry(self) -> Optional[AccessKeysEntryView]:
        view = self.view()
        for section in view.sections:
            for entry in section.entries:
                if entry.selected:
                    return entry
        return None


def access_keys_detail_lines(entry: AccessKeysEntryView) -> tuple[tuple[str, str], ...]:
    capabilities = ", ".join(entry.enabled_capabilities) or "none"
    return (
        ("Name", entry.display_name),
        ("Entry kind", entry.entry_kind.value),
        ("Platform family", entry.platform_family or "other"),
        ("Implementation", entry.implementation_state or "not stated"),
        ("Access mode", entry.access_mode),
        ("Credential status", entry.credential_status),
        ("Credential type", entry.credential_type or "not stated"),
        ("Project status", entry.project_status or "not stated"),
        ("Test status", entry.last_test_status or "not stated"),
        ("Capabilities", capabilities),
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
        on_close: Optional[Callable[[], None]] = None,
    ) -> None:
        super().__init__(parent)
        self._on_close_callback = on_close
        self._closed = False
        self.controller = AccessKeysDialogController(
            catalog or build_default_access_keys_catalog()
        )

        self.title(ACCESS_KEYS_WINDOW_TITLE)
        self.geometry("980x680")
        self.minsize(820, 560)
        self.configure(fg_color=COLORS["bg_dark"])
        self.transient(parent)
        self.protocol("WM_DELETE_WINDOW", self.close)

        self._search_var = ctk.StringVar(value="")
        self._family_var = ctk.StringVar(value=ALL_FAMILIES_LABEL)
        self._build_widgets()
        self._search_var.trace_add("write", self._on_search_changed)
        self._refresh()

    def _build_widgets(self) -> None:
        header = ctk.CTkFrame(self, fg_color=COLORS["bg_card"], corner_radius=0)
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
                "Non-secret access metadata only. This window does not read, store, "
                "reveal, migrate, or test credentials."
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
        self.search_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.family_menu = ctk.CTkOptionMenu(
            filters,
            variable=self._family_var,
            values=list(self.controller.family_options()),
            command=self._on_family_changed,
            width=230,
            height=36,
            fg_color=COLORS["accent_secondary"],
            button_color=COLORS["accent"],
            button_hover_color=COLORS["accent_hover"],
        )
        self.family_menu.grid(row=0, column=1)

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=16, pady=(0, 12))
        body.grid_columnconfigure(0, weight=2)
        body.grid_columnconfigure(1, weight=3)
        body.grid_rowconfigure(0, weight=1)

        self.list_panel = ctk.CTkScrollableFrame(
            body,
            fg_color=COLORS["bg_card"],
            corner_radius=8,
        )
        self.list_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        self.details_panel = ctk.CTkScrollableFrame(
            body,
            fg_color=COLORS["bg_card"],
            corner_radius=8,
        )
        self.details_panel.grid(row=0, column=1, sticky="nsew", padx=(8, 0))

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

    @staticmethod
    def _clear_children(frame: ctk.CTkFrame) -> None:
        for child in frame.winfo_children():
            child.destroy()

    def _on_search_changed(self, *_args: object) -> None:
        self.controller.set_search(self._search_var.get())
        self._refresh()

    def _on_family_changed(self, value: str) -> None:
        self.controller.set_family(value)
        self._refresh()

    def _select_entry(self, entry_id: str) -> None:
        self.controller.select_entry(entry_id)
        self._refresh()

    def _refresh(self) -> None:
        view = self.controller.view()
        self._render_list(view)
        self._render_details(self.controller.selected_entry())

    def _render_list(self, view: AccessKeysManagerView) -> None:
        self._clear_children(self.list_panel)

        for warning in view.warnings:
            ctk.CTkLabel(
                self.list_panel,
                text=warning,
                text_color=COLORS["warning"],
                wraplength=310,
                justify="left",
            ).pack(fill="x", padx=10, pady=(8, 2))

        if view.empty_message:
            ctk.CTkLabel(
                self.list_panel,
                text=view.empty_message,
                text_color=COLORS["text_secondary"],
                wraplength=310,
            ).pack(fill="x", padx=12, pady=20)
            return

        for section in view.sections:
            ctk.CTkLabel(
                self.list_panel,
                text=section.display_name,
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color=COLORS["text_secondary"],
            ).pack(anchor="w", padx=10, pady=(12, 5))
            for entry in section.entries:
                ctk.CTkButton(
                    self.list_panel,
                    text=entry.display_name,
                    anchor="w",
                    command=lambda entry_id=entry.entry_id: self._select_entry(entry_id),
                    fg_color=(
                        COLORS["accent"]
                        if entry.selected
                        else COLORS["accent_secondary"]
                    ),
                    hover_color=COLORS["accent_hover"],
                    text_color=COLORS["text_primary"],
                ).pack(fill="x", padx=10, pady=3)

    def _render_details(self, entry: Optional[AccessKeysEntryView]) -> None:
        self._clear_children(self.details_panel)
        if entry is None:
            ctk.CTkLabel(
                self.details_panel,
                text="Select an access entry to review its non-secret metadata.",
                text_color=COLORS["text_secondary"],
                wraplength=470,
            ).pack(anchor="w", padx=14, pady=18)
            return

        for label, value in access_keys_detail_lines(entry):
            ctk.CTkLabel(
                self.details_panel,
                text=label,
                font=ctk.CTkFont(size=11, weight="bold"),
                text_color=COLORS["text_secondary"],
            ).pack(anchor="w", padx=14, pady=(10, 1))
            ctk.CTkLabel(
                self.details_panel,
                text=value,
                font=ctk.CTkFont(size=12),
                text_color=COLORS["text_primary"],
                wraplength=470,
                justify="left",
            ).pack(anchor="w", fill="x", padx=14)

    def close(self) -> None:
        if self._closed:
            return
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
