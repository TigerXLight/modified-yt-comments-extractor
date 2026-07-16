from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from evidence_database_index import EvidenceClassificationValue, EvidenceDatabaseRoot
from evidence_database_review import (
    EVIDENCE_DATABASE_REVIEW_SCOPE,
    EvidenceDatabaseApplyPlan,
    EvidenceDatabasePreviewResult,
    EvidenceDatabaseReviewSession,
)


EVIDENCE_DATABASE_REVIEW_UI_SCHEMA_VERSION = "evidence-database-review-ui-v1"
EVIDENCE_DATABASE_REVIEW_DRY_RUN_WARNING = (
    "Evidence Database review is dry-run only. It uses explicitly supplied "
    "records only and does not scan folders, move files, or apply "
    "classification changes."
)
EVIDENCE_DATABASE_REVIEW_DESTRUCTIVE_STATUS = "Destructive actions are not implemented."


def _yes_no(value: bool) -> str:
    return "yes" if value else "no"


def _value_for_dict(value: Any) -> Any:
    if hasattr(value, "value"):
        return value.value
    if isinstance(value, tuple):
        return [_value_for_dict(item) for item in value]
    if isinstance(value, list):
        return [_value_for_dict(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _value_for_dict(item) for key, item in sorted(value.items())}
    return value


def review_ui_stable_json_dumps(data: Any) -> str:
    return json.dumps(_value_for_dict(data), ensure_ascii=False, sort_keys=True, separators=(",", ":"))


@dataclass(frozen=True)
class EvidenceDatabaseReviewGroupSummary:
    classification_value: EvidenceClassificationValue
    row_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "classification_value": self.classification_value.value,
            "row_count": self.row_count,
        }


@dataclass(frozen=True)
class EvidenceDatabaseReviewWindowState:
    session_id: str
    selected_root_id: str = ""
    registered_root_count: int = 0
    preview_record_count: int = 0
    preview_group_counts: tuple[EvidenceDatabaseReviewGroupSummary, ...] = field(default_factory=tuple)
    selected_decision_count: int = 0
    apply_plan_entry_count: int = 0
    dry_run_only: bool = True
    supplied_records_only: bool = True
    broad_scan_performed: bool = False
    file_operation_performed: bool = False
    classification_changes_executed: bool = False
    destructive_actions_not_implemented: bool = True
    user_confirmation_required: bool = True
    dry_run_warning: str = EVIDENCE_DATABASE_REVIEW_DRY_RUN_WARNING
    destructive_action_status: str = EVIDENCE_DATABASE_REVIEW_DESTRUCTIVE_STATUS
    warnings: tuple[str, ...] = ()
    schema_version: str = EVIDENCE_DATABASE_REVIEW_UI_SCHEMA_VERSION
    scope: str = EVIDENCE_DATABASE_REVIEW_SCOPE

    def to_dict(self) -> dict[str, Any]:
        return {
            "apply_plan_entry_count": self.apply_plan_entry_count,
            "broad_scan_performed": self.broad_scan_performed,
            "classification_changes_executed": self.classification_changes_executed,
            "destructive_action_status": self.destructive_action_status,
            "destructive_actions_not_implemented": self.destructive_actions_not_implemented,
            "dry_run_only": self.dry_run_only,
            "dry_run_warning": self.dry_run_warning,
            "file_operation_performed": self.file_operation_performed,
            "preview_group_counts": [item.to_dict() for item in self.preview_group_counts],
            "preview_record_count": self.preview_record_count,
            "registered_root_count": self.registered_root_count,
            "schema_version": self.schema_version,
            "scope": self.scope,
            "selected_decision_count": self.selected_decision_count,
            "selected_root_id": self.selected_root_id,
            "session_id": self.session_id,
            "supplied_records_only": self.supplied_records_only,
            "user_confirmation_required": self.user_confirmation_required,
            "warnings": list(self.warnings),
        }


def _preview_group_summaries(
    preview_result: EvidenceDatabasePreviewResult | None,
) -> tuple[EvidenceDatabaseReviewGroupSummary, ...]:
    grouped = preview_result.grouped_record_ids if preview_result is not None else {}
    summaries = []
    for value in EvidenceClassificationValue:
        summaries.append(
            EvidenceDatabaseReviewGroupSummary(
                classification_value=value,
                row_count=len(grouped.get(value.value, ())),
            )
        )
    return tuple(summaries)


def build_evidence_database_review_window_state(
    *,
    session: EvidenceDatabaseReviewSession,
    registered_roots: tuple[EvidenceDatabaseRoot, ...] = (),
    preview_result: EvidenceDatabasePreviewResult | None = None,
    apply_plan: EvidenceDatabaseApplyPlan | None = None,
    warnings: tuple[str, ...] = (),
) -> EvidenceDatabaseReviewWindowState:
    registered_root_count = len(registered_roots) if registered_roots else len(session.registered_root_ids)
    combined_warnings = list(warnings)
    if preview_result is not None:
        combined_warnings.extend(preview_result.warnings)
    if apply_plan is not None:
        combined_warnings.extend(apply_plan.warnings)

    return EvidenceDatabaseReviewWindowState(
        session_id=session.session_id,
        selected_root_id=session.selected_root_id,
        registered_root_count=registered_root_count,
        preview_record_count=preview_result.record_count if preview_result is not None else 0,
        preview_group_counts=_preview_group_summaries(preview_result),
        selected_decision_count=len(apply_plan.decisions) if apply_plan is not None else 0,
        apply_plan_entry_count=len(apply_plan.entries) if apply_plan is not None else 0,
        dry_run_only=session.dry_run_only and (apply_plan.dry_run if apply_plan is not None else True),
        supplied_records_only=(
            preview_result.supplied_records_only if preview_result is not None else True
        ),
        broad_scan_performed=(
            preview_result.broad_scan_performed if preview_result is not None else False
        ),
        file_operation_performed=(
            (preview_result.file_operation_performed if preview_result is not None else False)
            or (apply_plan.file_operation_performed if apply_plan is not None else False)
        ),
        classification_changes_executed=(
            apply_plan.execute_classification_changes if apply_plan is not None else False
        ),
        destructive_actions_not_implemented=(
            apply_plan.destructive_action_not_implemented if apply_plan is not None else True
        ),
        user_confirmation_required=(
            session.user_confirmation_required
            or (apply_plan.user_confirmation_required if apply_plan is not None else False)
        ),
        warnings=tuple(combined_warnings),
    )


def build_evidence_database_review_window_text(
    state: EvidenceDatabaseReviewWindowState,
) -> str:
    lines = [
        "Evidence Database review",
        f"Warning: {state.dry_run_warning}",
        f"Session: {state.session_id}",
        f"Selected root: {state.selected_root_id or '(none)'}",
        f"Registered roots: {state.registered_root_count}",
        f"Preview rows: {state.preview_record_count}",
        "Preview rows by state:",
    ]
    for summary in state.preview_group_counts:
        lines.append(f"- {summary.classification_value.value}: {summary.row_count}")
    lines.extend(
        [
            "Apply plan:",
            f"- Decisions: {state.selected_decision_count}",
            f"- Entries: {state.apply_plan_entry_count}",
            f"- Dry run only: {_yes_no(state.dry_run_only)}",
            f"- Supplied records only: {_yes_no(state.supplied_records_only)}",
            f"- Broad scan performed: {_yes_no(state.broad_scan_performed)}",
            f"- File operation performed: {_yes_no(state.file_operation_performed)}",
            f"- Classification changes executed: {_yes_no(state.classification_changes_executed)}",
            f"- Destructive actions: {state.destructive_action_status}",
            "Warnings:",
        ]
    )
    if state.warnings:
        lines.extend(f"- {warning}" for warning in state.warnings)
    else:
        lines.append("- (none)")
    return "\n".join(lines) + "\n"


@dataclass(frozen=True)
class EvidenceDatabaseReviewWindowController:
    state: EvidenceDatabaseReviewWindowState

    def to_dict(self) -> dict[str, Any]:
        return self.state.to_dict()

    def to_text(self) -> str:
        return build_evidence_database_review_window_text(self.state)


def build_evidence_database_review_window_controller(
    *,
    session: EvidenceDatabaseReviewSession,
    registered_roots: tuple[EvidenceDatabaseRoot, ...] = (),
    preview_result: EvidenceDatabasePreviewResult | None = None,
    apply_plan: EvidenceDatabaseApplyPlan | None = None,
    warnings: tuple[str, ...] = (),
) -> EvidenceDatabaseReviewWindowController:
    return EvidenceDatabaseReviewWindowController(
        state=build_evidence_database_review_window_state(
            session=session,
            registered_roots=registered_roots,
            preview_result=preview_result,
            apply_plan=apply_plan,
            warnings=warnings,
        )
    )


def create_evidence_database_review_window(parent: Any, state: EvidenceDatabaseReviewWindowState) -> Any:
    """Create a minimal review-only window without scanning or applying changes."""
    import tkinter as tk

    window = tk.Toplevel(parent)
    window.title("Evidence Database Review")
    window.geometry("760x520")

    text = tk.Text(window, wrap="word", height=24)
    text.insert("1.0", build_evidence_database_review_window_text(state))
    text.configure(state="disabled")
    text.pack(fill="both", expand=True, padx=12, pady=(12, 8))

    close_button = tk.Button(window, text="Close", command=window.destroy)
    close_button.pack(anchor="e", padx=12, pady=(0, 12))
    return window
