from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from source_capture_plan import SourceCapturePlan
from total_export_assets import (
    asset_destination_path,
    export_asset_for_file,
    register_asset_in_manifest_file,
    safe_asset_filename,
)
from total_export_manifest import ASSET_TEXT_EXPORT
from total_export_workflow import TotalExportWorkflowResult


DEFAULT_PLAN_REPORT_FILENAME = "SOURCE_CAPTURE_PLAN.txt"


@dataclass(frozen=True)
class TotalExportPlanReportFileResult:
    report_path: str
    registered: bool = False
    manifest_path: str = ""
    asset_path: str = ""
    warnings: tuple[str, ...] = ()


def _format_sequence(values: object) -> str:
    sequence = tuple(values or ())
    if not sequence:
        return "(none)"
    return ", ".join(str(value) for value in sequence)


def _append_sequence_lines(lines: list[str], label: str, values: object) -> None:
    sequence = tuple(values or ())
    lines.append(f"{label}:")
    if not sequence:
        lines.append("- (none)")
        return
    for value in sequence:
        lines.append(f"- {value}")


def _title_from_plan(plan: SourceCapturePlan) -> str:
    if not plan.context_result:
        return ""
    for hint in plan.context_result.context_hints:
        if hint.label == "title":
            return hint.value
    return ""


def build_total_export_plan_report_text(workflow_result: TotalExportWorkflowResult) -> str:
    plan = workflow_result.plan
    context_result = plan.context_result
    lines = [
        "Total Export Source Capture Plan",
        "",
        f"Source URL: {plan.source_url or '(none)'}",
        f"Normalized URL: {plan.normalized_url or '(none)'}",
        f"Source ID: {plan.source_id or '(none)'}",
        f"Source label: {context_result.source_label if context_result else '(none)'}",
        f"Title: {_title_from_plan(plan) or '(none)'}",
        f"Adapter name: {plan.adapter_name or '(none)'}",
        f"Adapter display name: {plan.adapter_display_name or '(none)'}",
        f"Plan status: {plan.status}",
        f"Selected capture options: {_format_sequence(plan.selected_capture_options)}",
        f"Unknown capture options: {_format_sequence(plan.unknown_capture_options)}",
        f"Duplicate capture options: {_format_sequence(plan.duplicate_capture_options)}",
    ]
    _append_sequence_lines(lines, "Warnings", plan.warnings)

    lines.append("Context hints:")
    if context_result and context_result.context_hints:
        for hint in context_result.context_hints:
            label = hint.label or hint.source or "hint"
            lines.append(f"- {label}: {hint.value}")
    else:
        lines.append("- (none)")

    lines.append("User glossary terms:")
    user_terms = [
        term.text
        for term in (context_result.glossary_terms if context_result else ())
        if term.source == "user"
    ]
    if user_terms:
        for term in user_terms:
            lines.append(f"- {term}")
    else:
        lines.append("- (none)")

    lines.extend(
        [
            "",
            (
                "Safety note: This report is local metadata only. It does not prove content "
                "was fetched, captured, archived, downloaded, or transcribed."
            ),
        ]
    )
    return "\n".join(lines)


def write_total_export_plan_report_file(
    *,
    workflow_result: TotalExportWorkflowResult,
    filename: str = DEFAULT_PLAN_REPORT_FILENAME,
    register_in_manifest: bool = True,
) -> TotalExportPlanReportFileResult:
    package_result = workflow_result.package_result.package_result
    package_folder = package_result.package_folder
    if not package_folder:
        raise ValueError("Workflow result does not include a package folder.")

    safe_filename = safe_asset_filename(filename)
    report_path = asset_destination_path(
        package_folder=package_folder,
        asset_type=ASSET_TEXT_EXPORT,
        filename=safe_filename,
    )
    path = Path(report_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(build_total_export_plan_report_text(workflow_result), encoding="utf-8")

    if not register_in_manifest:
        return TotalExportPlanReportFileResult(
            report_path=report_path,
            registered=False,
            manifest_path=workflow_result.package_result.manifest_path,
        )

    asset = export_asset_for_file(
        file_path=report_path,
        asset_type=ASSET_TEXT_EXPORT,
        package_folder=package_folder,
    )
    register_asset_in_manifest_file(
        manifest_path=workflow_result.package_result.manifest_path,
        asset=asset,
        dedupe=True,
    )
    return TotalExportPlanReportFileResult(
        report_path=report_path,
        registered=True,
        manifest_path=workflow_result.package_result.manifest_path,
        asset_path=asset.path,
    )
