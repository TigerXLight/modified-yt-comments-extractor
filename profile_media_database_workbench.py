"""Workbench bundle for Profile/Media Database mode.

V76A combines the read-only Database session, dashboard, navigation, review
report, and saved-view helpers into one UI-neutral workbench state.  This is
for the future main Database mode area.  The sidebar remains only the square
DATABASE On/Off toggle.

The workbench only consumes explicit batch JSON files supplied by the caller.
It does not discover files by scanning folders.  It does not create case
workspaces, move folders, rename folders, copy media, download media, classify
automatically, or infer sensitive identifiers.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping

from profile_media_database import sanitize_path_part, utc_now_iso
from profile_media_database_dashboard import (
    ProfileMediaDashboard,
    build_dashboard_from_batch_json_files,
    dashboard_payload,
    render_dashboard_text,
)
from profile_media_database_navigation import (
    ProfileMediaNavigationIndex,
    build_navigation_index_from_batch_json_files,
    navigation_payload,
    render_navigation_text,
)
from profile_media_database_review_report import (
    ProfileMediaReviewReport,
    build_review_report_from_session,
    render_review_report_text,
)
from profile_media_database_saved_views import (
    ProfileMediaSavedView,
    ProfileMediaSavedViewLibrary,
    render_saved_view_library_text,
    upsert_saved_view,
)
from profile_media_database_session import (
    ProfileMediaDatabaseExportPlan,
    ProfileMediaDatabaseSessionConfig,
    ProfileMediaDatabaseSessionSnapshot,
    apply_database_export_plan,
    build_database_export_plan,
    build_database_session_snapshot,
    render_database_session_text,
)

PROFILE_MEDIA_DATABASE_WORKBENCH_SCHEMA_VERSION = "profile-media-database-workbench-v76a"
PROFILE_MEDIA_DATABASE_WORKBENCH_EXPORT_SCHEMA_VERSION = "profile-media-database-workbench-export-v76a"
PROFILE_MEDIA_DATABASE_WORKBENCH_EXPORT_CONFIRMATION = "EXPORT_PROFILE_MEDIA_DATABASE_WORKBENCH"


@dataclass(frozen=True)
class ProfileMediaDatabaseWorkbenchState:
    """Full read-only state for a Database-mode workbench."""

    session: ProfileMediaDatabaseSessionSnapshot
    dashboard: ProfileMediaDashboard
    navigation: ProfileMediaNavigationIndex
    review_report: ProfileMediaReviewReport
    saved_views: ProfileMediaSavedViewLibrary
    schema_version: str = PROFILE_MEDIA_DATABASE_WORKBENCH_SCHEMA_VERSION
    created_at_utc: str = field(default_factory=utc_now_iso)
    status: str = "success"
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

    def to_dict(self, *, include_text: bool = False) -> dict[str, Any]:
        warnings = list(self.warnings)
        warnings.extend(self.session.warnings)
        warnings.extend(self.dashboard.warnings)
        warnings.extend(self.navigation.warnings)
        data = {
            "schema_version": self.schema_version,
            "created_at_utc": self.created_at_utc,
            "status": self.status,
            "session": self.session.to_dict(include_view_text=include_text),
            "dashboard": dashboard_payload(self.dashboard, include_text=include_text),
            "navigation": navigation_payload(self.navigation, include_text=include_text),
            "review_report": self.review_report.to_dict(),
            "saved_views": self.saved_views.to_dict(),
            "database_root": self.session.config.database_root,
            "batch_json_files": list(self.session.config.batch_json_files),
            "index_case_count": self.session.to_dict()["index_case_count"],
            "index_source_count": self.session.to_dict()["index_source_count"],
            "index_profile_row_count": self.session.to_dict()["index_profile_row_count"],
            "matched_source_count": self.session.to_dict()["matched_source_count"],
            "matched_profile_count": self.session.to_dict()["matched_profile_count"],
            "review_item_count": len(self.review_report.items),
            "saved_view_count": len(self.saved_views.views),
            "navigation_target_count": len(self.navigation.targets),
            "folder_scan_performed": self.folder_scan_performed,
            "folder_creation_performed": self.folder_creation_performed,
            "folder_move_performed": self.folder_move_performed,
            "folder_rename_performed": self.folder_rename_performed,
            "file_copy_performed": self.file_copy_performed,
            "file_write_performed": self.file_write_performed,
            "media_download_performed": self.media_download_performed,
            "automatic_classification_performed": self.automatic_classification_performed,
            "sensitive_identifier_inference_performed": self.sensitive_identifier_inference_performed,
            "warnings": sorted(set(warnings)),
        }
        data["warning_count"] = len(data["warnings"])
        if include_text:
            data["workbench_text"] = render_workbench_text(self)
        return data


@dataclass(frozen=True)
class ProfileMediaWorkbenchExportPlan:
    """Guarded export plan for a full workbench bundle."""

    output_dir: str
    workbench_json_path: str
    workbench_text_path: str
    dashboard_json_path: str
    navigation_json_path: str
    review_json_path: str
    saved_views_json_path: str
    execute_requested: bool = False
    confirmation_phrase: str = ""
    schema_version: str = PROFILE_MEDIA_DATABASE_WORKBENCH_EXPORT_SCHEMA_VERSION
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
        return self.confirmation_phrase == PROFILE_MEDIA_DATABASE_WORKBENCH_EXPORT_CONFIRMATION

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["confirmation_required"] = self.execute_requested
        data["confirmation_valid"] = self.confirmation_valid
        data["confirmation_phrase_expected"] = PROFILE_MEDIA_DATABASE_WORKBENCH_EXPORT_CONFIRMATION if self.execute_requested else ""
        return data


@dataclass(frozen=True)
class ProfileMediaWorkbenchExportResult:
    """Result of applying a workbench export plan."""

    status: str
    output_dir: str
    written_files: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    schema_version: str = PROFILE_MEDIA_DATABASE_WORKBENCH_EXPORT_SCHEMA_VERSION
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


def build_default_workbench_saved_views(config: ProfileMediaDatabaseSessionConfig) -> ProfileMediaSavedViewLibrary:
    """Build useful default saved views without writing them to disk."""

    library = ProfileMediaSavedViewLibrary()
    base = config.to_dict()
    presets = [
        ("All Database Records", "All explicit batch records in Database mode.", {}),
        ("Source-chain gaps", "Sources where the original source is missing or not yet cited.", {"source_chain_gap": True}),
        ("Disputed framing", "Sources where framing/context is disputed by the original author or uploader.", {"disputed_framing": True}),
        ("Unknown source roles", "Rows needing source-role review.", {"source_role": "UNKNOWN"}),
        ("Parser warnings", "Profile rows with missing or malformed fields.", {"has_parser_warnings": True}),
    ]
    for name, description, overrides in presets:
        payload = dict(base)
        payload.update(overrides)
        view = ProfileMediaSavedView(
            name=name,
            description=description,
            config=ProfileMediaDatabaseSessionConfig(**{key: payload.get(key, getattr(config, key)) for key in config.to_dict().keys() if key != "schema_version"}),
        )
        library = upsert_saved_view(library, view)
    return library


def build_workbench_state(config: ProfileMediaDatabaseSessionConfig, *, saved_views: ProfileMediaSavedViewLibrary | None = None) -> ProfileMediaDatabaseWorkbenchState:
    """Build the combined Database-mode workbench state from explicit batch JSON files."""

    session = build_database_session_snapshot(config)
    if config.batch_json_files:
        dashboard = build_dashboard_from_batch_json_files(config.batch_json_files)
        navigation = build_navigation_index_from_batch_json_files(config.batch_json_files)
    else:
        dashboard = ProfileMediaDashboard(config.database_root, (), (), (), (), (), status="no_batch_json_files")
        navigation = ProfileMediaNavigationIndex(config.database_root, (), status="no_batch_json_files")
    review_report = build_review_report_from_session(session)
    library = saved_views or build_default_workbench_saved_views(config)
    warnings: list[str] = []
    warnings.extend(session.warnings)
    warnings.extend(dashboard.warnings)
    warnings.extend(navigation.warnings)
    return ProfileMediaDatabaseWorkbenchState(
        session=session,
        dashboard=dashboard,
        navigation=navigation,
        review_report=review_report,
        saved_views=library,
        status=session.status,
        warnings=tuple(sorted(set(warnings))),
    )


def render_workbench_text(workbench: ProfileMediaDatabaseWorkbenchState) -> str:
    """Render a complete workbench snapshot for logs, CLI proof, and export."""

    data = workbench.to_dict(include_text=False)
    lines = [
        "Profile/Media Database Workbench",
        f"Status: {workbench.status}",
        f"Database root: {data['database_root']}",
        f"Batch JSON files: {len(data['batch_json_files'])}",
        f"Index cases: {data['index_case_count']}",
        f"Index sources: {data['index_source_count']}",
        f"Index profile rows: {data['index_profile_row_count']}",
        f"Matched sources: {data['matched_source_count']}",
        f"Matched profiles: {data['matched_profile_count']}",
        f"Review items: {data['review_item_count']}",
        f"Navigation targets: {data['navigation_target_count']}",
        f"Saved views: {data['saved_view_count']}",
        "Folder scan performed: false",
        "Folder creation performed: false",
        "Folder move performed: false",
        "Folder rename performed: false",
        "File copy performed: false",
        "File write performed: false",
        "Media download performed: false",
        "Automatic classification performed: false",
        "Sensitive identifier inference performed: false",
        "",
        render_database_session_text(workbench.session),
        "",
        render_dashboard_text(workbench.dashboard),
        "",
        render_navigation_text(workbench.navigation),
        "",
        render_review_report_text(workbench.review_report),
        "",
        render_saved_view_library_text(workbench.saved_views),
    ]
    return "\n".join(lines)


def build_workbench_export_plan(
    output_dir: str | Path,
    *,
    execute: bool = False,
    confirmation_phrase: str = "",
    basename: str = "database_workbench",
) -> ProfileMediaWorkbenchExportPlan:
    """Plan a guarded export of the full Database workbench bundle."""

    root = Path(output_dir)
    base = sanitize_path_part(basename or "database_workbench", fallback="database_workbench")
    return ProfileMediaWorkbenchExportPlan(
        output_dir=str(root),
        workbench_json_path=str(root / f"{base}.json"),
        workbench_text_path=str(root / f"{base}.txt"),
        dashboard_json_path=str(root / f"{base}_dashboard.json"),
        navigation_json_path=str(root / f"{base}_navigation.json"),
        review_json_path=str(root / f"{base}_review.json"),
        saved_views_json_path=str(root / f"{base}_saved_views.json"),
        execute_requested=bool(execute),
        confirmation_phrase=confirmation_phrase,
    )


def apply_workbench_export_plan(plan: ProfileMediaWorkbenchExportPlan, workbench: ProfileMediaDatabaseWorkbenchState) -> ProfileMediaWorkbenchExportResult:
    """Apply a guarded workbench export plan.  Default behavior is dry-run."""

    if not plan.execute_requested:
        return ProfileMediaWorkbenchExportResult(
            status="planned_dry_run",
            output_dir=plan.output_dir,
            warnings=("dry_run_no_database_workbench_export_written",),
        )
    if not plan.confirmation_valid:
        return ProfileMediaWorkbenchExportResult(
            status="blocked_confirmation_required",
            output_dir=plan.output_dir,
            warnings=(f"confirmation_required:{PROFILE_MEDIA_DATABASE_WORKBENCH_EXPORT_CONFIRMATION}",),
        )
    root = Path(plan.output_dir)
    root.mkdir(parents=True, exist_ok=True)
    write_payloads = {
        plan.workbench_json_path: workbench.to_dict(include_text=True),
        plan.dashboard_json_path: dashboard_payload(workbench.dashboard, include_text=True),
        plan.navigation_json_path: navigation_payload(workbench.navigation, include_text=True),
        plan.review_json_path: workbench.review_report.to_dict(),
        plan.saved_views_json_path: workbench.saved_views.to_dict(),
    }
    for path, payload in write_payloads.items():
        Path(path).write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    Path(plan.workbench_text_path).write_text(render_workbench_text(workbench) + "\n", encoding="utf-8")
    written = tuple(list(write_payloads.keys()) + [plan.workbench_text_path])
    return ProfileMediaWorkbenchExportResult(
        status="success",
        output_dir=plan.output_dir,
        written_files=written,
        folder_creation_performed=True,
        file_write_performed=True,
    )


def workbench_payload(
    workbench: ProfileMediaDatabaseWorkbenchState,
    *,
    include_text: bool = False,
    export_plan: ProfileMediaWorkbenchExportPlan | None = None,
    export_result: ProfileMediaWorkbenchExportResult | None = None,
    legacy_export_plan: ProfileMediaDatabaseExportPlan | None = None,
) -> dict[str, Any]:
    """Return a CLI-friendly payload for the combined workbench."""

    data = workbench.to_dict(include_text=include_text)
    if include_text:
        data["workbench_text"] = render_workbench_text(workbench)
    if export_plan is not None:
        data["workbench_export_plan"] = export_plan.to_dict()
    if export_result is not None:
        data["workbench_export_result"] = export_result.to_dict()
    if legacy_export_plan is not None:
        data["database_view_export_plan"] = legacy_export_plan.to_dict()
    return data
