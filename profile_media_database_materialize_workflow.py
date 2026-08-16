"""Controlled Database materialization workflow for Profile/Media Database mode.

V76F connects the explicit batch-JSON planning layers to a single guarded
materialization workflow.  The workflow accepts only caller-supplied batch JSON
paths.  It never discovers folders on its own and never copies/downloads media.

Default behavior is a dry-run review.  Real folder creation and metadata-file
writing require execute=True and the exact confirmation phrase
MATERIALIZE_PROFILE_MEDIA_DATABASE_SELECTION.  The workflow delegates to the
already guarded V75V/V75U batch and materialize layers using their internal
confirmations after the V76F top-level confirmation has been satisfied.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping

from profile_media_case_batch import (
    PROFILE_MEDIA_CASE_BATCH_CONFIRMATION,
    ProfileMediaCaseBatchPlan,
    ProfileMediaCaseBatchResult,
    apply_case_batch_plan,
    build_case_batch_plan,
    load_case_batch_json,
    render_case_batch_text,
)
from profile_media_database import stable_profile_id, utc_now_iso

PROFILE_MEDIA_DATABASE_MATERIALIZE_WORKFLOW_SCHEMA_VERSION = "profile-media-database-materialize-workflow-v76f"
PROFILE_MEDIA_DATABASE_MATERIALIZE_CONFIRMATION = "MATERIALIZE_PROFILE_MEDIA_DATABASE_SELECTION"


@dataclass(frozen=True)
class ProfileMediaDatabaseMaterializeBatchReview:
    """Review entry for one explicit batch JSON file before execution."""

    path: str
    status: str
    case_title: str = ""
    case_root: str = ""
    source_count: int = 0
    profile_count: int = 0
    plan_id: str = ""
    warnings: tuple[str, ...] = ()
    schema_version: str = PROFILE_MEDIA_DATABASE_MATERIALIZE_WORKFLOW_SCHEMA_VERSION
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
        return asdict(self)


@dataclass(frozen=True)
class ProfileMediaDatabaseMaterializePlan:
    """Top-level review/execution plan for selected explicit batch JSON files."""

    database_root: str
    batch_json_files: tuple[str, ...]
    batch_reviews: tuple[ProfileMediaDatabaseMaterializeBatchReview, ...]
    execute_requested: bool = False
    confirmation_phrase: str = ""
    plan_id: str = ""
    schema_version: str = PROFILE_MEDIA_DATABASE_MATERIALIZE_WORKFLOW_SCHEMA_VERSION
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
        return self.confirmation_phrase == PROFILE_MEDIA_DATABASE_MATERIALIZE_CONFIRMATION

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["batch_reviews"] = [review.to_dict() for review in self.batch_reviews]
        data["batch_json_file_count"] = len(self.batch_json_files)
        data["review_batch_count"] = len(self.batch_reviews)
        data["review_source_count"] = sum(review.source_count for review in self.batch_reviews if review.status == "ready")
        data["review_profile_count"] = sum(review.profile_count for review in self.batch_reviews if review.status == "ready")
        data["confirmation_required"] = self.execute_requested
        data["confirmation_valid"] = self.confirmation_valid
        data["materialize_confirmation"] = PROFILE_MEDIA_DATABASE_MATERIALIZE_CONFIRMATION
        data["delegated_batch_confirmation"] = PROFILE_MEDIA_CASE_BATCH_CONFIRMATION
        return data


@dataclass(frozen=True)
class ProfileMediaDatabaseMaterializeResult:
    """Result for a dry-run, blocked run, or confirmed materialization run."""

    status: str
    plan_id: str
    database_root: str
    batch_json_files: tuple[str, ...]
    batch_results: tuple[dict[str, Any], ...] = ()
    created_directories: tuple[str, ...] = ()
    already_existing_directories: tuple[str, ...] = ()
    written_files: tuple[str, ...] = ()
    blocked_paths: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    schema_version: str = PROFILE_MEDIA_DATABASE_MATERIALIZE_WORKFLOW_SCHEMA_VERSION
    created_at_utc: str = field(default_factory=utc_now_iso)
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
        data = asdict(self)
        data["batch_json_file_count"] = len(self.batch_json_files)
        data["batch_result_count"] = len(self.batch_results)
        data["created_directory_count"] = len(self.created_directories)
        data["already_existing_directory_count"] = len(self.already_existing_directories)
        data["written_file_count"] = len(self.written_files)
        data["blocked_path_count"] = len(self.blocked_paths)
        data["warning_count"] = len(self.warnings)
        return data


def _tuple_of_paths(batch_json_files: Iterable[object] | None) -> tuple[str, ...]:
    if not batch_json_files:
        return ()
    return tuple(str(item).strip() for item in batch_json_files if str(item).strip())


def _safe_batch_review(path: str, *, database_root: str) -> ProfileMediaDatabaseMaterializeBatchReview:
    try:
        payload = load_case_batch_json(path)
        plan = build_case_batch_plan(payload=payload, database_root=database_root, execute=False)
        return ProfileMediaDatabaseMaterializeBatchReview(
            path=path,
            status="ready",
            case_title=plan.case_title,
            case_root=plan.case_root,
            source_count=len(plan.source_specs),
            profile_count=len(plan.profile_specs),
            plan_id=plan.plan_id,
            warnings=plan.forbidden_operation_warnings,
        )
    except Exception as exc:
        return ProfileMediaDatabaseMaterializeBatchReview(
            path=path,
            status="blocked_invalid_batch_json",
            warnings=(f"batch_json_error:{type(exc).__name__}:{exc}",),
        )


def build_database_materialize_plan(
    *,
    database_root: str,
    batch_json_files: Iterable[object] | None,
    execute: bool = False,
    confirmation_phrase: str = "",
) -> ProfileMediaDatabaseMaterializePlan:
    """Build a reviewable materialization plan without filesystem mutation."""

    root = str(database_root or "").strip()
    paths = _tuple_of_paths(batch_json_files)
    reviews = tuple(_safe_batch_review(path, database_root=root) for path in paths)
    plan_id = stable_profile_id(
        "database_materialize_workflow",
        root,
        "|".join(paths),
        str(len(reviews)),
        str(sum(review.source_count for review in reviews)),
        str(sum(review.profile_count for review in reviews)),
    )
    return ProfileMediaDatabaseMaterializePlan(
        database_root=root,
        batch_json_files=paths,
        batch_reviews=reviews,
        execute_requested=bool(execute),
        confirmation_phrase=confirmation_phrase,
        plan_id=plan_id,
    )


def _build_executable_batch_plan(path: str, *, database_root: str) -> ProfileMediaCaseBatchPlan:
    payload = load_case_batch_json(path)
    return build_case_batch_plan(
        payload=payload,
        database_root=database_root,
        execute=True,
        confirmation_phrase=PROFILE_MEDIA_CASE_BATCH_CONFIRMATION,
    )


def _dedupe(items: Iterable[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(str(item) for item in items if str(item).strip()))


def apply_database_materialize_plan(plan: ProfileMediaDatabaseMaterializePlan) -> ProfileMediaDatabaseMaterializeResult:
    """Apply only a top-level confirmed materialization plan."""

    warnings: list[str] = []
    if not plan.database_root:
        warnings.append("database_root_required")
    if not plan.batch_json_files:
        warnings.append("no_batch_json_files_selected")
    for review in plan.batch_reviews:
        warnings.extend(review.warnings)
        if review.status != "ready":
            warnings.append(f"batch_not_ready:{review.path}:{review.status}")

    if not plan.batch_json_files:
        return ProfileMediaDatabaseMaterializeResult(
            status="blocked_no_batch_json",
            plan_id=plan.plan_id,
            database_root=plan.database_root,
            batch_json_files=plan.batch_json_files,
            warnings=_dedupe(warnings),
        )
    if not plan.database_root:
        return ProfileMediaDatabaseMaterializeResult(
            status="blocked_database_root_required",
            plan_id=plan.plan_id,
            database_root=plan.database_root,
            batch_json_files=plan.batch_json_files,
            warnings=_dedupe(warnings),
        )
    if any(review.status != "ready" for review in plan.batch_reviews):
        return ProfileMediaDatabaseMaterializeResult(
            status="blocked_invalid_batch_json",
            plan_id=plan.plan_id,
            database_root=plan.database_root,
            batch_json_files=plan.batch_json_files,
            warnings=_dedupe(warnings),
        )
    if not plan.execute_requested:
        return ProfileMediaDatabaseMaterializeResult(
            status="planned_dry_run",
            plan_id=plan.plan_id,
            database_root=plan.database_root,
            batch_json_files=plan.batch_json_files,
            warnings=_dedupe(warnings + ["dry_run_no_database_materialized"]),
        )
    if not plan.confirmation_valid:
        return ProfileMediaDatabaseMaterializeResult(
            status="blocked_confirmation_required",
            plan_id=plan.plan_id,
            database_root=plan.database_root,
            batch_json_files=plan.batch_json_files,
            warnings=_dedupe(warnings + [f"confirmation_phrase_must_equal:{PROFILE_MEDIA_DATABASE_MATERIALIZE_CONFIRMATION}"]),
        )

    batch_payloads: list[dict[str, Any]] = []
    created_dirs: list[str] = []
    existing_dirs: list[str] = []
    written_files: list[str] = []
    blocked_paths: list[str] = []

    for path in plan.batch_json_files:
        try:
            child_plan = _build_executable_batch_plan(path, database_root=plan.database_root)
            child_result: ProfileMediaCaseBatchResult = apply_case_batch_plan(child_plan)
            child_payload = child_result.to_dict()
            child_payload["batch_json_file"] = path
            child_payload["case_title"] = child_plan.case_title
            child_payload["source_count"] = len(child_plan.source_specs)
            child_payload["profile_count"] = len(child_plan.profile_specs)
            batch_payloads.append(child_payload)
            created_dirs.extend(child_result.created_directories)
            existing_dirs.extend(child_result.already_existing_directories)
            written_files.extend(child_result.written_files)
            blocked_paths.extend(child_result.blocked_paths)
            warnings.extend(child_result.warnings)
        except Exception as exc:
            batch_payloads.append({
                "batch_json_file": path,
                "status": "blocked_exception",
                "error_type": type(exc).__name__,
                "error": str(exc),
            })
            warnings.append(f"batch_exception:{path}:{type(exc).__name__}:{exc}")

    child_statuses = tuple(str(payload.get("status", "")) for payload in batch_payloads)
    all_materialized = bool(child_statuses) and all(status == "batch_materialized" for status in child_statuses)
    any_materialized = any(status == "batch_materialized" for status in child_statuses)
    status = "materialized" if all_materialized else ("partially_materialized" if any_materialized else "blocked_child_operation")
    return ProfileMediaDatabaseMaterializeResult(
        status=status,
        plan_id=plan.plan_id,
        database_root=plan.database_root,
        batch_json_files=plan.batch_json_files,
        batch_results=tuple(batch_payloads),
        created_directories=_dedupe(created_dirs),
        already_existing_directories=_dedupe(existing_dirs),
        written_files=_dedupe(written_files),
        blocked_paths=_dedupe(blocked_paths),
        warnings=_dedupe(warnings),
        folder_creation_performed=bool(created_dirs),
        file_write_performed=bool(written_files),
    )


def render_database_materialize_plan_text(plan: ProfileMediaDatabaseMaterializePlan) -> str:
    """Render the plan for confirmation review."""

    lines = [
        "Profile/Media Database Materialize Plan",
        f"Status: {'execute_requested' if plan.execute_requested else 'dry_run'}",
        f"Database root: {plan.database_root or '(not configured)'}",
        f"Batch JSON files: {len(plan.batch_json_files)}",
        f"Review batches: {len(plan.batch_reviews)}",
        f"Source records: {sum(review.source_count for review in plan.batch_reviews)}",
        f"Profile records: {sum(review.profile_count for review in plan.batch_reviews)}",
        f"Execute requested: {plan.execute_requested}",
        f"Confirmation required: {PROFILE_MEDIA_DATABASE_MATERIALIZE_CONFIRMATION}",
        "Folder scan performed: False",
        "Folder move performed: False",
        "Folder rename performed: False",
        "File copy performed: False",
        "Media download performed: False",
        "Automatic classification performed: False",
        "Sensitive identifier inference performed: False",
        "",
        "Batches:",
    ]
    if not plan.batch_reviews:
        lines.append("- none")
    for review in plan.batch_reviews:
        warning_text = f"; warnings={len(review.warnings)}" if review.warnings else ""
        lines.append(
            f"- {review.path}: {review.status}; case={review.case_title or '(unknown)'}; "
            f"sources={review.source_count}; profiles={review.profile_count}{warning_text}"
        )
    return "\n".join(lines)


def render_database_materialize_result_text(result: ProfileMediaDatabaseMaterializeResult) -> str:
    """Render a materialization result for logs/GUI details."""

    lines = [
        "Profile/Media Database Materialize Result",
        f"Status: {result.status}",
        f"Database root: {result.database_root or '(not configured)'}",
        f"Batch JSON files: {len(result.batch_json_files)}",
        f"Created directories: {len(result.created_directories)}",
        f"Already existing directories: {len(result.already_existing_directories)}",
        f"Written files: {len(result.written_files)}",
        f"Blocked paths: {len(result.blocked_paths)}",
        f"Warnings: {len(result.warnings)}",
        f"Folder creation performed: {result.folder_creation_performed}",
        f"Folder scan performed: {result.folder_scan_performed}",
        f"Folder move performed: {result.folder_move_performed}",
        f"Folder rename performed: {result.folder_rename_performed}",
        f"File copy performed: {result.file_copy_performed}",
        f"File write performed: {result.file_write_performed}",
        f"Media download performed: {result.media_download_performed}",
        f"Automatic classification performed: {result.automatic_classification_performed}",
        f"Sensitive identifier inference performed: {result.sensitive_identifier_inference_performed}",
        "",
        "Batch results:",
    ]
    if not result.batch_results:
        lines.append("- none")
    for payload in result.batch_results:
        lines.append(
            f"- {payload.get('batch_json_file', '')}: {payload.get('status', '')}; "
            f"case={payload.get('case_title', '')}; written={payload.get('written_file_count', 0)}"
        )
    return "\n".join(lines)


def materialize_workflow_payload(
    result: ProfileMediaDatabaseMaterializeResult,
    *,
    plan: ProfileMediaDatabaseMaterializePlan | None = None,
) -> dict[str, Any]:
    payload = result.to_dict()
    payload["result_text"] = render_database_materialize_result_text(result)
    if plan is not None:
        payload["plan"] = plan.to_dict()
        payload["plan_text"] = render_database_materialize_plan_text(plan)
    return payload
