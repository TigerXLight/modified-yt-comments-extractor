"""GUI adapter for the V76E existing-folder import planner.

This layer exposes a compact payload the main Database workbench can render when
the user wants to plan an import from an already-organized folder tree.  It is
still dry-run only and uses explicit folder-tree text supplied by the caller;
it does not scan the filesystem.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from profile_media_database import utc_now_iso
from profile_media_existing_folder_batch_planner import ExistingFolderToBatchPlan, render_existing_folder_plan_text

PROFILE_MEDIA_EXISTING_FOLDER_GUI_SCHEMA_VERSION = "profile-media-existing-folder-gui-adapter-v76e"


@dataclass(frozen=True)
class ExistingFolderGuiAction:
    action_id: str
    label: str
    status: str
    description: str


@dataclass(frozen=True)
class ExistingFolderGuiPayload:
    status: str
    title: str
    subtitle: str
    source_candidate_count: int
    profile_candidate_count: int
    global_profile_candidate_count: int
    ignored_entry_count: int
    batch_preview_source_count: int
    batch_preview_profile_count: int
    actions: tuple[ExistingFolderGuiAction, ...]
    plan_text: str
    schema_version: str = PROFILE_MEDIA_EXISTING_FOLDER_GUI_SCHEMA_VERSION
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


def build_existing_folder_gui_payload(plan: ExistingFolderToBatchPlan) -> ExistingFolderGuiPayload:
    preview = plan.batch_preview()
    return ExistingFolderGuiPayload(
        status="dry_run_preview",
        title="Plan existing folder import",
        subtitle="Build a batch-JSON preview from an explicit folder-tree list; no folder scan is performed.",
        source_candidate_count=len(plan.source_candidates),
        profile_candidate_count=len(plan.profile_candidates),
        global_profile_candidate_count=len(plan.global_profile_candidates),
        ignored_entry_count=len(plan.ignored_entries),
        batch_preview_source_count=len(preview.get("sources", ())),
        batch_preview_profile_count=len(preview.get("profiles", ())),
        actions=(
            ExistingFolderGuiAction(
                "review_existing_folder_plan",
                "Review plan",
                "available",
                "Review source/profile candidates before any batch JSON is written.",
            ),
            ExistingFolderGuiAction(
                "write_batch_preview",
                "Write batch preview",
                "guarded",
                "Requires WRITE_EXISTING_FOLDER_BATCH_PREVIEW confirmation and writes only a standalone JSON preview.",
            ),
            ExistingFolderGuiAction(
                "load_preview_as_batch_json",
                "Load preview as batch JSON",
                "planned_after_write",
                "Use the V76C/V76D explicit batch JSON loader after a preview file exists.",
            ),
        ),
        plan_text=render_existing_folder_plan_text(plan),
    )
