"""Saved view presets for Profile/Media Database mode.

A saved view is a named, user-controlled query preset for the main Database mode
view.  It stores explicit batch JSON paths and query fields; it does not scan
folders or discover cases automatically.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping

from profile_media_database import stable_profile_id, utc_now_iso
from profile_media_database_session import (
    PROFILE_MEDIA_DATABASE_SESSION_SCHEMA_VERSION,
    ProfileMediaDatabaseSessionConfig,
    database_session_config_from_mapping,
)

PROFILE_MEDIA_DATABASE_SAVED_VIEWS_SCHEMA_VERSION = "profile-media-database-saved-views-v75z"


@dataclass(frozen=True)
class ProfileMediaSavedView:
    """A named query preset for the Database mode main view."""

    name: str
    config: ProfileMediaDatabaseSessionConfig
    view_id: str = ""
    description: str = ""
    created_at_utc: str = field(default_factory=utc_now_iso)
    updated_at_utc: str = field(default_factory=utc_now_iso)
    schema_version: str = PROFILE_MEDIA_DATABASE_SAVED_VIEWS_SCHEMA_VERSION
    folder_scan_performed: bool = False
    folder_move_performed: bool = False
    folder_rename_performed: bool = False
    file_copy_performed: bool = False
    media_download_performed: bool = False
    automatic_classification_performed: bool = False
    sensitive_identifier_inference_performed: bool = False

    def normalized(self) -> "ProfileMediaSavedView":
        clean_name = (self.name or "Untitled Database View").strip() or "Untitled Database View"
        view_id = self.view_id or stable_profile_id("saved_view", clean_name)
        return ProfileMediaSavedView(
            name=clean_name,
            description=str(self.description or ""),
            config=self.config,
            view_id=view_id,
            created_at_utc=self.created_at_utc,
            updated_at_utc=utc_now_iso(),
        )

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self.normalized())
        data["config"] = self.config.to_dict()
        return data


@dataclass(frozen=True)
class ProfileMediaSavedViewLibrary:
    """A small collection of saved Database-mode views."""

    views: tuple[ProfileMediaSavedView, ...] = ()
    schema_version: str = PROFILE_MEDIA_DATABASE_SAVED_VIEWS_SCHEMA_VERSION
    created_at_utc: str = field(default_factory=utc_now_iso)
    updated_at_utc: str = field(default_factory=utc_now_iso)
    folder_scan_performed: bool = False
    folder_move_performed: bool = False
    folder_rename_performed: bool = False
    file_copy_performed: bool = False
    media_download_performed: bool = False
    automatic_classification_performed: bool = False
    sensitive_identifier_inference_performed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "created_at_utc": self.created_at_utc,
            "updated_at_utc": self.updated_at_utc,
            "view_count": len(self.views),
            "views": [view.to_dict() for view in self.views],
            "folder_scan_performed": self.folder_scan_performed,
            "folder_move_performed": self.folder_move_performed,
            "folder_rename_performed": self.folder_rename_performed,
            "file_copy_performed": self.file_copy_performed,
            "media_download_performed": self.media_download_performed,
            "automatic_classification_performed": self.automatic_classification_performed,
            "sensitive_identifier_inference_performed": self.sensitive_identifier_inference_performed,
        }


def saved_view_from_mapping(payload: Mapping[str, Any]) -> ProfileMediaSavedView:
    """Create a saved view from JSON-like data."""

    config_payload = payload.get("config") if isinstance(payload.get("config"), Mapping) else payload
    return ProfileMediaSavedView(
        name=str(payload.get("name", "Untitled Database View") or "Untitled Database View"),
        description=str(payload.get("description", "") or ""),
        view_id=str(payload.get("view_id", "") or ""),
        config=database_session_config_from_mapping(config_payload),
        created_at_utc=str(payload.get("created_at_utc", utc_now_iso()) or utc_now_iso()),
        updated_at_utc=str(payload.get("updated_at_utc", utc_now_iso()) or utc_now_iso()),
    ).normalized()


def saved_view_library_from_mapping(payload: Mapping[str, Any] | None) -> ProfileMediaSavedViewLibrary:
    """Create a saved view library from JSON-like data."""

    if not isinstance(payload, Mapping):
        return ProfileMediaSavedViewLibrary()
    raw_views = payload.get("views", ())
    views: list[ProfileMediaSavedView] = []
    if isinstance(raw_views, Iterable) and not isinstance(raw_views, (str, bytes, Mapping)):
        for item in raw_views:
            if isinstance(item, Mapping):
                views.append(saved_view_from_mapping(item))
    return ProfileMediaSavedViewLibrary(
        views=tuple(views),
        created_at_utc=str(payload.get("created_at_utc", utc_now_iso()) or utc_now_iso()),
        updated_at_utc=str(payload.get("updated_at_utc", utc_now_iso()) or utc_now_iso()),
    )


def load_saved_view_library(path: str | Path) -> ProfileMediaSavedViewLibrary:
    """Load saved views from an explicit JSON file path."""

    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError:
        return ProfileMediaSavedViewLibrary()
    if not isinstance(payload, Mapping):
        return ProfileMediaSavedViewLibrary()
    return saved_view_library_from_mapping(payload)


def save_saved_view_library(path: str | Path, library: ProfileMediaSavedViewLibrary) -> str:
    """Persist saved views to an explicit JSON file path."""

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(library.to_dict(), indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    return str(target)


def upsert_saved_view(library: ProfileMediaSavedViewLibrary, view: ProfileMediaSavedView) -> ProfileMediaSavedViewLibrary:
    """Add or replace a saved view by stable ID."""

    normalized = view.normalized()
    retained = [existing for existing in library.views if existing.normalized().view_id != normalized.view_id]
    retained.append(normalized)
    retained.sort(key=lambda item: item.name.lower())
    return ProfileMediaSavedViewLibrary(views=tuple(retained), created_at_utc=library.created_at_utc, updated_at_utc=utc_now_iso())


def remove_saved_view(library: ProfileMediaSavedViewLibrary, view_id_or_name: str) -> ProfileMediaSavedViewLibrary:
    """Remove a saved view by ID or case-insensitive name."""

    needle = str(view_id_or_name or "").strip().lower()
    retained = [
        view for view in library.views
        if view.normalized().view_id.lower() != needle and view.name.lower() != needle
    ]
    return ProfileMediaSavedViewLibrary(views=tuple(retained), created_at_utc=library.created_at_utc, updated_at_utc=utc_now_iso())


def render_saved_view_library_text(library: ProfileMediaSavedViewLibrary) -> str:
    """Render saved views for CLI proof and future UI diagnostics."""

    lines = [
        "Profile/Media Saved Database Views",
        f"View count: {len(library.views)}",
        "Folder scan performed: false",
        "Folder move performed: false",
        "Folder rename performed: false",
        "File copy performed: false",
        "Media download performed: false",
        "Automatic classification performed: false",
        "Sensitive identifier inference performed: false",
    ]
    if not library.views:
        lines.append("- none")
    for view in library.views:
        normalized = view.normalized()
        query = normalized.config.query_kwargs()
        active = ", ".join(f"{k}={v}" for k, v in sorted(query.items()) if v not in ("", None, 0)) or "no query"
        lines.append(f"- {normalized.name} [{normalized.view_id}] {active}")
    return "\n".join(lines)
