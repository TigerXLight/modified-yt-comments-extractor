from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from total_export_zip_inspect import (
    ZIP_INSPECTION_STATUS_INVALID_ZIP,
    ZIP_INSPECTION_STATUS_MISSING_ZIP,
    ZIP_INSPECTION_STATUS_OK,
    ZIP_INSPECTION_STATUS_UNSAFE_ENTRIES,
    TotalExportZipInspectionResult,
    inspect_total_export_zip,
)
from total_export_zip_sidecar import (
    default_zip_json_sidecar_path,
    default_zip_sha256_sidecar_path,
)


REVIEW_BUNDLE_VERIFY_STATUS_VERIFIED = "verified"
REVIEW_BUNDLE_VERIFY_STATUS_VERIFIED_WITH_WARNINGS = "verified_with_warnings"
REVIEW_BUNDLE_VERIFY_STATUS_MISSING_ZIP = "missing_zip"
REVIEW_BUNDLE_VERIFY_STATUS_INVALID_ZIP = "invalid_zip"
REVIEW_BUNDLE_VERIFY_STATUS_MISSING_SIDECAR = "missing_sidecar"
REVIEW_BUNDLE_VERIFY_STATUS_INVALID_SIDECAR = "invalid_sidecar"
REVIEW_BUNDLE_VERIFY_STATUS_MISMATCH = "mismatch"
REVIEW_BUNDLE_VERIFY_STATUS_UNSAFE_ZIP = "unsafe_zip"


@dataclass(frozen=True)
class TotalExportReviewBundleVerificationResult:
    zip_path: str
    sha256_path: str = ""
    inspection_json_path: str = ""
    status: str = REVIEW_BUNDLE_VERIFY_STATUS_MISSING_ZIP
    zip_found: bool = False
    zip_readable: bool = False
    zip_status: str = ""
    zip_sha256: str = ""
    zip_size_bytes: int = 0
    sha256_sidecar_found: bool = False
    sha256_sidecar_valid: bool = False
    sha256_sidecar_sha256: str = ""
    sha256_sidecar_filename: str = ""
    inspection_json_found: bool = False
    inspection_json_readable: bool = False
    inspection_json_valid: bool = False
    inspection_json_zip_status: str = ""
    inspection_json_zip_sha256: str = ""
    inspection_json_zip_size_bytes: int = 0
    inspection_json_entry_count: int = 0
    current_entry_count: int = 0
    current_file_entry_count: int = 0
    hash_matches_sha256_sidecar: bool = False
    hash_matches_inspection_json: bool = False
    size_matches_inspection_json: bool = False
    entry_count_matches_inspection_json: bool = False
    status_matches_inspection_json: bool = False
    standard_entries_ok: bool = False
    unsafe_entries: tuple[str, ...] = ()
    duplicate_entries: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()


def default_review_bundle_sha256_path(zip_path: str) -> str:
    return default_zip_sha256_sidecar_path(zip_path)


def default_review_bundle_inspection_json_path(zip_path: str) -> str:
    return default_zip_json_sidecar_path(zip_path)


def parse_sha256_sidecar_text(text: str) -> tuple[str, str]:
    stripped = (text or "").strip()
    if not stripped:
        raise ValueError("SHA256 sidecar is empty.")
    parts = stripped.split(None, 1)
    if len(parts) != 2:
        raise ValueError("SHA256 sidecar must contain a hash and filename.")
    sha256_value, filename = parts[0].strip(), parts[1].strip()
    if not re.fullmatch(r"[0-9a-fA-F]{64}", sha256_value):
        raise ValueError("SHA256 sidecar hash must be 64 hexadecimal characters.")
    if not filename:
        raise ValueError("SHA256 sidecar filename is empty.")
    return sha256_value.lower(), filename


def _read_sha256_sidecar(
    *,
    zip_path: str,
    sha256_path: str,
    current_zip_sha256: str,
) -> tuple[bool, bool, str, str, bool, tuple[str, ...], tuple[str, ...]]:
    path = Path(sha256_path)
    if not path.is_file():
        return False, False, "", "", False, (f"SHA256 sidecar missing: {sha256_path}",), ()
    try:
        sidecar_sha256, sidecar_filename = parse_sha256_sidecar_text(
            path.read_text(encoding="utf-8")
        )
    except Exception as exc:
        return True, False, "", "", False, (f"SHA256 sidecar invalid: {exc}",), ()

    errors: list[str] = []
    filename_matches = sidecar_filename == Path(zip_path).name
    if not filename_matches:
        errors.append(
            "SHA256 sidecar filename does not match ZIP filename: "
            f"{sidecar_filename} != {Path(zip_path).name}"
        )
    hash_matches = bool(current_zip_sha256 and sidecar_sha256 == current_zip_sha256)
    if not hash_matches:
        errors.append("SHA256 sidecar hash does not match current ZIP SHA-256.")
    return True, filename_matches, sidecar_sha256, sidecar_filename, hash_matches, tuple(errors), ()


def _read_inspection_json(
    *,
    inspection_json_path: str,
    current: TotalExportZipInspectionResult,
) -> tuple[
    bool,
    bool,
    bool,
    str,
    str,
    int,
    int,
    bool,
    bool,
    bool,
    bool,
    bool,
    tuple[str, ...],
    tuple[str, ...],
]:
    path = Path(inspection_json_path)
    if not path.is_file():
        return (
            False,
            False,
            False,
            "",
            "",
            0,
            0,
            False,
            False,
            False,
            False,
            False,
            (f"Inspection JSON sidecar missing: {inspection_json_path}",),
            (),
        )
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return (
            True,
            False,
            False,
            "",
            "",
            0,
            0,
            False,
            False,
            False,
            False,
            False,
            (f"Inspection JSON sidecar is not readable JSON: {exc}",),
            (),
        )

    inspection = data.get("zip_inspection") if isinstance(data, dict) else None
    if not isinstance(inspection, dict):
        return (
            True,
            True,
            False,
            "",
            "",
            0,
            0,
            False,
            False,
            False,
            False,
            False,
            ("Inspection JSON sidecar is missing zip_inspection object.",),
            (),
        )

    try:
        json_status = str(inspection.get("status", ""))
        json_sha256 = str(inspection.get("zip_sha256", ""))
        json_size = int(inspection.get("zip_size_bytes") or 0)
        json_entry_count = int(inspection.get("entry_count") or 0)
    except (TypeError, ValueError) as exc:
        return (
            True,
            True,
            False,
            "",
            "",
            0,
            0,
            False,
            False,
            False,
            False,
            False,
            (f"Inspection JSON sidecar has invalid field types: {exc}",),
            (),
        )

    required_fields_present = all(
        field in inspection
        for field in ("status", "zip_sha256", "zip_size_bytes", "entry_count")
    )
    if not required_fields_present:
        return (
            True,
            True,
            False,
            json_status,
            json_sha256,
            json_size,
            json_entry_count,
            False,
            False,
            False,
            False,
            False,
            ("Inspection JSON sidecar is missing required zip_inspection fields.",),
            (),
        )

    hash_matches = bool(current.zip_sha256 and json_sha256 == current.zip_sha256)
    size_matches = json_size == current.zip_size_bytes
    count_matches = json_entry_count == current.entry_count
    status_matches = json_status == current.status
    standard_entries_ok = _standard_entries_match_current(inspection, current)

    errors: list[str] = []
    if not hash_matches:
        errors.append("Inspection JSON ZIP SHA-256 does not match current ZIP SHA-256.")
    if not size_matches:
        errors.append("Inspection JSON ZIP size does not match current ZIP size.")
    if not count_matches:
        errors.append("Inspection JSON entry count does not match current ZIP entry count.")
    if not status_matches:
        errors.append("Inspection JSON ZIP status does not match current ZIP status.")
    if not standard_entries_ok:
        errors.append("Inspection JSON standard entries do not match current ZIP standard entries.")

    return (
        True,
        True,
        True,
        json_status,
        json_sha256,
        json_size,
        json_entry_count,
        hash_matches,
        size_matches,
        count_matches,
        status_matches,
        standard_entries_ok,
        tuple(errors),
        (),
    )


def _standard_entries_match_current(
    inspection_json: dict[str, object],
    current: TotalExportZipInspectionResult,
) -> bool:
    stored_entries = inspection_json.get("standard_entries")
    if not isinstance(stored_entries, list):
        return False
    stored_by_path = {
        str(entry.get("relative_path", "")): bool(entry.get("exists"))
        for entry in stored_entries
        if isinstance(entry, dict)
    }
    for entry in current.standard_entries:
        if entry.exists and not stored_by_path.get(entry.relative_path, False):
            return False
    return True


def _status_for_result(
    *,
    zip_inspection: TotalExportZipInspectionResult,
    missing_sidecar: bool,
    invalid_sidecar: bool,
    mismatch: bool,
    warnings: tuple[str, ...],
) -> str:
    if zip_inspection.status == ZIP_INSPECTION_STATUS_MISSING_ZIP:
        return REVIEW_BUNDLE_VERIFY_STATUS_MISSING_ZIP
    if zip_inspection.status == ZIP_INSPECTION_STATUS_INVALID_ZIP:
        return REVIEW_BUNDLE_VERIFY_STATUS_INVALID_ZIP
    if zip_inspection.unsafe_entries or zip_inspection.status == ZIP_INSPECTION_STATUS_UNSAFE_ENTRIES:
        return REVIEW_BUNDLE_VERIFY_STATUS_UNSAFE_ZIP
    if missing_sidecar:
        return REVIEW_BUNDLE_VERIFY_STATUS_MISSING_SIDECAR
    if invalid_sidecar:
        return REVIEW_BUNDLE_VERIFY_STATUS_INVALID_SIDECAR
    if mismatch:
        return REVIEW_BUNDLE_VERIFY_STATUS_MISMATCH
    if zip_inspection.status != ZIP_INSPECTION_STATUS_OK or warnings:
        return REVIEW_BUNDLE_VERIFY_STATUS_VERIFIED_WITH_WARNINGS
    return REVIEW_BUNDLE_VERIFY_STATUS_VERIFIED


def verify_total_export_review_bundle(
    zip_path: str,
    sha256_path: str = "",
    inspection_json_path: str = "",
    include_zip_entries: bool = False,
    hash_zip_entries: bool = False,
) -> TotalExportReviewBundleVerificationResult:
    selected_sha256_path = sha256_path or default_review_bundle_sha256_path(zip_path)
    selected_json_path = inspection_json_path or default_review_bundle_inspection_json_path(zip_path)
    zip_inspection = inspect_total_export_zip(
        zip_path,
        include_entries=include_zip_entries,
        hash_entries=hash_zip_entries,
    )

    (
        sha_found,
        sha_valid,
        sidecar_sha,
        sidecar_filename,
        hash_matches_sha,
        sha_errors,
        sha_warnings,
    ) = _read_sha256_sidecar(
        zip_path=zip_path,
        sha256_path=selected_sha256_path,
        current_zip_sha256=zip_inspection.zip_sha256,
    )
    (
        json_found,
        json_readable,
        json_valid,
        json_status,
        json_sha,
        json_size,
        json_entry_count,
        hash_matches_json,
        size_matches_json,
        entry_count_matches_json,
        status_matches_json,
        standard_entries_ok,
        json_errors,
        json_warnings,
    ) = _read_inspection_json(
        inspection_json_path=selected_json_path,
        current=zip_inspection,
    )

    errors = tuple(zip_inspection.errors) + sha_errors + json_errors
    warnings = tuple(zip_inspection.warnings) + sha_warnings + json_warnings
    missing_sidecar = not sha_found or not json_found
    invalid_sidecar = (sha_found and not sha_valid) or (json_found and not json_valid)
    mismatch = any(
        (
            sha_found and sha_valid and not hash_matches_sha,
            json_found and json_valid and not hash_matches_json,
            json_found and json_valid and not size_matches_json,
            json_found and json_valid and not entry_count_matches_json,
            json_found and json_valid and not status_matches_json,
            json_found and json_valid and not standard_entries_ok,
        )
    )

    return TotalExportReviewBundleVerificationResult(
        zip_path=zip_path,
        sha256_path=selected_sha256_path,
        inspection_json_path=selected_json_path,
        status=_status_for_result(
            zip_inspection=zip_inspection,
            missing_sidecar=missing_sidecar,
            invalid_sidecar=invalid_sidecar,
            mismatch=mismatch,
            warnings=warnings,
        ),
        zip_found=zip_inspection.zip_found,
        zip_readable=zip_inspection.zip_readable,
        zip_status=zip_inspection.status,
        zip_sha256=zip_inspection.zip_sha256,
        zip_size_bytes=zip_inspection.zip_size_bytes,
        sha256_sidecar_found=sha_found,
        sha256_sidecar_valid=sha_valid,
        sha256_sidecar_sha256=sidecar_sha,
        sha256_sidecar_filename=sidecar_filename,
        inspection_json_found=json_found,
        inspection_json_readable=json_readable,
        inspection_json_valid=json_valid,
        inspection_json_zip_status=json_status,
        inspection_json_zip_sha256=json_sha,
        inspection_json_zip_size_bytes=json_size,
        inspection_json_entry_count=json_entry_count,
        current_entry_count=zip_inspection.entry_count,
        current_file_entry_count=zip_inspection.file_entry_count,
        hash_matches_sha256_sidecar=hash_matches_sha,
        hash_matches_inspection_json=hash_matches_json,
        size_matches_inspection_json=size_matches_json,
        entry_count_matches_inspection_json=entry_count_matches_json,
        status_matches_inspection_json=status_matches_json,
        standard_entries_ok=standard_entries_ok,
        unsafe_entries=zip_inspection.unsafe_entries,
        duplicate_entries=zip_inspection.duplicate_entries,
        errors=errors,
        warnings=warnings,
    )


def review_bundle_verification_to_dict(
    result: TotalExportReviewBundleVerificationResult,
) -> dict[str, object]:
    return {
        "current_entry_count": result.current_entry_count,
        "current_file_entry_count": result.current_file_entry_count,
        "duplicate_entries": list(result.duplicate_entries),
        "entry_count_matches_inspection_json": result.entry_count_matches_inspection_json,
        "errors": list(result.errors),
        "hash_matches_inspection_json": result.hash_matches_inspection_json,
        "hash_matches_sha256_sidecar": result.hash_matches_sha256_sidecar,
        "inspection_json_entry_count": result.inspection_json_entry_count,
        "inspection_json_found": result.inspection_json_found,
        "inspection_json_path": result.inspection_json_path,
        "inspection_json_readable": result.inspection_json_readable,
        "inspection_json_valid": result.inspection_json_valid,
        "inspection_json_zip_sha256": result.inspection_json_zip_sha256,
        "inspection_json_zip_size_bytes": result.inspection_json_zip_size_bytes,
        "inspection_json_zip_status": result.inspection_json_zip_status,
        "sha256_path": result.sha256_path,
        "sha256_sidecar_filename": result.sha256_sidecar_filename,
        "sha256_sidecar_found": result.sha256_sidecar_found,
        "sha256_sidecar_sha256": result.sha256_sidecar_sha256,
        "sha256_sidecar_valid": result.sha256_sidecar_valid,
        "size_matches_inspection_json": result.size_matches_inspection_json,
        "standard_entries_ok": result.standard_entries_ok,
        "status": result.status,
        "status_matches_inspection_json": result.status_matches_inspection_json,
        "unsafe_entries": list(result.unsafe_entries),
        "warnings": list(result.warnings),
        "zip_found": result.zip_found,
        "zip_path": result.zip_path,
        "zip_readable": result.zip_readable,
        "zip_sha256": result.zip_sha256,
        "zip_size_bytes": result.zip_size_bytes,
        "zip_status": result.zip_status,
    }


def _yes_no(value: bool) -> str:
    return "yes" if value else "no"


def _append_sequence(lines: list[str], label: str, values: tuple[str, ...]) -> None:
    lines.append(label)
    if values:
        lines.extend(f"- {value}" for value in values)
    else:
        lines.append("- (none)")


def build_total_export_review_bundle_verification_text(
    result: TotalExportReviewBundleVerificationResult,
) -> str:
    lines = [
        "Total Export review bundle verification",
        f"ZIP path: {result.zip_path}",
        f"SHA256 sidecar path: {result.sha256_path}",
        f"Inspection JSON path: {result.inspection_json_path}",
        f"Status: {result.status}",
        f"ZIP found: {_yes_no(result.zip_found)}",
        f"ZIP readable: {_yes_no(result.zip_readable)}",
        f"ZIP inspection status: {result.zip_status or '(none)'}",
        f"ZIP SHA-256: {result.zip_sha256 or '(none)'}",
        f"ZIP size bytes: {result.zip_size_bytes}",
        f"SHA256 sidecar found: {_yes_no(result.sha256_sidecar_found)}",
        f"SHA256 sidecar valid: {_yes_no(result.sha256_sidecar_valid)}",
        f"Inspection JSON found: {_yes_no(result.inspection_json_found)}",
        f"Inspection JSON readable: {_yes_no(result.inspection_json_readable)}",
        f"Inspection JSON valid: {_yes_no(result.inspection_json_valid)}",
        f"Hash matches SHA256 sidecar: {_yes_no(result.hash_matches_sha256_sidecar)}",
        f"Hash matches inspection JSON: {_yes_no(result.hash_matches_inspection_json)}",
        f"Size matches inspection JSON: {_yes_no(result.size_matches_inspection_json)}",
        f"Entry count matches inspection JSON: {_yes_no(result.entry_count_matches_inspection_json)}",
        f"Status matches inspection JSON: {_yes_no(result.status_matches_inspection_json)}",
        f"Standard entries OK: {_yes_no(result.standard_entries_ok)}",
    ]
    _append_sequence(lines, "Unsafe entries:", result.unsafe_entries)
    _append_sequence(lines, "Duplicate entries:", result.duplicate_entries)
    _append_sequence(lines, "Errors:", result.errors)
    _append_sequence(lines, "Warnings:", result.warnings)
    return "\n".join(lines)
