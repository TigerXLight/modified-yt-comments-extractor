from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from total_export_zip_inspect import (
    ZIP_INSPECTION_STATUS_OK,
    TotalExportZipInspectionResult,
    inspect_total_export_zip,
    total_export_zip_inspection_to_dict,
)


@dataclass(frozen=True)
class TotalExportZipSidecarResult:
    zip_path: str
    sha256_path: str = ""
    json_path: str = ""
    sha256_written: bool = False
    json_written: bool = False
    zip_status: str = ""
    zip_sha256: str = ""
    zip_size_bytes: int = 0
    zip_entry_count: int = 0
    zip_file_entry_count: int = 0
    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()


def default_zip_sha256_sidecar_path(zip_path: str) -> str:
    return f"{zip_path}.sha256"


def default_zip_json_sidecar_path(zip_path: str) -> str:
    return f"{zip_path}.inspection.json"


def build_zip_sha256_sidecar_text(zip_path: str, zip_sha256: str) -> str:
    return f"{zip_sha256}  {Path(zip_path).name}\n"


def build_zip_inspection_sidecar_dict(
    inspection: TotalExportZipInspectionResult,
) -> dict[str, object]:
    return {
        "sidecar_metadata": {
            "format": "total_export_zip_inspection",
            "version": 1,
            "zip_basename": Path(inspection.zip_path).name,
            "zip_path": inspection.zip_path,
        },
        "zip_inspection": total_export_zip_inspection_to_dict(inspection),
    }


def _error_result(
    *,
    zip_path: str,
    sha256_path: str,
    json_path: str,
    inspection: TotalExportZipInspectionResult | None = None,
    errors: tuple[str, ...],
    warnings: tuple[str, ...] = (),
) -> TotalExportZipSidecarResult:
    return TotalExportZipSidecarResult(
        zip_path=zip_path,
        sha256_path=sha256_path,
        json_path=json_path,
        zip_status=inspection.status if inspection else "",
        zip_sha256=inspection.zip_sha256 if inspection else "",
        zip_size_bytes=inspection.zip_size_bytes if inspection else 0,
        zip_entry_count=inspection.entry_count if inspection else 0,
        zip_file_entry_count=inspection.file_entry_count if inspection else 0,
        errors=errors,
        warnings=warnings,
    )


def _path_equals_zip(sidecar_path: str, zip_path: str) -> bool:
    try:
        return Path(sidecar_path).resolve() == Path(zip_path).resolve()
    except OSError:
        return Path(sidecar_path) == Path(zip_path)


def write_total_export_zip_sidecars(
    zip_path: str,
    sha256_path: str = "",
    json_path: str = "",
    overwrite: bool = False,
    require_zip_status_ok: bool = True,
    include_entries: bool = False,
    hash_entries: bool = False,
) -> TotalExportZipSidecarResult:
    selected_sha256_path = sha256_path or default_zip_sha256_sidecar_path(zip_path)
    selected_json_path = json_path or default_zip_json_sidecar_path(zip_path)

    inspection = inspect_total_export_zip(
        zip_path,
        include_entries=include_entries,
        hash_entries=hash_entries,
    )

    errors: list[str] = []
    if _path_equals_zip(selected_sha256_path, zip_path):
        errors.append("SHA256 sidecar path must not equal the ZIP path.")
    if _path_equals_zip(selected_json_path, zip_path):
        errors.append("Inspection JSON sidecar path must not equal the ZIP path.")
    if require_zip_status_ok and inspection.status != ZIP_INSPECTION_STATUS_OK:
        errors.append(f"ZIP inspection status prevents sidecar creation: {inspection.status}")
    if Path(selected_sha256_path).exists() and not overwrite:
        errors.append(f"SHA256 sidecar already exists: {selected_sha256_path}")
    if Path(selected_json_path).exists() and not overwrite:
        errors.append(f"Inspection JSON sidecar already exists: {selected_json_path}")
    if errors:
        return _error_result(
            zip_path=zip_path,
            sha256_path=selected_sha256_path,
            json_path=selected_json_path,
            inspection=inspection,
            errors=tuple(errors),
            warnings=inspection.warnings,
        )

    sha256_written = False
    json_written = False
    if inspection.zip_sha256:
        sha256_file = Path(selected_sha256_path)
        sha256_file.parent.mkdir(parents=True, exist_ok=True)
        sha256_file.write_text(
            build_zip_sha256_sidecar_text(zip_path, inspection.zip_sha256),
            encoding="utf-8",
        )
        sha256_written = True

    json_file = Path(selected_json_path)
    json_file.parent.mkdir(parents=True, exist_ok=True)
    json_file.write_text(
        json.dumps(
            build_zip_inspection_sidecar_dict(inspection),
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    json_written = True

    return TotalExportZipSidecarResult(
        zip_path=zip_path,
        sha256_path=selected_sha256_path,
        json_path=selected_json_path,
        sha256_written=sha256_written,
        json_written=json_written,
        zip_status=inspection.status,
        zip_sha256=inspection.zip_sha256,
        zip_size_bytes=inspection.zip_size_bytes,
        zip_entry_count=inspection.entry_count,
        zip_file_entry_count=inspection.file_entry_count,
        warnings=inspection.warnings,
    )


def zip_sidecar_result_to_dict(
    result: TotalExportZipSidecarResult,
) -> dict[str, object]:
    return {
        "errors": list(result.errors),
        "json_path": result.json_path,
        "json_written": result.json_written,
        "sha256_path": result.sha256_path,
        "sha256_written": result.sha256_written,
        "warnings": list(result.warnings),
        "zip_entry_count": result.zip_entry_count,
        "zip_file_entry_count": result.zip_file_entry_count,
        "zip_path": result.zip_path,
        "zip_sha256": result.zip_sha256,
        "zip_size_bytes": result.zip_size_bytes,
        "zip_status": result.zip_status,
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


def build_total_export_zip_sidecar_text(result: TotalExportZipSidecarResult) -> str:
    lines = [
        "Total Export ZIP sidecars",
        f"ZIP path: {result.zip_path}",
        f"SHA256 path: {result.sha256_path or '(none)'}",
        f"Inspection JSON path: {result.json_path or '(none)'}",
        f"SHA256 written: {_yes_no(result.sha256_written)}",
        f"JSON written: {_yes_no(result.json_written)}",
        f"ZIP status: {result.zip_status or '(none)'}",
        f"ZIP SHA-256: {result.zip_sha256 or '(none)'}",
        f"ZIP size bytes: {result.zip_size_bytes}",
        f"ZIP entry count: {result.zip_entry_count}",
        f"ZIP file entry count: {result.zip_file_entry_count}",
    ]
    _append_sequence(lines, "Errors:", result.errors)
    _append_sequence(lines, "Warnings:", result.warnings)
    return "\n".join(lines)
