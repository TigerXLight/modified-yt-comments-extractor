"""GUI adapter for reviewed Profile/Media folder operations.

The adapter converts the V76G controlled folder operation workflow into a
UI-neutral payload.  It does not scan folders, create folders, copy files,
download media, classify automatically, or infer sensitive identifiers.
"""

from __future__ import annotations

from typing import Any, Mapping

from profile_media_database_folder_operations import (
    PROFILE_MEDIA_DATABASE_FOLDER_OPERATIONS_CONFIRMATION,
    ProfileMediaFolderOperationsPlan,
    ProfileMediaFolderOperationsResult,
    apply_folder_operations_plan,
    build_folder_operations_plan,
    folder_operations_payload,
)

PROFILE_MEDIA_DATABASE_FOLDER_OPERATIONS_GUI_SCHEMA_VERSION = "profile-media-folder-operations-gui-v76g"


def build_folder_operations_gui_payload(
    *,
    database_root: str,
    operations_payload: Mapping[str, Any] | None = None,
    operations_json_path: str | None = None,
    execute: bool = False,
    confirmation_phrase: str = "",
) -> dict[str, Any]:
    """Return GUI-safe review/execution state for reviewed folder operations."""

    plan: ProfileMediaFolderOperationsPlan = build_folder_operations_plan(
        database_root=database_root,
        operations_payload=operations_payload,
        operations_json_path=operations_json_path,
        execute=execute,
        confirmation_phrase=confirmation_phrase,
    )
    result: ProfileMediaFolderOperationsResult = apply_folder_operations_plan(plan)
    payload = folder_operations_payload(result, plan=plan)
    payload.update({
        "schema_version": PROFILE_MEDIA_DATABASE_FOLDER_OPERATIONS_GUI_SCHEMA_VERSION,
        "title": "Reviewed folder operations",
        "subtitle": (
            "Confirmed reviewed folder operations have run."
            if result.status in {"operations_applied", "partially_applied"}
            else "Review exact folder rename/move operations before confirming."
        ),
        "confirmation_phrase": PROFILE_MEDIA_DATABASE_FOLDER_OPERATIONS_CONFIRMATION,
        "actions": [
            {
                "action_id": "review_folder_operations_plan",
                "label": "Review folder operations plan",
                "status": "available",
                "description": "Review exact source and destination folders before any operation runs.",
            },
            {
                "action_id": "execute_folder_operations_plan",
                "label": "Execute reviewed operations",
                "status": "guarded_confirmation_required",
                "description": f"Requires typing {PROFILE_MEDIA_DATABASE_FOLDER_OPERATIONS_CONFIRMATION}.",
            },
            {
                "action_id": "refresh_database_after_folder_operations",
                "label": "Refresh Database view",
                "status": "available_after_execution",
                "description": "Refresh explicit batch/database views after reviewed folder operations.",
            },
        ],
        "notices": [
            "No folder scan is performed by this reviewed-operation adapter.",
            "Only explicitly supplied folder source/destination paths are considered.",
            "No file copy, media download, auto-classification, or sensitive inference is performed.",
        ],
    })
    return payload
