from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from total_export_batch_review_bundle import (
    derive_total_export_batch_package_id,
    parse_total_export_batch_rows,
)
from total_export_manifest import default_package_folder, safe_package_id
from total_export_package_zip import default_total_export_zip_path
from total_export_zip_sidecar import (
    default_zip_json_sidecar_path,
    default_zip_sha256_sidecar_path,
)
from youtube_url_utils import normalize_youtube_url


@dataclass(frozen=True)
class TotalExportBatchReviewPlanItem:
    line_number: int
    source_url: str
    package_id: str
    title: str = ""
    normalized_url: str = ""
    package_folder: str = ""
    zip_path: str = ""
    sha256_sidecar_path: str = ""
    inspection_json_path: str = ""
    source_supported: bool = False
    existing_package_folder: bool = False
    existing_zip: bool = False
    existing_sha256_sidecar: bool = False
    existing_inspection_json_sidecar: bool = False
    duplicate_package_id: bool = False
    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class TotalExportBatchReviewPlanResult:
    batch_source_file: str
    base_folder: str
    row_count: int = 0
    ready_count: int = 0
    warning_count: int = 0
    error_count: int = 0
    duplicate_package_id_count: int = 0
    existing_zip_count: int = 0
    items: tuple[TotalExportBatchReviewPlanItem, ...] = ()
    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()


def _package_key(package_id: str) -> str:
    return safe_package_id(package_id)


def _expected_paths(base_folder: str, package_id: str) -> tuple[str, str, str, str]:
    package_folder = default_package_folder(base_folder, package_id)
    zip_path = default_total_export_zip_path(package_folder)
    return (
        package_folder,
        zip_path,
        default_zip_sha256_sidecar_path(zip_path),
        default_zip_json_sidecar_path(zip_path),
    )


def _source_plan(source_url: str) -> tuple[str, bool, tuple[str, ...]]:
    try:
        return normalize_youtube_url(source_url), True, ()
    except ValueError:
        return "", False, (f"No source adapter supports the URL: {source_url}",)


def _ready_count(items: tuple[TotalExportBatchReviewPlanItem, ...]) -> int:
    return sum(1 for item in items if not item.errors)


def _warning_count(
    items: tuple[TotalExportBatchReviewPlanItem, ...],
    warnings: tuple[str, ...],
) -> int:
    return sum(1 for item in items if item.warnings) + len(warnings)


def _error_count(
    items: tuple[TotalExportBatchReviewPlanItem, ...],
    errors: tuple[str, ...],
) -> int:
    return sum(1 for item in items if item.errors) + len(errors)


def _build_result(
    *,
    batch_source_file: str,
    base_folder: str,
    items: tuple[TotalExportBatchReviewPlanItem, ...] = (),
    errors: tuple[str, ...] = (),
    warnings: tuple[str, ...] = (),
) -> TotalExportBatchReviewPlanResult:
    return TotalExportBatchReviewPlanResult(
        batch_source_file=batch_source_file,
        base_folder=base_folder,
        row_count=len(items),
        ready_count=_ready_count(items),
        warning_count=_warning_count(items, warnings),
        error_count=_error_count(items, errors),
        duplicate_package_id_count=sum(1 for item in items if item.duplicate_package_id),
        existing_zip_count=sum(1 for item in items if item.existing_zip),
        items=items,
        errors=errors,
        warnings=warnings,
    )


def build_total_export_batch_review_plan(
    batch_source_file: str,
    base_folder: str,
    selected_capture_options: Sequence[str] = (),
    source_label: str = "",
    check_existing: bool = True,
) -> TotalExportBatchReviewPlanResult:
    del selected_capture_options, source_label
    if not Path(batch_source_file).is_file():
        return _build_result(
            batch_source_file=batch_source_file,
            base_folder=base_folder,
            errors=(f"Batch source file does not exist: {batch_source_file}",),
        )

    rows = parse_total_export_batch_rows(batch_source_file)
    package_ids = [derive_total_export_batch_package_id(row) for row in rows]
    package_key_counts = Counter(_package_key(package_id) for package_id in package_ids)
    items: list[TotalExportBatchReviewPlanItem] = []

    for row, package_id in zip(rows, package_ids):
        package_folder, zip_path, sha_path, json_path = _expected_paths(base_folder, package_id)
        errors: list[str] = []
        warnings: list[str] = []
        normalized_url = ""
        source_supported = False

        if not row.source_url:
            errors.append(f"Line {row.line_number}: source URL is empty.")
        else:
            normalized_url, source_supported, source_warnings = _source_plan(row.source_url)
            warnings.extend(source_warnings)

        duplicate = package_key_counts[_package_key(package_id)] > 1
        if duplicate:
            warnings.append(f"Duplicate package ID/output path detected: {safe_package_id(package_id)}")

        existing_package_folder = Path(package_folder).is_dir() if check_existing else False
        existing_zip = Path(zip_path).is_file() if check_existing else False
        existing_sha = Path(sha_path).is_file() if check_existing else False
        existing_json = Path(json_path).is_file() if check_existing else False
        if existing_package_folder:
            warnings.append(f"Expected package folder already exists: {package_folder}")
        if existing_zip:
            warnings.append(f"Expected ZIP already exists: {zip_path}")
        if existing_sha:
            warnings.append(f"Expected SHA256 sidecar already exists: {sha_path}")
        if existing_json:
            warnings.append(f"Expected inspection JSON sidecar already exists: {json_path}")

        items.append(
            TotalExportBatchReviewPlanItem(
                line_number=row.line_number,
                source_url=row.source_url,
                package_id=package_id,
                title=row.title,
                normalized_url=normalized_url,
                package_folder=package_folder,
                zip_path=zip_path,
                sha256_sidecar_path=sha_path,
                inspection_json_path=json_path,
                source_supported=source_supported,
                existing_package_folder=existing_package_folder,
                existing_zip=existing_zip,
                existing_sha256_sidecar=existing_sha,
                existing_inspection_json_sidecar=existing_json,
                duplicate_package_id=duplicate,
                errors=tuple(errors),
                warnings=tuple(warnings),
            )
        )

    return _build_result(
        batch_source_file=batch_source_file,
        base_folder=base_folder,
        items=tuple(items),
    )


def batch_review_plan_to_dict(
    result: TotalExportBatchReviewPlanResult,
) -> dict[str, object]:
    return {
        "base_folder": result.base_folder,
        "batch_source_file": result.batch_source_file,
        "duplicate_package_id_count": result.duplicate_package_id_count,
        "error_count": result.error_count,
        "errors": list(result.errors),
        "existing_zip_count": result.existing_zip_count,
        "items": [
            {
                "duplicate_package_id": item.duplicate_package_id,
                "errors": list(item.errors),
                "existing_inspection_json_sidecar": item.existing_inspection_json_sidecar,
                "existing_package_folder": item.existing_package_folder,
                "existing_sha256_sidecar": item.existing_sha256_sidecar,
                "existing_zip": item.existing_zip,
                "inspection_json_path": item.inspection_json_path,
                "line_number": item.line_number,
                "normalized_url": item.normalized_url,
                "package_folder": item.package_folder,
                "package_id": item.package_id,
                "sha256_sidecar_path": item.sha256_sidecar_path,
                "source_supported": item.source_supported,
                "source_url": item.source_url,
                "title": item.title,
                "warnings": list(item.warnings),
                "zip_path": item.zip_path,
            }
            for item in result.items
        ],
        "ready_count": result.ready_count,
        "row_count": result.row_count,
        "warning_count": result.warning_count,
        "warnings": list(result.warnings),
    }


def _append_sequence(lines: list[str], label: str, values: tuple[str, ...]) -> None:
    lines.append(label)
    if values:
        lines.extend(f"- {value}" for value in values)
    else:
        lines.append("- (none)")


def build_total_export_batch_review_plan_text(
    result: TotalExportBatchReviewPlanResult,
) -> str:
    lines = [
        "Total Export batch review plan",
        f"Batch source file: {result.batch_source_file}",
        f"Base folder: {result.base_folder}",
        f"Row count: {result.row_count}",
        f"Ready count: {result.ready_count}",
        f"Warning count: {result.warning_count}",
        f"Error count: {result.error_count}",
        f"Duplicate package ID count: {result.duplicate_package_id_count}",
        f"Existing ZIP count: {result.existing_zip_count}",
        "Items:",
    ]
    if result.items:
        for item in result.items:
            if item.errors:
                status = "error"
            elif item.warnings:
                status = "warning"
            else:
                status = "ready"
            lines.append(
                f"- line {item.line_number}: {item.package_id} "
                f"[{status}; source={item.source_url or '(none)'}; zip={item.zip_path or '(none)'}]"
            )
    else:
        lines.append("- (none)")
    _append_sequence(lines, "Errors:", result.errors)
    _append_sequence(lines, "Warnings:", result.warnings)
    return "\n".join(lines)
