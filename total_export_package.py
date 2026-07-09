from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from total_export_manifest import (
    ASSET_ARCHIVE_RESULT,
    ASSET_CSV_EXPORT,
    ASSET_EXCEL_EXPORT,
    ASSET_EXTRACTED_TEXT,
    ASSET_HTML_SNAPSHOT,
    ASSET_JSON_EXPORT,
    ASSET_MANIFEST,
    ASSET_MEDIA,
    ASSET_RAW_SIDECAR,
    ASSET_SCREENSHOT,
    ASSET_TEXT_EXPORT,
    TotalExportManifest,
    asset_subfolder,
    default_package_folder,
    default_package_id,
    manifest_filename,
    safe_package_id,
    write_manifest_json,
)


KNOWN_ASSET_TYPES = (
    ASSET_TEXT_EXPORT,
    ASSET_CSV_EXPORT,
    ASSET_EXCEL_EXPORT,
    ASSET_JSON_EXPORT,
    ASSET_MANIFEST,
    ASSET_SCREENSHOT,
    ASSET_HTML_SNAPSHOT,
    ASSET_EXTRACTED_TEXT,
    ASSET_ARCHIVE_RESULT,
    ASSET_MEDIA,
    ASSET_RAW_SIDECAR,
)


@dataclass(frozen=True)
class TotalExportPackageResult:
    package_id: str
    package_folder: str
    manifest_path: str
    created_folders: tuple[str, ...] = ()


def ensure_folder(path: str) -> str:
    os.makedirs(path, exist_ok=True)
    return path


def _asset_subfolders() -> tuple[str, ...]:
    subfolders = []
    seen = set()
    for asset_type in KNOWN_ASSET_TYPES:
        subfolder = asset_subfolder(asset_type)
        if not subfolder or subfolder in seen:
            continue
        seen.add(subfolder)
        subfolders.append(subfolder)
    return tuple(subfolders)


def create_total_export_package(
    *,
    base_folder: str,
    source_label: str = "",
    package_id: str = "",
    selected_capture_options: Sequence[str] = (),
    create_asset_folders: bool = True,
) -> TotalExportPackageResult:
    resolved_package_id = safe_package_id(package_id) if package_id else default_package_id(source_label)
    package_folder = default_package_folder(base_folder, resolved_package_id)

    created_folders = [ensure_folder(package_folder)]
    if create_asset_folders:
        for subfolder in _asset_subfolders():
            created_folders.append(ensure_folder(str(Path(package_folder) / subfolder)))

    manifest = TotalExportManifest(
        package_id=resolved_package_id,
        output_folder=package_folder,
        capture_options=list(selected_capture_options),
        notes=f"Source label: {source_label}" if source_label else "",
    )
    manifest_path = str(Path(package_folder) / manifest_filename(resolved_package_id))
    write_manifest_json(manifest, manifest_path)

    return TotalExportPackageResult(
        package_id=resolved_package_id,
        package_folder=package_folder,
        manifest_path=manifest_path,
        created_folders=tuple(created_folders),
    )
