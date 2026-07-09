from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from total_export_inventory_report import (
    TotalExportInventoryReportFileResult,
    write_total_export_inventory_report_file,
)
from total_export_plan_report import (
    DEFAULT_PLAN_REPORT_FILENAME,
    TotalExportPlanReportFileResult,
    write_total_export_plan_report_file,
)
from total_export_readme import TotalExportReadmeFileResult, write_total_export_readme_file
from total_export_summary import TotalExportSummaryFileResult, write_workflow_summary_file
from total_export_validation import ManifestValidationResult, validate_manifest_json_file
from total_export_workflow import TotalExportWorkflowResult, prepare_total_export_from_source


@dataclass(frozen=True)
class PreparedTotalExportResult:
    workflow_result: TotalExportWorkflowResult
    summary_file_result: TotalExportSummaryFileResult
    readme_file_result: TotalExportReadmeFileResult | None = None
    plan_report_file_result: TotalExportPlanReportFileResult | None = None
    inventory_report_file_result: TotalExportInventoryReportFileResult | None = None
    final_validation_result: ManifestValidationResult | None = None
    warnings: tuple[str, ...] = ()


def _combined_warnings(
    workflow_result: TotalExportWorkflowResult,
    summary_file_result: TotalExportSummaryFileResult,
    readme_file_result: TotalExportReadmeFileResult | None = None,
    plan_report_file_result: TotalExportPlanReportFileResult | None = None,
    inventory_report_file_result: TotalExportInventoryReportFileResult | None = None,
) -> tuple[str, ...]:
    warnings: list[str] = []
    seen = set()
    source_warnings = list(workflow_result.warnings) + list(summary_file_result.warnings)
    if readme_file_result:
        source_warnings.extend(readme_file_result.warnings)
    if plan_report_file_result:
        source_warnings.extend(plan_report_file_result.warnings)
    if inventory_report_file_result:
        source_warnings.extend(inventory_report_file_result.warnings)
    for warning in source_warnings:
        if not warning or warning in seen:
            continue
        seen.add(warning)
        warnings.append(warning)
    return tuple(warnings)


def prepare_total_export_with_summary(
    *,
    base_folder: str,
    source_url: str,
    source_label: str = "",
    title: str = "",
    selected_capture_options: Sequence[str] = (),
    user_terms: Sequence[str] = (),
    package_id: str = "",
    create_asset_folders: bool = True,
    summary_filename: str = "TOTAL_EXPORT_SUMMARY.txt",
    register_summary_in_manifest: bool = True,
    write_readme: bool = False,
    readme_filename: str = "README_TOTAL_EXPORT.txt",
    register_readme_in_manifest: bool = True,
    write_plan_report: bool = False,
    plan_report_filename: str = DEFAULT_PLAN_REPORT_FILENAME,
    register_plan_report_in_manifest: bool = True,
    write_inventory_report: bool = False,
    inventory_report_filename: str = "TOTAL_EXPORT_INVENTORY.txt",
    register_inventory_report_in_manifest: bool = True,
    validate_final_manifest: bool = True,
) -> PreparedTotalExportResult:
    workflow_result = prepare_total_export_from_source(
        base_folder=base_folder,
        source_url=source_url,
        source_label=source_label,
        title=title,
        selected_capture_options=selected_capture_options,
        user_terms=user_terms,
        package_id=package_id,
        create_asset_folders=create_asset_folders,
    )
    summary_file_result = write_workflow_summary_file(
        workflow_result=workflow_result,
        filename=summary_filename,
        register_in_manifest=register_summary_in_manifest,
    )
    readme_file_result = None
    if write_readme:
        readme_file_result = write_total_export_readme_file(
            workflow_result=workflow_result,
            filename=readme_filename,
            register_in_manifest=register_readme_in_manifest,
        )
    plan_report_file_result = None
    if write_plan_report:
        plan_report_file_result = write_total_export_plan_report_file(
            workflow_result=workflow_result,
            filename=plan_report_filename,
            register_in_manifest=register_plan_report_in_manifest,
        )
    inventory_report_file_result = None
    if write_inventory_report:
        package_result = workflow_result.package_result.package_result
        inventory_report_file_result = write_total_export_inventory_report_file(
            package_folder=package_result.package_folder,
            manifest_path=workflow_result.package_result.manifest_path,
            filename=inventory_report_filename,
            register_in_manifest=register_inventory_report_in_manifest,
        )
    final_validation_result = None
    if validate_final_manifest:
        final_validation_result = validate_manifest_json_file(workflow_result.package_result.manifest_path)
    return PreparedTotalExportResult(
        workflow_result=workflow_result,
        summary_file_result=summary_file_result,
        readme_file_result=readme_file_result,
        plan_report_file_result=plan_report_file_result,
        inventory_report_file_result=inventory_report_file_result,
        final_validation_result=final_validation_result,
        warnings=_combined_warnings(
            workflow_result,
            summary_file_result,
            readme_file_result,
            plan_report_file_result,
            inventory_report_file_result,
        ),
    )
