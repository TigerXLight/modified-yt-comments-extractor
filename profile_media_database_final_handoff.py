"""Final handoff/status summary for Profile/Media Database mode through V76J."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from profile_media_database import utc_now_iso
from profile_media_database_gui_smoke_readiness import build_gui_smoke_readiness_report

PROFILE_MEDIA_DATABASE_FINAL_HANDOFF_SCHEMA_VERSION = "profile-media-database-final-handoff-v76j"


@dataclass(frozen=True)
class ProfileMediaFinalHandoff:
    status: str
    latest_pack: str
    implemented_packs: tuple[str, ...]
    next_recommended_action: str
    upload_notes: tuple[str, ...]
    schema_version: str = PROFILE_MEDIA_DATABASE_FINAL_HANDOFF_SCHEMA_VERSION
    created_at_utc: str = field(default_factory=utc_now_iso)
    folder_scan_performed: bool = False
    file_copy_performed: bool = False
    media_download_performed: bool = False
    automatic_classification_performed: bool = False
    sensitive_identifier_inference_performed: bool = False

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["implemented_pack_count"] = len(self.implemented_packs)
        data["upload_note_count"] = len(self.upload_notes)
        return data


def build_profile_media_final_handoff() -> ProfileMediaFinalHandoff:
    packs = (
        "V75A-V75P sidebar/runtime foundation",
        "V75Q-V75Z case workspace, intake, index, search, session/export",
        "V76A workbench",
        "V76B integration readiness/regression",
        "V76C main GUI Database workbench panel",
        "V76D GUI state/project restore",
        "V76E existing-folder import planner and source-role policy",
        "V76F controlled materialize workflow",
        "V76G reviewed folder operations",
        "V76H end-to-end workflow proof",
        "V76I reconciliation closeout",
        "V76J manual GUI smoke readiness",
    )
    return ProfileMediaFinalHandoff(
        status="ready_for_manual_gui_smoke_then_clickable_ui_polish",
        latest_pack="V76J",
        implemented_packs=packs,
        next_recommended_action="Run one manual GUI smoke test against a disposable database root, then wire/polish the final clickable controls using the existing controllers.",
        upload_notes=(
            "For a new session, upload the latest source context zip or at minimum main.py plus all profile_media*.py, profile_media*_test.py, tools/run_profile_media*.py, PROFILE_MEDIA_DATABASE_*.md, and testdata/profile_media_database*.json.",
            "Do not upload venv, dist, build, .git, browser profiles, credentials, third_party runtimes, or downloaded media unless a task specifically needs them.",
        ),
    )


def render_profile_media_final_handoff_text(handoff: ProfileMediaFinalHandoff) -> str:
    lines = [
        "Profile/Media Database Final Handoff",
        f"Status: {handoff.status}",
        f"Latest pack: {handoff.latest_pack}",
        "",
        "Implemented chain:",
    ]
    for item in handoff.implemented_packs:
        lines.append(f"- {item}")
    lines.extend([
        "",
        "Next recommended action:",
        f"- {handoff.next_recommended_action}",
        "",
        "Upload notes for a new session:",
    ])
    for item in handoff.upload_notes:
        lines.append(f"- {item}")
    smoke = build_gui_smoke_readiness_report()
    lines.extend([
        "",
        f"Manual GUI smoke steps ready: {len(smoke.steps)}",
        "Safety:",
        f"- Folder scan performed by handoff: {handoff.folder_scan_performed}",
        f"- File copy performed by handoff: {handoff.file_copy_performed}",
        f"- Media download performed by handoff: {handoff.media_download_performed}",
        f"- Automatic classification performed by handoff: {handoff.automatic_classification_performed}",
        f"- Sensitive identifier inference performed by handoff: {handoff.sensitive_identifier_inference_performed}",
    ])
    return "\n".join(lines)


def profile_media_final_handoff_payload(handoff: ProfileMediaFinalHandoff, *, include_text: bool = False) -> dict[str, Any]:
    payload = handoff.to_dict()
    if include_text:
        payload["handoff_text"] = render_profile_media_final_handoff_text(handoff)
    return payload
