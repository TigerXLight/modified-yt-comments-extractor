from pathlib import Path
from tempfile import TemporaryDirectory

from total_export_package_inspect import (
    INSPECTION_STATUS_INVALID_MANIFEST,
    INSPECTION_STATUS_MISSING_MANIFEST,
    INSPECTION_STATUS_MISSING_PACKAGE_FOLDER,
    INSPECTION_STATUS_MULTIPLE_MANIFESTS,
    INSPECTION_STATUS_OK,
    TotalExportPackageInspectionResult,
    build_total_export_package_inspection_text,
    discover_total_export_manifest,
    inspect_total_export_package,
    package_inspection_to_dict,
)
from total_export_prepare import prepare_total_export_with_summary


VALID_ID = "aB3_dE-9xYz"


def _assert_inspection_status(
    result: TotalExportPackageInspectionResult,
    expected_status: str,
) -> None:
    assert result.status == expected_status


def run_self_test() -> None:
    with TemporaryDirectory() as temp_dir:
        prepared = prepare_total_export_with_summary(
            base_folder=temp_dir,
            source_url=f"https://www.youtube.com/watch?v={VALID_ID}&t=30s",
            selected_capture_options=["comments"],
            package_id="inspection package",
            create_asset_folders=False,
            write_readme=True,
            write_plan_report=True,
            write_inventory_report=True,
        )
        package_folder = prepared.workflow_result.package_result.package_result.package_folder
        manifest_path = prepared.workflow_result.package_result.manifest_path

        discovered_manifest, candidates = discover_total_export_manifest(package_folder)
        assert discovered_manifest == manifest_path
        assert candidates == (manifest_path,)

        result = inspect_total_export_package(package_folder=package_folder)
        _assert_inspection_status(result, INSPECTION_STATUS_OK)
        assert result.manifest_found
        assert result.manifest_readable
        assert result.manifest_valid
        assert result.inventory_ran
        assert result.inventory_registered_asset_count == 4
        assert result.inventory_local_file_count == 5
        assert result.inventory_missing_registered_assets == ()
        assert any(path.endswith("_manifest.json") for path in result.inventory_unregistered_files)
        standard_by_label = {item.label: item for item in result.standard_files}
        assert standard_by_label["summary"].exists
        assert standard_by_label["summary"].registered
        assert standard_by_label["readme"].exists
        assert standard_by_label["readme"].registered
        assert standard_by_label["source_plan_report"].exists
        assert standard_by_label["source_plan_report"].registered
        assert standard_by_label["inventory_report"].exists
        assert standard_by_label["inventory_report"].registered
        assert standard_by_label["manifest"].exists

        explicit = inspect_total_export_package(
            package_folder=package_folder,
            manifest_path=manifest_path,
        )
        _assert_inspection_status(explicit, INSPECTION_STATUS_OK)
        assert explicit.manifest_path == manifest_path

        as_dict = package_inspection_to_dict(result)
        assert as_dict["status"] == INSPECTION_STATUS_OK
        assert as_dict["manifest_found"] is True
        assert any(
            item["relative_path"] == "metadata/SOURCE_CAPTURE_PLAN.txt"
            for item in as_dict["standard_files"]
        )

        text = build_total_export_package_inspection_text(result)
        assert "Total Export package inspection" in text
        assert f"Package folder: {package_folder}" in text
        assert f"Manifest path: {manifest_path}" in text
        assert "Status: ok" in text
        assert "Manifest valid: yes" in text
        assert "Registered assets: 4" in text
        assert "Local files: 5" in text
        assert "source_plan_report: metadata/SOURCE_CAPTURE_PLAN.txt" in text

        extra_file = Path(package_folder) / "extra_local_note.txt"
        extra_file.write_text("local note", encoding="utf-8")
        with_extra = inspect_total_export_package(package_folder=package_folder)
        assert "extra_local_note.txt" in with_extra.inventory_unregistered_files

        missing_asset_path = Path(package_folder) / "metadata" / "SOURCE_CAPTURE_PLAN.txt"
        missing_asset_path.unlink()
        missing_asset = inspect_total_export_package(package_folder=package_folder)
        assert "metadata/SOURCE_CAPTURE_PLAN.txt" in missing_asset.inventory_missing_registered_assets
        _assert_inspection_status(missing_asset, INSPECTION_STATUS_INVALID_MANIFEST)
        assert any("ASSET_FILE_MISSING" in error for error in missing_asset.validation_errors)

        missing_package = inspect_total_export_package(
            package_folder=str(Path(temp_dir) / "missing_package")
        )
        _assert_inspection_status(
            missing_package,
            INSPECTION_STATUS_MISSING_PACKAGE_FOLDER,
        )

        empty_folder = Path(temp_dir) / "empty_package"
        empty_folder.mkdir()
        missing_manifest = inspect_total_export_package(package_folder=str(empty_folder))
        _assert_inspection_status(missing_manifest, INSPECTION_STATUS_MISSING_MANIFEST)

        multiple_folder = Path(temp_dir) / "multiple_manifests"
        multiple_folder.mkdir()
        (multiple_folder / "a_manifest.json").write_text("{}", encoding="utf-8")
        (multiple_folder / "b_manifest.json").write_text("{}", encoding="utf-8")
        multiple = inspect_total_export_package(package_folder=str(multiple_folder))
        _assert_inspection_status(multiple, INSPECTION_STATUS_MULTIPLE_MANIFESTS)
        assert "Multiple manifest candidates" in multiple.warnings[0]


if __name__ == "__main__":
    run_self_test()
    print("Total Export package inspection self-test passed.")
