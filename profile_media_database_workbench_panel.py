"""GUI-safe presenter for the Profile/Media Database workbench panel.

V76C is the first main-window bridge for Database mode.  This module stays
UI-neutral so the GUI can render a main Database workbench panel without doing
filesystem discovery or mutating the user's case folders.

The presenter only accepts explicit values already supplied by the caller.
It does not scan folders, create folders, move folders, rename folders, copy
media, download media, classify automatically, or infer sensitive identifiers.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Iterable, Mapping

from profile_media_database import utc_now_iso

PROFILE_MEDIA_DATABASE_GUI_PANEL_SCHEMA_VERSION = "profile-media-database-home-ui-panel-v76k2"


@dataclass(frozen=True)
class ProfileMediaDatabaseGuiPanelMetric:
    """One compact metric displayed in the main Database workbench panel."""

    key: str
    label: str
    value: int
    severity: str = "info"


@dataclass(frozen=True)
class ProfileMediaDatabaseGuiPanelAction:
    """One GUI action entry shown as available, planned, or disabled."""

    action_id: str
    label: str
    status: str = "planned"
    description: str = ""


@dataclass(frozen=True)
class ProfileMediaDatabaseGuiPanelState:
    """UI-neutral state for the main Database workbench panel."""

    mode: str = "FILES"
    database_root: str = ""
    batch_json_files: tuple[str, ...] = ()
    status: str = "database_mode_off"
    title: str = "Profile/Media Database"
    subtitle: str = "Switch DATABASE on to view the case/profile/source workbench."
    metrics: tuple[ProfileMediaDatabaseGuiPanelMetric, ...] = ()
    display_metrics: tuple[ProfileMediaDatabaseGuiPanelMetric, ...] = ()
    review_lanes: tuple[ProfileMediaDatabaseGuiPanelMetric, ...] = ()
    actions: tuple[ProfileMediaDatabaseGuiPanelAction, ...] = ()
    notices: tuple[str, ...] = ()
    source_folder_preview: Mapping[str, Any] = field(default_factory=dict)
    schema_version: str = PROFILE_MEDIA_DATABASE_GUI_PANEL_SCHEMA_VERSION
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


def _int_from_payload(payload: Mapping[str, Any] | None, *keys: str) -> int:
    if not payload:
        return 0
    for key in keys:
        try:
            value = int(payload.get(key, 0))
        except Exception:
            value = 0
        if value:
            return value
    return 0



def _int_from_nested_payload(payload: Mapping[str, Any] | None, *paths: str) -> int:
    """Read an integer from dotted payload paths, returning the first non-zero value.

    V76I uses this for GUI review lanes because the workbench bundle stores
    review totals inside dashboard/review_report children rather than always at
    the top level.  The helper is read-only and does not execute any workflow.
    """

    if not payload:
        return 0
    for path in paths:
        current: Any = payload
        parts = str(path).split('.')
        index = 0
        while index < len(parts):
            part = parts[index]
            if isinstance(current, list):
                wanted = part
                current = next((item.get('value') for item in current if isinstance(item, Mapping) and item.get('key') == wanted), None)
                index += 1
                continue
            if not isinstance(current, Mapping):
                current = None
                break
            current = current.get(part)
            index += 1
        try:
            value = int(current or 0)
        except Exception:
            value = 0
        if value:
            return value
    return 0

def _first_nonempty(payload: Mapping[str, Any] | None, *keys: str) -> str:
    if not payload:
        return ""
    for key in keys:
        value = payload.get(key, "")
        if value:
            return str(value)
    return ""


def _metric(key: str, label: str, value: object, severity: str = "info") -> ProfileMediaDatabaseGuiPanelMetric:
    try:
        numeric_value = int(value)
    except Exception:
        numeric_value = 0
    return ProfileMediaDatabaseGuiPanelMetric(key=key, label=label, value=numeric_value, severity=severity)


def _action(action_id: str, label: str, status: str, description: str) -> ProfileMediaDatabaseGuiPanelAction:
    return ProfileMediaDatabaseGuiPanelAction(
        action_id=action_id,
        label=label,
        status=status,
        description=description,
    )


def _batch_tuple(batch_json_files: Iterable[object] | None) -> tuple[str, ...]:
    if not batch_json_files:
        return ()
    return tuple(str(item) for item in batch_json_files if str(item).strip())


def _facet_count(payload: Mapping[str, Any] | None, facet_type: str, value: str) -> int:
    """Read a count from dashboard facets without inferring anything."""
    if not payload:
        return 0
    dashboard = payload.get("dashboard") if isinstance(payload, Mapping) else None
    facets = dashboard.get("facets", ()) if isinstance(dashboard, Mapping) else ()
    for facet in facets or ():
        if not isinstance(facet, Mapping):
            continue
        if str(facet.get("facet_type", "")) != facet_type:
            continue
        if str(facet.get("value", "")) != value:
            continue
        try:
            return int(facet.get("count", 0) or 0)
        except Exception:
            return 0
    return 0


def _person_count(payload: Mapping[str, Any] | None, fallback: int = 0) -> int:
    if not payload:
        return fallback
    dashboard = payload.get("dashboard") if isinstance(payload, Mapping) else None
    if isinstance(dashboard, Mapping):
        for key in ("unique_profile_count", "profile_row_count"):
            try:
                value = int(dashboard.get(key, 0) or 0)
            except Exception:
                value = 0
            if value:
                return value
    return fallback


def build_profile_media_database_gui_panel_state(
    *,
    mode: object = "FILES",
    database_root: object = "",
    batch_json_files: Iterable[object] | None = None,
    workbench_payload: Mapping[str, Any] | None = None,
    source_folder_preview: Mapping[str, Any] | None = None,
) -> ProfileMediaDatabaseGuiPanelState:
    """Build safe main-panel state from explicit caller-supplied values only."""

    coerced_mode = "DATABASE" if str(mode).upper() == "DATABASE" else "FILES"
    batches = _batch_tuple(batch_json_files)
    root = str(database_root or _first_nonempty(workbench_payload, "database_root") or "")
    preview_payload = dict(source_folder_preview or {})

    if coerced_mode != "DATABASE":
        return ProfileMediaDatabaseGuiPanelState(
            mode="FILES",
            database_root=root,
            batch_json_files=batches,
            status="database_mode_off",
            subtitle="DATABASE is off. FILES remains the active local-session mode.",
            metrics=(
                _metric("cases", "Cases", 0),
                _metric("sources", "Sources", 0),
                _metric("profile_rows", "Profile rows", 0),
                _metric("review_items", "Review items", 0),
            ),
            display_metrics=(
                _metric("primary_sources", "👤 Primary", 0),
                _metric("secondary_sources", "👥 Secondary", 0),
                _metric("tertiary_sources", "👥+ Tertiary", 0),
                _metric("persons", "Persons", 0),
                _metric("review_items", "Review", 0),
            ),
            review_lanes=(
                _metric("source_chain_gaps", "Source-chain gaps", 0, "none"),
                _metric("disputed_framing", "Disputed framing", 0, "none"),
                _metric("unknown_source_roles", "Unknown source roles", 0, "none"),
            ),
            actions=(
                _action("turn_database_on", "Turn DATABASE on", "available", "Use the sidebar DATABASE switch."),
            ),
            notices=("No Database work is run while FILES mode is active.",),
        )

    case_count = _int_from_payload(workbench_payload, "index_case_count", "case_count")
    source_count = _int_from_payload(workbench_payload, "index_source_count", "source_count")
    profile_rows = _int_from_payload(workbench_payload, "index_profile_row_count", "profile_row_count")
    matched_sources = _int_from_payload(workbench_payload, "matched_source_count")
    matched_profiles = _int_from_payload(workbench_payload, "matched_profile_count")
    navigation_targets = _int_from_payload(workbench_payload, "navigation_target_count", "target_count")
    review_items = _int_from_payload(workbench_payload, "review_item_count")
    saved_views = _int_from_payload(workbench_payload, "saved_view_count", "view_count")
    preview_sources = len(preview_payload.get("source_urls") or ())
    preview_segments = len(preview_payload.get("source_role_segments") or ())
    preview_media = len(preview_payload.get("media_references") or ())
    primary_sources = _facet_count(workbench_payload, "source_role", "PRIMARY_SELF_AUTHORED_SCOPE")
    secondary_sources = _facet_count(workbench_payload, "source_role", "SECONDARY_WITNESS_ACCOUNT")
    tertiary_sources = _facet_count(workbench_payload, "source_role", "TERTIARY_PROPAGATED_SOURCE")
    persons = _person_count(workbench_payload, profile_rows)

    configured = bool(batches or workbench_payload or preview_payload)
    status = "ready_for_import" if not configured else "success"
    subtitle = (
        "HOME mode is on. Add or import source material, then SAVE reviewed structure into HOME."
        if not configured
        else "HOME repository view is populated from selected source material and saved index metadata."
    )

    return ProfileMediaDatabaseGuiPanelState(
        mode="DATABASE",
        database_root=root,
        batch_json_files=batches,
        status=status,
        subtitle=subtitle,
        metrics=(
            _metric("cases", "Cases", case_count),
            _metric("sources", "Sources", source_count),
            _metric("profile_rows", "Profile rows", profile_rows),
            _metric("matched_sources", "Matched sources", matched_sources),
            _metric("matched_profiles", "Matched profiles", matched_profiles),
            _metric("navigation_targets", "Navigation targets", navigation_targets),
            _metric("review_items", "Review items", review_items, "high" if review_items else "info"),
            _metric("saved_views", "Saved views", saved_views),
            _metric("source_folder_sources", "Source folder URLs", preview_sources),
            _metric("source_folder_segments", "Source role segments", preview_segments, "high" if preview_segments else "info"),
            _metric("source_folder_media_references", "Media references", preview_media),
        ),
        display_metrics=(
            _metric("primary_sources", "👤 Primary", primary_sources),
            _metric("secondary_sources", "👥 Secondary", secondary_sources),
            _metric("tertiary_sources", "👥+ Tertiary", tertiary_sources),
            _metric("persons", "Persons", persons),
            _metric("review_items", "Review", review_items, "high" if review_items else "info"),
        ),
        review_lanes=(
            _metric(
                "source_chain_gaps",
                "Source-chain gaps",
                _int_from_nested_payload(
                    workbench_payload,
                    "source_chain_gap_count",
                    "dashboard.metrics.source_chain_gaps",
                    "dashboard.source_chain_gap_count",
                    "review_report.source_chain_gap_count",
                ),
                "high",
            ),
            _metric(
                "disputed_framing",
                "Disputed framing",
                _int_from_nested_payload(
                    workbench_payload,
                    "disputed_framing_count",
                    "dashboard.metrics.disputed_framing",
                    "review_report.disputed_framing_count",
                ),
                "medium",
            ),
            _metric(
                "unknown_source_roles",
                "Unknown source roles",
                _int_from_nested_payload(
                    workbench_payload,
                    "unknown_source_role_count",
                    "dashboard.metrics.unknown_source_roles",
                    "review_report.unknown_source_role_count",
                ),
                "medium",
            ),
            _metric(
                "parser_warnings",
                "Parser warnings",
                _int_from_nested_payload(
                    workbench_payload,
                    "parser_warning_count",
                    "dashboard.metrics.parser_warnings",
                    "review_report.parser_warning_count",
                    "warning_count",
                ),
                "medium",
            ),
        ),
        actions=(
            _action("refresh_database_view", "Sync HOME", "available", "Refresh the current HOME view internally after imports or saves."),
            _action("add_import_source_folder_preview", "Add / Import source folder", "available_preview", "Select one source folder and generate a review preview; no HOME scan, media download, or classification."),
            _action("load_batch_json", "Add / Import", "available", "Add source files, pasted URLs, dragged media, or a saved import package."),
            _action("plan_existing_folder_import", "Plan folder import", "available_dry_run", "Build a dry-run preview from an explicit folder-tree list; no folder scan."),
            _action("save_to_home_repository", "Save to HOME", "guarded_v76f", "Save reviewed folders and metadata under the selected HOME repository only."),
            _action("review_folder_operations", "Review moves", "guarded_v76g", "Review explicit folder rename/move operations; execution requires confirmation."),
            _action("reconcile_batch_after_folder_operations", "Update saved index", "guarded_v76i", "Write a standalone reconciled index preview after reviewed folder operations."),
            _action("run_end_to_end_workflow_check", "Check workflow", "available_v76h", "Run the explicit end-to-end readiness workflow over selected inputs."),
            _action("review_report", "Review items", "available", "Open the aggregated review list."),
        ),
        notices=(
            "HOME is a managed repository. The app saves reviewed folders/indexes; it does not require users to understand JSON.",
            "Add / Import can generate a selected source-folder preview from source.txt, local article files, and media references.",
            "No media download, automatic classification, or sensitive inference is performed.",
            "The left sidebar shows Primary, Secondary, Tertiary, Persons, and Review summary counts.",
        ),
        source_folder_preview=preview_payload,
    )


def gui_panel_payload(state: ProfileMediaDatabaseGuiPanelState) -> dict[str, Any]:
    """Return a JSON-safe payload for GUI tests and CLI diagnostics."""

    return state.to_dict()


def render_profile_media_database_gui_panel_text(state: ProfileMediaDatabaseGuiPanelState) -> str:
    """Render a human-readable summary for the main Database panel."""

    lines = [
        "Profile/Media HOME Repository Panel",
        f"Status: {state.status}",
        f"Mode: {state.mode}",
        f"Database root: {state.database_root or '(not configured)'}",
        f"Import files: {len(state.batch_json_files)}",
        f"Source folder preview: {'yes' if state.source_folder_preview else 'no'}",
        "",
        "Display metrics:",
    ]
    for metric in state.display_metrics:
        lines.append(f"- {metric.label}: {metric.value} [{metric.severity}]")
    lines.append("")
    lines.append("Hidden/internal counters:")
    for metric in state.metrics:
        lines.append(f"- {metric.label}: {metric.value} [{metric.severity}]")
    lines.append("")
    lines.append("Review lanes:")
    for lane in state.review_lanes:
        lines.append(f"- {lane.label}: {lane.value} [{lane.severity}]")
    if state.source_folder_preview:
        preview = state.source_folder_preview
        lines.append("")
        lines.append("Add / Import source folder preview:")
        lines.append(f"- Source folder: {preview.get('source_folder') or '(not supplied)'}")
        lines.append(f"- Source URLs: {len(preview.get('source_urls') or [])}")
        lines.append(f"- Source role segments: {len(preview.get('source_role_segments') or [])}")
        lines.append(f"- Final source role decision: {preview.get('final_source_role_decision')}")
    lines.append("")
    lines.append("Actions:")
    for action in state.actions:
        lines.append(f"- {action.label}: {action.status}")
    lines.append("")
    lines.append("Safety:")
    lines.append(f"- Folder scan performed: {state.folder_scan_performed}")
    lines.append(f"- Folder creation performed: {state.folder_creation_performed}")
    lines.append(f"- Folder move performed: {state.folder_move_performed}")
    lines.append(f"- Folder rename performed: {state.folder_rename_performed}")
    lines.append(f"- File copy performed: {state.file_copy_performed}")
    lines.append(f"- File write performed: {state.file_write_performed}")
    lines.append(f"- Media download performed: {state.media_download_performed}")
    lines.append(f"- Automatic classification performed: {state.automatic_classification_performed}")
    lines.append(f"- Sensitive identifier inference performed: {state.sensitive_identifier_inference_performed}")
    if state.notices:
        lines.append("")
        lines.append("Notices:")
        for notice in state.notices:
            lines.append(f"- {notice}")
    return "\n".join(lines)
