"""Manual GUI smoke-test readiness for Profile/Media Database mode.

V76J is a closeout/readiness layer. It does not discover local folders or
perform any filesystem mutation.  It turns the completed V75/V76 backend and
GUI-neutral controller pieces into a concise manual smoke checklist for the
final clickable CustomTkinter wiring pass.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Iterable, Mapping

from profile_media_database import utc_now_iso
from profile_media_database_operation_reconciliation import (
    PROFILE_MEDIA_DATABASE_RECONCILIATION_WRITE_CONFIRMATION,
)
from profile_media_database_materialize_workflow import (
    PROFILE_MEDIA_DATABASE_MATERIALIZE_CONFIRMATION,
)
from profile_media_database_folder_operations import (
    PROFILE_MEDIA_DATABASE_FOLDER_OPERATIONS_CONFIRMATION,
)

PROFILE_MEDIA_GUI_SMOKE_READINESS_SCHEMA_VERSION = "profile-media-gui-smoke-readiness-v76j"


@dataclass(frozen=True)
class ProfileMediaGuiSmokeStep:
    step_id: str
    label: str
    expected_result: str
    status: str = "ready"
    guarded_confirmation: str = ""
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ProfileMediaGuiSmokeReadinessReport:
    status: str
    steps: tuple[ProfileMediaGuiSmokeStep, ...]
    warnings: tuple[str, ...] = ()
    manual_test_database_root: str = ""
    schema_version: str = PROFILE_MEDIA_GUI_SMOKE_READINESS_SCHEMA_VERSION
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
        data["steps"] = [step.to_dict() for step in self.steps]
        data["step_count"] = len(self.steps)
        data["guarded_step_count"] = sum(1 for step in self.steps if step.guarded_confirmation)
        data["warning_count"] = len(self.warnings)
        return data


def _step(step_id: str, label: str, expected_result: str, *, guarded_confirmation: str = "", notes: str = "") -> ProfileMediaGuiSmokeStep:
    return ProfileMediaGuiSmokeStep(
        step_id=step_id,
        label=label,
        expected_result=expected_result,
        guarded_confirmation=guarded_confirmation,
        notes=notes,
    )


def build_gui_smoke_readiness_report(
    *,
    manual_test_database_root: str = "%TEMP%\\ytce_profile_media_manual_gui_smoke",
    include_folder_operations: bool = True,
    include_reconciliation: bool = True,
) -> ProfileMediaGuiSmokeReadinessReport:
    """Build a read-only manual GUI smoke-test plan."""

    steps: list[ProfileMediaGuiSmokeStep] = [
        _step(
            "start_clean",
            "Start from a clean disposable database root",
            "The GUI should open without scanning any folder and should show DATABASE off until toggled.",
            notes="Use a temp root for smoke testing; do not use a real case root first.",
        ),
        _step(
            "toggle_database_mode",
            "Turn DATABASE mode on",
            "The sidebar stays mode-only and the main Profile/Media Database panel appears.",
        ),
        _step(
            "plan_existing_folder_import",
            "Plan existing folder import from pasted folder-tree text",
            "The import planner shows source/profile/global-profile candidates with no folder scan.",
        ),
        _step(
            "write_batch_preview",
            "Write standalone batch-preview JSON",
            "Only the selected preview JSON is written; no media or source folders are touched.",
            guarded_confirmation="WRITE_EXISTING_FOLDER_BATCH_PREVIEW",
        ),
        _step(
            "load_batch_json",
            "Load explicit batch JSON",
            "The Database workbench metrics, navigation targets, and review lanes populate from explicit JSON.",
        ),
        _step(
            "materialize_selection",
            "Materialize selected batch",
            "Known case/source/profile folders and metadata files are created under the disposable root only.",
            guarded_confirmation=PROFILE_MEDIA_DATABASE_MATERIALIZE_CONFIRMATION,
        ),
    ]
    if include_folder_operations:
        steps.append(
            _step(
                "reviewed_folder_operations",
                "Apply reviewed folder rename/move operations",
                "Only explicitly reviewed paths under the database root are renamed/moved.",
                guarded_confirmation=PROFILE_MEDIA_DATABASE_FOLDER_OPERATIONS_CONFIRMATION,
            )
        )
    if include_reconciliation:
        steps.append(
            _step(
                "reconcile_batch_preview",
                "Write reconciled batch-preview JSON",
                "The standalone reconciled JSON reflects reviewed source title/bucket changes without modifying media.",
                guarded_confirmation=PROFILE_MEDIA_DATABASE_RECONCILIATION_WRITE_CONFIRMATION,
            )
        )
    steps.extend([
        _step(
            "refresh_database_panel",
            "Refresh Database panel",
            "Review lane counts should come from the nested workbench/dashboard/review-report payloads.",
        ),
        _step(
            "confirm_safety_flags",
            "Confirm safety flags",
            "Folder scan, file copy, media download, auto-classification, and sensitive inference remain False.",
        ),
    ])
    return ProfileMediaGuiSmokeReadinessReport(
        status="ready_for_manual_gui_smoke",
        steps=tuple(steps),
        manual_test_database_root=manual_test_database_root,
    )


def render_gui_smoke_readiness_text(report: ProfileMediaGuiSmokeReadinessReport) -> str:
    lines = [
        "Profile/Media Database Manual GUI Smoke Readiness",
        f"Status: {report.status}",
        f"Manual test database root: {report.manual_test_database_root}",
        "",
        "Steps:",
    ]
    for index, step in enumerate(report.steps, start=1):
        guard = f" [requires: {step.guarded_confirmation}]" if step.guarded_confirmation else ""
        lines.append(f"{index}. {step.label}{guard}")
        lines.append(f"   Expected: {step.expected_result}")
        if step.notes:
            lines.append(f"   Notes: {step.notes}")
    lines.extend([
        "",
        "Safety assertions for this readiness report:",
        f"- Folder scan performed: {report.folder_scan_performed}",
        f"- Folder creation performed by readiness report: {report.folder_creation_performed}",
        f"- Folder move performed by readiness report: {report.folder_move_performed}",
        f"- Folder rename performed by readiness report: {report.folder_rename_performed}",
        f"- File copy performed: {report.file_copy_performed}",
        f"- File write performed by readiness report: {report.file_write_performed}",
        f"- Media download performed: {report.media_download_performed}",
        f"- Automatic classification performed: {report.automatic_classification_performed}",
        f"- Sensitive identifier inference performed: {report.sensitive_identifier_inference_performed}",
    ])
    return "\n".join(lines)


def gui_smoke_readiness_payload(report: ProfileMediaGuiSmokeReadinessReport, *, include_text: bool = False) -> dict[str, Any]:
    payload = report.to_dict()
    if include_text:
        payload["readiness_text"] = render_gui_smoke_readiness_text(report)
    return payload
