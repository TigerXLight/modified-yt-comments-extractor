from __future__ import annotations

import mimetypes
import re
import shutil
from dataclasses import dataclass, replace
from pathlib import Path

from total_export_manifest import (
    ExportAsset,
    TotalExportManifest,
    asset_subfolder,
    sha256_for_file,
)


@dataclass(frozen=True)
class RegisteredExportAsset:
    asset: ExportAsset
    source_path: str
    destination_path: str
    copied: bool = False


def safe_asset_filename(value: str) -> str:
    filename = (value or "").strip()
    filename = filename.replace("\\", "_").replace("/", "_")
    filename = re.sub(r"[^A-Za-z0-9._-]+", "_", filename)
    filename = re.sub(r"_+", "_", filename).strip("._")
    return filename or "asset"


def asset_destination_path(
    *,
    package_folder: str,
    asset_type: str,
    filename: str,
) -> str:
    safe_filename = safe_asset_filename(filename)
    subfolder = asset_subfolder(asset_type)
    if subfolder:
        return str(Path(package_folder) / subfolder / safe_filename)
    return str(Path(package_folder) / safe_filename)


def _package_relative_path(file_path: Path, package_folder: str) -> str:
    if not package_folder:
        return str(file_path)

    try:
        return str(file_path.resolve().relative_to(Path(package_folder).resolve()))
    except ValueError:
        return str(file_path)


def export_asset_for_file(
    *,
    file_path: str,
    asset_type: str,
    package_folder: str = "",
) -> ExportAsset:
    path = Path(file_path)
    if not path.is_file():
        raise FileNotFoundError(str(path))

    mime_type, _ = mimetypes.guess_type(str(path))
    return ExportAsset(
        asset_type=asset_type,
        path=_package_relative_path(path, package_folder),
        sha256=sha256_for_file(str(path)),
        mime_type=mime_type or "",
        size_bytes=path.stat().st_size,
    )


def copy_asset_into_package(
    *,
    source_path: str,
    package_folder: str,
    asset_type: str,
    filename: str = "",
    overwrite: bool = False,
) -> RegisteredExportAsset:
    source = Path(source_path)
    if not source.is_file():
        raise FileNotFoundError(str(source))

    destination = Path(
        asset_destination_path(
            package_folder=package_folder,
            asset_type=asset_type,
            filename=filename or source.name,
        )
    )
    if destination.exists() and not overwrite:
        raise FileExistsError(str(destination))

    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(str(source), str(destination))
    return RegisteredExportAsset(
        asset=export_asset_for_file(
            file_path=str(destination),
            asset_type=asset_type,
            package_folder=package_folder,
        ),
        source_path=str(source),
        destination_path=str(destination),
        copied=True,
    )


def manifest_with_asset(
    manifest: TotalExportManifest,
    asset: ExportAsset,
) -> TotalExportManifest:
    return replace(manifest, assets=list(manifest.assets) + [asset])
