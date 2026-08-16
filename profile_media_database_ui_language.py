"""Common-user HOME repository wording and source-role display helpers.

V76K2 supersedes the earlier batch/workbench wording.  The user-facing model is
HOME repository management: add/import material, review provenance, then SAVE
reviewed folders/metadata into HOME.  JSON/package objects remain internal.

This module is pure formatting/state summarisation.  It does not scan folders,
create folders, move folders, rename folders, copy media, download media,
automatically classify source roles, or infer sensitive identifiers.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping

PROFILE_MEDIA_DATABASE_UI_LANGUAGE_SCHEMA_VERSION = "profile-media-database-home-ui-language-v76k2"

PRIMARY_SOURCE_ROLE = "PRIMARY_SELF_AUTHORED_SCOPE"
SECONDARY_SOURCE_ROLE = "SECONDARY_WITNESS_ACCOUNT"
TERTIARY_SOURCE_ROLE = "TERTIARY_PROPAGATED_SOURCE"
INTERNAL_MEDIA_ROLE = "INTERNAL_MEDIA"
UNKNOWN_SOURCE_ROLE = "UNKNOWN_SOURCE_ROLE"

SOURCE_ROLE_UI = {
    PRIMARY_SOURCE_ROLE: {
        "short_label": "Primary",
        "long_label": "Primary / self-authored scope",
        "icon_text": "👤",
        "asset_hint": "assets/profile_media/source_roles/icons8-contacts-32.png",
        "meaning": "Self-authored or direct-subject material; applies only to that author/speaker within scope.",
    },
    SECONDARY_SOURCE_ROLE: {
        "short_label": "Secondary",
        "long_label": "Secondary / witness account",
        "icon_text": "👥",
        "asset_hint": "assets/profile_media/source_roles/icons8-user-account-32.png",
        "meaning": "A witness/observer directly describes the event or person.",
    },
    TERTIARY_SOURCE_ROLE: {
        "short_label": "Tertiary",
        "long_label": "Tertiary / propagated report",
        "icon_text": "👥+",
        "asset_hint": "assets/profile_media/source_roles/icons8-people-32.png",
        "meaning": "A publisher, institution, family/authority statement, agency wire, or outside retelling propagates a claim.",
    },
    INTERNAL_MEDIA_ROLE: {
        "short_label": "Internal",
        "long_label": "Internal Media",
        "icon_text": "✍",
        "asset_hint": "assets/profile_media/source_roles/icons8-writer-male-32.png",
        "meaning": "Media created, captured, scanned, or obtained locally by the user/project creator.",
    },
    UNKNOWN_SOURCE_ROLE: {
        "short_label": "Review",
        "long_label": "Needs source-role review",
        "icon_text": "?",
        "asset_hint": "",
        "meaning": "The source role is not marked yet; send this to Review items rather than displaying an unknown-role counter.",
    },
}

ACTION_UI = {
    "save_to_home_repository": {
        "label": "SAVE",
        "long_label": "Save to HOME",
        "description": "Save/update reviewed folders and metadata in the selected HOME repository.",
    },
    "load_batch_json": {
        "label": "Add / Import",
        "long_label": "Add / Import",
        "description": "Add source files, pasted URLs, dragged media, existing folders, or an internal import package.",
    },
    "clear_batch": {
        "label": "Unload",
        "long_label": "Unload current import",
        "description": "Remove the current import from the view without deleting files, folders, or source material.",
    },
    "plan_existing_folder_import": {
        "label": "Plan folder import",
        "long_label": "Plan folder import",
        "description": "Preview how an existing folder tree would map into HOME before saving anything.",
    },
    "review_folder_operations": {
        "label": "Review moves",
        "long_label": "Review folder moves/renames",
        "description": "Review explicit folder changes before applying them under HOME.",
    },
    "reconcile_batch_after_folder_operations": {
        "label": "Update saved index",
        "long_label": "Update saved index",
        "description": "Update the saved internal index after reviewed folder changes.",
    },
}

BACKEND_TERMS_HIDDEN_FROM_COMMON_UI = (
    "batch JSON",
    "materialize",
    "profile rows",
    "unknown source roles",
    "disputed framing counter",
    "source-chain gaps counter",
)


@dataclass(frozen=True)
class SourceRoleDisplay:
    source_role: str
    label: str
    long_label: str
    icon_text: str
    asset_hint: str
    meaning: str
    count: int = 0
    schema_version: str = PROFILE_MEDIA_DATABASE_UI_LANGUAGE_SCHEMA_VERSION
    folder_scan_performed: bool = False
    folder_creation_performed: bool = False
    folder_move_performed: bool = False
    folder_rename_performed: bool = False
    file_copy_performed: bool = False
    media_download_performed: bool = False
    automatic_classification_performed: bool = False
    sensitive_identifier_inference_performed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def source_role_display(source_role: object, *, count: object = 0) -> SourceRoleDisplay:
    role = str(source_role or UNKNOWN_SOURCE_ROLE).strip() or UNKNOWN_SOURCE_ROLE
    data = SOURCE_ROLE_UI.get(role, SOURCE_ROLE_UI[UNKNOWN_SOURCE_ROLE])
    try:
        numeric_count = int(count or 0)
    except Exception:
        numeric_count = 0
    return SourceRoleDisplay(
        source_role=role,
        label=str(data["short_label"]),
        long_label=str(data["long_label"]),
        icon_text=str(data["icon_text"]),
        asset_hint=str(data["asset_hint"]),
        meaning=str(data["meaning"]),
        count=numeric_count,
    )


def common_user_action_label(action_id: object) -> str:
    data = ACTION_UI.get(str(action_id or ""), {})
    return str(data.get("label") or data.get("long_label") or action_id or "")


def _int(value: object) -> int:
    try:
        return int(value or 0)
    except Exception:
        return 0


def home_repository_status_payload(
    *,
    home_root: object = "",
    primary_count: object = 0,
    secondary_count: object = 0,
    tertiary_count: object = 0,
    internal_media_count: object = 0,
    person_count: object = 0,
    review_count: object = 0,
) -> dict[str, Any]:
    return {
        "schema_version": PROFILE_MEDIA_DATABASE_UI_LANGUAGE_SCHEMA_VERSION,
        "home_repository": str(home_root or ""),
        "primary_sources": _int(primary_count),
        "secondary_sources": _int(secondary_count),
        "tertiary_sources": _int(tertiary_count),
        "internal_media": _int(internal_media_count),
        "persons": _int(person_count),
        "review_items": _int(review_count),
        "visible_metric_order": ["primary_sources", "secondary_sources", "tertiary_sources", "persons", "review_items"],
        "backend_terms_hidden_from_common_ui": BACKEND_TERMS_HIDDEN_FROM_COMMON_UI,
        "folder_scan_performed": False,
        "folder_creation_performed": False,
        "folder_move_performed": False,
        "folder_rename_performed": False,
        "file_copy_performed": False,
        "media_download_performed": False,
        "automatic_classification_performed": False,
        "sensitive_identifier_inference_performed": False,
    }


def source_role_summary_from_dashboard(workbench_payload: Mapping[str, Any] | None) -> dict[str, Any]:
    counts = {
        PRIMARY_SOURCE_ROLE: 0,
        SECONDARY_SOURCE_ROLE: 0,
        TERTIARY_SOURCE_ROLE: 0,
        INTERNAL_MEDIA_ROLE: 0,
        UNKNOWN_SOURCE_ROLE: 0,
    }
    if workbench_payload:
        dashboard = workbench_payload.get("dashboard") if isinstance(workbench_payload, Mapping) else None
        facets = dashboard.get("facets", ()) if isinstance(dashboard, Mapping) else ()
        for facet in facets or ():
            if not isinstance(facet, Mapping) or facet.get("facet_type") != "source_role":
                continue
            role = str(facet.get("value", UNKNOWN_SOURCE_ROLE) or UNKNOWN_SOURCE_ROLE)
            count = _int(facet.get("count", 0))
            if role in counts:
                counts[role] += count
            else:
                counts[UNKNOWN_SOURCE_ROLE] += count
    return {
        "schema_version": PROFILE_MEDIA_DATABASE_UI_LANGUAGE_SCHEMA_VERSION,
        "roles": [source_role_display(role, count=count).to_dict() for role, count in counts.items()],
        "folder_scan_performed": False,
        "file_copy_performed": False,
        "media_download_performed": False,
        "automatic_classification_performed": False,
        "sensitive_identifier_inference_performed": False,
    }


def render_home_repository_status(payload: Mapping[str, Any]) -> str:
    lines = ["Profile/Media HOME Repository", f"HOME: {payload.get('home_repository') or '(not selected)'}", ""]
    labels = {
        "primary_sources": "Primary",
        "secondary_sources": "Secondary",
        "tertiary_sources": "Tertiary",
        "persons": "Persons",
        "review_items": "Review items",
    }
    for key in payload.get("visible_metric_order", ()): 
        lines.append(f"- {labels.get(str(key), str(key))}: {_int(payload.get(str(key), 0))}")
    lines.append("")
    lines.append("Common-user UI hides backend terms: " + ", ".join(payload.get("backend_terms_hidden_from_common_ui", ())))
    return "\n".join(lines)
