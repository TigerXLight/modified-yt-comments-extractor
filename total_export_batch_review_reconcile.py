from __future__ import annotations

import json
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Sequence

from total_export_batch_review_plan import (
    TotalExportBatchReviewPlanItem,
    build_total_export_batch_review_plan,
)
from total_export_review_bundle_verify import (
    REVIEW_BUNDLE_VERIFY_STATUS_VERIFIED,
    REVIEW_BUNDLE_VERIFY_STATUS_VERIFIED_WITH_WARNINGS,
    review_bundle_verification_to_dict,
    verify_total_export_review_bundle,
)


BATCH_RECONCILE_STATUS_ERROR = "error"
BATCH_RECONCILE_STATUS_MISSING_ZIP = "missing_zip"
BATCH_RECONCILE_STATUS_MISSING_SIDECARS = "missing_sidecars"
BATCH_RECONCILE_STATUS_VERIFY_FAILED = "verify_failed"
BATCH_RECONCILE_STATUS_VERIFY_PASSED = "verify_passed"
BATCH_RECONCILE_STATUS_WARNING = "warning"

BATCH_RECONCILE_REPORT_FILENAME = "TOTAL_EXPORT_BATCH_RECONCILE_REPORT.json"


@dataclass(frozen=True)
class TotalExportBatchReviewReconcileItem:
    line_number: int
    source_url: str
    normalized_url: str
    package_id: str
    title: str = ""
    package_folder: str = ""
    zip_path: str = ""
    sha256_sidecar_path: str = ""
    inspection_json_path: str = ""
    package_folder_exists: bool = False
    zip_exists: bool = False
    sha256_sidecar_exists: bool = False
    inspection_json_exists: bool = False
    duplicate_package_id: bool = False
    source_supported: bool = False
    status: str = BATCH_RECONCILE_STATUS_MISSING_ZIP
    verification_status: str = ""
    verification: dict[str, object] | None = None
    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class TotalExportBatchReviewReconcileResult:
    batch_source_file: str
    base_folder: str
    row_count: int = 0
    complete_count: int = 0
    missing_zip_count: int = 0
    missing_sidecar_count: int = 0
    verification_passed_count: int = 0
    verification_failed_count: int = 0
    duplicate_package_id_count: int = 0
    warning_count: int = 0
    error_count: int = 0
    report_path: str = ""
    report_written: bool = False
    items: tuple[TotalExportBatchReviewReconcileItem, ...] = ()
    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()


def default_batch_review_reconcile_report_path(base_folder: str) -> str:
    return str(Path(base_folder) / BATCH_RECONCILE_REPORT_FILENAME)


def _is_existing_output_warning(value: str) -> bool:
    return value.startswith("Expected ") and " already exists:" in value


def _plan_item_warnings(item: TotalExportBatchReviewPlanItem) -> tuple[str, ...]:
    return tuple(
        warning
        for warning in item.warnings
        if not _is_existing_output_warning(warning)
    )


def _item_status(
    *,
    errors: tuple[str, ...],
    warnings: tuple[str, ...],
    zip_exists: bool,
    sha_exists: bool,
    json_exists: bool,
    verification_status: str,
) -> str:
    if errors:
        return BATCH_RECONCILE_STATUS_ERROR
    if not zip_exists:
        return BATCH_RECONCILE_STATUS_MISSING_ZIP
    if not sha_exists or not json_exists:
        return BATCH_RECONCILE_STATUS_MISSING_SIDECARS
    if verification_status == REVIEW_BUNDLE_VERIFY_STATUS_VERIFIED:
        return BATCH_RECONCILE_STATUS_VERIFY_PASSED
    if verification_status == REVIEW_BUNDLE_VERIFY_STATUS_VERIFIED_WITH_WARNINGS:
        return BATCH_RECONCILE_STATUS_WARNING
    if verification_status:
        return BATCH_RECONCILE_STATUS_VERIFY_FAILED
    if warnings:
        return BATCH_RECONCILE_STATUS_WARNING
    return BATCH_RECONCILE_STATUS_VERIFY_FAILED


def _reconcile_item(plan_item: TotalExportBatchReviewPlanItem) -> TotalExportBatchReviewReconcileItem:
    zip_exists = Path(plan_item.zip_path).is_file()
    sha_exists = Path(plan_item.sha256_sidecar_path).is_file()
    json_exists = Path(plan_item.inspection_json_path).is_file()
    package_folder_exists = Path(plan_item.package_folder).is_dir()
    errors = tuple(plan_item.errors)
    warnings = _plan_item_warnings(plan_item)
    verification_status = ""
    verification: dict[str, object] | None = None

    if zip_exists and sha_exists and json_exists and not errors:
        verification_result = verify_total_export_review_bundle(
            plan_item.zip_path,
            sha256_path=plan_item.sha256_sidecar_path,
            inspection_json_path=plan_item.inspection_json_path,
        )
        verification_status = verification_result.status
        verification = review_bundle_verification_to_dict(verification_result)
        errors = errors + tuple(verification_result.errors)
        warnings = warnings + tuple(verification_result.warnings)

    status = _item_status(
        errors=errors,
        warnings=warnings,
        zip_exists=zip_exists,
        sha_exists=sha_exists,
        json_exists=json_exists,
        verification_status=verification_status,
    )

    return TotalExportBatchReviewReconcileItem(
        line_number=plan_item.line_number,
        source_url=plan_item.source_url,
        normalized_url=plan_item.normalized_url,
        package_id=plan_item.package_id,
        title=plan_item.title,
        package_folder=plan_item.package_folder,
        zip_path=plan_item.zip_path,
        sha256_sidecar_path=plan_item.sha256_sidecar_path,
        inspection_json_path=plan_item.inspection_json_path,
        package_folder_exists=package_folder_exists,
        zip_exists=zip_exists,
        sha256_sidecar_exists=sha_exists,
        inspection_json_exists=json_exists,
        duplicate_package_id=plan_item.duplicate_package_id,
        source_supported=plan_item.source_supported,
        status=status,
        verification_status=verification_status,
        verification=verification,
        errors=errors,
        warnings=warnings,
    )


def _count_items(items: tuple[TotalExportBatchReviewReconcileItem, ...], status: str) -> int:
    return sum(1 for item in items if item.status == status)


def _missing_sidecar_count(items: tuple[TotalExportBatchReviewReconcileItem, ...]) -> int:
    return sum(
        1
        for item in items
        if item.zip_exists
        and (not item.sha256_sidecar_exists or not item.inspection_json_exists)
    )


def _warning_count(
    items: tuple[TotalExportBatchReviewReconcileItem, ...],
    warnings: tuple[str, ...],
) -> int:
    return sum(1 for item in items if item.warnings) + len(warnings)


def _error_count(
    items: tuple[TotalExportBatchReviewReconcileItem, ...],
    errors: tuple[str, ...],
) -> int:
    return sum(1 for item in items if item.errors) + len(errors)


def _build_result(
    *,
    batch_source_file: str,
    base_folder: str,
    report_path: str,
    report_written: bool = False,
    items: tuple[TotalExportBatchReviewReconcileItem, ...] = (),
    errors: tuple[str, ...] = (),
    warnings: tuple[str, ...] = (),
) -> TotalExportBatchReviewReconcileResult:
    return TotalExportBatchReviewReconcileResult(
        batch_source_file=batch_source_file,
        base_folder=base_folder,
        row_count=len(items),
        complete_count=_count_items(items, BATCH_RECONCILE_STATUS_VERIFY_PASSED),
        missing_zip_count=_count_items(items, BATCH_RECONCILE_STATUS_MISSING_ZIP),
        missing_sidecar_count=_missing_sidecar_count(items),
        verification_passed_count=_count_items(items, BATCH_RECONCILE_STATUS_VERIFY_PASSED),
        verification_failed_count=_count_items(items, BATCH_RECONCILE_STATUS_VERIFY_FAILED),
        duplicate_package_id_count=sum(1 for item in items if item.duplicate_package_id),
        warning_count=_warning_count(items, warnings),
        error_count=_error_count(items, errors),
        report_path=report_path,
        report_written=report_written,
        items=items,
        errors=errors,
        warnings=warnings,
    )


def build_total_export_batch_review_reconcile(
    batch_source_file: str,
    base_folder: str,
    selected_capture_options: Sequence[str] = (),
    source_label: str = "",
) -> TotalExportBatchReviewReconcileResult:
    report_path = default_batch_review_reconcile_report_path(base_folder)
    plan = build_total_export_batch_review_plan(
        batch_source_file=batch_source_file,
        base_folder=base_folder,
        selected_capture_options=selected_capture_options,
        source_label=source_label,
        check_existing=True,
    )
    items = tuple(_reconcile_item(item) for item in plan.items)
    return _build_result(
        batch_source_file=batch_source_file,
        base_folder=base_folder,
        report_path=report_path,
        items=items,
        errors=tuple(plan.errors),
        warnings=tuple(plan.warnings),
    )


def batch_review_reconcile_to_dict(
    result: TotalExportBatchReviewReconcileResult,
) -> dict[str, object]:
    return {
        "base_folder": result.base_folder,
        "batch_source_file": result.batch_source_file,
        "complete_count": result.complete_count,
        "duplicate_package_id_count": result.duplicate_package_id_count,
        "error_count": result.error_count,
        "errors": list(result.errors),
        "items": [
            {
                "duplicate_package_id": item.duplicate_package_id,
                "errors": list(item.errors),
                "inspection_json_exists": item.inspection_json_exists,
                "inspection_json_path": item.inspection_json_path,
                "line_number": item.line_number,
                "normalized_url": item.normalized_url,
                "package_folder": item.package_folder,
                "package_folder_exists": item.package_folder_exists,
                "package_id": item.package_id,
                "sha256_sidecar_exists": item.sha256_sidecar_exists,
                "sha256_sidecar_path": item.sha256_sidecar_path,
                "source_supported": item.source_supported,
                "source_url": item.source_url,
                "status": item.status,
                "title": item.title,
                "verification": item.verification,
                "verification_status": item.verification_status,
                "warnings": list(item.warnings),
                "zip_exists": item.zip_exists,
                "zip_path": item.zip_path,
            }
            for item in result.items
        ],
        "missing_sidecar_count": result.missing_sidecar_count,
        "missing_zip_count": result.missing_zip_count,
        "report_path": result.report_path,
        "report_written": result.report_written,
        "row_count": result.row_count,
        "verification_failed_count": result.verification_failed_count,
        "verification_passed_count": result.verification_passed_count,
        "warning_count": result.warning_count,
        "warnings": list(result.warnings),
    }


def _yes_no(value: bool) -> str:
    return "yes" if value else "no"


def _append_sequence(lines: list[str], label: str, values: tuple[str, ...]) -> None:
    lines.append(label)
    if values:
        lines.extend(f"- {value}" for value in values)
    else:
        lines.append("- (none)")


def build_total_export_batch_review_reconcile_text(
    result: TotalExportBatchReviewReconcileResult,
) -> str:
    lines = [
        "Total Export batch review reconciliation",
        f"Batch source file: {result.batch_source_file}",
        f"Base folder: {result.base_folder}",
        f"Row count: {result.row_count}",
        f"Complete count: {result.complete_count}",
        f"Missing ZIP count: {result.missing_zip_count}",
        f"Missing sidecar count: {result.missing_sidecar_count}",
        f"Verification passed count: {result.verification_passed_count}",
        f"Verification failed count: {result.verification_failed_count}",
        f"Duplicate package ID count: {result.duplicate_package_id_count}",
        f"Warning count: {result.warning_count}",
        f"Error count: {result.error_count}",
        f"Report path: {result.report_path or '(none)'}",
        f"Report written: {_yes_no(result.report_written)}",
        "Items:",
    ]
    if result.items:
        for item in result.items:
            lines.append(
                f"- line {item.line_number}: {item.package_id} "
                f"[status={item.status}; zip={_yes_no(item.zip_exists)}; "
                f"sha256={_yes_no(item.sha256_sidecar_exists)}; "
                f"inspection_json={_yes_no(item.inspection_json_exists)}; "
                f"verify={item.verification_status or '(not run)'}]"
            )
    else:
        lines.append("- (none)")
    _append_sequence(lines, "Errors:", result.errors)
    _append_sequence(lines, "Warnings:", result.warnings)
    return "\n".join(lines)


def write_total_export_batch_review_reconcile_report(
    result: TotalExportBatchReviewReconcileResult,
    report_path: str = "",
    overwrite: bool = False,
) -> TotalExportBatchReviewReconcileResult:
    selected_report_path = report_path or result.report_path or default_batch_review_reconcile_report_path(
        result.base_folder
    )
    path = Path(selected_report_path)
    if path.exists() and not overwrite:
        return replace(
            result,
            report_path=selected_report_path,
            report_written=False,
            errors=result.errors + (f"Batch reconcile report already exists: {selected_report_path}",),
            error_count=result.error_count + 1,
        )

    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        updated = replace(result, report_path=selected_report_path, report_written=True)
        path.write_text(
            json.dumps(batch_review_reconcile_to_dict(updated), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return updated
    except OSError as exc:
        return replace(
            result,
            report_path=selected_report_path,
            report_written=False,
            errors=result.errors + (f"Batch reconcile report could not be written: {exc}",),
            error_count=result.error_count + 1,
        )
