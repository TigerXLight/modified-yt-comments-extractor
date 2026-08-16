"""GUI controller helpers for the Profile/Media Database workbench.

V76D coordinates explicit batch JSON import, optional GUI-state persistence,
and safe panel/workbench payload creation.  It is intentionally UI-neutral so
main.py can stay thin and tests can prove that Database mode does not become a
sidebar filter, folder scanner, media downloader, auto-classifier, or sensitive
identifier inference path.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping

from profile_media_database import utc_now_iso
from profile_media_database_batch_import_assistant import (
    ProfileMediaDatabaseBatchImportResult,
    apply_batch_import_plan,
    batch_import_result_payload,
    build_batch_import_plan,
)
from profile_media_database_gui_state_store import (
    PROFILE_MEDIA_DATABASE_GUI_STATE_SAVE_CONFIRMATION,
    ProfileMediaDatabaseGuiStateConfig,
    ProfileMediaDatabaseGuiStateIoResult,
    build_gui_state_config,
    clear_gui_state_config,
    gui_state_payload,
    load_gui_state_config,
    save_gui_state_config,
)
from profile_media_database_session import ProfileMediaDatabaseSessionConfig
from profile_media_database_workbench import build_workbench_state, workbench_payload
from profile_media_database_workbench_panel import (
    ProfileMediaDatabaseGuiPanelState,
    build_profile_media_database_gui_panel_state,
    gui_panel_payload,
)

PROFILE_MEDIA_DATABASE_GUI_CONTROLLER_SCHEMA_VERSION = "profile-media-database-gui-controller-v76d"


@dataclass(frozen=True)
class ProfileMediaDatabaseGuiSelectionResult:
    """Result for loading/clearing Database GUI selection state."""

    status: str
    database_root: str = ""
    batch_json_files: tuple[str, ...] = ()
    import_result: ProfileMediaDatabaseBatchImportResult | None = None
    state_config: ProfileMediaDatabaseGuiStateConfig | None = None
    state_io_result: ProfileMediaDatabaseGuiStateIoResult | None = None
    workbench_payload: Mapping[str, Any] | None = None
    panel_state: ProfileMediaDatabaseGuiPanelState | None = None
    warnings: tuple[str, ...] = ()
    schema_version: str = PROFILE_MEDIA_DATABASE_GUI_CONTROLLER_SCHEMA_VERSION
    created_at_utc: str = field(default_factory=utc_now_iso)
    folder_scan_performed: bool = False
    folder_creation_performed: bool = False
    folder_move_performed: bool = False
    folder_rename_performed: bool = False
    file_copy_performed: bool = False
    media_download_performed: bool = False
    automatic_classification_performed: bool = False
    sensitive_identifier_inference_performed: bool = False

    def to_dict(self, *, include_text: bool = False) -> dict[str, Any]:
        payload = {
            "schema_version": self.schema_version,
            "created_at_utc": self.created_at_utc,
            "status": self.status,
            "database_root": self.database_root,
            "batch_json_files": list(self.batch_json_files),
            "batch_json_file_count": len(self.batch_json_files),
            "import_result": batch_import_result_payload(self.import_result, include_text=include_text) if self.import_result else None,
            "state_config": gui_state_payload(self.state_config) if self.state_config else None,
            "state_io_result": self.state_io_result.to_dict() if self.state_io_result else None,
            "workbench_payload": dict(self.workbench_payload) if self.workbench_payload else None,
            "panel_state": gui_panel_payload(self.panel_state) if self.panel_state else None,
            "warnings": list(self.warnings),
            "warning_count": len(self.warnings),
            "folder_scan_performed": self.folder_scan_performed,
            "folder_creation_performed": self.folder_creation_performed,
            "folder_move_performed": self.folder_move_performed,
            "folder_rename_performed": self.folder_rename_performed,
            "file_copy_performed": self.file_copy_performed,
            "media_download_performed": self.media_download_performed,
            "automatic_classification_performed": self.automatic_classification_performed,
            "sensitive_identifier_inference_performed": self.sensitive_identifier_inference_performed,
        }
        if include_text and self.panel_state:
            from profile_media_database_workbench_panel import render_profile_media_database_gui_panel_text

            payload["panel_text"] = render_profile_media_database_gui_panel_text(self.panel_state)
        return payload


def _build_workbench_payload_from_config(config: ProfileMediaDatabaseGuiStateConfig) -> dict[str, Any] | None:
    if not config.batch_json_files:
        return None
    session_config = config.to_session_config()
    return workbench_payload(build_workbench_state(session_config), include_text=False)


def build_database_gui_selection_from_batch_json(
    batch_json_files: Iterable[object] | None,
    *,
    database_root: object = "",
    state_path: object | None = None,
    persist_state: bool = False,
    confirmation_phrase: str = "",
) -> ProfileMediaDatabaseGuiSelectionResult:
    """Validate explicit batch JSON files and build GUI panel/workbench payload."""

    import_plan = build_batch_import_plan(batch_json_files, database_root=database_root)
    import_result = apply_batch_import_plan(import_plan)
    accepted_paths = import_result.batch_json_files
    root = import_result.database_root or str(database_root or "")
    status = import_result.status
    warnings = list(import_result.warnings)

    config = build_gui_state_config(
        database_root=root,
        batch_json_files=accepted_paths,
        mode="DATABASE",
        last_import_status=status,
    )

    state_io: ProfileMediaDatabaseGuiStateIoResult | None = None
    if persist_state:
        state_io = save_gui_state_config(
            config,
            state_path,
            execute=True,
            confirmation_phrase=confirmation_phrase or PROFILE_MEDIA_DATABASE_GUI_STATE_SAVE_CONFIRMATION,
        )
        warnings.extend(state_io.warnings)

    workbench = _build_workbench_payload_from_config(config)
    panel = build_profile_media_database_gui_panel_state(
        mode="DATABASE",
        database_root=config.database_root,
        batch_json_files=config.batch_json_files,
        workbench_payload=workbench,
    )

    return ProfileMediaDatabaseGuiSelectionResult(
        status=status,
        database_root=config.database_root,
        batch_json_files=config.batch_json_files,
        import_result=import_result,
        state_config=config,
        state_io_result=state_io,
        workbench_payload=workbench,
        panel_state=panel,
        warnings=tuple(warnings),
    )


def build_database_gui_selection_from_saved_state(
    *,
    state_path: object | None = None,
) -> ProfileMediaDatabaseGuiSelectionResult:
    """Load persisted explicit GUI state and rebuild the safe panel payload."""

    state_io = load_gui_state_config(state_path)
    if not state_io.config:
        panel = build_profile_media_database_gui_panel_state(mode="DATABASE", database_root="", batch_json_files=())
        return ProfileMediaDatabaseGuiSelectionResult(
            status=state_io.status,
            state_io_result=state_io,
            panel_state=panel,
            warnings=state_io.warnings,
        )

    config = state_io.config
    import_result: ProfileMediaDatabaseBatchImportResult | None = None
    warnings = list(state_io.warnings)
    if config.batch_json_files:
        import_plan = build_batch_import_plan(config.batch_json_files, database_root=config.database_root)
        import_result = apply_batch_import_plan(import_plan)
        warnings.extend(import_result.warnings)
        config = build_gui_state_config(
            database_root=import_result.database_root or config.database_root,
            batch_json_files=import_result.batch_json_files,
            mode=config.mode,
            profile_name=config.profile_name,
            case_title=config.case_title,
            source_bucket=config.source_bucket,
            source_role=config.source_role,
            claim_basis=config.claim_basis,
            currentness_status=config.currentness_status,
            text=config.text,
            source_chain_gap=config.source_chain_gap,
            disputed_framing=config.disputed_framing,
            has_parser_warnings=config.has_parser_warnings,
            limit=config.limit,
            last_import_status=import_result.status,
        )

    workbench = _build_workbench_payload_from_config(config)
    panel = build_profile_media_database_gui_panel_state(
        mode=config.mode,
        database_root=config.database_root,
        batch_json_files=config.batch_json_files,
        workbench_payload=workbench,
    )
    status = "success" if workbench else (import_result.status if import_result else state_io.status)
    return ProfileMediaDatabaseGuiSelectionResult(
        status=status,
        database_root=config.database_root,
        batch_json_files=config.batch_json_files,
        import_result=import_result,
        state_config=config,
        state_io_result=state_io,
        workbench_payload=workbench,
        panel_state=panel,
        warnings=tuple(warnings),
    )


def build_database_gui_clear_selection(
    *,
    state_path: object | None = None,
    clear_persisted_state: bool = False,
    confirmation_phrase: str = "",
) -> ProfileMediaDatabaseGuiSelectionResult:
    """Clear in-memory selection and optionally clear the persisted GUI state file."""

    state_io: ProfileMediaDatabaseGuiStateIoResult | None = None
    if clear_persisted_state:
        state_io = clear_gui_state_config(state_path, execute=True, confirmation_phrase=confirmation_phrase)
    panel = build_profile_media_database_gui_panel_state(mode="DATABASE", database_root="", batch_json_files=())
    warnings = state_io.warnings if state_io else ()
    return ProfileMediaDatabaseGuiSelectionResult(
        status="cleared",
        state_io_result=state_io,
        panel_state=panel,
        warnings=warnings,
    )


def database_gui_selection_result_payload(result: ProfileMediaDatabaseGuiSelectionResult, *, include_text: bool = False) -> dict[str, Any]:
    return result.to_dict(include_text=include_text)


def render_database_gui_selection_text(result: ProfileMediaDatabaseGuiSelectionResult) -> str:
    lines = [
        "Profile/Media Database GUI Selection",
        f"Status: {result.status}",
        f"Database root: {result.database_root or '(not configured)'}",
        f"Batch JSON files: {len(result.batch_json_files)}",
        f"Folder scan performed: {result.folder_scan_performed}",
        f"Folder creation performed: {result.folder_creation_performed}",
        f"Folder move performed: {result.folder_move_performed}",
        f"Folder rename performed: {result.folder_rename_performed}",
        f"File copy performed: {result.file_copy_performed}",
        f"Media download performed: {result.media_download_performed}",
        f"Automatic classification performed: {result.automatic_classification_performed}",
        f"Sensitive identifier inference performed: {result.sensitive_identifier_inference_performed}",
    ]
    if result.state_io_result:
        lines.append(f"State IO: {result.state_io_result.status}")
    if result.panel_state:
        lines.append("")
        lines.append(f"Panel: {result.panel_state.status}")
        for metric in result.panel_state.metrics:
            lines.append(f"- {metric.label}: {metric.value}")
    return "\n".join(lines)
