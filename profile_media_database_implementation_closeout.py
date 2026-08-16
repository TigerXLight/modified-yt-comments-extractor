"""Implementation closeout report for Profile/Media Database mode.

V76H gives the project a consolidated, code-level readiness summary after the
Database workflow pieces have been connected.  It summarizes the implemented
capabilities without performing filesystem discovery, media retrieval,
classification, or sensitive identifier inference.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Mapping

from profile_media_database import utc_now_iso
from profile_media_database_end_to_end_workflow import ProfileMediaDatabaseEndToEndResult

PROFILE_MEDIA_DATABASE_IMPLEMENTATION_CLOSEOUT_SCHEMA_VERSION = "profile-media-database-implementation-closeout-v76h"


@dataclass(frozen=True)
class ProfileMediaImplementationCapability:
    key: str
    label: str
    status: str
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ProfileMediaImplementationCloseout:
    status: str
    capabilities: tuple[ProfileMediaImplementationCapability, ...]
    remaining_items: tuple[str, ...]
    workflow_status: str = ""
    schema_version: str = PROFILE_MEDIA_DATABASE_IMPLEMENTATION_CLOSEOUT_SCHEMA_VERSION
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
        data["capabilities"] = [capability.to_dict() for capability in self.capabilities]
        data["capability_count"] = len(self.capabilities)
        data["implemented_count"] = sum(1 for item in self.capabilities if item.status in {"implemented", "guarded_implemented"})
        data["remaining_count"] = len(self.remaining_items)
        return data


def _cap(key: str, label: str, status: str, notes: str = "") -> ProfileMediaImplementationCapability:
    return ProfileMediaImplementationCapability(key=key, label=label, status=status, notes=notes)


def build_implementation_closeout_report(
    workflow_result: ProfileMediaDatabaseEndToEndResult | Mapping[str, Any] | None = None,
) -> ProfileMediaImplementationCloseout:
    """Build a closeout summary from the current V75/V76 implementation state."""

    workflow_status = ""
    if isinstance(workflow_result, ProfileMediaDatabaseEndToEndResult):
        workflow_status = workflow_result.status
    elif isinstance(workflow_result, Mapping):
        workflow_status = str(workflow_result.get("status", ""))

    end_to_end_done = workflow_status in {
        "workflow_batch_preview_written",
        "workflow_materialized",
        "workflow_operations_applied",
    }
    operations_done = workflow_status == "workflow_operations_applied"

    capabilities = (
        _cap("sidebar_database_mode", "DATABASE mode switch", "implemented", "Sidebar remains mode-only; filtering/search lives in the main panel."),
        _cap("persistent_runtime_mode", "Persistent runtime mode", "implemented", "FILES/DATABASE state is persisted separately from case content."),
        _cap("case_workspace", "Case workspace hierarchy", "implemented", "Cases, Profiles, People, Sources, Reference Extants layout is modeled."),
        _cap("source_intake", "Source intake metadata", "implemented", "Source role, claim basis, currentness, disputed framing, and source-chain gaps are represented."),
        _cap("profile_intake", "Profile intake metadata", "implemented", "Case-local and global profile records remain source-bound."),
        _cap("case_batch", "Explicit batch JSON case model", "implemented", "Batch JSON is the controlled input surface for Database mode."),
        _cap("database_index_search", "Database index and search", "implemented", "Explicit batch JSON can be indexed and searched without folder scanning."),
        _cap("workbench_panel", "Main GUI Database panel", "implemented", "Panel state is main-content workbench state, not sidebar filtering."),
        _cap("gui_state_project", "GUI state/project restore", "implemented", "Selected explicit batch JSON files can be restored."),
        _cap("existing_folder_import_planner", "Existing-folder import planner", "implemented", "Uses user-provided folder-tree text only; no filesystem crawl."),
        _cap("source_role_policy", "Source-role normalization", "implemented", "Legacy secondary role strings are normalized toward canonical role policy."),
        _cap("controlled_materialize", "Controlled materialize workflow", "guarded_implemented", "Folder creation and metadata writes require exact confirmation."),
        _cap("reviewed_folder_operations", "Reviewed folder operations", "guarded_implemented", "Rename/move operations require explicit paths and exact confirmation."),
        _cap("end_to_end_workflow", "End-to-end workflow", "implemented" if end_to_end_done else "available", "V76H chains planning, preview, load, materialize, operations, and refresh."),
        _cap("temp_execution_proof", "Temp execution proof", "implemented" if operations_done else "available", "Full proof is satisfied when the V76H temp workflow applies reviewed ops."),
    )
    remaining = (
        "Wire final clickable GUI buttons to the already-tested UI-neutral controllers.",
        "Run one manual GUI smoke test against a disposable database root before using real case roots.",
        "Create a user-facing quick-start note for the Database workflow.",
    )
    status = "implementation_ready_for_gui_smoke" if end_to_end_done else "implementation_ready_for_end_to_end_proof"
    return ProfileMediaImplementationCloseout(
        status=status,
        capabilities=capabilities,
        remaining_items=remaining,
        workflow_status=workflow_status,
        folder_creation_performed=False,
        folder_move_performed=False,
        folder_rename_performed=False,
        file_write_performed=False,
    )


def render_implementation_closeout_text(closeout: ProfileMediaImplementationCloseout) -> str:
    lines = [
        "Profile/Media Database Implementation Closeout",
        f"Status: {closeout.status}",
        f"Workflow status: {closeout.workflow_status or '(not supplied)'}",
        "",
        "Capabilities:",
    ]
    for item in closeout.capabilities:
        suffix = f" — {item.notes}" if item.notes else ""
        lines.append(f"- {item.label}: {item.status}{suffix}")
    lines.append("")
    lines.append("Remaining:")
    for item in closeout.remaining_items:
        lines.append(f"- {item}")
    lines.extend([
        "",
        "Safety:",
        f"- Folder scan performed: {closeout.folder_scan_performed}",
        f"- Folder creation performed by closeout report: {closeout.folder_creation_performed}",
        f"- Folder move performed by closeout report: {closeout.folder_move_performed}",
        f"- Folder rename performed by closeout report: {closeout.folder_rename_performed}",
        f"- File copy performed: {closeout.file_copy_performed}",
        f"- File write performed by closeout report: {closeout.file_write_performed}",
        f"- Media download performed: {closeout.media_download_performed}",
        f"- Automatic classification performed: {closeout.automatic_classification_performed}",
        f"- Sensitive identifier inference performed: {closeout.sensitive_identifier_inference_performed}",
    ])
    return "\n".join(lines)


def implementation_closeout_payload(closeout: ProfileMediaImplementationCloseout, *, include_text: bool = False) -> dict[str, Any]:
    payload = closeout.to_dict()
    if include_text:
        payload["closeout_text"] = render_implementation_closeout_text(closeout)
    return payload
