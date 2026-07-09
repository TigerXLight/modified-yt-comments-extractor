from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from total_export_review_bundle_verify import (
    REVIEW_BUNDLE_VERIFY_STATUS_INVALID_SIDECAR,
    REVIEW_BUNDLE_VERIFY_STATUS_INVALID_ZIP,
    REVIEW_BUNDLE_VERIFY_STATUS_MISMATCH,
    REVIEW_BUNDLE_VERIFY_STATUS_MISSING_SIDECAR,
    REVIEW_BUNDLE_VERIFY_STATUS_MISSING_ZIP,
    REVIEW_BUNDLE_VERIFY_STATUS_UNSAFE_ZIP,
    REVIEW_BUNDLE_VERIFY_STATUS_VERIFIED,
    REVIEW_BUNDLE_VERIFY_STATUS_VERIFIED_WITH_WARNINGS,
    verify_total_export_review_bundle,
)


FOLDER_VERIFY_REPORT_FILENAME = "TOTAL_EXPORT_REVIEW_BUNDLE_VERIFY_REPORT.json"


@dataclass(frozen=True)
class TotalExportReviewBundleFolderItem:
    zip_path: str
    status: str
    zip_sha256: str = ""
    zip_size_bytes: int = 0
    zip_found: bool = False
    zip_readable: bool = False
    sha256_sidecar_found: bool = False
    inspection_json_found: bool = False
    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class TotalExportReviewBundleFolderVerificationResult:
    folder_path: str
    recursive: bool = False
    zip_count: int = 0
    verified_count: int = 0
    verified_with_warnings_count: int = 0
    missing_zip_count: int = 0
    invalid_zip_count: int = 0
    missing_sidecar_count: int = 0
    invalid_sidecar_count: int = 0
    mismatch_count: int = 0
    unsafe_zip_count: int = 0
    failed_count: int = 0
    report_path: str = ""
    report_written: bool = False
    items: tuple[TotalExportReviewBundleFolderItem, ...] = ()
    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()


def _relative_sort_key(path: Path, folder_path: Path) -> str:
    try:
        return path.resolve().relative_to(folder_path.resolve()).as_posix()
    except ValueError:
        return path.as_posix().replace("\\", "/")


def discover_review_bundle_zip_paths(
    folder_path: str,
    recursive: bool = False,
) -> tuple[str, ...]:
    folder = Path(folder_path)
    if not folder.is_dir():
        return ()
    pattern = "**/*.zip" if recursive else "*.zip"
    paths = [path for path in folder.glob(pattern) if path.is_file()]
    return tuple(str(path) for path in sorted(paths, key=lambda item: _relative_sort_key(item, folder)))


def default_review_bundle_folder_report_path(folder_path: str) -> str:
    return str(Path(folder_path) / FOLDER_VERIFY_REPORT_FILENAME)


def _item_from_verification(verification) -> TotalExportReviewBundleFolderItem:
    return TotalExportReviewBundleFolderItem(
        zip_path=verification.zip_path,
        status=verification.status,
        zip_sha256=verification.zip_sha256,
        zip_size_bytes=verification.zip_size_bytes,
        zip_found=verification.zip_found,
        zip_readable=verification.zip_readable,
        sha256_sidecar_found=verification.sha256_sidecar_found,
        inspection_json_found=verification.inspection_json_found,
        errors=tuple(verification.errors),
        warnings=tuple(verification.warnings),
    )


def _count_status(items: tuple[TotalExportReviewBundleFolderItem, ...], status: str) -> int:
    return sum(1 for item in items if item.status == status)


def _failed_count(items: tuple[TotalExportReviewBundleFolderItem, ...]) -> int:
    return sum(
        1
        for item in items
        if item.status
        not in {
            REVIEW_BUNDLE_VERIFY_STATUS_VERIFIED,
            REVIEW_BUNDLE_VERIFY_STATUS_VERIFIED_WITH_WARNINGS,
        }
    )


def _build_result(
    *,
    folder_path: str,
    recursive: bool,
    report_path: str,
    report_written: bool = False,
    items: tuple[TotalExportReviewBundleFolderItem, ...] = (),
    errors: tuple[str, ...] = (),
    warnings: tuple[str, ...] = (),
) -> TotalExportReviewBundleFolderVerificationResult:
    return TotalExportReviewBundleFolderVerificationResult(
        folder_path=folder_path,
        recursive=recursive,
        zip_count=len(items),
        verified_count=_count_status(items, REVIEW_BUNDLE_VERIFY_STATUS_VERIFIED),
        verified_with_warnings_count=_count_status(
            items,
            REVIEW_BUNDLE_VERIFY_STATUS_VERIFIED_WITH_WARNINGS,
        ),
        missing_zip_count=_count_status(items, REVIEW_BUNDLE_VERIFY_STATUS_MISSING_ZIP),
        invalid_zip_count=_count_status(items, REVIEW_BUNDLE_VERIFY_STATUS_INVALID_ZIP),
        missing_sidecar_count=_count_status(items, REVIEW_BUNDLE_VERIFY_STATUS_MISSING_SIDECAR),
        invalid_sidecar_count=_count_status(items, REVIEW_BUNDLE_VERIFY_STATUS_INVALID_SIDECAR),
        mismatch_count=_count_status(items, REVIEW_BUNDLE_VERIFY_STATUS_MISMATCH),
        unsafe_zip_count=_count_status(items, REVIEW_BUNDLE_VERIFY_STATUS_UNSAFE_ZIP),
        failed_count=_failed_count(items),
        report_path=report_path,
        report_written=report_written,
        items=items,
        errors=errors,
        warnings=warnings,
    )


def verify_total_export_review_bundle_folder(
    folder_path: str,
    recursive: bool = False,
    include_zip_entries: bool = False,
    hash_zip_entries: bool = False,
    write_report: bool = False,
    report_path: str = "",
    overwrite_report: bool = False,
) -> TotalExportReviewBundleFolderVerificationResult:
    selected_report_path = report_path or default_review_bundle_folder_report_path(folder_path)
    folder = Path(folder_path)
    if not folder.is_dir():
        return _build_result(
            folder_path=folder_path,
            recursive=recursive,
            report_path=selected_report_path,
            errors=(f"Review bundle folder does not exist: {folder_path}",),
        )

    items = tuple(
        _item_from_verification(
            verify_total_export_review_bundle(
                zip_path,
                include_zip_entries=include_zip_entries,
                hash_zip_entries=hash_zip_entries,
            )
        )
        for zip_path in discover_review_bundle_zip_paths(folder_path, recursive=recursive)
    )
    result = _build_result(
        folder_path=folder_path,
        recursive=recursive,
        report_path=selected_report_path,
        items=items,
    )
    if not write_report:
        return result

    report_file = Path(selected_report_path)
    if report_file.exists() and not overwrite_report:
        return _build_result(
            folder_path=folder_path,
            recursive=recursive,
            report_path=selected_report_path,
            items=items,
            errors=(f"Folder verification report already exists: {selected_report_path}",),
        )

    result = _build_result(
        folder_path=folder_path,
        recursive=recursive,
        report_path=selected_report_path,
        report_written=True,
        items=items,
    )
    try:
        report_file.parent.mkdir(parents=True, exist_ok=True)
        report_file.write_text(
            json.dumps(
                review_bundle_folder_verification_to_dict(result),
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
    except OSError as exc:
        return _build_result(
            folder_path=folder_path,
            recursive=recursive,
            report_path=selected_report_path,
            items=items,
            errors=(f"Folder verification report could not be written: {exc}",),
        )
    return result


def review_bundle_folder_verification_to_dict(
    result: TotalExportReviewBundleFolderVerificationResult,
) -> dict[str, object]:
    return {
        "errors": list(result.errors),
        "failed_count": result.failed_count,
        "folder_path": result.folder_path,
        "invalid_sidecar_count": result.invalid_sidecar_count,
        "invalid_zip_count": result.invalid_zip_count,
        "items": [
            {
                "errors": list(item.errors),
                "inspection_json_found": item.inspection_json_found,
                "sha256_sidecar_found": item.sha256_sidecar_found,
                "status": item.status,
                "warnings": list(item.warnings),
                "zip_found": item.zip_found,
                "zip_path": item.zip_path,
                "zip_readable": item.zip_readable,
                "zip_sha256": item.zip_sha256,
                "zip_size_bytes": item.zip_size_bytes,
            }
            for item in result.items
        ],
        "mismatch_count": result.mismatch_count,
        "missing_sidecar_count": result.missing_sidecar_count,
        "missing_zip_count": result.missing_zip_count,
        "recursive": result.recursive,
        "report_path": result.report_path,
        "report_written": result.report_written,
        "unsafe_zip_count": result.unsafe_zip_count,
        "verified_count": result.verified_count,
        "verified_with_warnings_count": result.verified_with_warnings_count,
        "warnings": list(result.warnings),
        "zip_count": result.zip_count,
    }


def _yes_no(value: bool) -> str:
    return "yes" if value else "no"


def _append_sequence(lines: list[str], label: str, values: tuple[str, ...]) -> None:
    lines.append(label)
    if values:
        lines.extend(f"- {value}" for value in values)
    else:
        lines.append("- (none)")


def build_total_export_review_bundle_folder_verification_text(
    result: TotalExportReviewBundleFolderVerificationResult,
) -> str:
    lines = [
        "Total Export review bundle folder verification",
        f"Folder path: {result.folder_path}",
        f"Recursive: {_yes_no(result.recursive)}",
        f"ZIP count: {result.zip_count}",
        f"Verified count: {result.verified_count}",
        f"Verified with warnings count: {result.verified_with_warnings_count}",
        f"Missing ZIP count: {result.missing_zip_count}",
        f"Invalid ZIP count: {result.invalid_zip_count}",
        f"Missing sidecar count: {result.missing_sidecar_count}",
        f"Invalid sidecar count: {result.invalid_sidecar_count}",
        f"Mismatch count: {result.mismatch_count}",
        f"Unsafe ZIP count: {result.unsafe_zip_count}",
        f"Failed count: {result.failed_count}",
        f"Report path: {result.report_path or '(none)'}",
        f"Report written: {_yes_no(result.report_written)}",
        "Items:",
    ]
    if result.items:
        for item in result.items:
            lines.append(
                f"- {item.zip_path} "
                f"[status={item.status}; size={item.zip_size_bytes}; sha256={item.zip_sha256 or '(none)'}]"
            )
    else:
        lines.append("- (none)")
    _append_sequence(lines, "Errors:", result.errors)
    _append_sequence(lines, "Warnings:", result.warnings)
    return "\n".join(lines)
