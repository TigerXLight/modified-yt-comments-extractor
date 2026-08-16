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

PROFILE_MEDIA_DATABASE_GUI_PANEL_SCHEMA_VERSION = "profile-media-database-gui-panel-v76c"


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
    review_lanes: tuple[ProfileMediaDatabaseGuiPanelMetric, ...] = ()
    actions: tuple[ProfileMediaDatabaseGuiPanelAction, ...] = ()
    notices: tuple[str, ...] = ()
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


def build_profile_media_database_gui_panel_state(
    *,
    mode: object = "FILES",
    database_root: object = "",
    batch_json_files: Iterable[object] | None = None,
    workbench_payload: Mapping[str, Any] | None = None,
) -> ProfileMediaDatabaseGuiPanelState:
    """Build safe main-panel state from explicit caller-supplied values only."""

    coerced_mode = "DATABASE" if str(mode).upper() == "DATABASE" else "FILES"
    batches = _batch_tuple(batch_json_files)
    root = str(database_root or _first_nonempty(workbench_payload, "database_root") or "")

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

    configured = bool(batches or workbench_payload)
    status = "ready_no_batch_json" if not configured else "success"
    subtitle = (
        "Database mode is on. Add explicit batch JSON in the next import step to populate this panel."
        if not configured
        else "Database workbench view is populated from explicit batch JSON only."
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
        ),
        review_lanes=(
            _metric("source_chain_gaps", "Source-chain gaps", _int_from_payload(workbench_payload, "source_chain_gap_count"), "high"),
            _metric("disputed_framing", "Disputed framing", _int_from_payload(workbench_payload, "disputed_framing_count"), "medium"),
            _metric("unknown_source_roles", "Unknown source roles", _int_from_payload(workbench_payload, "unknown_source_role_count"), "medium"),
            _metric("parser_warnings", "Parser warnings", _int_from_payload(workbench_payload, "parser_warning_count", "warning_count"), "medium"),
        ),
        actions=(
            _action("refresh_database_view", "Refresh view", "available", "Refresh already configured explicit batch JSON view."),
            _action("load_batch_json", "Load batch JSON", "available", "Select explicit batch JSON files for the main Database workbench."),
            _action("plan_existing_folder_import", "Plan existing folder import", "available_dry_run", "Build a dry-run batch preview from an explicit folder-tree list; no folder scan."),
            _action("materialize_case", "Materialize case", "guarded", "Requires explicit confirmation in backend materialize flow."),
            _action("review_report", "Review report", "available", "Open source-chain gaps, disputed framing, and unknown-role lanes."),
        ),
        notices=(
            "No folder scan is performed by the GUI panel.",
            "No move, rename, copy, download, classification, or sensitive inference is performed.",
            "The sidebar remains mode-only; filtering/search lives in the main Database workbench.",
        ),
    )


def gui_panel_payload(state: ProfileMediaDatabaseGuiPanelState) -> dict[str, Any]:
    """Return a JSON-safe payload for GUI tests and CLI diagnostics."""

    return state.to_dict()


def render_profile_media_database_gui_panel_text(state: ProfileMediaDatabaseGuiPanelState) -> str:
    """Render a human-readable summary for the main Database panel."""

    lines = [
        "Profile/Media Database GUI Panel",
        f"Status: {state.status}",
        f"Mode: {state.mode}",
        f"Database root: {state.database_root or '(not configured)'}",
        f"Batch JSON files: {len(state.batch_json_files)}",
        "",
        "Metrics:",
    ]
    for metric in state.metrics:
        lines.append(f"- {metric.label}: {metric.value} [{metric.severity}]")
    lines.append("")
    lines.append("Review lanes:")
    for lane in state.review_lanes:
        lines.append(f"- {lane.label}: {lane.value} [{lane.severity}]")
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
