from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from total_export_manifest import safe_package_id
from total_export_review_bundle import build_total_export_review_bundle
from total_export_review_bundle_folder_verify import verify_total_export_review_bundle_folder


@dataclass(frozen=True)
class TotalExportBatchReviewBundleRow:
    line_number: int
    source_url: str
    package_id: str = ""
    title: str = ""


@dataclass(frozen=True)
class TotalExportBatchReviewBundleItem:
    line_number: int
    source_url: str
    package_id: str
    title: str
    package_folder: str = ""
    zip_path: str = ""
    zip_created: bool = False
    zip_sha256: str = ""
    zip_inspection_status: str = ""
    zip_sidecar_sha256_written: bool = False
    zip_sidecar_json_written: bool = False
    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class TotalExportBatchReviewBundleResult:
    batch_source_file: str
    base_folder: str
    row_count: int = 0
    success_count: int = 0
    failed_count: int = 0
    continue_on_error: bool = True
    folder_verification_ran: bool = False
    folder_verification_zip_count: int = 0
    folder_verification_verified_count: int = 0
    folder_verification_failed_count: int = 0
    folder_verification_report_path: str = ""
    folder_verification_report_written: bool = False
    items: tuple[TotalExportBatchReviewBundleItem, ...] = ()
    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()


def parse_total_export_batch_rows(
    batch_source_file: str,
) -> tuple[TotalExportBatchReviewBundleRow, ...]:
    path = Path(batch_source_file)
    if not path.is_file():
        return ()

    rows: list[TotalExportBatchReviewBundleRow] = []
    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        fields = [field.strip() for field in raw_line.split("\t")]
        rows.append(
            TotalExportBatchReviewBundleRow(
                line_number=line_number,
                source_url=fields[0] if fields else "",
                package_id=fields[1] if len(fields) > 1 else "",
                title=fields[2] if len(fields) > 2 else "",
            )
        )
    return tuple(rows)


def _fallback_package_id(row: TotalExportBatchReviewBundleRow) -> str:
    if row.package_id:
        return row.package_id
    return safe_package_id(f"batch_line_{row.line_number}_{row.source_url}")


def _success_count(items: tuple[TotalExportBatchReviewBundleItem, ...]) -> int:
    return sum(1 for item in items if item.zip_created and not item.errors)


def _failed_count(items: tuple[TotalExportBatchReviewBundleItem, ...]) -> int:
    return sum(1 for item in items if item.errors or not item.zip_created)


def _item_from_error(
    row: TotalExportBatchReviewBundleRow,
    package_id: str,
    error: str,
) -> TotalExportBatchReviewBundleItem:
    return TotalExportBatchReviewBundleItem(
        line_number=row.line_number,
        source_url=row.source_url,
        package_id=package_id,
        title=row.title,
        errors=(error,),
    )


def _build_result(
    *,
    batch_source_file: str,
    base_folder: str,
    row_count: int,
    continue_on_error: bool,
    items: tuple[TotalExportBatchReviewBundleItem, ...] = (),
    folder_verification_ran: bool = False,
    folder_verification_zip_count: int = 0,
    folder_verification_verified_count: int = 0,
    folder_verification_failed_count: int = 0,
    folder_verification_report_path: str = "",
    folder_verification_report_written: bool = False,
    errors: tuple[str, ...] = (),
    warnings: tuple[str, ...] = (),
) -> TotalExportBatchReviewBundleResult:
    return TotalExportBatchReviewBundleResult(
        batch_source_file=batch_source_file,
        base_folder=base_folder,
        row_count=row_count,
        success_count=_success_count(items),
        failed_count=_failed_count(items),
        continue_on_error=continue_on_error,
        folder_verification_ran=folder_verification_ran,
        folder_verification_zip_count=folder_verification_zip_count,
        folder_verification_verified_count=folder_verification_verified_count,
        folder_verification_failed_count=folder_verification_failed_count,
        folder_verification_report_path=folder_verification_report_path,
        folder_verification_report_written=folder_verification_report_written,
        items=items,
        errors=errors,
        warnings=warnings,
    )


def build_total_export_batch_review_bundles(
    batch_source_file: str,
    base_folder: str,
    selected_capture_options: Sequence[str] = (),
    user_terms: Sequence[str] = (),
    source_label: str = "",
    create_asset_folders: bool = True,
    overwrite_zip: bool = False,
    overwrite_sidecars: bool = False,
    continue_on_error: bool = True,
    verify_folder_after: bool = True,
    write_folder_report: bool = False,
    overwrite_folder_report: bool = False,
    include_zip_entries: bool = False,
    hash_zip_entries: bool = False,
) -> TotalExportBatchReviewBundleResult:
    source_path = Path(batch_source_file)
    if not source_path.is_file():
        return _build_result(
            batch_source_file=batch_source_file,
            base_folder=base_folder,
            row_count=0,
            continue_on_error=continue_on_error,
            errors=(f"Batch source file does not exist: {batch_source_file}",),
        )

    rows = parse_total_export_batch_rows(batch_source_file)
    items: list[TotalExportBatchReviewBundleItem] = []
    errors: list[str] = []
    warnings: list[str] = []

    for row in rows:
        package_id = _fallback_package_id(row)
        if not row.source_url:
            item = _item_from_error(row, package_id, f"Line {row.line_number}: source URL is empty.")
            items.append(item)
            if not continue_on_error:
                warnings.append(f"Batch stopped after line {row.line_number} because continue_on_error is false.")
                break
            continue

        try:
            bundle = build_total_export_review_bundle(
                base_folder=base_folder,
                source_url=row.source_url,
                source_label=source_label,
                title=row.title,
                package_id=package_id,
                selected_capture_options=selected_capture_options,
                user_terms=user_terms,
                create_asset_folders=create_asset_folders,
                overwrite_zip=overwrite_zip,
                overwrite_sidecars=overwrite_sidecars,
                include_zip_entries=include_zip_entries,
                hash_zip_entries=hash_zip_entries,
            )
            item = TotalExportBatchReviewBundleItem(
                line_number=row.line_number,
                source_url=row.source_url,
                package_id=package_id,
                title=row.title,
                package_folder=bundle.package_folder,
                zip_path=bundle.zip_path,
                zip_created=bundle.zip_created,
                zip_sha256=bundle.zip_sha256,
                zip_inspection_status=bundle.zip_inspection_status,
                zip_sidecar_sha256_written=bundle.zip_sidecar_sha256_written,
                zip_sidecar_json_written=bundle.zip_sidecar_json_written,
                errors=tuple(bundle.errors),
                warnings=tuple(bundle.warnings),
            )
        except Exception as exc:
            item = _item_from_error(row, package_id, f"Line {row.line_number}: {exc}")
        items.append(item)

        if item.errors and not continue_on_error:
            warnings.append(f"Batch stopped after line {row.line_number} because continue_on_error is false.")
            break

    folder_verification = None
    if verify_folder_after:
        folder_verification = verify_total_export_review_bundle_folder(
            folder_path=base_folder,
            recursive=False,
            include_zip_entries=include_zip_entries,
            hash_zip_entries=hash_zip_entries,
            write_report=write_folder_report,
            overwrite_report=overwrite_folder_report,
        )
        errors.extend(folder_verification.errors)
        warnings.extend(folder_verification.warnings)

    return _build_result(
        batch_source_file=batch_source_file,
        base_folder=base_folder,
        row_count=len(rows),
        continue_on_error=continue_on_error,
        items=tuple(items),
        folder_verification_ran=folder_verification is not None,
        folder_verification_zip_count=folder_verification.zip_count if folder_verification else 0,
        folder_verification_verified_count=(
            folder_verification.verified_count if folder_verification else 0
        ),
        folder_verification_failed_count=folder_verification.failed_count if folder_verification else 0,
        folder_verification_report_path=folder_verification.report_path if folder_verification else "",
        folder_verification_report_written=folder_verification.report_written if folder_verification else False,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def batch_review_bundle_result_to_dict(
    result: TotalExportBatchReviewBundleResult,
) -> dict[str, object]:
    return {
        "base_folder": result.base_folder,
        "batch_source_file": result.batch_source_file,
        "continue_on_error": result.continue_on_error,
        "errors": list(result.errors),
        "failed_count": result.failed_count,
        "folder_verification_failed_count": result.folder_verification_failed_count,
        "folder_verification_ran": result.folder_verification_ran,
        "folder_verification_report_path": result.folder_verification_report_path,
        "folder_verification_report_written": result.folder_verification_report_written,
        "folder_verification_verified_count": result.folder_verification_verified_count,
        "folder_verification_zip_count": result.folder_verification_zip_count,
        "items": [
            {
                "errors": list(item.errors),
                "line_number": item.line_number,
                "package_folder": item.package_folder,
                "package_id": item.package_id,
                "source_url": item.source_url,
                "title": item.title,
                "warnings": list(item.warnings),
                "zip_created": item.zip_created,
                "zip_inspection_status": item.zip_inspection_status,
                "zip_path": item.zip_path,
                "zip_sha256": item.zip_sha256,
                "zip_sidecar_json_written": item.zip_sidecar_json_written,
                "zip_sidecar_sha256_written": item.zip_sidecar_sha256_written,
            }
            for item in result.items
        ],
        "row_count": result.row_count,
        "success_count": result.success_count,
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


def build_total_export_batch_review_bundle_text(
    result: TotalExportBatchReviewBundleResult,
) -> str:
    lines = [
        "Total Export batch review bundles",
        f"Batch source file: {result.batch_source_file}",
        f"Base folder: {result.base_folder}",
        f"Row count: {result.row_count}",
        f"Success count: {result.success_count}",
        f"Failed count: {result.failed_count}",
        f"Continue on error: {_yes_no(result.continue_on_error)}",
        f"Folder verification ran: {_yes_no(result.folder_verification_ran)}",
        f"Folder verification ZIP count: {result.folder_verification_zip_count}",
        f"Folder verification verified count: {result.folder_verification_verified_count}",
        f"Folder verification failed count: {result.folder_verification_failed_count}",
        f"Folder verification report path: {result.folder_verification_report_path or '(none)'}",
        f"Folder verification report written: {_yes_no(result.folder_verification_report_written)}",
        "Items:",
    ]
    if result.items:
        for item in result.items:
            status = "ok" if item.zip_created and not item.errors else "failed"
            lines.append(
                f"- line {item.line_number}: {item.package_id} "
                f"[{status}; zip_created={_yes_no(item.zip_created)}; zip={item.zip_path or '(none)'}]"
            )
    else:
        lines.append("- (none)")
    _append_sequence(lines, "Errors:", result.errors)
    _append_sequence(lines, "Warnings:", result.warnings)
    return "\n".join(lines)
