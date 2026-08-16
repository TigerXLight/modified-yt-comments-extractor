"""Session and export planning for Profile/Media Database mode.

V75Z combines the V75W index, V75X search, and V75Y Database-mode view into a
single UI-neutral session snapshot.  It also adds guarded export planning for a
Database-mode view.  This is intended for the main Database mode area, not for a
sidebar preview or sidebar filter.

This module only consumes explicit batch JSON paths supplied by the caller.  It
does not scan folders, create case workspaces, move folders, rename folders,
copy media, download media, classify automatically, or infer sensitive
identifiers.  Export writes are disabled by default and require an explicit
confirmation phrase.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from profile_media_database import sanitize_path_part, utc_now_iso
from profile_media_database_mode import (
    ProfileMediaDatabaseModeView,
    build_database_mode_view_from_batch_json_files,
    database_mode_payload,
    render_database_mode_view_text,
)
from profile_media_database_runtime import build_profile_media_runtime_state
from profile_media_database_search import ProfileMediaDatabaseSearchQuery

PROFILE_MEDIA_DATABASE_SESSION_SCHEMA_VERSION = "profile-media-database-session-v75z"
PROFILE_MEDIA_DATABASE_EXPORT_SCHEMA_VERSION = "profile-media-database-export-v75z"
PROFILE_MEDIA_DATABASE_EXPORT_CONFIRMATION = "EXPORT_PROFILE_MEDIA_DATABASE_VIEW"

_QUERY_KEYS = (
    "profile_name",
    "case_title",
    "source_bucket",
    "source_role",
    "claim_basis",
    "currentness_status",
    "text",
    "source_chain_gap",
    "disputed_framing",
    "has_parser_warnings",
    "limit",
)


@dataclass(frozen=True)
class ProfileMediaDatabaseSessionConfig:
    """Configuration for a read-only Database-mode session."""

    database_root: str = ""
    batch_json_files: tuple[str, ...] = ()
    mode: str = "DATABASE"
    profile_name: str = ""
    case_title: str = ""
    source_bucket: str = ""
    source_role: str = ""
    claim_basis: str = ""
    currentness_status: str = ""
    text: str = ""
    source_chain_gap: bool | None = None
    disputed_framing: bool | None = None
    has_parser_warnings: bool | None = None
    limit: int = 0
    schema_version: str = PROFILE_MEDIA_DATABASE_SESSION_SCHEMA_VERSION

    def query_kwargs(self) -> dict[str, Any]:
        return {key: getattr(self, key) for key in _QUERY_KEYS}

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ProfileMediaDatabaseSessionSnapshot:
    """Read-only session state used by the future main Database-mode UI."""

    config: ProfileMediaDatabaseSessionConfig
    runtime_state: Mapping[str, Any]
    mode_view: ProfileMediaDatabaseModeView | None = None
    status: str = "success"
    created_at_utc: str = field(default_factory=utc_now_iso)
    schema_version: str = PROFILE_MEDIA_DATABASE_SESSION_SCHEMA_VERSION
    folder_scan_performed: bool = False
    folder_creation_performed: bool = False
    folder_move_performed: bool = False
    folder_rename_performed: bool = False
    file_copy_performed: bool = False
    file_write_performed: bool = False
    media_download_performed: bool = False
    automatic_classification_performed: bool = False
    sensitive_identifier_inference_performed: bool = False
    warnings: tuple[str, ...] = ()

    def to_dict(self, *, include_view_text: bool = False) -> dict[str, Any]:
        mode_view_payload: dict[str, Any] | None = None
        if self.mode_view is not None:
            mode_view_payload = database_mode_payload(self.mode_view, include_text=include_view_text)
        return {
            "schema_version": self.schema_version,
            "created_at_utc": self.created_at_utc,
            "status": self.status,
            "config": self.config.to_dict(),
            "runtime_state": dict(self.runtime_state),
            "mode_view": mode_view_payload,
            "batch_json_files": list(self.config.batch_json_files),
            "mode": self.config.mode,
            "database_root": self.config.database_root,
            "index_case_count": self.mode_view.search_result.index_case_count if self.mode_view else 0,
            "index_source_count": self.mode_view.search_result.index_source_count if self.mode_view else 0,
            "index_profile_row_count": self.mode_view.search_result.index_profile_row_count if self.mode_view else 0,
            "matched_source_count": len(self.mode_view.search_result.matched_sources) if self.mode_view else 0,
            "matched_profile_count": len(self.mode_view.search_result.matched_profiles) if self.mode_view else 0,
            "folder_scan_performed": self.folder_scan_performed,
            "folder_creation_performed": self.folder_creation_performed,
            "folder_move_performed": self.folder_move_performed,
            "folder_rename_performed": self.folder_rename_performed,
            "file_copy_performed": self.file_copy_performed,
            "file_write_performed": self.file_write_performed,
            "media_download_performed": self.media_download_performed,
            "automatic_classification_performed": self.automatic_classification_performed,
            "sensitive_identifier_inference_performed": self.sensitive_identifier_inference_performed,
            "warnings": list(self.warnings),
            "warning_count": len(self.warnings),
        }


@dataclass(frozen=True)
class ProfileMediaDatabaseExportPlan:
    """Dry-run or explicitly executable export plan for a Database-mode view."""

    output_dir: str
    json_path: str
    text_path: str
    summary_json_path: str
    execute_requested: bool = False
    confirmation_phrase: str = ""
    schema_version: str = PROFILE_MEDIA_DATABASE_EXPORT_SCHEMA_VERSION
    created_at_utc: str = field(default_factory=utc_now_iso)
    folder_scan_performed: bool = False
    folder_move_performed: bool = False
    folder_rename_performed: bool = False
    file_copy_performed: bool = False
    media_download_performed: bool = False
    automatic_classification_performed: bool = False
    sensitive_identifier_inference_performed: bool = False

    @property
    def confirmation_valid(self) -> bool:
        return self.confirmation_phrase == PROFILE_MEDIA_DATABASE_EXPORT_CONFIRMATION

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["confirmation_required"] = self.execute_requested
        data["confirmation_valid"] = self.confirmation_valid
        data["confirmation_phrase_expected"] = PROFILE_MEDIA_DATABASE_EXPORT_CONFIRMATION if self.execute_requested else ""
        return data


@dataclass(frozen=True)
class ProfileMediaDatabaseExportResult:
    """Result of applying a guarded Database-mode view export plan."""

    status: str
    output_dir: str
    written_files: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    schema_version: str = PROFILE_MEDIA_DATABASE_EXPORT_SCHEMA_VERSION
    folder_creation_performed: bool = False
    folder_scan_performed: bool = False
    folder_move_performed: bool = False
    folder_rename_performed: bool = False
    file_copy_performed: bool = False
    file_write_performed: bool = False
    media_download_performed: bool = False
    automatic_classification_performed: bool = False
    sensitive_identifier_inference_performed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "status": self.status,
            "output_dir": self.output_dir,
            "written_files": list(self.written_files),
            "written_file_count": len(self.written_files),
            "warnings": list(self.warnings),
            "warning_count": len(self.warnings),
            "folder_creation_performed": self.folder_creation_performed,
            "folder_scan_performed": self.folder_scan_performed,
            "folder_move_performed": self.folder_move_performed,
            "folder_rename_performed": self.folder_rename_performed,
            "file_copy_performed": self.file_copy_performed,
            "file_write_performed": self.file_write_performed,
            "media_download_performed": self.media_download_performed,
            "automatic_classification_performed": self.automatic_classification_performed,
            "sensitive_identifier_inference_performed": self.sensitive_identifier_inference_performed,
        }


def _coerce_bool_or_none(value: Any) -> bool | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"any", "none", "null", ""}:
        return None
    if text in {"1", "true", "yes", "y", "on"}:
        return True
    if text in {"0", "false", "no", "n", "off"}:
        return False
    raise ValueError(f"expected boolean/any value, got {value!r}")


def _coerce_limit(value: Any) -> int:
    try:
        parsed = int(value or 0)
    except Exception:
        return 0
    return max(0, parsed)


def normalize_batch_json_files(paths: Iterable[str | Path]) -> tuple[str, ...]:
    """Normalize explicit batch paths without discovering or scanning folders."""

    normalized: list[str] = []
    for path in paths:
        text = str(path).strip()
        if not text:
            continue
        candidate = str(Path(text))
        if candidate not in normalized:
            normalized.append(candidate)
    return tuple(normalized)


def database_session_config_from_mapping(payload: Mapping[str, Any]) -> ProfileMediaDatabaseSessionConfig:
    """Build a session config from a JSON-style mapping."""

    batch_files = payload.get("batch_json_files", payload.get("batch_json", ()))
    if isinstance(batch_files, (str, Path)):
        batch_paths: Sequence[str | Path] = (batch_files,)
    else:
        batch_paths = tuple(batch_files or ())
    return ProfileMediaDatabaseSessionConfig(
        database_root=str(payload.get("database_root", "") or ""),
        batch_json_files=normalize_batch_json_files(batch_paths),
        mode=str(payload.get("mode", "DATABASE") or "DATABASE").upper(),
        profile_name=str(payload.get("profile_name", "") or ""),
        case_title=str(payload.get("case_title", "") or ""),
        source_bucket=str(payload.get("source_bucket", "") or ""),
        source_role=str(payload.get("source_role", "") or ""),
        claim_basis=str(payload.get("claim_basis", "") or ""),
        currentness_status=str(payload.get("currentness_status", "") or ""),
        text=str(payload.get("text", "") or ""),
        source_chain_gap=_coerce_bool_or_none(payload.get("source_chain_gap")),
        disputed_framing=_coerce_bool_or_none(payload.get("disputed_framing")),
        has_parser_warnings=_coerce_bool_or_none(payload.get("has_parser_warnings")),
        limit=_coerce_limit(payload.get("limit", 0)),
    )


def load_database_session_config(path: str | Path) -> ProfileMediaDatabaseSessionConfig:
    """Load a session config from an explicit JSON file."""

    with Path(path).open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError("Database session config root must be an object")
    return database_session_config_from_mapping(payload)


def write_database_session_config(path: str | Path, config: ProfileMediaDatabaseSessionConfig) -> str:
    """Write a user-requested session config JSON file."""

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(config.to_dict(), indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    return str(target)


def build_database_session_snapshot(config: ProfileMediaDatabaseSessionConfig) -> ProfileMediaDatabaseSessionSnapshot:
    """Build a read-only Database mode session snapshot from explicit batch JSON files."""

    runtime_state = asdict(build_profile_media_runtime_state(config.mode))
    mode = str(config.mode or "FILES").upper()
    warnings: list[str] = []
    mode_view: ProfileMediaDatabaseModeView | None = None
    status = "success"
    if mode == "DATABASE":
        if not config.batch_json_files:
            status = "no_batch_json_files"
            warnings.append("database_mode_requires_explicit_batch_json_files")
        else:
            mode_view = build_database_mode_view_from_batch_json_files(config.batch_json_files, **config.query_kwargs())
            warnings.extend(mode_view.warnings)
    elif mode == "FILES":
        status = "files_mode_passthrough"
        warnings.append("database_view_not_built_in_files_mode")
    else:
        status = "unknown_mode"
        warnings.append(f"unknown_mode:{mode}")
    return ProfileMediaDatabaseSessionSnapshot(
        config=config,
        runtime_state=runtime_state,
        mode_view=mode_view,
        status=status,
        warnings=tuple(warnings),
    )


def render_database_session_text(snapshot: ProfileMediaDatabaseSessionSnapshot) -> str:
    """Render a compact text summary for logs, CLI smoke tests, and future UI status."""

    data = snapshot.to_dict(include_view_text=False)
    lines = [
        "Profile/Media Database Session",
        f"Status: {snapshot.status}",
        f"Mode: {snapshot.config.mode}",
        f"Database root: {snapshot.config.database_root}",
        f"Batch JSON files: {len(snapshot.config.batch_json_files)}",
        f"Index cases: {data['index_case_count']}",
        f"Index sources: {data['index_source_count']}",
        f"Index profile rows: {data['index_profile_row_count']}",
        f"Matched sources: {data['matched_source_count']}",
        f"Matched profiles: {data['matched_profile_count']}",
        "Folder scan performed: false",
        "Folder creation performed: false",
        "Folder move performed: false",
        "Folder rename performed: false",
        "File copy performed: false",
        "File write performed: false",
        "Media download performed: false",
        "Automatic classification performed: false",
        "Sensitive identifier inference performed: false",
    ]
    active_query = {key: value for key, value in snapshot.config.query_kwargs().items() if value not in ("", None, 0)}
    if active_query:
        lines.extend(["", "Active query:"])
        for key, value in sorted(active_query.items()):
            lines.append(f"- {key}: {value}")
    if snapshot.mode_view is not None:
        lines.extend(["", render_database_mode_view_text(snapshot.mode_view)])
    if snapshot.warnings:
        lines.extend(["", "Warnings:"])
        lines.extend(f"- {warning}" for warning in snapshot.warnings)
    return "\n".join(lines)


def build_database_export_plan(
    output_dir: str | Path,
    *,
    execute: bool = False,
    confirmation_phrase: str = "",
    basename: str = "database_mode_view",
) -> ProfileMediaDatabaseExportPlan:
    """Plan a guarded export of a Database-mode session/view."""

    base = sanitize_path_part(basename or "database_mode_view", fallback="database_mode_view")
    root = Path(output_dir)
    return ProfileMediaDatabaseExportPlan(
        output_dir=str(root),
        json_path=str(root / f"{base}.json"),
        text_path=str(root / f"{base}.txt"),
        summary_json_path=str(root / f"{base}_summary.json"),
        execute_requested=bool(execute),
        confirmation_phrase=confirmation_phrase,
    )


def apply_database_export_plan(
    plan: ProfileMediaDatabaseExportPlan,
    snapshot: ProfileMediaDatabaseSessionSnapshot,
) -> ProfileMediaDatabaseExportResult:
    """Apply a guarded export plan.  Default behavior is dry-run only."""

    if not plan.execute_requested:
        return ProfileMediaDatabaseExportResult(
            status="planned_dry_run",
            output_dir=plan.output_dir,
            warnings=("dry_run_no_database_view_export_written",),
        )
    if not plan.confirmation_valid:
        return ProfileMediaDatabaseExportResult(
            status="blocked_confirmation_required",
            output_dir=plan.output_dir,
            warnings=(f"confirmation_required:{PROFILE_MEDIA_DATABASE_EXPORT_CONFIRMATION}",),
        )

    output_dir = Path(plan.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    json_payload = snapshot.to_dict(include_view_text=True)
    text_payload = render_database_session_text(snapshot)
    summary_payload = {
        "schema_version": PROFILE_MEDIA_DATABASE_EXPORT_SCHEMA_VERSION,
        "status": snapshot.status,
        "mode": snapshot.config.mode,
        "database_root": snapshot.config.database_root,
        "batch_json_file_count": len(snapshot.config.batch_json_files),
        "index_case_count": json_payload["index_case_count"],
        "index_source_count": json_payload["index_source_count"],
        "index_profile_row_count": json_payload["index_profile_row_count"],
        "matched_source_count": json_payload["matched_source_count"],
        "matched_profile_count": json_payload["matched_profile_count"],
        "folder_scan_performed": False,
        "folder_move_performed": False,
        "folder_rename_performed": False,
        "file_copy_performed": False,
        "media_download_performed": False,
        "automatic_classification_performed": False,
        "sensitive_identifier_inference_performed": False,
    }
    Path(plan.json_path).write_text(json.dumps(json_payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    Path(plan.text_path).write_text(text_payload + "\n", encoding="utf-8")
    Path(plan.summary_json_path).write_text(json.dumps(summary_payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    return ProfileMediaDatabaseExportResult(
        status="success",
        output_dir=plan.output_dir,
        written_files=(plan.json_path, plan.text_path, plan.summary_json_path),
        folder_creation_performed=True,
        file_write_performed=True,
    )
