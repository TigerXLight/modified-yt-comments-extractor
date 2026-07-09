from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from total_export_manifest import (
    ExportAsset,
    TotalExportManifest,
    read_manifest_json,
    sha256_for_file,
)


VALIDATION_LEVEL_ERROR = "error"
VALIDATION_LEVEL_WARNING = "warning"
VALIDATION_LEVEL_INFO = "info"


@dataclass(frozen=True)
class ManifestValidationIssue:
    level: str
    code: str
    message: str
    path: str = ""


@dataclass(frozen=True)
class ManifestValidationResult:
    manifest_path: str
    package_folder: str = ""
    issues: tuple[ManifestValidationIssue, ...] = ()

    @property
    def has_errors(self) -> bool:
        return bool(self.errors)

    @property
    def errors(self) -> tuple[ManifestValidationIssue, ...]:
        return tuple(issue for issue in self.issues if issue.level == VALIDATION_LEVEL_ERROR)

    @property
    def warnings(self) -> tuple[ManifestValidationIssue, ...]:
        return tuple(issue for issue in self.issues if issue.level == VALIDATION_LEVEL_WARNING)


def _issue(level: str, code: str, message: str, path: str = "") -> ManifestValidationIssue:
    return ManifestValidationIssue(level=level, code=code, message=message, path=path)


def _package_folder_for_manifest(manifest: TotalExportManifest, manifest_path: str) -> str:
    if manifest.output_folder:
        return manifest.output_folder
    if manifest_path:
        return str(Path(manifest_path).parent)
    return ""


def _asset_path(asset: ExportAsset, package_folder: str) -> Path | None:
    if not asset.path:
        return None

    path = Path(asset.path)
    if path.is_absolute():
        return path
    if package_folder:
        return Path(package_folder) / path
    return None


def _validate_asset(asset: ExportAsset, package_folder: str, index: int) -> list[ManifestValidationIssue]:
    issues: list[ManifestValidationIssue] = []
    asset_label = f"assets[{index}]"
    resolved_path = _asset_path(asset, package_folder)

    if resolved_path is None:
        issues.append(
            _issue(
                VALIDATION_LEVEL_WARNING,
                "ASSET_PATH_UNRESOLVED",
                "Asset path is empty or relative without a known package folder.",
                asset_label,
            )
        )
        return issues

    if not resolved_path.is_file():
        issues.append(
            _issue(
                VALIDATION_LEVEL_ERROR,
                "ASSET_FILE_MISSING",
                f"Asset file is missing: {resolved_path}",
                str(resolved_path),
            )
        )
        return issues

    actual_size = resolved_path.stat().st_size
    if asset.size_bytes and asset.size_bytes != actual_size:
        issues.append(
            _issue(
                VALIDATION_LEVEL_ERROR,
                "ASSET_SIZE_MISMATCH",
                f"Asset size mismatch: expected {asset.size_bytes}, got {actual_size}.",
                str(resolved_path),
            )
        )

    if asset.sha256:
        actual_hash = sha256_for_file(str(resolved_path))
        if asset.sha256 != actual_hash:
            issues.append(
                _issue(
                    VALIDATION_LEVEL_ERROR,
                    "ASSET_SHA256_MISMATCH",
                    "Asset SHA-256 mismatch.",
                    str(resolved_path),
                )
            )

    return issues


def validate_total_export_manifest(
    manifest: TotalExportManifest,
    *,
    manifest_path: str = "",
) -> ManifestValidationResult:
    package_folder = _package_folder_for_manifest(manifest, manifest_path)
    issues: list[ManifestValidationIssue] = []

    if not manifest.package_id:
        issues.append(
            _issue(
                VALIDATION_LEVEL_ERROR,
                "MISSING_PACKAGE_ID",
                "Manifest package_id is empty.",
                "package_id",
            )
        )

    if manifest.output_folder and not Path(manifest.output_folder).is_dir():
        issues.append(
            _issue(
                VALIDATION_LEVEL_ERROR,
                "OUTPUT_FOLDER_MISSING",
                f"Manifest output_folder does not exist: {manifest.output_folder}",
                manifest.output_folder,
            )
        )

    if not manifest.source_urls:
        issues.append(
            _issue(
                VALIDATION_LEVEL_INFO,
                "NO_SOURCE_URLS",
                "Manifest has no source URLs recorded.",
                "source_urls",
            )
        )

    if not manifest.capture_options:
        issues.append(
            _issue(
                VALIDATION_LEVEL_INFO,
                "NO_CAPTURE_OPTIONS",
                "Manifest has no capture options recorded.",
                "capture_options",
            )
        )

    for index, asset in enumerate(manifest.assets):
        issues.extend(_validate_asset(asset, package_folder, index))

    return ManifestValidationResult(
        manifest_path=manifest_path,
        package_folder=package_folder,
        issues=tuple(issues),
    )


def validate_manifest_json_file(manifest_path: str) -> ManifestValidationResult:
    package_folder = str(Path(manifest_path).parent) if manifest_path else ""
    try:
        manifest = read_manifest_json(manifest_path)
    except Exception as exc:
        return ManifestValidationResult(
            manifest_path=manifest_path,
            package_folder=package_folder,
            issues=(
                _issue(
                    VALIDATION_LEVEL_ERROR,
                    "MANIFEST_READ_FAILED",
                    f"Manifest JSON could not be read or reconstructed: {exc}",
                    manifest_path,
                ),
            ),
        )

    return validate_total_export_manifest(manifest, manifest_path=manifest_path)
