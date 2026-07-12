from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from access_keys_catalog import AccessKeysEntryLayout
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


def _fallback_layout(
    entry: AccessEntryMetadata,
    *,
    original_index: int,
) -> AccessKeysEntryLayout:
    section_id = _normalized_text(entry.platform_family) or "other"
    return AccessKeysEntryLayout(
        entry_id=entry.entry_id,
        section_id=section_id,
        section_label=section_id,
        section_order=original_index,
        subgroup_id="",
        subgroup_label="",
        subgroup_order=0,
        entry_order=original_index,
        canonical_name=entry.display_name,
    )


def _layout_map(
    entries: Sequence[AccessEntryMetadata],
    layouts: Sequence[AccessKeysEntryLayout],
) -> dict[str, AccessKeysEntryLayout]:
    result = {layout.entry_id: layout for layout in layouts}
    for index, entry in enumerate(entries):
        result.setdefault(
            entry.entry_id,
            _fallback_layout(entry, original_index=index),
        )
    return result


def _entry_search_text(
    entry: AccessEntryMetadata,
    layout: AccessKeysEntryLayout,
) -> str:
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
            entry.privacy_notes,
            entry.cost_or_rate_limit_notes,
            entry.access_limitations,
            layout.section_id,
            layout.section_label,
            layout.subgroup_id,
            layout.subgroup_label,
            layout.canonical_name,
            *layout.aliases,
            *layout.tags,
            *layout.planned_capabilities,
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
    section_id: str = ""
    section_label: str = ""
    subgroup_id: str = ""
    subgroup_label: str = ""
    planned_capabilities: tuple[str, ...] = ()
    aliases: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()
    canonical_name: str = ""
    planned_only: bool = False

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
            "section_id": self.section_id,
            "section_label": self.section_label,
            "subgroup_id": self.subgroup_id,
            "subgroup_label": self.subgroup_label,
            "planned_capabilities": list(self.planned_capabilities),
            "aliases": list(self.aliases),
            "tags": list(self.tags),
            "canonical_name": self.canonical_name,
            "planned_only": self.planned_only,
        }


@dataclass(frozen=True)
class AccessKeysSubgroupView:
    subgroup_id: str
    display_name: str
    entries: tuple[AccessKeysEntryView, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "subgroup_id": self.subgroup_id,
            "display_name": self.display_name,
            "entry_count": len(self.entries),
            "entries": [entry.to_dict() for entry in self.entries],
        }


@dataclass(frozen=True)
class AccessKeysSectionView:
    section_id: str
    display_name: str
    entries: tuple[AccessKeysEntryView, ...] = ()
    subgroups: tuple[AccessKeysSubgroupView, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "section_id": self.section_id,
            "display_name": self.display_name,
            "entry_count": len(self.entries),
            "entries": [entry.to_dict() for entry in self.entries],
            "subgroup_count": len(self.subgroups),
            "subgroups": [subgroup.to_dict() for subgroup in self.subgroups],
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
    layout: AccessKeysEntryLayout,
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
        section_id=layout.section_id,
        section_label=layout.section_label,
        subgroup_id=layout.subgroup_id,
        subgroup_label=layout.subgroup_label,
        planned_capabilities=layout.planned_capabilities,
        aliases=layout.aliases,
        tags=layout.tags,
        canonical_name=layout.canonical_name or entry.display_name,
        planned_only=entry.implementation_state == "planned metadata only",
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


def _duplicate_layout_warnings(
    layouts: Sequence[AccessKeysEntryLayout],
) -> tuple[str, ...]:
    seen: set[str] = set()
    warned: set[str] = set()
    warnings: list[str] = []
    for layout in layouts:
        if layout.entry_id in seen and layout.entry_id not in warned:
            warnings.append(f"Duplicate access layout ID: {layout.entry_id}")
            warned.add(layout.entry_id)
        seen.add(layout.entry_id)
    return tuple(warnings)


def _family_matches(
    layout: AccessKeysEntryLayout,
    entry: AccessEntryMetadata,
    normalized_family: str,
) -> bool:
    if not normalized_family:
        return True
    target = normalized_family.casefold()
    return target in {
        layout.section_id.casefold(),
        layout.section_label.casefold(),
        entry.platform_family.casefold(),
    }


def build_access_keys_manager_view(
    catalog: AccessKeysCatalog,
    *,
    search_query: str = "",
    entry_kind: AccessEntryKind | None = None,
    platform_family: str = "",
    selected_entry_id: str = "",
    layouts: Sequence[AccessKeysEntryLayout] = (),
) -> AccessKeysManagerView:
    normalized_query = _normalized_text(search_query)
    normalized_family = _normalized_text(platform_family)
    requested_selection = _normalized_text(selected_entry_id)

    layout_by_id = _layout_map(catalog.entries, layouts)
    indexed_entries = list(enumerate(catalog.entries))
    visible_pairs = [
        (index, entry, layout_by_id[entry.entry_id])
        for index, entry in indexed_entries
        if (entry_kind is None or entry.entry_kind is entry_kind)
        and _family_matches(
            layout_by_id[entry.entry_id],
            entry,
            normalized_family,
        )
        and (
            not normalized_query
            or normalized_query.casefold()
            in _entry_search_text(entry, layout_by_id[entry.entry_id])
        )
    ]
    visible_pairs.sort(
        key=lambda item: (
            item[2].section_order,
            item[2].subgroup_order,
            item[2].entry_order,
            item[0],
            item[1].display_name.casefold(),
        )
    )

    visible_ids = {entry.entry_id for _, entry, _ in visible_pairs}
    resolved_selection = (
        requested_selection if requested_selection in visible_ids else ""
    )

    warnings = list(_duplicate_entry_warnings(catalog.entries))
    warnings.extend(_duplicate_layout_warnings(layouts))
    if requested_selection and not resolved_selection:
        warnings.append(
            f"Selected access entry is not visible: {requested_selection}"
        )

    section_order: list[str] = []
    section_labels: dict[str, str] = {}
    section_entries: dict[str, list[AccessKeysEntryView]] = {}
    subgroup_order: dict[str, list[str]] = {}
    subgroup_labels: dict[tuple[str, str], str] = {}
    subgroup_entries: dict[tuple[str, str], list[AccessKeysEntryView]] = {}

    for _, entry, layout in visible_pairs:
        section_id = layout.section_id or "other"
        if section_id not in section_order:
            section_order.append(section_id)
        section_labels.setdefault(
            section_id,
            layout.section_label or section_id,
        )
        entry_view = _entry_view(
            entry,
            layout,
            selected_entry_id=resolved_selection,
        )
        section_entries.setdefault(section_id, []).append(entry_view)

        subgroup_id = layout.subgroup_id
        if subgroup_id:
            subgroup_order.setdefault(section_id, [])
            if subgroup_id not in subgroup_order[section_id]:
                subgroup_order[section_id].append(subgroup_id)
            subgroup_labels.setdefault(
                (section_id, subgroup_id),
                layout.subgroup_label or subgroup_id,
            )
            subgroup_entries.setdefault((section_id, subgroup_id), []).append(
                entry_view
            )

    sections = tuple(
        AccessKeysSectionView(
            section_id=section_id,
            display_name=section_labels[section_id],
            entries=tuple(section_entries.get(section_id, ())),
            subgroups=tuple(
                AccessKeysSubgroupView(
                    subgroup_id=subgroup_id,
                    display_name=subgroup_labels[(section_id, subgroup_id)],
                    entries=tuple(
                        subgroup_entries.get((section_id, subgroup_id), ())
                    ),
                )
                for subgroup_id in subgroup_order.get(section_id, ())
            ),
        )
        for section_id in section_order
    )

    visible_count = len(visible_pairs)
    return AccessKeysManagerView(
        search_query=normalized_query,
        entry_kind_filter=entry_kind.value if entry_kind is not None else "",
        platform_family_filter=normalized_family,
        selected_entry_id=resolved_selection,
        sections=sections,
        visible_entry_count=visible_count,
        empty_message=(
            "No access entries match the current filters."
            if catalog.entries and not visible_pairs
            else "No access entries are available."
            if not catalog.entries
            else ""
        ),
        warnings=tuple(warnings),
    )
