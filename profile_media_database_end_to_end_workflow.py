"""End-to-end Profile/Media Database workflow coordinator.

V76H ties together the already-reviewed V76E/V76F/V76G building blocks:
explicit folder-tree text -> batch preview -> explicit batch JSON loading ->
confirmed materialization -> reviewed folder operations -> refreshed Database
panel.  The coordinator is deliberately UI-neutral and still uses explicit
inputs only.  It does not scan folders, copy media, download media, classify
automatically, or infer sensitive identifiers.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping

from profile_media_database import utc_now_iso
from profile_media_database_folder_operations import (
    PROFILE_MEDIA_DATABASE_FOLDER_OPERATIONS_CONFIRMATION,
    ProfileMediaFolderOperationsResult,
    apply_folder_operations_plan,
    build_folder_operations_plan,
    folder_operations_payload,
    render_folder_operations_plan_text,
    render_folder_operations_result_text,
)
from profile_media_database_gui_controller import (
    ProfileMediaDatabaseGuiSelectionResult,
    build_database_gui_selection_from_batch_json,
)
from profile_media_database_materialize_workflow import (
    PROFILE_MEDIA_DATABASE_MATERIALIZE_CONFIRMATION,
    ProfileMediaDatabaseMaterializeResult,
    apply_database_materialize_plan,
    build_database_materialize_plan,
    materialize_workflow_payload,
    render_database_materialize_plan_text,
    render_database_materialize_result_text,
)
from profile_media_existing_folder_batch_planner import (
    PROFILE_MEDIA_EXISTING_FOLDER_BATCH_WRITE_CONFIRMATION,
    ExistingFolderBatchPreviewWriteResult,
    ExistingFolderToBatchPlan,
    build_existing_folder_to_batch_plan,
    render_existing_folder_plan_text,
    write_batch_preview_if_confirmed,
)
from profile_media_existing_folder_gui_adapter import build_existing_folder_gui_payload

PROFILE_MEDIA_DATABASE_END_TO_END_SCHEMA_VERSION = "profile-media-database-end-to-end-v76h"


@dataclass(frozen=True)
class ProfileMediaDatabaseEndToEndConfig:
    """Configuration for one explicit end-to-end workflow run."""

    folder_tree_lines: tuple[str, ...] = ()
    database_root: str = ""
    case_title: str = ""
    batch_preview_path: str = ""
    write_batch_preview: bool = False
    batch_write_confirmation: str = ""
    materialize_database: bool = False
    materialize_confirmation: str = ""
    operations_payload: Mapping[str, Any] | None = None
    operations_json_path: str = ""
    execute_folder_operations: bool = False
    folder_operations_confirmation: str = ""
    schema_version: str = PROFILE_MEDIA_DATABASE_END_TO_END_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["folder_tree_line_count"] = len(self.folder_tree_lines)
        payload["operations_payload_provided"] = self.operations_payload is not None
        return payload


@dataclass(frozen=True)
class ProfileMediaDatabaseEndToEndResult:
    """Combined result for the V76H workflow."""

    status: str
    config: ProfileMediaDatabaseEndToEndConfig
    existing_folder_plan: ExistingFolderToBatchPlan
    existing_folder_gui_payload: Mapping[str, Any]
    batch_preview_write_result: ExistingFolderBatchPreviewWriteResult | None = None
    gui_selection_result: ProfileMediaDatabaseGuiSelectionResult | None = None
    materialize_result: ProfileMediaDatabaseMaterializeResult | None = None
    materialize_plan_text: str = ""
    materialize_result_text: str = ""
    folder_operations_result: ProfileMediaFolderOperationsResult | None = None
    folder_operations_plan_text: str = ""
    folder_operations_result_text: str = ""
    refreshed_gui_selection_result: ProfileMediaDatabaseGuiSelectionResult | None = None
    warnings: tuple[str, ...] = ()
    schema_version: str = PROFILE_MEDIA_DATABASE_END_TO_END_SCHEMA_VERSION
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

    def to_dict(self, *, include_text: bool = False) -> dict[str, Any]:
        materialize_payload = (
            materialize_workflow_payload(self.materialize_result) if self.materialize_result else None
        )
        folder_ops_payload = (
            folder_operations_payload(self.folder_operations_result) if self.folder_operations_result else None
        )
        payload: dict[str, Any] = {
            "schema_version": self.schema_version,
            "created_at_utc": self.created_at_utc,
            "status": self.status,
            "config": self.config.to_dict(),
            "database_root": self.config.database_root,
            "case_title": self.config.case_title or (self.existing_folder_plan.cases[0] if self.existing_folder_plan.cases else ""),
            "existing_folder_plan": self.existing_folder_plan.to_dict(),
            "existing_folder_gui_payload": dict(self.existing_folder_gui_payload),
            "batch_preview_write_result": self.batch_preview_write_result.to_dict() if self.batch_preview_write_result else None,
            "gui_selection_result": self.gui_selection_result.to_dict(include_text=include_text) if self.gui_selection_result else None,
            "materialize_result": materialize_payload,
            "folder_operations_result": folder_ops_payload,
            "refreshed_gui_selection_result": self.refreshed_gui_selection_result.to_dict(include_text=include_text) if self.refreshed_gui_selection_result else None,
            "warning_count": len(self.warnings),
            "warnings": list(self.warnings),
            "folder_scan_performed": self.folder_scan_performed,
            "folder_creation_performed": self.folder_creation_performed,
            "folder_move_performed": self.folder_move_performed,
            "folder_rename_performed": self.folder_rename_performed,
            "file_copy_performed": self.file_copy_performed,
            "file_write_performed": self.file_write_performed,
            "media_download_performed": self.media_download_performed,
            "automatic_classification_performed": self.automatic_classification_performed,
            "sensitive_identifier_inference_performed": self.sensitive_identifier_inference_performed,
        }
        if include_text:
            payload["existing_folder_plan_text"] = render_existing_folder_plan_text(self.existing_folder_plan)
            payload["materialize_plan_text"] = self.materialize_plan_text
            payload["materialize_result_text"] = self.materialize_result_text
            payload["folder_operations_plan_text"] = self.folder_operations_plan_text
            payload["folder_operations_result_text"] = self.folder_operations_result_text
            payload["workflow_text"] = render_end_to_end_workflow_text(self)
        return payload


def _dedupe(items: Iterable[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(str(item) for item in items if str(item).strip()))


def _read_lines(path: str | Path) -> tuple[str, ...]:
    return tuple(Path(path).read_text(encoding="utf-8").splitlines())


def build_end_to_end_config_from_files(
    *,
    tree_list_paths: Iterable[str | Path],
    database_root: str,
    case_title: str = "",
    batch_preview_path: str = "",
    write_batch_preview: bool = False,
    batch_write_confirmation: str = "",
    materialize_database: bool = False,
    materialize_confirmation: str = "",
    operations_json_path: str = "",
    execute_folder_operations: bool = False,
    folder_operations_confirmation: str = "",
) -> ProfileMediaDatabaseEndToEndConfig:
    """Build config from explicit text/JSON files selected by the caller."""

    lines: list[str] = []
    for path in tree_list_paths:
        if str(path).strip():
            lines.extend(_read_lines(path))
    return ProfileMediaDatabaseEndToEndConfig(
        folder_tree_lines=tuple(lines),
        database_root=str(database_root or ""),
        case_title=str(case_title or ""),
        batch_preview_path=str(batch_preview_path or ""),
        write_batch_preview=bool(write_batch_preview),
        batch_write_confirmation=str(batch_write_confirmation or ""),
        materialize_database=bool(materialize_database),
        materialize_confirmation=str(materialize_confirmation or ""),
        operations_json_path=str(operations_json_path or ""),
        execute_folder_operations=bool(execute_folder_operations),
        folder_operations_confirmation=str(folder_operations_confirmation or ""),
    )


def run_profile_media_database_end_to_end_workflow(
    config: ProfileMediaDatabaseEndToEndConfig,
) -> ProfileMediaDatabaseEndToEndResult:
    """Run the explicit V76H workflow with guarded writes/execution."""

    warnings: list[str] = []
    existing_plan = build_existing_folder_to_batch_plan(
        config.folder_tree_lines,
        database_root=config.database_root,
        case_title=config.case_title,
    )
    warnings.extend(existing_plan.warnings)
    existing_gui = build_existing_folder_gui_payload(existing_plan).to_dict()

    write_result: ExistingFolderBatchPreviewWriteResult | None = None
    selected_batch_paths: tuple[str, ...] = ()
    if config.write_batch_preview or config.batch_preview_path:
        if not config.batch_preview_path:
            write_result = ExistingFolderBatchPreviewWriteResult(
                status="blocked_batch_preview_path_required",
                path="",
                warning="batch_preview_path_required",
            )
            warnings.append("batch_preview_path_required")
        else:
            write_result = write_batch_preview_if_confirmed(
                existing_plan,
                config.batch_preview_path,
                confirmation_phrase=config.batch_write_confirmation,
            )
            warnings.extend([warning for warning in (write_result.warning,) if warning])
            if write_result.status == "batch_preview_written":
                selected_batch_paths = (write_result.path,)

    gui_selection: ProfileMediaDatabaseGuiSelectionResult | None = None
    if selected_batch_paths:
        gui_selection = build_database_gui_selection_from_batch_json(
            selected_batch_paths,
            database_root=config.database_root,
        )
        warnings.extend(gui_selection.warnings)

    materialize_result: ProfileMediaDatabaseMaterializeResult | None = None
    materialize_plan_text = ""
    materialize_result_text = ""
    if selected_batch_paths and (config.materialize_database or config.materialize_confirmation):
        materialize_plan = build_database_materialize_plan(
            database_root=config.database_root,
            batch_json_files=selected_batch_paths,
            execute=config.materialize_database,
            confirmation_phrase=config.materialize_confirmation,
        )
        materialize_result = apply_database_materialize_plan(materialize_plan)
        materialize_plan_text = render_database_materialize_plan_text(materialize_plan)
        materialize_result_text = render_database_materialize_result_text(materialize_result)
        warnings.extend(materialize_result.warnings)

    operations_result: ProfileMediaFolderOperationsResult | None = None
    operations_plan_text = ""
    operations_result_text = ""
    has_operations = bool(config.operations_payload or config.operations_json_path)
    if has_operations:
        folder_plan = build_folder_operations_plan(
            database_root=config.database_root,
            operations_payload=config.operations_payload,
            operations_json_path=config.operations_json_path or None,
            execute=config.execute_folder_operations,
            confirmation_phrase=config.folder_operations_confirmation,
        )
        operations_result = apply_folder_operations_plan(folder_plan)
        operations_plan_text = render_folder_operations_plan_text(folder_plan)
        operations_result_text = render_folder_operations_result_text(operations_result)
        warnings.extend(operations_result.warnings)

    refreshed_gui_selection: ProfileMediaDatabaseGuiSelectionResult | None = None
    if selected_batch_paths:
        refreshed_gui_selection = build_database_gui_selection_from_batch_json(
            selected_batch_paths,
            database_root=config.database_root,
        )
        warnings.extend(refreshed_gui_selection.warnings)

    if operations_result and operations_result.status in {"operations_applied", "partially_applied"}:
        status = "workflow_operations_applied"
    elif materialize_result and materialize_result.status in {"materialized", "partially_materialized"}:
        status = "workflow_materialized"
    elif write_result and write_result.status == "batch_preview_written":
        status = "workflow_batch_preview_written"
    elif write_result and write_result.status.startswith("blocked"):
        status = write_result.status
    else:
        status = "workflow_dry_run_preview"

    return ProfileMediaDatabaseEndToEndResult(
        status=status,
        config=config,
        existing_folder_plan=existing_plan,
        existing_folder_gui_payload=existing_gui,
        batch_preview_write_result=write_result,
        gui_selection_result=gui_selection,
        materialize_result=materialize_result,
        materialize_plan_text=materialize_plan_text,
        materialize_result_text=materialize_result_text,
        folder_operations_result=operations_result,
        folder_operations_plan_text=operations_plan_text,
        folder_operations_result_text=operations_result_text,
        refreshed_gui_selection_result=refreshed_gui_selection,
        warnings=_dedupe(warnings),
        folder_creation_performed=bool(materialize_result and materialize_result.folder_creation_performed),
        folder_move_performed=bool(operations_result and operations_result.folder_move_performed),
        folder_rename_performed=bool(operations_result and operations_result.folder_rename_performed),
        file_write_performed=bool(
            (write_result and write_result.file_write_performed)
            or (materialize_result and materialize_result.file_write_performed)
        ),
    )


def render_end_to_end_workflow_text(result: ProfileMediaDatabaseEndToEndResult) -> str:
    """Render a compact user-facing summary of a V76H workflow result."""

    payload = result.to_dict(include_text=False)
    write_status = payload.get("batch_preview_write_result") or {}
    mat = payload.get("materialize_result") or {}
    ops = payload.get("folder_operations_result") or {}
    refreshed = payload.get("refreshed_gui_selection_result") or {}
    refreshed_panel = refreshed.get("panel_state") if isinstance(refreshed, dict) else None
    lines = [
        "Profile/Media Database End-to-End Workflow",
        f"Status: {result.status}",
        f"Database root: {result.config.database_root or '(not configured)'}",
        f"Folder-tree lines: {len(result.config.folder_tree_lines)}",
        f"Source candidates: {len(result.existing_folder_plan.source_candidates)}",
        f"Profile candidates: {len(result.existing_folder_plan.profile_candidates)}",
        f"Batch preview write: {write_status.get('status', 'not_requested')}",
        f"Materialize result: {mat.get('status', 'not_requested')}",
        f"Folder operations result: {ops.get('status', 'not_requested')}",
    ]
    if isinstance(refreshed_panel, dict):
        metrics = {item.get("key"): item.get("value") for item in refreshed_panel.get("metrics", []) if isinstance(item, dict)}
        lines.append(f"Refreshed cases: {metrics.get('cases', 0)}")
        lines.append(f"Refreshed sources: {metrics.get('sources', 0)}")
        lines.append(f"Refreshed profile rows: {metrics.get('profile_rows', 0)}")
    lines.extend([
        "",
        "Safety:",
        f"- Folder scan performed: {result.folder_scan_performed}",
        f"- Folder creation performed: {result.folder_creation_performed}",
        f"- Folder move performed: {result.folder_move_performed}",
        f"- Folder rename performed: {result.folder_rename_performed}",
        f"- File copy performed: {result.file_copy_performed}",
        f"- File write performed: {result.file_write_performed}",
        f"- Media download performed: {result.media_download_performed}",
        f"- Automatic classification performed: {result.automatic_classification_performed}",
        f"- Sensitive identifier inference performed: {result.sensitive_identifier_inference_performed}",
    ])
    if result.warnings:
        lines.append("")
        lines.append("Warnings:")
        for warning in result.warnings[:40]:
            lines.append(f"- {warning}")
        if len(result.warnings) > 40:
            lines.append(f"- ... {len(result.warnings) - 40} more")
    return "\n".join(lines)


def end_to_end_workflow_payload(result: ProfileMediaDatabaseEndToEndResult, *, include_text: bool = False) -> dict[str, Any]:
    return result.to_dict(include_text=include_text)


def confirmation_phrases() -> dict[str, str]:
    """Expose exact confirmation phrases in one place for GUI wiring."""

    return {
        "write_batch_preview": PROFILE_MEDIA_EXISTING_FOLDER_BATCH_WRITE_CONFIRMATION,
        "materialize_database": PROFILE_MEDIA_DATABASE_MATERIALIZE_CONFIRMATION,
        "folder_operations": PROFILE_MEDIA_DATABASE_FOLDER_OPERATIONS_CONFIRMATION,
    }
