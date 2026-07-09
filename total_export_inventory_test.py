from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory

from source_capture_plan import PLAN_STATUS_UNSUPPORTED_SOURCE
from total_export_inventory import (
    build_total_export_inventory,
    summarize_total_export_inventory,
)
from total_export_manifest import ASSET_TEXT_EXPORT, ExportAsset, read_manifest_json, write_manifest_json
from total_export_prepare import prepare_total_export_with_summary


VALID_ID = "aB3_dE-9xYz"


def _posix_path(value: str) -> str:
    return (value or "").replace("\\", "/")


def run_self_test() -> None:
    with TemporaryDirectory() as temp_dir:
        prepared = prepare_total_export_with_summary(
            base_folder=temp_dir,
            source_url=f"https://www.youtube.com/watch?v={VALID_ID}&t=30s",
            selected_capture_options=["comments"],
            package_id="inventory package",
            create_asset_folders=True,
            write_readme=True,
        )
        package_folder = prepared.workflow_result.package_result.package_result.package_folder
        manifest_path = prepared.workflow_result.package_result.manifest_path
        inventory = build_total_export_inventory(
            package_folder=package_folder,
            manifest_path=manifest_path,
        )
        assert inventory.registered_asset_count == 2
        assert inventory.local_file_count == 3
        assert "manifest.json" in inventory.unregistered_files or any(
            path.endswith("_manifest.json") for path in inventory.unregistered_files
        )
        assert inventory.missing_registered_assets == ()

        by_path = {item.path: item for item in inventory.items}
        summary_asset_path = _posix_path(prepared.summary_file_result.asset_path)
        assert summary_asset_path in by_path
        assert by_path[summary_asset_path].registered
        assert by_path[summary_asset_path].exists
        assert prepared.readme_file_result is not None
        readme_asset_path = _posix_path(prepared.readme_file_result.asset_path)
        assert readme_asset_path in by_path
        assert by_path[readme_asset_path].registered
        assert by_path[readme_asset_path].exists

        extra_file = Path(package_folder) / "extra_local_note.txt"
        extra_file.write_text("local note", encoding="utf-8")
        manifest = read_manifest_json(manifest_path)
        fake_asset = ExportAsset(
            asset_type=ASSET_TEXT_EXPORT,
            path="metadata/missing_registered.txt",
        )
        write_manifest_json(
            replace(manifest, assets=list(manifest.assets) + [fake_asset]),
            manifest_path,
        )

        updated_inventory = build_total_export_inventory(
            package_folder=package_folder,
            manifest_path=manifest_path,
        )
        assert "extra_local_note.txt" in updated_inventory.unregistered_files
        assert "metadata/missing_registered.txt" in updated_inventory.missing_registered_assets
        assert updated_inventory.registered_asset_count == 3
        assert updated_inventory.local_file_count == 4
        missing_item = {
            item.path: item for item in updated_inventory.items
        }["metadata/missing_registered.txt"]
        assert missing_item.registered
        assert not missing_item.exists

        summary = summarize_total_export_inventory(updated_inventory)
        assert "Total Export Package Inventory" in summary
        assert f"Package folder: {package_folder}" in summary
        assert f"Manifest path: {manifest_path}" in summary
        assert "Registered asset count: 3" in summary
        assert "Local file count: 4" in summary
        assert "- extra_local_note.txt" in summary
        assert "- metadata/missing_registered.txt" in summary

        unsupported = prepare_total_export_with_summary(
            base_folder=temp_dir,
            source_url="https://example.com/article",
            selected_capture_options=["comments"],
            package_id="inventory unsupported",
            create_asset_folders=False,
            write_readme=True,
        )
        assert unsupported.workflow_result.plan.status == PLAN_STATUS_UNSUPPORTED_SOURCE
        unsupported_inventory = build_total_export_inventory(
            package_folder=unsupported.workflow_result.package_result.package_result.package_folder,
            manifest_path=unsupported.workflow_result.package_result.manifest_path,
        )
        assert unsupported_inventory.registered_asset_count == 2
        assert unsupported_inventory.local_file_count == 3


if __name__ == "__main__":
    run_self_test()
    print("Total Export inventory self-test passed.")
