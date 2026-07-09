from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from total_export_manifest import read_manifest_json, sha256_for_file


@dataclass(frozen=True)
class TotalExportInventoryItem:
    path: str
    exists: bool
    registered: bool
    asset_type: str = ""
    size_bytes: int = 0
    sha256: str = ""


@dataclass(frozen=True)
class TotalExportPackageInventory:
    package_folder: str
    manifest_path: str
    items: tuple[TotalExportInventoryItem, ...] = ()
    unregistered_files: tuple[str, ...] = ()
    missing_registered_assets: tuple[str, ...] = ()
    registered_asset_count: int = 0
    local_file_count: int = 0


def _relative_posix_path(path: Path, package_folder: Path) -> str:
    try:
        return path.resolve().relative_to(package_folder.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _asset_path(value: str) -> str:
    return (value or "").replace("\\", "/")


def _local_files(package_folder: Path) -> dict[str, Path]:
    if not package_folder.is_dir():
        return {}
    files = {}
    for path in package_folder.rglob("*"):
        if path.is_file():
            files[_relative_posix_path(path, package_folder)] = path
    return files


def build_total_export_inventory(
    *,
    package_folder: str,
    manifest_path: str,
) -> TotalExportPackageInventory:
    package_path = Path(package_folder)
    manifest = read_manifest_json(manifest_path)
    local_files = _local_files(package_path)
    registered_by_path = {_asset_path(asset.path): asset for asset in manifest.assets}

    items = []
    for path in sorted(set(local_files) | set(registered_by_path)):
        local_path = local_files.get(path)
        asset = registered_by_path.get(path)
        exists = local_path is not None and local_path.is_file()
        if asset:
            items.append(
                TotalExportInventoryItem(
                    path=path,
                    exists=exists,
                    registered=True,
                    asset_type=asset.asset_type,
                    size_bytes=asset.size_bytes,
                    sha256=asset.sha256,
                )
            )
        elif local_path:
            items.append(
                TotalExportInventoryItem(
                    path=path,
                    exists=True,
                    registered=False,
                    size_bytes=local_path.stat().st_size,
                    sha256=sha256_for_file(str(local_path)),
                )
            )

    unregistered_files = tuple(sorted(path for path in local_files if path not in registered_by_path))
    missing_registered_assets = tuple(
        sorted(path for path in registered_by_path if path not in local_files)
    )
    return TotalExportPackageInventory(
        package_folder=package_folder,
        manifest_path=manifest_path,
        items=tuple(sorted(items, key=lambda item: item.path)),
        unregistered_files=unregistered_files,
        missing_registered_assets=missing_registered_assets,
        registered_asset_count=len(manifest.assets),
        local_file_count=len(local_files),
    )


def summarize_total_export_inventory(inventory: TotalExportPackageInventory) -> str:
    lines = [
        "Total Export Package Inventory",
        f"Package folder: {inventory.package_folder}",
        f"Manifest path: {inventory.manifest_path}",
        f"Registered asset count: {inventory.registered_asset_count}",
        f"Local file count: {inventory.local_file_count}",
        "Unregistered files:",
    ]
    if inventory.unregistered_files:
        for path in inventory.unregistered_files:
            lines.append(f"- {path}")
    else:
        lines.append("- (none)")

    lines.append("Missing registered assets:")
    if inventory.missing_registered_assets:
        for path in inventory.missing_registered_assets:
            lines.append(f"- {path}")
    else:
        lines.append("- (none)")

    lines.append("Items:")
    if inventory.items:
        for item in inventory.items:
            status = "registered" if item.registered else "unregistered"
            exists = "exists" if item.exists else "missing"
            lines.append(f"- {item.path} [{status}; {exists}; {item.asset_type or 'file'}]")
    else:
        lines.append("- (none)")
    return "\n".join(lines)
