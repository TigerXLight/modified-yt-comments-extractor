from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from access_keys_metadata import (
    AccessEntryKind,
    AccessEntryMetadata,
    AccessKeysCatalog,
)


ACCESS_KEYS_VIEW_MODEL_SCOPE = (
    "local non-secret Access & Keys presentation state only; no GUI widgets, "
    "credential values/storage/testing, OAuth, browser-profile access, provider/API "
    "calls, archive execution, source fetching, persistence, or runtime wiring"
)


_CAPABILITY_FIELDS = (
    ("browser_capture", "supports_browser_capture"),
    ("manual_import", "supports_manual_import"),
    ("connection_test", "supports_connection_test"),
    ("comments", "supports_comments"),
    ("replies", "supports_replies"),
    ("live_chat", "supports_live_chat"),
    ("captions_or_transcripts", "supports_captions_or_transcripts"),
    ("visible_text", "supports_visible_text"),
    ("article_text", "supports_article_text"),
    ("screenshot", "supports_screenshot"),
    ("archive_check", "supports_archive_check"),
    ("archive_submit", "supports_archive_submit"),
    ("media_evidence", "supports_media_evidence"),
    ("keyterms", "supports_keyterms"),
    ("custom_vocabulary", "supports_custom_vocabulary"),
    ("phrase_prompts", "supports_phrase_prompts"),
)


def _normalized_text(value: str) -> str:
    return " ".join((value or "").split())


def _enabled_capabilities(entry: AccessEntryMetadata) -> tuple[str, ...]:
    return tuple(
        label
        for label, field_name in _CAPABILITY_FIELDS
        if getattr(entry, field_name)
    )


def _entry_search_text(entry: AccessEntryMetadata) -> str:
    return " ".join(
        (
            entry.entry_id,
            entry.display_name,
            entry.entry_kind.value,
            entry.platform_family,
            entry.access_mode.value,
            entry.credential_status.value,
            entry.implementation_state,
            entry.credential_type,
            entry.project_status,
            entry.setup_hint,
            entry.access_limitations,
            *_enabled_capabilities(entry),
        )
    ).casefold()


@dataclass(frozen=True)
class AccessKeysEntryView:
    entry_id: str
    display_name: str
    entry_kind: AccessEntryKind
    platform_family: str
    implementation_state: str
    access_mode: str
    credential_status: str
    credential_type: str = ""
    project_status: str = ""
    last_test_status: str = ""
    enabled_capabilities: tuple[str, ...] = ()
    setup_hint: str = ""
    privacy_notes: str = ""
    cost_or_rate_limit_notes: str = ""
    access_limitations: str = ""
    selected: bool = False

    def to_dict(self) -> dict[str, object]:
        return {
            "entry_id": self.entry_id,
            "display_name": self.display_name,
            "entry_kind": self.entry_kind.value,
            "platform_family": self.platform_family,
            "implementation_state": self.implementation_state,
            "access_mode": self.access_mode,
            "credential_status": self.credential_status,
            "credential_type": self.credential_type,
            "project_status": self.project_status,
            "last_test_status": self.last_test_status,
            "enabled_capabilities": list(self.enabled_capabilities),
            "setup_hint": self.setup_hint,
            "privacy_notes": self.privacy_notes,
            "cost_or_rate_limit_notes": self.cost_or_rate_limit_notes,
            "access_limitations": self.access_limitations,
            "selected": self.selected,
        }


@dataclass(frozen=True)
class AccessKeysSectionView:
    section_id: str
    display_name: str
    entries: tuple[AccessKeysEntryView, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "section_id": self.section_id,
            "display_name": self.display_name,
            "entry_count": len(self.entries),
            "entries": [entry.to_dict() for entry in self.entries],
        }


@dataclass(frozen=True)
class AccessKeysManagerView:
    window_title: str = "Access & Keys"
    sidebar_button_label: str = "KEYS"
    search_query: str = ""
    entry_kind_filter: str = ""
    platform_family_filter: str = ""
    selected_entry_id: str = ""
    sections: tuple[AccessKeysSectionView, ...] = ()
    visible_entry_count: int = 0
    empty_message: str = ""
    warnings: tuple[str, ...] = ()
    scope: str = ACCESS_KEYS_VIEW_MODEL_SCOPE

    def to_dict(self) -> dict[str, object]:
        return {
            "window_title": self.window_title,
            "sidebar_button_label": self.sidebar_button_label,
            "search_query": self.search_query,
            "entry_kind_filter": self.entry_kind_filter,
            "platform_family_filter": self.platform_family_filter,
            "selected_entry_id": self.selected_entry_id,
            "section_count": len(self.sections),
            "sections": [section.to_dict() for section in self.sections],
            "visible_entry_count": self.visible_entry_count,
            "empty_message": self.empty_message,
            "warnings": list(self.warnings),
            "scope": self.scope,
        }


def _entry_view(
    entry: AccessEntryMetadata,
    *,
    selected_entry_id: str,
) -> AccessKeysEntryView:
    return AccessKeysEntryView(
        entry_id=entry.entry_id,
        display_name=entry.display_name,
        entry_kind=entry.entry_kind,
        platform_family=entry.platform_family,
        implementation_state=entry.implementation_state,
        access_mode=entry.access_mode.value,
        credential_status=entry.credential_status.value,
        credential_type=entry.credential_type,
        project_status=entry.project_status,
        last_test_status=entry.last_test_status.value,
        enabled_capabilities=_enabled_capabilities(entry),
        setup_hint=entry.setup_hint,
        privacy_notes=entry.privacy_notes,
        cost_or_rate_limit_notes=entry.cost_or_rate_limit_notes,
        access_limitations=entry.access_limitations,
        selected=entry.entry_id == selected_entry_id,
    )


def _duplicate_entry_warnings(
    entries: Sequence[AccessEntryMetadata],
) -> tuple[str, ...]:
    seen: set[str] = set()
    warned: set[str] = set()
    warnings: list[str] = []
    for entry in entries:
        if entry.entry_id in seen and entry.entry_id not in warned:
            warnings.append(f"Duplicate access entry ID: {entry.entry_id}")
            warned.add(entry.entry_id)
        seen.add(entry.entry_id)
    return tuple(warnings)


def build_access_keys_manager_view(
    catalog: AccessKeysCatalog,
    *,
    search_query: str = "",
    entry_kind: AccessEntryKind | None = None,
    platform_family: str = "",
    selected_entry_id: str = "",
) -> AccessKeysManagerView:
    normalized_query = _normalized_text(search_query)
    normalized_family = _normalized_text(platform_family)
    requested_selection = _normalized_text(selected_entry_id)

    visible_entries = [
        entry
        for entry in catalog.entries
        if (entry_kind is None or entry.entry_kind is entry_kind)
        and (
            not normalized_family
            or entry.platform_family.casefold() == normalized_family.casefold()
        )
        and (
            not normalized_query
            or normalized_query.casefold() in _entry_search_text(entry)
        )
    ]

    visible_ids = {entry.entry_id for entry in visible_entries}
    resolved_selection = (
        requested_selection if requested_selection in visible_ids else ""
    )
    warnings = list(_duplicate_entry_warnings(catalog.entries))
    if requested_selection and not resolved_selection:
        warnings.append(
            f"Selected access entry is not visible: {requested_selection}"
        )

    grouped: dict[str, list[AccessKeysEntryView]] = {}
    section_names: dict[str, str] = {}
    for entry in visible_entries:
        section_id = _normalized_text(entry.platform_family) or "other"
        section_names.setdefault(section_id, section_id)
        grouped.setdefault(section_id, []).append(
            _entry_view(entry, selected_entry_id=resolved_selection)
        )

    sections = tuple(
        AccessKeysSectionView(
            section_id=section_id,
            display_name=section_names[section_id],
            entries=tuple(entries),
        )
        for section_id, entries in grouped.items()
    )
    visible_count = len(visible_entries)

    return AccessKeysManagerView(
        search_query=normalized_query,
        entry_kind_filter=entry_kind.value if entry_kind is not None else "",
        platform_family_filter=normalized_family,
        selected_entry_id=resolved_selection,
        sections=sections,
        visible_entry_count=visible_count,
        empty_message=(
            "No access entries match the current filters."
            if catalog.entries and not visible_entries
            else "No access entries are available."
            if not catalog.entries
            else ""
        ),
        warnings=tuple(warnings),
    )
