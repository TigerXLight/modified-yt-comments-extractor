"""Explicit batch JSON import assistant for Profile/Media Database mode.

V76C provides a safe bridge between the GUI and the Database workbench backend.
It accepts only user-selected JSON file paths supplied by the caller.  It never
discovers files by walking a database folder and never mutates case folders.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping

from profile_media_database import utc_now_iso

PROFILE_MEDIA_DATABASE_BATCH_IMPORT_SCHEMA_VERSION = "profile-media-database-batch-import-v76c"


@dataclass(frozen=True)
class ProfileMediaDatabaseBatchImportFile:
    """Validation result for one explicit batch JSON file."""

    path: str
    status: str
    source_count: int = 0
    profile_count: int = 0
    case_title: str = ""
    database_root: str = ""
    warning_count: int = 0
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class ProfileMediaDatabaseBatchImportPlan:
    """Plan for importing explicit batch JSON files into the main Database workbench."""

    batch_json_files: tuple[str, ...]
    requested_database_root: str = ""
    schema_version: str = PROFILE_MEDIA_DATABASE_BATCH_IMPORT_SCHEMA_VERSION
    created_at_utc: str = field(default_factory=utc_now_iso)
    folder_scan_performed: bool = False
    folder_creation_performed: bool = False
    folder_move_performed: bool = False
    folder_rename_performed: bool = False
    file_copy_performed: bool = False
    file_write_performed: bool = False
    media_download_performed: bool = False
    automatic_classification_performed: bool = False
    sensitive_identifier_inference_performed: bool = False


@dataclass(frozen=True)
class ProfileMediaDatabaseBatchImportResult:
    """Result of validating explicit batch JSON files for GUI use."""

    plan: ProfileMediaDatabaseBatchImportPlan
    status: str
    accepted_files: tuple[ProfileMediaDatabaseBatchImportFile, ...] = ()
    rejected_files: tuple[ProfileMediaDatabaseBatchImportFile, ...] = ()
    database_root: str = ""
    warning_count: int = 0
    warnings: tuple[str, ...] = ()
    schema_version: str = PROFILE_MEDIA_DATABASE_BATCH_IMPORT_SCHEMA_VERSION
    created_at_utc: str = field(default_factory=utc_now_iso)
    folder_scan_performed: bool = False
    folder_creation_performed: bool = False
    folder_move_performed: bool = False
    folder_rename_performed: bool = False
    file_copy_performed: bool = False
    file_write_performed: bool = False
    media_download_performed: bool = False
    automatic_classification_performed: bool = False
    sensitive_identifier_inference_performed: bool = False

    @property
    def batch_json_files(self) -> tuple[str, ...]:
        return tuple(item.path for item in self.accepted_files)

    def to_dict(self, *, include_text: bool = False) -> dict[str, Any]:
        payload = asdict(self)
        payload["accepted_file_count"] = len(self.accepted_files)
        payload["rejected_file_count"] = len(self.rejected_files)
        payload["batch_json_files"] = self.batch_json_files
        if include_text:
            payload["import_text"] = render_batch_import_result_text(self)
        return payload


def _coerce_paths(batch_json_files: Iterable[object] | None) -> tuple[str, ...]:
    if not batch_json_files:
        return ()
    seen: set[str] = set()
    output: list[str] = []
    for value in batch_json_files:
        path_text = str(value or "").strip()
        if not path_text:
            continue
        key = str(Path(path_text))
        if key in seen:
            continue
        seen.add(key)
        output.append(path_text)
    return tuple(output)


def build_batch_import_plan(
    batch_json_files: Iterable[object] | None,
    *,
    database_root: object = "",
) -> ProfileMediaDatabaseBatchImportPlan:
    """Build an explicit-file import plan without scanning folders."""

    return ProfileMediaDatabaseBatchImportPlan(
        batch_json_files=_coerce_paths(batch_json_files),
        requested_database_root=str(database_root or ""),
    )


def _load_json_file(path: Path) -> tuple[Mapping[str, Any] | None, tuple[str, ...]]:
    warnings: list[str] = []
    if path.suffix.lower() != ".json":
        warnings.append("not_json_file")
        return None, tuple(warnings)
    if not path.exists():
        warnings.append("missing_file")
        return None, tuple(warnings)
    if not path.is_file():
        warnings.append("not_a_file")
        return None, tuple(warnings)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        warnings.append(f"json_parse_error:{exc.__class__.__name__}")
        return None, tuple(warnings)
    if not isinstance(payload, Mapping):
        warnings.append("json_root_not_object")
        return None, tuple(warnings)
    return payload, tuple(warnings)


def validate_batch_json_file(path_text: object) -> ProfileMediaDatabaseBatchImportFile:
    """Validate one explicit batch JSON file path supplied by the caller."""

    path = Path(str(path_text))
    payload, warnings = _load_json_file(path)
    if payload is None:
        return ProfileMediaDatabaseBatchImportFile(
            path=str(path),
            status="rejected",
            warning_count=len(warnings),
            warnings=warnings,
        )

    sources = payload.get("sources", ())
    profiles = payload.get("profiles", ())
    if not isinstance(sources, list):
        warnings = warnings + ("sources_not_list",)
        sources = []
    if not isinstance(profiles, list):
        warnings = warnings + ("profiles_not_list",)
        profiles = []

    case_title = str(payload.get("case_title", "") or "")
    database_root = str(payload.get("database_root", "") or "")
    if not case_title:
        warnings = warnings + ("missing_case_title",)
    if not sources and not profiles:
        warnings = warnings + ("empty_batch_records",)

    status = "accepted_with_warnings" if warnings else "accepted"
    if "empty_batch_records" in warnings:
        status = "rejected"

    return ProfileMediaDatabaseBatchImportFile(
        path=str(path),
        status=status,
        source_count=len(sources),
        profile_count=len(profiles),
        case_title=case_title,
        database_root=database_root,
        warning_count=len(warnings),
        warnings=warnings,
    )


def apply_batch_import_plan(plan: ProfileMediaDatabaseBatchImportPlan) -> ProfileMediaDatabaseBatchImportResult:
    """Validate explicit batch JSON files and return safe GUI import state."""

    accepted: list[ProfileMediaDatabaseBatchImportFile] = []
    rejected: list[ProfileMediaDatabaseBatchImportFile] = []
    warnings: list[str] = []

    for path_text in plan.batch_json_files:
        item = validate_batch_json_file(path_text)
        if item.status.startswith("accepted"):
            accepted.append(item)
            warnings.extend(item.warnings)
        else:
            rejected.append(item)
            warnings.extend(item.warnings)

    database_root = plan.requested_database_root
    if not database_root:
        database_root = next((item.database_root for item in accepted if item.database_root), "")

    if accepted and rejected:
        status = "partial_success"
    elif accepted:
        status = "success"
    elif plan.batch_json_files:
        status = "blocked_no_valid_batch_json"
    else:
        status = "planned_no_batch_json_selected"

    return ProfileMediaDatabaseBatchImportResult(
        plan=plan,
        status=status,
        accepted_files=tuple(accepted),
        rejected_files=tuple(rejected),
        database_root=database_root,
        warning_count=len(warnings),
        warnings=tuple(warnings),
    )


def batch_import_result_payload(result: ProfileMediaDatabaseBatchImportResult, *, include_text: bool = False) -> dict[str, Any]:
    return result.to_dict(include_text=include_text)


def render_batch_import_result_text(result: ProfileMediaDatabaseBatchImportResult) -> str:
    lines = [
        "Profile/Media Database Batch Import",
        f"Status: {result.status}",
        f"Database root: {result.database_root or '(not configured)'}",
        f"Accepted files: {len(result.accepted_files)}",
        f"Rejected files: {len(result.rejected_files)}",
        f"Folder scan performed: {result.folder_scan_performed}",
        f"Folder creation performed: {result.folder_creation_performed}",
        f"Folder move performed: {result.folder_move_performed}",
        f"Folder rename performed: {result.folder_rename_performed}",
        f"File copy performed: {result.file_copy_performed}",
        f"File write performed: {result.file_write_performed}",
        f"Media download performed: {result.media_download_performed}",
        f"Automatic classification performed: {result.automatic_classification_performed}",
        f"Sensitive identifier inference performed: {result.sensitive_identifier_inference_performed}",
        "",
        "Accepted:",
    ]
    if result.accepted_files:
        for item in result.accepted_files:
            lines.append(f"- {item.path} [{item.case_title or 'untitled'}; sources={item.source_count}; profiles={item.profile_count}]")
    else:
        lines.append("- none")
    lines.append("")
    lines.append("Rejected:")
    if result.rejected_files:
        for item in result.rejected_files:
            detail = ", ".join(item.warnings) if item.warnings else "unknown"
            lines.append(f"- {item.path} [{detail}]")
    else:
        lines.append("- none")
    return "\n".join(lines)
