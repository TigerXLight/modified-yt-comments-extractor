"""GUI adapter for controlled Profile/Media Database materialization.

This module converts the V76F materialization plan/result into a compact
UI-neutral payload for the main Database workbench.  It does not execute by
itself, scan folders, copy media, download media, auto-classify, or infer
sensitive identifiers.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from profile_media_database import utc_now_iso
from profile_media_database_materialize_workflow import (
    PROFILE_MEDIA_DATABASE_MATERIALIZE_CONFIRMATION,
    ProfileMediaDatabaseMaterializePlan,
    ProfileMediaDatabaseMaterializeResult,
    render_database_materialize_plan_text,
    render_database_materialize_result_text,
)

PROFILE_MEDIA_DATABASE_MATERIALIZE_GUI_SCHEMA_VERSION = "profile-media-database-materialize-gui-v76f"


@dataclass(frozen=True)
class ProfileMediaMaterializeGuiAction:
    action_id: str
    label: str
    status: str
    description: str


@dataclass(frozen=True)
class ProfileMediaMaterializeGuiPayload:
    status: str
    title: str
    subtitle: str
    batch_json_file_count: int
    review_source_count: int
    review_profile_count: int
    created_directory_count: int = 0
    written_file_count: int = 0
    warning_count: int = 0
    actions: tuple[ProfileMediaMaterializeGuiAction, ...] = ()
    plan_text: str = ""
    result_text: str = ""
    confirmation_phrase: str = PROFILE_MEDIA_DATABASE_MATERIALIZE_CONFIRMATION
    schema_version: str = PROFILE_MEDIA_DATABASE_MATERIALIZE_GUI_SCHEMA_VERSION
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


def build_materialize_gui_payload(
    plan: ProfileMediaDatabaseMaterializePlan,
    result: ProfileMediaDatabaseMaterializeResult | None = None,
) -> ProfileMediaMaterializeGuiPayload:
    """Build a GUI-safe status payload for materialization review/results."""

    ready_batches = sum(1 for review in plan.batch_reviews if review.status == "ready")
    blocked_batches = len(plan.batch_reviews) - ready_batches
    source_count = sum(review.source_count for review in plan.batch_reviews if review.status == "ready")
    profile_count = sum(review.profile_count for review in plan.batch_reviews if review.status == "ready")
    if result is None:
        status = "ready_for_confirmation" if ready_batches and not blocked_batches else "blocked_or_empty"
        subtitle = "Review the selected explicit batch JSON files, then type the exact confirmation phrase to materialize."
        created_count = 0
        written_count = 0
        warning_count = sum(len(review.warnings) for review in plan.batch_reviews)
        folder_creation_performed = False
        file_write_performed = False
        result_text = ""
    else:
        status = result.status
        subtitle = "Confirmed materialization result. Only folders and metadata files may have been written."
        created_count = len(result.created_directories)
        written_count = len(result.written_files)
        warning_count = len(result.warnings)
        folder_creation_performed = result.folder_creation_performed
        file_write_performed = result.file_write_performed
        result_text = render_database_materialize_result_text(result)

    return ProfileMediaMaterializeGuiPayload(
        status=status,
        title="Materialize Database batch selection",
        subtitle=subtitle,
        batch_json_file_count=len(plan.batch_json_files),
        review_source_count=source_count,
        review_profile_count=profile_count,
        created_directory_count=created_count,
        written_file_count=written_count,
        warning_count=warning_count,
        actions=(
            ProfileMediaMaterializeGuiAction(
                "review_materialize_plan",
                "Review materialize plan",
                "available",
                "Review exactly which explicit batch JSON files would create folders/metadata.",
            ),
            ProfileMediaMaterializeGuiAction(
                "execute_materialize_plan",
                "Execute materialize plan",
                "guarded_confirmation_required",
                f"Requires typing {PROFILE_MEDIA_DATABASE_MATERIALIZE_CONFIRMATION}.",
            ),
            ProfileMediaMaterializeGuiAction(
                "refresh_database_after_materialize",
                "Refresh Database view",
                "available_after_execution",
                "Refresh the main Database workbench after the batch JSON selection is materialized.",
            ),
        ),
        plan_text=render_database_materialize_plan_text(plan),
        result_text=result_text,
        folder_creation_performed=folder_creation_performed,
        file_write_performed=file_write_performed,
        folder_scan_performed=False,
        folder_move_performed=False,
        folder_rename_performed=False,
        file_copy_performed=False,
        media_download_performed=False,
        automatic_classification_performed=False,
        sensitive_identifier_inference_performed=False,
    )


def materialize_gui_payload_dict(payload: ProfileMediaMaterializeGuiPayload) -> dict[str, Any]:
    return payload.to_dict()
