from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from source_capture_plan import SourceCapturePlan, build_source_capture_plan
from total_export_package import (
    TotalExportPlanPackageResult,
    create_total_export_package_from_plan,
)
from total_export_validation import ManifestValidationResult, validate_manifest_json_file


@dataclass(frozen=True)
class TotalExportWorkflowResult:
    plan: SourceCapturePlan
    package_result: TotalExportPlanPackageResult
    validation_result: ManifestValidationResult
    warnings: tuple[str, ...] = ()


def _combined_warnings(
    plan: SourceCapturePlan,
    package_result: TotalExportPlanPackageResult,
    validation_result: ManifestValidationResult,
) -> tuple[str, ...]:
    warnings: list[str] = []
    seen = set()

    for message in (
        list(plan.warnings)
        + list(package_result.warnings)
        + [issue.message for issue in validation_result.issues]
    ):
        if not message or message in seen:
            continue
        seen.add(message)
        warnings.append(message)
    return tuple(warnings)


def prepare_total_export_from_source(
    *,
    base_folder: str,
    source_url: str,
    source_label: str = "",
    title: str = "",
    selected_capture_options: Sequence[str] = (),
    user_terms: Sequence[str] = (),
    package_id: str = "",
    create_asset_folders: bool = True,
) -> TotalExportWorkflowResult:
    plan = build_source_capture_plan(
        source_url=source_url,
        source_label=source_label,
        title=title,
        selected_capture_options=selected_capture_options,
        user_terms=user_terms,
    )
    package_result = create_total_export_package_from_plan(
        base_folder=base_folder,
        plan=plan,
        package_id=package_id,
        create_asset_folders=create_asset_folders,
    )
    validation_result = validate_manifest_json_file(package_result.manifest_path)

    return TotalExportWorkflowResult(
        plan=plan,
        package_result=package_result,
        validation_result=validation_result,
        warnings=_combined_warnings(plan, package_result, validation_result),
    )
