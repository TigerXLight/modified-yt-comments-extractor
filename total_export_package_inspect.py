from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from total_export_inventory import TotalExportPackageInventory, build_total_export_inventory
from total_export_manifest import TotalExportManifest, read_manifest_json
from total_export_validation import ManifestValidationResult, validate_manifest_json_file


INSPECTION_STATUS_OK = "ok"
INSPECTION_STATUS_OK_WITH_WARNINGS = "ok_with_warnings"
INSPECTION_STATUS_MISSING_PACKAGE_FOLDER = "missing_package_folder"
INSPECTION_STATUS_MISSING_MANIFEST = "missing_manifest"
INSPECTION_STATUS_MULTIPLE_MANIFESTS = "multiple_manifests"
INSPECTION_STATUS_INVALID_MANIFEST = "invalid_manifest"


@dataclass(frozen=True)
class TotalExportStandardFileInspection:
    label: str
    relative_path: str
    exists: bool
    registered: bool


@dataclass(frozen=True)
class TotalExportPackageInspectionResult:
    package_folder: str
    manifest_path: str = ""
    status: str = INSPECTION_STATUS_MISSING_MANIFEST
    manifest_found: bool = False
    manifest_readable: bool = False
    manifest_valid: bool = False
    validation_issue_count: int = 0
    validation_errors: tuple[str, ...] = ()
    validation_warnings: tuple[str, ...] = ()
    inventory_ran: bool = False
    inventory_local_file_count: int = 0
    inventory_registered_asset_count: int = 0
    inventory_unregistered_files: tuple[str, ...] = ()
    inventory_missing_registered_assets: tuple[str, ...] = ()
    registered_asset_paths: tuple[str, ...] = ()
    standard_files: tuple[TotalExportStandardFileInspection, ...] = ()
    warnings: tuple[str, ...] = ()


def _relative_posix_path(path: Path, package_folder: Path) -> str:
    try:
        return path.resolve().relative_to(package_folder.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _asset_path(value: str) -> str:
    return (value or "").replace("\\", "/")


def _issue_messages(result: ManifestValidationResult, level: str) -> tuple[str, ...]:
    return tuple(
        f"{issue.code}: {issue.message}"
        for issue in result.issues
        if issue.level == level
    )


def _manifest_read_failed(result: ManifestValidationResult) -> bool:
    return any(issue.code == "MANIFEST_READ_FAILED" for issue in result.issues)


def discover_total_export_manifest(package_folder: str) -> tuple[str, tuple[str, ...]]:
    package_path = Path(package_folder)
    if not package_path.is_dir():
        return "", ()
    candidates = tuple(
        sorted(
            (
                str(path)
                for path in package_path.glob("*_manifest.json")
                if path.is_file()
            ),
            key=lambda value: Path(value).name,
        )
    )
    if len(candidates) == 1:
        return candidates[0], candidates
    return "", candidates


def _read_manifest_if_possible(manifest_path: str) -> TotalExportManifest | None:
    try:
        return read_manifest_json(manifest_path)
    except Exception:
        return None


def _standard_files(
    *,
    package_folder: str,
    manifest_path: str,
    registered_asset_paths: tuple[str, ...],
) -> tuple[TotalExportStandardFileInspection, ...]:
    package_path = Path(package_folder)
    registered = set(registered_asset_paths)
    standard_paths: list[tuple[str, str]] = []
    if manifest_path:
        standard_paths.append(
            (
                "manifest",
                _relative_posix_path(Path(manifest_path), package_path),
            )
        )
    else:
        standard_paths.append(("manifest", ""))
    standard_paths.extend(
        [
            ("summary", "metadata/TOTAL_EXPORT_SUMMARY.txt"),
            ("readme", "README_TOTAL_EXPORT.txt"),
            ("source_plan_report", "metadata/SOURCE_CAPTURE_PLAN.txt"),
            ("inventory_report", "metadata/TOTAL_EXPORT_INVENTORY.txt"),
        ]
    )
    return tuple(
        TotalExportStandardFileInspection(
            label=label,
            relative_path=relative_path,
            exists=bool(relative_path) and (package_path / relative_path).is_file(),
            registered=relative_path in registered,
        )
        for label, relative_path in standard_paths
    )


def _status_for_result(
    *,
    validation_result: ManifestValidationResult,
    manifest_readable: bool,
    warnings: tuple[str, ...],
) -> str:
    if not manifest_readable or validation_result.has_errors:
        return INSPECTION_STATUS_INVALID_MANIFEST
    if warnings or validation_result.warnings:
        return INSPECTION_STATUS_OK_WITH_WARNINGS
    return INSPECTION_STATUS_OK


def inspect_total_export_package(
    *,
    package_folder: str,
    manifest_path: str = "",
) -> TotalExportPackageInspectionResult:
    package_path = Path(package_folder)
    if not package_path.is_dir():
        return TotalExportPackageInspectionResult(
            package_folder=package_folder,
            status=INSPECTION_STATUS_MISSING_PACKAGE_FOLDER,
            warnings=(f"Package folder does not exist: {package_folder}",),
        )

    warnings: list[str] = []
    selected_manifest_path = manifest_path
    if selected_manifest_path:
        if not Path(selected_manifest_path).is_file():
            return TotalExportPackageInspectionResult(
                package_folder=package_folder,
                manifest_path=selected_manifest_path,
                status=INSPECTION_STATUS_MISSING_MANIFEST,
                warnings=(f"Manifest file does not exist: {selected_manifest_path}",),
            )
    else:
        selected_manifest_path, candidates = discover_total_export_manifest(package_folder)
        if not candidates:
            return TotalExportPackageInspectionResult(
                package_folder=package_folder,
                status=INSPECTION_STATUS_MISSING_MANIFEST,
                warnings=("No *_manifest.json file found in the package folder.",),
            )
        if len(candidates) > 1:
            candidate_names = ", ".join(
                _relative_posix_path(Path(candidate), package_path)
                for candidate in candidates
            )
            return TotalExportPackageInspectionResult(
                package_folder=package_folder,
                status=INSPECTION_STATUS_MULTIPLE_MANIFESTS,
                warnings=(f"Multiple manifest candidates found: {candidate_names}",),
            )

    validation_result = validate_manifest_json_file(selected_manifest_path)
    manifest_readable = not _manifest_read_failed(validation_result)
    manifest = _read_manifest_if_possible(selected_manifest_path) if manifest_readable else None
    registered_asset_paths = tuple(
        sorted(_asset_path(asset.path) for asset in (manifest.assets if manifest else ()))
    )

    inventory: TotalExportPackageInventory | None = None
    if manifest_readable:
        try:
            inventory = build_total_export_inventory(
                package_folder=package_folder,
                manifest_path=selected_manifest_path,
            )
        except Exception as exc:
            warnings.append(f"Inventory could not be built: {exc}")

    status = _status_for_result(
        validation_result=validation_result,
        manifest_readable=manifest_readable,
        warnings=tuple(warnings),
    )
    standard_files = _standard_files(
        package_folder=package_folder,
        manifest_path=selected_manifest_path,
        registered_asset_paths=registered_asset_paths,
    )
    return TotalExportPackageInspectionResult(
        package_folder=package_folder,
        manifest_path=selected_manifest_path,
        status=status,
        manifest_found=True,
        manifest_readable=manifest_readable,
        manifest_valid=manifest_readable and not validation_result.has_errors,
        validation_issue_count=len(validation_result.issues),
        validation_errors=_issue_messages(validation_result, "error"),
        validation_warnings=_issue_messages(validation_result, "warning"),
        inventory_ran=inventory is not None,
        inventory_local_file_count=inventory.local_file_count if inventory else 0,
        inventory_registered_asset_count=inventory.registered_asset_count if inventory else 0,
        inventory_unregistered_files=inventory.unregistered_files if inventory else (),
        inventory_missing_registered_assets=(
            inventory.missing_registered_assets if inventory else ()
        ),
        registered_asset_paths=registered_asset_paths,
        standard_files=standard_files,
        warnings=tuple(warnings),
    )


def package_inspection_to_dict(
    result: TotalExportPackageInspectionResult,
) -> dict[str, object]:
    return {
        "inventory_local_file_count": result.inventory_local_file_count,
        "inventory_missing_registered_assets": list(result.inventory_missing_registered_assets),
        "inventory_ran": result.inventory_ran,
        "inventory_registered_asset_count": result.inventory_registered_asset_count,
        "inventory_unregistered_files": list(result.inventory_unregistered_files),
        "manifest_found": result.manifest_found,
        "manifest_path": result.manifest_path,
        "manifest_readable": result.manifest_readable,
        "manifest_valid": result.manifest_valid,
        "package_folder": result.package_folder,
        "registered_asset_paths": list(result.registered_asset_paths),
        "standard_files": [
            {
                "exists": standard_file.exists,
                "label": standard_file.label,
                "registered": standard_file.registered,
                "relative_path": standard_file.relative_path,
            }
            for standard_file in result.standard_files
        ],
        "status": result.status,
        "validation_errors": list(result.validation_errors),
        "validation_issue_count": result.validation_issue_count,
        "validation_warnings": list(result.validation_warnings),
        "warnings": list(result.warnings),
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


def build_total_export_package_inspection_text(
    result: TotalExportPackageInspectionResult,
) -> str:
    lines = [
        "Total Export package inspection",
        f"Package folder: {result.package_folder}",
        f"Manifest path: {result.manifest_path or '(none)'}",
        f"Status: {result.status}",
        f"Manifest found: {_yes_no(result.manifest_found)}",
        f"Manifest readable: {_yes_no(result.manifest_readable)}",
        f"Manifest valid: {_yes_no(result.manifest_valid)}",
        f"Validation issues: {result.validation_issue_count}",
        f"Registered assets: {result.inventory_registered_asset_count}",
        f"Local files: {result.inventory_local_file_count}",
    ]
    _append_sequence(lines, "Missing registered assets:", result.inventory_missing_registered_assets)
    _append_sequence(lines, "Unregistered files:", result.inventory_unregistered_files)
    lines.append("Standard files:")
    if result.standard_files:
        for standard_file in result.standard_files:
            lines.append(
                f"- {standard_file.label}: {standard_file.relative_path or '(none)'} "
                f"[exists={_yes_no(standard_file.exists)}, "
                f"registered={_yes_no(standard_file.registered)}]"
            )
    else:
        lines.append("- (none)")
    _append_sequence(lines, "Validation errors:", result.validation_errors)
    _append_sequence(lines, "Validation warnings:", result.validation_warnings)
    _append_sequence(lines, "Warnings:", result.warnings)
    return "\n".join(lines)
