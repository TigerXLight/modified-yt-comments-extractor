from pathlib import Path
from tempfile import TemporaryDirectory

from source_capture_plan import PLAN_STATUS_UNSUPPORTED_SOURCE
from total_export_inventory_report import write_total_export_inventory_report_file
from total_export_manifest import read_manifest_json
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
            package_id="inventory report package",
            create_asset_folders=False,
            write_readme=True,
        )
        package_folder = prepared.workflow_result.package_result.package_result.package_folder
        manifest_path = prepared.workflow_result.package_result.manifest_path

        result = write_total_export_inventory_report_file(
            package_folder=package_folder,
            manifest_path=manifest_path,
            filename=" Unsafe Inventory: Clip #1?.txt ",
            register_in_manifest=True,
        )
        assert result.registered
        assert result.manifest_path == manifest_path
        assert _posix_path(result.asset_path) == "metadata/Unsafe_Inventory_Clip_1_.txt"
        assert Path(result.report_path).is_file()
        assert Path(result.report_path).parent == Path(package_folder) / "metadata"

        report_text = Path(result.report_path).read_text(encoding="utf-8")
        assert "Total Export Package Inventory" in report_text
        assert f"Package folder: {package_folder}" in report_text
        assert f"Manifest path: {manifest_path}" in report_text
        assert "Registered asset count: 2" in report_text
        assert "Local file count: 3" in report_text
        assert "before this report registration step" in report_text

        manifest = read_manifest_json(manifest_path)
        report_assets = [
            asset
            for asset in manifest.assets
            if _posix_path(asset.path) == _posix_path(result.asset_path)
        ]
        assert len(report_assets) == 1
        assert report_assets[0].sha256
        assert report_assets[0].size_bytes == Path(result.report_path).stat().st_size

        repeated = write_total_export_inventory_report_file(
            package_folder=package_folder,
            manifest_path=manifest_path,
            filename=" Unsafe Inventory: Clip #1?.txt ",
            register_in_manifest=True,
        )
        assert repeated.registered
        repeated_manifest = read_manifest_json(manifest_path)
        repeated_report_assets = [
            asset
            for asset in repeated_manifest.assets
            if _posix_path(asset.path) == _posix_path(result.asset_path)
        ]
        assert len(repeated_report_assets) == 1

        unregistered = prepare_total_export_with_summary(
            base_folder=temp_dir,
            source_url=f"https://www.youtube.com/watch?v={VALID_ID}",
            selected_capture_options=["comments"],
            package_id="inventory report unregistered",
            create_asset_folders=False,
        )
        unregistered_package_folder = (
            unregistered.workflow_result.package_result.package_result.package_folder
        )
        unregistered_manifest_path = unregistered.workflow_result.package_result.manifest_path
        unregistered_result = write_total_export_inventory_report_file(
            package_folder=unregistered_package_folder,
            manifest_path=unregistered_manifest_path,
            register_in_manifest=False,
        )
        assert not unregistered_result.registered
        assert Path(unregistered_result.report_path).is_file()
        unregistered_manifest = read_manifest_json(unregistered_manifest_path)
        assert len(unregistered_manifest.assets) == 1

        unsupported = prepare_total_export_with_summary(
            base_folder=temp_dir,
            source_url="https://example.com/article",
            selected_capture_options=["comments"],
            package_id="inventory report unsupported",
            create_asset_folders=False,
            write_readme=True,
        )
        assert unsupported.workflow_result.plan.status == PLAN_STATUS_UNSUPPORTED_SOURCE
        unsupported_result = write_total_export_inventory_report_file(
            package_folder=unsupported.workflow_result.package_result.package_result.package_folder,
            manifest_path=unsupported.workflow_result.package_result.manifest_path,
        )
        unsupported_text = Path(unsupported_result.report_path).read_text(encoding="utf-8")
        assert "Total Export Package Inventory" in unsupported_text
        assert "Registered asset count: 2" in unsupported_text


if __name__ == "__main__":
    run_self_test()
    print("Total Export inventory report self-test passed.")
