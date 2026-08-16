"""Reviewed folder operation workflow for Profile/Media Database mode.

V76G adds a controlled workflow for moving or renaming already-known database
folders after the user has reviewed an explicit operation JSON.  It never scans
folders, copies files, downloads media, classifies content, or infers sensitive
identifiers.

Default behavior is dry-run only.  Real folder rename/move execution requires
execute=True and the exact confirmation phrase
APPLY_PROFILE_MEDIA_REVIEWED_FOLDER_OPERATIONS.  The workflow operates only on
explicit caller-supplied paths under the configured database_root.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping

from profile_media_database import stable_profile_id, utc_now_iso

PROFILE_MEDIA_DATABASE_FOLDER_OPERATIONS_SCHEMA_VERSION = "profile-media-folder-operations-v76g"
PROFILE_MEDIA_DATABASE_FOLDER_OPERATIONS_CONFIRMATION = "APPLY_PROFILE_MEDIA_REVIEWED_FOLDER_OPERATIONS"
_SUPPORTED_OPERATION_TYPES = {"rename_folder", "move_folder"}


@dataclass(frozen=True)
class ProfileMediaFolderOperationSpec:
    """One reviewed folder operation supplied by the user or GUI controller."""

    operation_type: str
    source_path: str
    destination_path: str = ""
    new_name: str = ""
    reason: str = ""
    review_note: str = ""
    operation_id: str = ""
    schema_version: str = PROFILE_MEDIA_DATABASE_FOLDER_OPERATIONS_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ProfileMediaFolderOperationReview:
    """Safety review for one explicit folder operation before execution."""

    operation_id: str
    operation_type: str
    source_path: str
    destination_path: str
    source_abs: str
    destination_abs: str
    status: str
    reason: str = ""
    review_note: str = ""
    warnings: tuple[str, ...] = ()
    schema_version: str = PROFILE_MEDIA_DATABASE_FOLDER_OPERATIONS_SCHEMA_VERSION
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

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["warning_count"] = len(self.warnings)
        return data


@dataclass(frozen=True)
class ProfileMediaFolderOperationsPlan:
    """Dry-run/execute plan for reviewed folder operations."""

    database_root: str
    operation_specs: tuple[ProfileMediaFolderOperationSpec, ...]
    operation_reviews: tuple[ProfileMediaFolderOperationReview, ...]
    execute_requested: bool = False
    confirmation_phrase: str = ""
    plan_id: str = ""
    schema_version: str = PROFILE_MEDIA_DATABASE_FOLDER_OPERATIONS_SCHEMA_VERSION
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
    def confirmation_valid(self) -> bool:
        return self.confirmation_phrase == PROFILE_MEDIA_DATABASE_FOLDER_OPERATIONS_CONFIRMATION

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["operation_specs"] = [spec.to_dict() for spec in self.operation_specs]
        data["operation_reviews"] = [review.to_dict() for review in self.operation_reviews]
        data["operation_count"] = len(self.operation_specs)
        data["review_count"] = len(self.operation_reviews)
        data["ready_count"] = sum(1 for item in self.operation_reviews if item.status == "ready")
        data["blocked_count"] = sum(1 for item in self.operation_reviews if item.status != "ready")
        data["confirmation_required"] = self.execute_requested
        data["confirmation_valid"] = self.confirmation_valid
        data["confirmation_phrase_required"] = PROFILE_MEDIA_DATABASE_FOLDER_OPERATIONS_CONFIRMATION
        return data


@dataclass(frozen=True)
class ProfileMediaFolderOperationsResult:
    """Result of a reviewed folder operation plan."""

    status: str
    plan_id: str
    database_root: str
    operation_results: tuple[dict[str, Any], ...] = ()
    moved_directories: tuple[str, ...] = ()
    renamed_directories: tuple[str, ...] = ()
    blocked_paths: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    schema_version: str = PROFILE_MEDIA_DATABASE_FOLDER_OPERATIONS_SCHEMA_VERSION
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

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["operation_result_count"] = len(self.operation_results)
        data["moved_directory_count"] = len(self.moved_directories)
        data["renamed_directory_count"] = len(self.renamed_directories)
        data["blocked_path_count"] = len(self.blocked_paths)
        data["warning_count"] = len(self.warnings)
        return data


def load_folder_operations_json(path: str | Path) -> dict[str, Any]:
    """Load a reviewed folder-operations JSON file."""

    with Path(path).open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError("folder operations JSON root must be an object")
    return payload


def _list_of_objects(value: Any) -> tuple[dict[str, Any], ...]:
    if value is None:
        return ()
    if not isinstance(value, list):
        raise ValueError("operations must be a list")
    result: list[dict[str, Any]] = []
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            raise ValueError(f"operations[{index}] must be an object")
        result.append(dict(item))
    return tuple(result)


def _safe_name(value: object) -> str:
    text = str(value or "").strip().replace("\\", "/")
    text = text.split("/")[-1]
    text = re.sub(r"[<>:\"/\\|?*\x00-\x1f]+", " - ", text).strip()
    text = re.sub(r"\s+", " ", text).strip(" .")
    return text[:120]


def _coerce_relative_path(value: object) -> str:
    text = str(value or "").strip().replace("\\", "/")
    while "//" in text:
        text = text.replace("//", "/")
    text = text.strip("/")
    return text


def _is_absolute_like(value: str) -> bool:
    return bool(re.match(r"^[A-Za-z]:/", value.replace("\\", "/"))) or value.startswith("/")


def _resolve_under_root(database_root: Path, value: object) -> tuple[Path, tuple[str, ...]]:
    warnings: list[str] = []
    rel_text = _coerce_relative_path(value)
    if not rel_text:
        warnings.append("path_required")
    if _is_absolute_like(str(value or "")):
        warnings.append("absolute_paths_not_allowed")
    parts = [part for part in rel_text.split("/") if part and part not in (".",)]
    if any(part == ".." for part in parts):
        warnings.append("parent_path_segments_not_allowed")
    safe_parts = [part for part in parts if part != ".."]
    candidate = database_root.joinpath(*safe_parts) if safe_parts else database_root
    try:
        root_resolved = database_root.resolve(strict=False)
        candidate_resolved = candidate.resolve(strict=False)
        if candidate_resolved != root_resolved and root_resolved not in candidate_resolved.parents:
            warnings.append("path_outside_database_root")
    except Exception as exc:
        warnings.append(f"path_resolution_error:{type(exc).__name__}:{exc}")
    return candidate, tuple(warnings)


def _operation_specs_from_payload(payload: Mapping[str, Any]) -> tuple[ProfileMediaFolderOperationSpec, ...]:
    raw_operations = _list_of_objects(payload.get("operations", []))
    specs: list[ProfileMediaFolderOperationSpec] = []
    for index, raw in enumerate(raw_operations):
        operation_type = str(raw.get("operation_type") or raw.get("operation") or raw.get("type") or "").strip()
        source_path = _coerce_relative_path(raw.get("source_path") or raw.get("source") or "")
        destination_path = _coerce_relative_path(raw.get("destination_path") or raw.get("destination") or "")
        new_name = _safe_name(raw.get("new_name") or "")
        if operation_type == "rename_folder" and not destination_path and source_path and new_name:
            parent = "/".join(source_path.split("/")[:-1])
            destination_path = "/".join(part for part in (parent, new_name) if part)
        operation_id = str(raw.get("operation_id") or "").strip() or stable_profile_id(
            "folder_operation", index, operation_type, source_path, destination_path, new_name
        )
        specs.append(ProfileMediaFolderOperationSpec(
            operation_type=operation_type,
            source_path=source_path,
            destination_path=destination_path,
            new_name=new_name,
            reason=str(raw.get("reason") or "").strip(),
            review_note=str(raw.get("review_note") or raw.get("notes") or "").strip(),
            operation_id=operation_id,
        ))
    return tuple(specs)


def _review_operation(spec: ProfileMediaFolderOperationSpec, *, database_root: Path) -> ProfileMediaFolderOperationReview:
    warnings: list[str] = []
    if spec.operation_type not in _SUPPORTED_OPERATION_TYPES:
        warnings.append(f"unsupported_operation_type:{spec.operation_type or '(blank)'}")
    source_abs, source_warnings = _resolve_under_root(database_root, spec.source_path)
    destination_abs, destination_warnings = _resolve_under_root(database_root, spec.destination_path)
    warnings.extend(source_warnings)
    warnings.extend(destination_warnings)
    if not spec.source_path:
        warnings.append("source_path_required")
    if not spec.destination_path:
        warnings.append("destination_path_required")
    if spec.operation_type == "rename_folder" and not spec.new_name:
        warnings.append("new_name_required_for_rename")
    if not database_root:
        warnings.append("database_root_required")
    if source_abs == destination_abs:
        warnings.append("source_and_destination_identical")
    if source_abs.exists() and not source_abs.is_dir():
        warnings.append("source_exists_but_is_not_directory")
    if not source_abs.exists():
        warnings.append("source_directory_missing")
    if destination_abs.exists():
        warnings.append("destination_already_exists")
    if destination_abs.parent and not destination_abs.parent.exists():
        warnings.append("destination_parent_missing")
    status = "ready" if not warnings else "blocked_review_required"
    return ProfileMediaFolderOperationReview(
        operation_id=spec.operation_id,
        operation_type=spec.operation_type,
        source_path=spec.source_path,
        destination_path=spec.destination_path,
        source_abs=str(source_abs),
        destination_abs=str(destination_abs),
        status=status,
        reason=spec.reason,
        review_note=spec.review_note,
        warnings=tuple(dict.fromkeys(warnings)),
    )


def build_folder_operations_plan(
    *,
    database_root: str | Path,
    operations_payload: Mapping[str, Any] | None = None,
    operations_json_path: str | Path | None = None,
    execute: bool = False,
    confirmation_phrase: str = "",
) -> ProfileMediaFolderOperationsPlan:
    """Build a dry-run review plan from explicit JSON data only."""

    payload: Mapping[str, Any]
    if operations_payload is not None:
        payload = operations_payload
    elif operations_json_path is not None:
        payload = load_folder_operations_json(operations_json_path)
    else:
        payload = {"operations": []}
    root = Path(str(database_root or payload.get("database_root") or "").strip())
    specs = _operation_specs_from_payload(payload)
    reviews = tuple(_review_operation(spec, database_root=root) for spec in specs)
    plan_id = stable_profile_id(
        "folder_operations_plan",
        str(root),
        "|".join(spec.operation_id for spec in specs),
        str(len(specs)),
    )
    return ProfileMediaFolderOperationsPlan(
        database_root=str(root),
        operation_specs=specs,
        operation_reviews=reviews,
        execute_requested=bool(execute),
        confirmation_phrase=confirmation_phrase,
        plan_id=plan_id,
    )


def _dedupe(items: Iterable[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(str(item) for item in items if str(item).strip()))


def apply_folder_operations_plan(plan: ProfileMediaFolderOperationsPlan) -> ProfileMediaFolderOperationsResult:
    """Apply only confirmed, review-ready folder rename/move operations."""

    warnings: list[str] = []
    blocked_paths: list[str] = []
    if not plan.database_root:
        warnings.append("database_root_required")
    if not plan.operation_reviews:
        warnings.append("no_folder_operations_selected")
    for review in plan.operation_reviews:
        warnings.extend(review.warnings)
        if review.status != "ready":
            blocked_paths.append(review.source_abs)
            blocked_paths.append(review.destination_abs)
            warnings.append(f"operation_not_ready:{review.operation_id}:{review.status}")

    if not plan.operation_reviews:
        return ProfileMediaFolderOperationsResult(
            status="blocked_no_operations",
            plan_id=plan.plan_id,
            database_root=plan.database_root,
            blocked_paths=_dedupe(blocked_paths),
            warnings=_dedupe(warnings),
        )
    if any(review.status != "ready" for review in plan.operation_reviews):
        return ProfileMediaFolderOperationsResult(
            status="blocked_review_required",
            plan_id=plan.plan_id,
            database_root=plan.database_root,
            blocked_paths=_dedupe(blocked_paths),
            warnings=_dedupe(warnings),
        )
    if not plan.execute_requested:
        return ProfileMediaFolderOperationsResult(
            status="planned_dry_run",
            plan_id=plan.plan_id,
            database_root=plan.database_root,
            warnings=_dedupe(warnings + ["dry_run_no_folder_operations_applied"]),
        )
    if not plan.confirmation_valid:
        return ProfileMediaFolderOperationsResult(
            status="blocked_confirmation_required",
            plan_id=plan.plan_id,
            database_root=plan.database_root,
            warnings=_dedupe(warnings + [f"confirmation_phrase_must_equal:{PROFILE_MEDIA_DATABASE_FOLDER_OPERATIONS_CONFIRMATION}"]),
        )

    results: list[dict[str, Any]] = []
    moved: list[str] = []
    renamed: list[str] = []
    for review in plan.operation_reviews:
        src = Path(review.source_abs)
        dst = Path(review.destination_abs)
        try:
            src.rename(dst)
            operation_payload = review.to_dict()
            operation_payload["status"] = "applied"
            operation_payload["applied_at_utc"] = utc_now_iso()
            results.append(operation_payload)
            if review.operation_type == "rename_folder":
                renamed.append(str(dst))
            else:
                moved.append(str(dst))
        except Exception as exc:
            payload = review.to_dict()
            payload["status"] = "blocked_exception"
            payload["error_type"] = type(exc).__name__
            payload["error"] = str(exc)
            results.append(payload)
            warnings.append(f"operation_exception:{review.operation_id}:{type(exc).__name__}:{exc}")
            blocked_paths.extend([review.source_abs, review.destination_abs])

    any_applied = bool(moved or renamed)
    all_applied = results and all(item.get("status") == "applied" for item in results)
    status = "operations_applied" if all_applied else ("partially_applied" if any_applied else "blocked_operation_exception")
    return ProfileMediaFolderOperationsResult(
        status=status,
        plan_id=plan.plan_id,
        database_root=plan.database_root,
        operation_results=tuple(results),
        moved_directories=_dedupe(moved),
        renamed_directories=_dedupe(renamed),
        blocked_paths=_dedupe(blocked_paths),
        warnings=_dedupe(warnings),
        folder_move_performed=bool(moved),
        folder_rename_performed=bool(renamed),
    )


def render_folder_operations_plan_text(plan: ProfileMediaFolderOperationsPlan) -> str:
    """Render a review text before execution."""

    lines = [
        "Profile/Media Reviewed Folder Operations Plan",
        f"Status: {'execute_requested' if plan.execute_requested else 'dry_run'}",
        f"Database root: {plan.database_root or '(not configured)'}",
        f"Operations: {len(plan.operation_reviews)}",
        f"Ready operations: {sum(1 for item in plan.operation_reviews if item.status == 'ready')}",
        f"Blocked operations: {sum(1 for item in plan.operation_reviews if item.status != 'ready')}",
        f"Execute requested: {plan.execute_requested}",
        f"Confirmation required: {PROFILE_MEDIA_DATABASE_FOLDER_OPERATIONS_CONFIRMATION}",
        "Folder scan performed: False",
        "Folder creation performed: False",
        "File copy performed: False",
        "File write performed: False",
        "Media download performed: False",
        "Automatic classification performed: False",
        "Sensitive identifier inference performed: False",
        "",
        "Operations:",
    ]
    if not plan.operation_reviews:
        lines.append("- none")
    for item in plan.operation_reviews:
        warning_text = f"; warnings={len(item.warnings)}" if item.warnings else ""
        lines.append(f"- {item.operation_type}: {item.source_path} -> {item.destination_path}; {item.status}{warning_text}")
    return "\n".join(lines)


def render_folder_operations_result_text(result: ProfileMediaFolderOperationsResult) -> str:
    """Render a folder-operation result for logs/GUI details."""

    lines = [
        "Profile/Media Reviewed Folder Operations Result",
        f"Status: {result.status}",
        f"Database root: {result.database_root or '(not configured)'}",
        f"Operation results: {len(result.operation_results)}",
        f"Moved directories: {len(result.moved_directories)}",
        f"Renamed directories: {len(result.renamed_directories)}",
        f"Blocked paths: {len(result.blocked_paths)}",
        f"Warnings: {len(result.warnings)}",
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
        "Operations:",
    ]
    if not result.operation_results:
        lines.append("- none")
    for item in result.operation_results:
        lines.append(
            f"- {item.get('operation_type', '')}: {item.get('source_path', '')} -> {item.get('destination_path', '')}; {item.get('status', '')}"
        )
    return "\n".join(lines)


def folder_operations_payload(
    result: ProfileMediaFolderOperationsResult,
    *,
    plan: ProfileMediaFolderOperationsPlan | None = None,
) -> dict[str, Any]:
    payload = result.to_dict()
    payload["result_text"] = render_folder_operations_result_text(result)
    if plan is not None:
        payload["plan"] = plan.to_dict()
        payload["plan_text"] = render_folder_operations_plan_text(plan)
    return payload


def build_demo_folder_operations_payload() -> dict[str, Any]:
    """Small fixture payload for CLI smoke tests."""

    return {
        "schema_version": PROFILE_MEDIA_DATABASE_FOLDER_OPERATIONS_SCHEMA_VERSION,
        "operations": [
            {
                "operation_type": "rename_folder",
                "source_path": "Cases/Demo Case/Sources/Articles/Old Article Folder",
                "new_name": "Renamed Article Folder",
                "reason": "Reviewed title normalization.",
                "review_note": "No media files are copied or downloaded.",
            },
            {
                "operation_type": "move_folder",
                "source_path": "Cases/Demo Case/Sources/Social Media/Online/Misfiled Offline Bundle",
                "destination_path": "Cases/Demo Case/Sources/Social Media/Offline/Misfiled Offline Bundle",
                "reason": "Reviewed source bucket correction.",
                "review_note": "Source was explicitly selected by the user.",
            },
        ],
    }


def write_demo_folder_operations_json(path: str | Path) -> str:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(build_demo_folder_operations_payload(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return str(target)
