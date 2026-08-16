"""Explicit case workspace folder planning for Profile/Media Database mode.

V75Q introduces guarded case-workspace creation.  The default is a dry-run
plan: no folder scan, no folder move, no folder rename, no file copy, no
classification, and no sensitive identifier inference.  Real folder creation is
allowed only when the caller passes execute=True and the exact confirmation
phrase CREATE_CASE_WORKSPACE.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable, Sequence

from profile_media_database import (
    build_case_folder_layout,
    build_global_profiles_path,
    sanitize_path_part,
    stable_profile_id,
    utc_now_iso,
)

PROFILE_MEDIA_CASE_WORKSPACE_SCHEMA_VERSION = "profile-media-case-workspace-v75q"
PROFILE_MEDIA_CASE_WORKSPACE_CONFIRMATION = "CREATE_CASE_WORKSPACE"


@dataclass(frozen=True)
class ProfileMediaCaseWorkspaceDirectory:
    """A single explicitly planned directory in a Database/case workspace."""

    label: str
    path: str
    row_type: str
    parent_label: str = ""
    required: bool = True

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class ProfileMediaCaseWorkspacePlan:
    """Dry-run or explicitly executable case-workspace creation plan."""

    database_root: str
    case_title: str
    case_root: str
    directories: tuple[ProfileMediaCaseWorkspaceDirectory, ...]
    execute_requested: bool = False
    confirmation_phrase: str = ""
    plan_id: str = ""
    schema_version: str = PROFILE_MEDIA_CASE_WORKSPACE_SCHEMA_VERSION
    created_at_utc: str = field(default_factory=utc_now_iso)
    folder_scan_performed: bool = False
    folder_move_performed: bool = False
    folder_rename_performed: bool = False
    file_copy_performed: bool = False
    automatic_classification_performed: bool = False
    sensitive_identifier_inference_performed: bool = False

    @property
    def confirmation_valid(self) -> bool:
        return self.confirmation_phrase == PROFILE_MEDIA_CASE_WORKSPACE_CONFIRMATION

    def to_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["directories"] = [directory.to_dict() for directory in self.directories]
        data["confirmation_required"] = self.execute_requested
        data["confirmation_valid"] = self.confirmation_valid
        data["directory_count"] = len(self.directories)
        return data


@dataclass(frozen=True)
class ProfileMediaCaseWorkspaceResult:
    """Result from applying a case-workspace plan."""

    status: str
    plan_id: str
    database_root: str
    case_root: str
    created_directories: tuple[str, ...] = ()
    already_existing_directories: tuple[str, ...] = ()
    blocked_paths: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    schema_version: str = PROFILE_MEDIA_CASE_WORKSPACE_SCHEMA_VERSION
    folder_creation_performed: bool = False
    folder_scan_performed: bool = False
    folder_move_performed: bool = False
    folder_rename_performed: bool = False
    file_copy_performed: bool = False
    automatic_classification_performed: bool = False
    sensitive_identifier_inference_performed: bool = False

    def to_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["created_directory_count"] = len(self.created_directories)
        data["already_existing_directory_count"] = len(self.already_existing_directories)
        data["blocked_path_count"] = len(self.blocked_paths)
        return data


def _dedupe_directories(
    directories: Iterable[ProfileMediaCaseWorkspaceDirectory],
) -> tuple[ProfileMediaCaseWorkspaceDirectory, ...]:
    seen: set[str] = set()
    unique: list[ProfileMediaCaseWorkspaceDirectory] = []
    for directory in directories:
        key = str(Path(directory.path))
        if key in seen:
            continue
        seen.add(key)
        unique.append(directory)
    return tuple(unique)


def build_case_workspace_directories(
    *,
    database_root: str,
    case_title: str,
    case_root: str = "",
) -> tuple[ProfileMediaCaseWorkspaceDirectory, ...]:
    """Return the exact Database/case folder shape without touching the filesystem."""

    root = str(Path(database_root))
    clean_title = sanitize_path_part(case_title, fallback="Untitled Case")
    resolved_case_root = str(Path(case_root)) if case_root else str(Path(root) / "Cases" / clean_title)
    layout = build_case_folder_layout(resolved_case_root)
    return _dedupe_directories(
        (
            ProfileMediaCaseWorkspaceDirectory("Database root", root, "database_root"),
            ProfileMediaCaseWorkspaceDirectory("Profiles", build_global_profiles_path(root), "global_profiles", "Database root"),
            ProfileMediaCaseWorkspaceDirectory(clean_title, layout.case_root, "case", "Database root"),
            ProfileMediaCaseWorkspaceDirectory("Profiles", layout.case_profiles_path, "case_profiles", clean_title),
            ProfileMediaCaseWorkspaceDirectory("People", layout.people_path, "people", clean_title),
            ProfileMediaCaseWorkspaceDirectory("Sources", layout.sources_path, "sources", clean_title),
            ProfileMediaCaseWorkspaceDirectory("Articles", layout.articles_path, "articles", "Sources"),
            ProfileMediaCaseWorkspaceDirectory("Social Media", layout.social_media_path, "social_media", "Sources"),
            ProfileMediaCaseWorkspaceDirectory("Offline", layout.social_media_offline_path, "social_media_offline", "Social Media"),
            ProfileMediaCaseWorkspaceDirectory("Online", layout.social_media_online_path, "social_media_online", "Social Media"),
            ProfileMediaCaseWorkspaceDirectory("Internal Media", layout.internal_media_path, "internal_media", "Sources"),
            ProfileMediaCaseWorkspaceDirectory("Reference Extants", layout.reference_extants_path, "reference_extants", clean_title),
        )
    )


def build_case_workspace_plan(
    *,
    database_root: str,
    case_title: str,
    case_root: str = "",
    execute: bool = False,
    confirmation_phrase: str = "",
) -> ProfileMediaCaseWorkspacePlan:
    """Build a guarded case-workspace plan without scanning folders."""

    clean_title = sanitize_path_part(case_title, fallback="Untitled Case")
    resolved_case_root = str(Path(case_root)) if case_root else str(Path(database_root) / "Cases" / clean_title)
    directories = build_case_workspace_directories(
        database_root=database_root,
        case_title=case_title,
        case_root=resolved_case_root,
    )
    plan_id = stable_profile_id("case_workspace", database_root, clean_title, resolved_case_root)
    return ProfileMediaCaseWorkspacePlan(
        database_root=str(Path(database_root)),
        case_title=clean_title,
        case_root=resolved_case_root,
        directories=directories,
        execute_requested=bool(execute),
        confirmation_phrase=confirmation_phrase,
        plan_id=plan_id,
    )


def render_case_workspace_plan_text(plan: ProfileMediaCaseWorkspacePlan) -> str:
    """Render the planned folder structure in a compact human-readable form."""

    lines = [f"{Path(plan.database_root).name or plan.database_root} [database_root]"]
    for directory in plan.directories:
        path = Path(directory.path)
        if directory.row_type == "database_root":
            continue
        relative_parts: Sequence[str]
        try:
            relative_parts = path.relative_to(plan.database_root).parts
        except Exception:
            relative_parts = path.parts
        depth = max(1, len(relative_parts))
        lines.append(f"{'  ' * depth}{directory.label} [{directory.row_type}]")
    return "\n".join(lines)


def apply_case_workspace_plan(plan: ProfileMediaCaseWorkspacePlan) -> ProfileMediaCaseWorkspaceResult:
    """Apply a plan only when explicitly confirmed; otherwise return dry-run/block."""

    if not plan.execute_requested:
        return ProfileMediaCaseWorkspaceResult(
            status="planned_dry_run",
            plan_id=plan.plan_id,
            database_root=plan.database_root,
            case_root=plan.case_root,
            warnings=("dry_run_no_folders_created",),
        )
    if not plan.confirmation_valid:
        return ProfileMediaCaseWorkspaceResult(
            status="blocked_confirmation_required",
            plan_id=plan.plan_id,
            database_root=plan.database_root,
            case_root=plan.case_root,
            warnings=(f"confirmation_phrase_must_equal:{PROFILE_MEDIA_CASE_WORKSPACE_CONFIRMATION}",),
        )

    created: list[str] = []
    existing: list[str] = []
    blocked: list[str] = []
    for directory in plan.directories:
        path = Path(directory.path)
        if path.exists() and not path.is_dir():
            blocked.append(str(path))
            continue
        if path.exists():
            existing.append(str(path))
            continue
        try:
            path.mkdir(parents=True, exist_ok=True)
            created.append(str(path))
        except Exception:
            blocked.append(str(path))

    if blocked:
        return ProfileMediaCaseWorkspaceResult(
            status="blocked_path_conflict_or_create_error",
            plan_id=plan.plan_id,
            database_root=plan.database_root,
            case_root=plan.case_root,
            created_directories=tuple(created),
            already_existing_directories=tuple(existing),
            blocked_paths=tuple(blocked),
            folder_creation_performed=bool(created),
        )
    return ProfileMediaCaseWorkspaceResult(
        status="created" if created else "already_exists",
        plan_id=plan.plan_id,
        database_root=plan.database_root,
        case_root=plan.case_root,
        created_directories=tuple(created),
        already_existing_directories=tuple(existing),
        folder_creation_performed=bool(created),
    )


def write_case_workspace_plan_json(
    plan: ProfileMediaCaseWorkspacePlan,
    path: str | Path,
    *,
    create_parent: bool = False,
) -> str:
    """Write the plan JSON only to the explicitly requested output path."""

    out = Path(path)
    if create_parent:
        out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(plan.to_dict(), indent=2, sort_keys=True), encoding="utf-8", newline="\n")
    return str(out)


def result_payload(result: ProfileMediaCaseWorkspaceResult, *, plan: ProfileMediaCaseWorkspacePlan | None = None) -> dict[str, Any]:
    """Return CLI-friendly result payload with optional plan summary."""

    payload: dict[str, Any] = result.to_dict()
    if plan is not None:
        payload["plan"] = plan.to_dict()
        payload["plan_text"] = render_case_workspace_plan_text(plan)
    return payload
