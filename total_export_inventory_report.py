from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from total_export_assets import (
    asset_destination_path,
    export_asset_for_file,
    register_asset_in_manifest_file,
    safe_asset_filename,
)
from total_export_inventory import build_total_export_inventory, summarize_total_export_inventory
from total_export_manifest import ASSET_TEXT_EXPORT


@dataclass(frozen=True)
class TotalExportInventoryReportFileResult:
    report_path: str
    registered: bool = False
    manifest_path: str = ""
    asset_path: str = ""
    warnings: tuple[str, ...] = ()


def _inventory_report_text(package_folder: str, manifest_path: str) -> str:
    inventory = build_total_export_inventory(
        package_folder=package_folder,
        manifest_path=manifest_path,
    )
    return "\n".join(
        [
            summarize_total_export_inventory(inventory),
            "",
            (
                "Note: Inventory report generated from local package files and manifest before "
                "this report registration step."
            ),
        ]
    )


def write_total_export_inventory_report_file(
    *,
    package_folder: str,
    manifest_path: str,
    filename: str = "TOTAL_EXPORT_INVENTORY.txt",
    register_in_manifest: bool = True,
) -> TotalExportInventoryReportFileResult:
    if not package_folder:
        raise ValueError("Package folder is required.")
    if not manifest_path:
        raise ValueError("Manifest path is required.")

    safe_filename = safe_asset_filename(filename)
    report_path = asset_destination_path(
        package_folder=package_folder,
        asset_type=ASSET_TEXT_EXPORT,
        filename=safe_filename,
    )
    path = Path(report_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_inventory_report_text(package_folder, manifest_path), encoding="utf-8")

    if not register_in_manifest:
        return TotalExportInventoryReportFileResult(
            report_path=report_path,
            registered=False,
            manifest_path=manifest_path,
        )

    asset = export_asset_for_file(
        file_path=report_path,
        asset_type=ASSET_TEXT_EXPORT,
        package_folder=package_folder,
    )
    register_asset_in_manifest_file(
        manifest_path=manifest_path,
        asset=asset,
        dedupe=True,
    )
    return TotalExportInventoryReportFileResult(
        report_path=report_path,
        registered=True,
        manifest_path=manifest_path,
        asset_path=asset.path,
    )
