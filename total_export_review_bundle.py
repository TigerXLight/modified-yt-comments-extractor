from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from total_export_package_inspect import (
    TotalExportPackageInspectionResult,
    inspect_total_export_package,
)
from total_export_package_zip import (
    TotalExportPackageZipResult,
    create_total_export_package_zip,
)
from total_export_prepare import PreparedTotalExportResult, prepare_total_export_with_summary
from total_export_zip_inspect import TotalExportZipInspectionResult, inspect_total_export_zip
from total_export_zip_sidecar import (
    TotalExportZipSidecarResult,
    write_total_export_zip_sidecars,
)


@dataclass(frozen=True)
class TotalExportReviewBundleResult:
    source_url: str
    normalized_url: str = ""
    package_folder: str = ""
    manifest_path: str = ""
    summary_path: str = ""
    readme_path: str = ""
    plan_report_path: str = ""
    inventory_report_path: str = ""
    package_inspection_status: str = ""
    package_manifest_valid: bool = False
    zip_path: str = ""
    zip_created: bool = False
    zip_sha256: str = ""
    zip_size_bytes: int = 0
    zip_inspection_status: str = ""
    zip_sidecar_sha256_path: str = ""
    zip_sidecar_json_path: str = ""
    zip_sidecar_sha256_written: bool = False
    zip_sidecar_json_written: bool = False
    final_validation_issue_count: int = 0
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()


def _dedupe(values: Sequence[str]) -> tuple[str, ...]:
    deduped: list[str] = []
    seen = set()
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        deduped.append(value)
    return tuple(deduped)


def _prepared_warnings(prepared: PreparedTotalExportResult) -> tuple[str, ...]:
    return tuple(prepared.warnings)


def _package_inspection_warnings(
    inspection: TotalExportPackageInspectionResult,
) -> tuple[str, ...]:
    return tuple(inspection.validation_warnings) + tuple(inspection.warnings)


def _zip_result_warnings(zip_result: TotalExportPackageZipResult) -> tuple[str, ...]:
    return tuple(zip_result.inspection_warnings) + tuple(zip_result.warnings)


def _zip_inspection_warnings(
    inspection: TotalExportZipInspectionResult | None,
) -> tuple[str, ...]:
    if not inspection:
        return ()
    return tuple(inspection.warnings)


def _sidecar_warnings(sidecar: TotalExportZipSidecarResult | None) -> tuple[str, ...]:
    if not sidecar:
        return ()
    return tuple(sidecar.warnings)


def _sidecar_errors(sidecar: TotalExportZipSidecarResult | None) -> tuple[str, ...]:
    if not sidecar:
        return ()
    return tuple(sidecar.errors)


def _final_validation_issue_count(prepared: PreparedTotalExportResult) -> int:
    if not prepared.final_validation_result:
        return 0
    return len(prepared.final_validation_result.issues)


def build_total_export_review_bundle(
    *,
    base_folder: str,
    source_url: str,
    source_label: str = "",
    title: str = "",
    package_id: str = "",
    selected_capture_options: Sequence[str] = (),
    user_terms: Sequence[str] = (),
    create_asset_folders: bool = True,
    zip_path: str = "",
    overwrite_zip: bool = False,
    write_sidecars: bool = True,
    overwrite_sidecars: bool = False,
    include_zip_entries: bool = False,
    hash_zip_entries: bool = False,
) -> TotalExportReviewBundleResult:
    prepared = prepare_total_export_with_summary(
        base_folder=base_folder,
        source_url=source_url,
        source_label=source_label,
        title=title,
        selected_capture_options=selected_capture_options,
        user_terms=user_terms,
        package_id=package_id,
        create_asset_folders=create_asset_folders,
        write_readme=True,
        write_plan_report=True,
        write_inventory_report=True,
        validate_final_manifest=True,
    )
    plan = prepared.workflow_result.plan
    package_result = prepared.workflow_result.package_result.package_result
    manifest_path = prepared.workflow_result.package_result.manifest_path
    package_folder = package_result.package_folder

    package_inspection = inspect_total_export_package(
        package_folder=package_folder,
        manifest_path=manifest_path,
    )
    zip_result = create_total_export_package_zip(
        package_folder=package_folder,
        manifest_path=manifest_path,
        zip_path=zip_path,
        overwrite=overwrite_zip,
    )

    zip_inspection = None
    sidecar_result = None
    if zip_result.zip_created:
        zip_inspection = inspect_total_export_zip(
            zip_result.zip_path,
            include_entries=include_zip_entries,
            hash_entries=hash_zip_entries,
        )
        if write_sidecars:
            sidecar_result = write_total_export_zip_sidecars(
                zip_result.zip_path,
                overwrite=overwrite_sidecars,
                require_zip_status_ok=True,
                include_entries=include_zip_entries,
                hash_entries=hash_zip_entries,
            )

    warnings = _dedupe(
        _prepared_warnings(prepared)
        + _package_inspection_warnings(package_inspection)
        + _zip_result_warnings(zip_result)
        + _zip_inspection_warnings(zip_inspection)
        + _sidecar_warnings(sidecar_result)
    )
    errors = _dedupe(tuple(zip_result.errors) + _sidecar_errors(sidecar_result))

    return TotalExportReviewBundleResult(
        source_url=plan.source_url or source_url,
        normalized_url=plan.normalized_url,
        package_folder=package_folder,
        manifest_path=manifest_path,
        summary_path=prepared.summary_file_result.summary_path,
        readme_path=(
            prepared.readme_file_result.readme_path if prepared.readme_file_result else ""
        ),
        plan_report_path=(
            prepared.plan_report_file_result.report_path
            if prepared.plan_report_file_result
            else ""
        ),
        inventory_report_path=(
            prepared.inventory_report_file_result.report_path
            if prepared.inventory_report_file_result
            else ""
        ),
        package_inspection_status=package_inspection.status,
        package_manifest_valid=package_inspection.manifest_valid,
        zip_path=zip_result.zip_path,
        zip_created=zip_result.zip_created,
        zip_sha256=zip_result.zip_sha256,
        zip_size_bytes=zip_result.zip_size_bytes,
        zip_inspection_status=zip_inspection.status if zip_inspection else "",
        zip_sidecar_sha256_path=sidecar_result.sha256_path if sidecar_result else "",
        zip_sidecar_json_path=sidecar_result.json_path if sidecar_result else "",
        zip_sidecar_sha256_written=bool(sidecar_result and sidecar_result.sha256_written),
        zip_sidecar_json_written=bool(sidecar_result and sidecar_result.json_written),
        final_validation_issue_count=_final_validation_issue_count(prepared),
        warnings=warnings,
        errors=errors,
    )


def review_bundle_result_to_dict(
    result: TotalExportReviewBundleResult,
) -> dict[str, object]:
    return {
        "errors": list(result.errors),
        "final_validation_issue_count": result.final_validation_issue_count,
        "inventory_report_path": result.inventory_report_path,
        "manifest_path": result.manifest_path,
        "normalized_url": result.normalized_url,
        "package_folder": result.package_folder,
        "package_inspection_status": result.package_inspection_status,
        "package_manifest_valid": result.package_manifest_valid,
        "plan_report_path": result.plan_report_path,
        "readme_path": result.readme_path,
        "source_url": result.source_url,
        "summary_path": result.summary_path,
        "warnings": list(result.warnings),
        "zip_created": result.zip_created,
        "zip_inspection_status": result.zip_inspection_status,
        "zip_path": result.zip_path,
        "zip_sha256": result.zip_sha256,
        "zip_sidecar_json_path": result.zip_sidecar_json_path,
        "zip_sidecar_json_written": result.zip_sidecar_json_written,
        "zip_sidecar_sha256_path": result.zip_sidecar_sha256_path,
        "zip_sidecar_sha256_written": result.zip_sidecar_sha256_written,
        "zip_size_bytes": result.zip_size_bytes,
    }


def _yes_no(value: bool) -> str:
    return "yes" if value else "no"


def _append_sequence(lines: list[str], label: str, values: tuple[str, ...]) -> None:
    lines.append(label)
    if values:
        for value in values:
            lines.append(f"- {value}")
    else:
        lines.append("- (none)")


def build_total_export_review_bundle_text(
    result: TotalExportReviewBundleResult,
) -> str:
    lines = [
        "Total Export review bundle",
        f"Source URL: {result.source_url or '(none)'}",
        f"Normalized URL: {result.normalized_url or '(none)'}",
        f"Package folder: {result.package_folder or '(none)'}",
        f"Manifest path: {result.manifest_path or '(none)'}",
        f"Summary path: {result.summary_path or '(none)'}",
        f"README path: {result.readme_path or '(none)'}",
        f"Plan report path: {result.plan_report_path or '(none)'}",
        f"Inventory report path: {result.inventory_report_path or '(none)'}",
        f"Package inspection status: {result.package_inspection_status or '(none)'}",
        f"Package manifest valid: {_yes_no(result.package_manifest_valid)}",
        f"ZIP path: {result.zip_path or '(none)'}",
        f"ZIP created: {_yes_no(result.zip_created)}",
        f"ZIP SHA-256: {result.zip_sha256 or '(none)'}",
        f"ZIP size bytes: {result.zip_size_bytes}",
        f"ZIP inspection status: {result.zip_inspection_status or '(none)'}",
        f"ZIP SHA256 sidecar path: {result.zip_sidecar_sha256_path or '(none)'}",
        f"ZIP inspection sidecar path: {result.zip_sidecar_json_path or '(none)'}",
        f"ZIP SHA256 sidecar written: {_yes_no(result.zip_sidecar_sha256_written)}",
        f"ZIP inspection sidecar written: {_yes_no(result.zip_sidecar_json_written)}",
        f"Final validation issue count: {result.final_validation_issue_count}",
    ]
    _append_sequence(lines, "Errors:", result.errors)
    _append_sequence(lines, "Warnings:", result.warnings)
    return "\n".join(lines)
