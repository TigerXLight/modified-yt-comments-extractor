from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Iterable, Mapping

from profile_media_database import (
    PROFILE_MEDIA_DATABASE_SCHEMA_VERSION,
    ProfileMediaDatabaseManifest,
    ProfileMediaTreeRow,
    build_database_tree_rows,
    render_database_tree_text,
    utc_now_iso,
)


PROFILE_MEDIA_DATABASE_VIEW_MODEL_SCHEMA_VERSION = "profile-media-database-view-model-v75h"


class ProfileMediaViewMode(str, Enum):
    FILES = "FILES"
    DATABASE = "DATABASE"

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class ProfileMediaDatabaseViewState:
    """Lightweight UI-neutral state for the future Files/Database toggle.

    This is deliberately a view model only. It does not scan folders, create
    folders, move folders, rename folders, classify records, fetch sources, or
    infer sensitive identifiers. GUI code can render this state beside or above
    the existing FILES panel without taking filesystem action.
    """

    mode: ProfileMediaViewMode
    rows: tuple[ProfileMediaTreeRow, ...] = ()
    visible_rows: tuple[ProfileMediaTreeRow, ...] = ()
    selected_row_id: str = ""
    query: str = ""
    tree_preview: str = ""
    row_type_counts: Mapping[str, int] = field(default_factory=dict)
    database_schema_version: str = PROFILE_MEDIA_DATABASE_SCHEMA_VERSION
    schema_version: str = PROFILE_MEDIA_DATABASE_VIEW_MODEL_SCHEMA_VERSION
    folder_scan_performed: bool = False
    folder_creation_performed: bool = False
    file_move_performed: bool = False
    sensitive_identifier_inference_performed: bool = False
    created_at_utc: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> dict[str, object]:
        return {
            "created_at_utc": self.created_at_utc,
            "database_schema_version": self.database_schema_version,
            "file_move_performed": self.file_move_performed,
            "folder_creation_performed": self.folder_creation_performed,
            "folder_scan_performed": self.folder_scan_performed,
            "mode": self.mode.value,
            "query": self.query,
            "row_count": len(self.rows),
            "row_type_counts": dict(self.row_type_counts),
            "schema_version": self.schema_version,
            "selected_row_id": self.selected_row_id,
            "sensitive_identifier_inference_performed": self.sensitive_identifier_inference_performed,
            "tree_preview": self.tree_preview,
            "visible_row_count": len(self.visible_rows),
            "visible_rows": [row.to_dict() for row in self.visible_rows],
        }


def coerce_profile_media_view_mode(value: ProfileMediaViewMode | str | None) -> ProfileMediaViewMode:
    if value is None:
        return ProfileMediaViewMode.FILES
    if isinstance(value, ProfileMediaViewMode):
        return value
    normalized = str(value).strip().upper()
    if normalized in {"DATABASE", "DB", "PROFILE_DATABASE", "PROFILE MEDIA DATABASE"}:
        return ProfileMediaViewMode.DATABASE
    if normalized in {"FILES", "FILE", "FILE_BROWSER"}:
        return ProfileMediaViewMode.FILES
    raise ValueError(f"Unsupported profile/media view mode: {value!r}")


def toggle_profile_media_view_mode(value: ProfileMediaViewMode | str | None) -> ProfileMediaViewMode:
    mode = coerce_profile_media_view_mode(value)
    return ProfileMediaViewMode.DATABASE if mode == ProfileMediaViewMode.FILES else ProfileMediaViewMode.FILES


def count_tree_rows_by_type(rows: Iterable[ProfileMediaTreeRow]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        counts[row.row_type] = counts.get(row.row_type, 0) + 1
    return dict(sorted(counts.items()))


def filter_database_tree_rows(rows: Iterable[ProfileMediaTreeRow], query: str = "") -> tuple[ProfileMediaTreeRow, ...]:
    """Return rows matching query plus their ancestors for tree context."""

    all_rows = tuple(rows)
    normalized = query.strip().casefold()
    if not normalized:
        return all_rows

    by_id = {row.row_id: row for row in all_rows}
    keep_ids: set[str] = set()

    def include_ancestors(row: ProfileMediaTreeRow) -> None:
        current = row
        while current.row_id and current.row_id not in keep_ids:
            keep_ids.add(current.row_id)
            if not current.parent_row_id:
                break
            parent = by_id.get(current.parent_row_id)
            if parent is None:
                break
            current = parent

    for row in all_rows:
        haystack = " ".join(
            (
                row.label,
                row.path,
                row.row_type,
                row.case_title,
                row.source_bucket,
            )
        ).casefold()
        if normalized in haystack:
            include_ancestors(row)

    return tuple(row for row in all_rows if row.row_id in keep_ids)


def select_database_tree_row(
    rows: Iterable[ProfileMediaTreeRow],
    selected_row_id: str = "",
) -> str:
    all_rows = tuple(rows)
    if not all_rows:
        return ""
    if selected_row_id and any(row.row_id == selected_row_id for row in all_rows):
        return selected_row_id
    return all_rows[0].row_id


def build_profile_media_database_view_state(
    manifest: ProfileMediaDatabaseManifest,
    mode: ProfileMediaViewMode | str = ProfileMediaViewMode.DATABASE,
    query: str = "",
    selected_row_id: str = "",
) -> ProfileMediaDatabaseViewState:
    view_mode = coerce_profile_media_view_mode(mode)
    rows = build_database_tree_rows(manifest) if view_mode == ProfileMediaViewMode.DATABASE else ()
    visible_rows = filter_database_tree_rows(rows, query) if rows else ()
    selected = select_database_tree_row(visible_rows, selected_row_id)
    return ProfileMediaDatabaseViewState(
        mode=view_mode,
        rows=tuple(rows),
        visible_rows=tuple(visible_rows),
        selected_row_id=selected,
        query=query,
        tree_preview=render_database_tree_text(visible_rows) if visible_rows else "",
        row_type_counts=count_tree_rows_by_type(rows),
    )
