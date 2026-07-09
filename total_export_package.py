from __future__ import annotations

import os
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Sequence

from capture_options import normalize_capture_option_ids
from source_capture_plan import SourceCapturePlan
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
    read_manifest_json,
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
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class TotalExportPlanPackageResult:
    package_result: TotalExportPackageResult
    plan_status: str = ""
    manifest_path: str = ""
    warnings: tuple[str, ...] = ()


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
    capture_selection = normalize_capture_option_ids(selected_capture_options)

    created_folders = [ensure_folder(package_folder)]
    if create_asset_folders:
        for subfolder in _asset_subfolders():
            created_folders.append(ensure_folder(str(Path(package_folder) / subfolder)))

    manifest = TotalExportManifest(
        package_id=resolved_package_id,
        output_folder=package_folder,
        capture_options=list(capture_selection.selected_option_ids),
        notes=f"Source label: {source_label}" if source_label else "",
    )
    manifest_path = str(Path(package_folder) / manifest_filename(resolved_package_id))
    write_manifest_json(manifest, manifest_path)

    return TotalExportPackageResult(
        package_id=resolved_package_id,
        package_folder=package_folder,
        manifest_path=manifest_path,
        created_folders=tuple(created_folders),
        warnings=capture_selection.warnings,
    )


def _plan_source_label(plan: SourceCapturePlan) -> str:
    if plan.adapter_display_name:
        return plan.adapter_display_name
    if plan.adapter_name:
        return plan.adapter_name
    if plan.source_id:
        return plan.source_id
    if plan.context_result and plan.context_result.source_label:
        return plan.context_result.source_label
    return "source"


def _append_note(existing_notes: str, note: str) -> str:
    if not existing_notes:
        return note
    return f"{existing_notes}\n{note}"


def create_total_export_package_from_plan(
    *,
    base_folder: str,
    plan: SourceCapturePlan,
    package_id: str = "",
    create_asset_folders: bool = True,
) -> TotalExportPlanPackageResult:
    package_result = create_total_export_package(
        base_folder=base_folder,
        source_label=_plan_source_label(plan),
        package_id=package_id,
        selected_capture_options=plan.selected_capture_options,
        create_asset_folders=create_asset_folders,
    )

    manifest = read_manifest_json(package_result.manifest_path)
    source_url = plan.normalized_url or plan.source_url
    source_urls = list(manifest.source_urls)
    if source_url and source_url not in source_urls:
        source_urls.append(source_url)

    note = f"Source Capture Plan status: {plan.status}"
    if plan.adapter_name or plan.source_id:
        adapter_label = plan.adapter_display_name or plan.adapter_name
        details = []
        if adapter_label:
            details.append(f"adapter={adapter_label}")
        if plan.source_id:
            details.append(f"source_id={plan.source_id}")
        note = f"{note} ({', '.join(details)})"

    updated_manifest = replace(
        manifest,
        source_urls=source_urls,
        capture_options=list(plan.selected_capture_options),
        notes=_append_note(manifest.notes, note),
    )
    write_manifest_json(updated_manifest, package_result.manifest_path)

    return TotalExportPlanPackageResult(
        package_result=package_result,
        plan_status=plan.status,
        manifest_path=package_result.manifest_path,
        warnings=tuple(plan.warnings) + tuple(package_result.warnings),
    )
