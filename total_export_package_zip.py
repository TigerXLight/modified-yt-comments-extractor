from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

from total_export_manifest import sha256_for_file
from total_export_package_inspect import (
    INSPECTION_STATUS_OK,
    INSPECTION_STATUS_OK_WITH_WARNINGS,
    inspect_total_export_package,
)


DETERMINISTIC_ZIP_TIMESTAMP = (1980, 1, 1, 0, 0, 0)


@dataclass(frozen=True)
class TotalExportPackageZipResult:
    package_folder: str
    manifest_path: str = ""
    zip_path: str = ""
    zip_created: bool = False
    zip_size_bytes: int = 0
    zip_sha256: str = ""
    zipped_file_count: int = 0
    inspection_status: str = ""
    inspection_manifest_valid: bool = False
    inspection_warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()


def default_total_export_zip_path(package_folder: str) -> str:
    package_path = Path(package_folder)
    return str(package_path.parent / f"{package_path.name}.zip")


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
    except ValueError:
        return False
    return True


def _package_file_paths(package_folder: Path) -> tuple[Path, ...]:
    return tuple(
        sorted(
            (path for path in package_folder.rglob("*") if path.is_file()),
            key=lambda path: path.resolve().relative_to(package_folder.resolve()).as_posix(),
        )
    )


def _zip_entry_name(package_folder: Path, file_path: Path) -> str:
    relative_path = file_path.resolve().relative_to(package_folder.resolve()).as_posix()
    return f"{package_folder.name}/{relative_path}"


def _write_file_to_zip(zip_file: ZipFile, entry_name: str, file_path: Path) -> None:
    info = ZipInfo(entry_name, DETERMINISTIC_ZIP_TIMESTAMP)
    info.create_system = 3
    info.compress_type = ZIP_DEFLATED
    info.external_attr = 0o100644 << 16
    with file_path.open("rb") as handle:
        zip_file.writestr(info, handle.read())


def _error_result(
    *,
    package_folder: str,
    manifest_path: str = "",
    zip_path: str = "",
    inspection_status: str = "",
    inspection_manifest_valid: bool = False,
    inspection_warnings: tuple[str, ...] = (),
    errors: tuple[str, ...],
    warnings: tuple[str, ...] = (),
) -> TotalExportPackageZipResult:
    return TotalExportPackageZipResult(
        package_folder=package_folder,
        manifest_path=manifest_path,
        zip_path=zip_path,
        inspection_status=inspection_status,
        inspection_manifest_valid=inspection_manifest_valid,
        inspection_warnings=inspection_warnings,
        errors=errors,
        warnings=warnings,
    )


def create_total_export_package_zip(
    package_folder: str,
    manifest_path: str = "",
    zip_path: str = "",
    overwrite: bool = False,
    allow_inspection_warnings: bool = False,
) -> TotalExportPackageZipResult:
    package_path = Path(package_folder)
    selected_zip_path = Path(zip_path or default_total_export_zip_path(package_folder))

    inspection = inspect_total_export_package(
        package_folder=package_folder,
        manifest_path=manifest_path,
    )
    if inspection.status != INSPECTION_STATUS_OK:
        if inspection.status == INSPECTION_STATUS_OK_WITH_WARNINGS and allow_inspection_warnings:
            pass
        else:
            return _error_result(
                package_folder=package_folder,
                manifest_path=inspection.manifest_path or manifest_path,
                zip_path=str(selected_zip_path),
                inspection_status=inspection.status,
                inspection_manifest_valid=inspection.manifest_valid,
                inspection_warnings=inspection.warnings,
                errors=(f"Package inspection status prevents ZIP creation: {inspection.status}",),
            )

    if _is_relative_to(selected_zip_path, package_path):
        return _error_result(
            package_folder=package_folder,
            manifest_path=inspection.manifest_path or manifest_path,
            zip_path=str(selected_zip_path),
            inspection_status=inspection.status,
            inspection_manifest_valid=inspection.manifest_valid,
            inspection_warnings=inspection.warnings,
            errors=("ZIP path must not be inside the package folder.",),
        )

    if selected_zip_path.exists() and not overwrite:
        return _error_result(
            package_folder=package_folder,
            manifest_path=inspection.manifest_path or manifest_path,
            zip_path=str(selected_zip_path),
            inspection_status=inspection.status,
            inspection_manifest_valid=inspection.manifest_valid,
            inspection_warnings=inspection.warnings,
            errors=(f"ZIP path already exists: {selected_zip_path}",),
        )

    selected_zip_path.parent.mkdir(parents=True, exist_ok=True)
    file_paths = _package_file_paths(package_path)
    with ZipFile(selected_zip_path, "w", compression=ZIP_DEFLATED) as zip_file:
        for file_path in file_paths:
            _write_file_to_zip(
                zip_file,
                _zip_entry_name(package_path, file_path),
                file_path,
            )

    return TotalExportPackageZipResult(
        package_folder=package_folder,
        manifest_path=inspection.manifest_path or manifest_path,
        zip_path=str(selected_zip_path),
        zip_created=True,
        zip_size_bytes=selected_zip_path.stat().st_size,
        zip_sha256=sha256_for_file(str(selected_zip_path)),
        zipped_file_count=len(file_paths),
        inspection_status=inspection.status,
        inspection_manifest_valid=inspection.manifest_valid,
        inspection_warnings=inspection.warnings,
    )


def package_zip_result_to_dict(result: TotalExportPackageZipResult) -> dict[str, object]:
    return {
        "errors": list(result.errors),
        "inspection_manifest_valid": result.inspection_manifest_valid,
        "inspection_status": result.inspection_status,
        "inspection_warnings": list(result.inspection_warnings),
        "manifest_path": result.manifest_path,
        "package_folder": result.package_folder,
        "warnings": list(result.warnings),
        "zip_created": result.zip_created,
        "zip_path": result.zip_path,
        "zip_sha256": result.zip_sha256,
        "zip_size_bytes": result.zip_size_bytes,
        "zipped_file_count": result.zipped_file_count,
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


def build_total_export_package_zip_text(result: TotalExportPackageZipResult) -> str:
    lines = [
        "Total Export package ZIP",
        f"Package folder: {result.package_folder}",
        f"Manifest path: {result.manifest_path or '(none)'}",
        f"ZIP path: {result.zip_path or '(none)'}",
        f"ZIP created: {_yes_no(result.zip_created)}",
        f"ZIP size bytes: {result.zip_size_bytes}",
        f"ZIP SHA-256: {result.zip_sha256 or '(none)'}",
        f"Zipped file count: {result.zipped_file_count}",
        f"Inspection status: {result.inspection_status or '(none)'}",
        f"Inspection manifest valid: {_yes_no(result.inspection_manifest_valid)}",
    ]
    _append_sequence(lines, "Inspection warnings:", result.inspection_warnings)
    _append_sequence(lines, "Errors:", result.errors)
    _append_sequence(lines, "Warnings:", result.warnings)
    return "\n".join(lines)
