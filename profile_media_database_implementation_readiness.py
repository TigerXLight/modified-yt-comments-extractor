"""Implementation readiness reporting for Profile/Media Database mode.

V76B converts the accumulated V75/V76 backend planning into a practical status
report.  The report distinguishes what is already implemented from what remains
before a full GUI workflow can be treated as complete.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Mapping

from profile_media_database import utc_now_iso

PROFILE_MEDIA_DATABASE_READINESS_SCHEMA_VERSION = "profile-media-database-implementation-readiness-v76b"


@dataclass(frozen=True)
class ProfileMediaReadinessItem:
    """One implementation readiness item."""

    area: str
    status: str
    summary: str
    evidence: tuple[str, ...] = ()
    next_action: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ProfileMediaImplementationReadinessReport:
    """Current readiness state for implementing the Database mode GUI workflow."""

    items: tuple[ProfileMediaReadinessItem, ...]
    schema_version: str = PROFILE_MEDIA_DATABASE_READINESS_SCHEMA_VERSION
    created_at_utc: str = field(default_factory=utc_now_iso)
    status: str = "ready_for_gui_panel_integration"
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

    def to_dict(self) -> dict[str, Any]:
        complete = [item for item in self.items if item.status in {"complete", "ready"}]
        pending = [item for item in self.items if item.status not in {"complete", "ready"}]
        return {
            "schema_version": self.schema_version,
            "created_at_utc": self.created_at_utc,
            "status": self.status,
            "item_count": len(self.items),
            "complete_or_ready_count": len(complete),
            "pending_count": len(pending),
            "items": [item.to_dict() for item in self.items],
            "ready_for_gui_panel": self.status == "ready_for_gui_panel_integration" and not self.warnings,
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


def build_implementation_readiness_report(regression_payload: Mapping[str, Any] | None = None) -> ProfileMediaImplementationReadinessReport:
    """Build a readiness report from the latest regression payload."""

    payload = dict(regression_payload or {})
    status = str(payload.get("status", "success"))
    safety_status = str(payload.get("safety_audit", {}).get("status", "passed")) if isinstance(payload.get("safety_audit"), Mapping) else "passed"
    workbench_status = str(payload.get("workbench", {}).get("status", "success")) if isinstance(payload.get("workbench"), Mapping) else "success"
    warnings: list[str] = []
    if status != "success":
        warnings.append(f"regression_status:{status}")
    if safety_status != "passed":
        warnings.append(f"safety_status:{safety_status}")
    if workbench_status != "success":
        warnings.append(f"workbench_status:{workbench_status}")

    items = (
        ProfileMediaReadinessItem(
            area="Sidebar mode",
            status="complete",
            summary="DATABASE On/Off is a persistent mode toggle; it is not a sidebar preview or sidebar filter.",
            evidence=("profile_media_database_runtime", "profile_media_database_mode"),
        ),
        ProfileMediaReadinessItem(
            area="Case/source/profile model",
            status="complete",
            summary="Case workspaces, source intake records, profile intake records, case manifests, materialization planning, and batch JSON are implemented as backend models.",
            evidence=("profile_media_case_workspace", "profile_media_source_intake", "profile_media_profile_intake", "profile_media_case_manifest", "profile_media_case_materialize", "profile_media_case_batch"),
        ),
        ProfileMediaReadinessItem(
            area="Database read model",
            status="complete",
            summary="Index, search, mode view, session snapshot, saved views, review report, dashboard, navigation, and workbench state are implemented.",
            evidence=("profile_media_database_index", "profile_media_database_search", "profile_media_database_mode", "profile_media_database_session", "profile_media_database_saved_views", "profile_media_database_review_report", "profile_media_database_dashboard", "profile_media_database_navigation", "profile_media_database_workbench"),
        ),
        ProfileMediaReadinessItem(
            area="Safety invariants",
            status="ready" if safety_status == "passed" else "blocked",
            summary="Default integration path remains read-only/planning-only and prohibits scanning, moving, renaming, copying media, media downloading, auto-classification, and sensitive identifier inference.",
            evidence=("profile_media_database_safety_invariants",),
            next_action="Repair any failed safety observation before GUI wiring." if safety_status != "passed" else "Carry invariant checks into GUI smoke tests.",
        ),
        ProfileMediaReadinessItem(
            area="Main GUI Database workbench panel",
            status="ready",
            summary="Backend state now has enough sections and navigation targets for a main Database-mode panel: dashboard, review lanes, cases, sources, profiles, and saved views.",
            evidence=("profile_media_database_workbench", "profile_media_database_navigation"),
            next_action="Wire a main panel renderer without adding sidebar preview/filter behavior.",
        ),
        ProfileMediaReadinessItem(
            area="Real user database/project selector",
            status="pending",
            summary="A real selector for database roots and explicit batch/session configs still needs GUI integration.",
            next_action="Add a guarded selector that loads explicit JSON configs and does not crawl folders by default.",
        ),
        ProfileMediaReadinessItem(
            area="Existing folder import",
            status="pending",
            summary="Existing folders are not yet converted into batch JSON; current code uses explicit batch JSON fixtures or user-supplied batch JSON only.",
            next_action="Build an existing-folder-to-batch planner that is dry-run first and review-only.",
        ),
        ProfileMediaReadinessItem(
            area="Reviewed rename/move workflow",
            status="pending",
            summary="Reviewed rename/move execution is still separate from the Database workbench and must remain confirmation-gated.",
            next_action="Use a dedicated controlled-operation pack after GUI workbench rendering is stable.",
        ),
        ProfileMediaReadinessItem(
            area="Source-role vocabulary alignment",
            status="pending",
            summary="Existing batches have used SECONDARY_WITNESS_SOURCE while the intended taxonomy also uses witness-account language. This should be normalised before the final GUI labels are treated as settled.",
            next_action="Add a compatibility alias/normalisation pack so old fixtures and the preferred taxonomy render consistently.",
        ),
    )
    readiness_status = "ready_for_gui_panel_integration" if not warnings else "blocked_until_regression_repaired"
    return ProfileMediaImplementationReadinessReport(items=items, status=readiness_status, warnings=tuple(warnings))


def render_implementation_readiness_text(report: ProfileMediaImplementationReadinessReport) -> str:
    """Render a compact terminal/readme readiness report."""

    data = report.to_dict()
    lines = [
        "Profile/Media Database Implementation Readiness",
        f"Status: {report.status}",
        f"Items: {data['item_count']}",
        f"Complete/ready: {data['complete_or_ready_count']}",
        f"Pending: {data['pending_count']}",
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
        "Items:",
    ]
    for item in report.items:
        lines.append(f"- {item.area}: {item.status} — {item.summary}")
        if item.next_action:
            lines.append(f"  Next: {item.next_action}")
    if report.warnings:
        lines.extend(["", "Warnings:"])
        lines.extend(f"- {warning}" for warning in report.warnings)
    return "\n".join(lines)
