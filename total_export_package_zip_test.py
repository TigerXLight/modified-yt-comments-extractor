from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile

from total_export_manifest import sha256_for_file
from total_export_package_zip import (
    TotalExportPackageZipResult,
    build_total_export_package_zip_text,
    create_total_export_package_zip,
    default_total_export_zip_path,
    package_zip_result_to_dict,
)
from total_export_prepare import prepare_total_export_with_summary


VALID_ID = "aB3_dE-9xYz"


def _prepare_full_review_package(temp_dir: str, package_id: str = "zip package"):
    return prepare_total_export_with_summary(
        base_folder=temp_dir,
        source_url=f"https://www.youtube.com/watch?v={VALID_ID}&t=30s",
        selected_capture_options=["comments"],
        package_id=package_id,
        create_asset_folders=False,
        write_readme=True,
        write_plan_report=True,
        write_inventory_report=True,
    )


def _package_file_count(package_folder: str) -> int:
    return sum(1 for path in Path(package_folder).rglob("*") if path.is_file())


def _assert_zip_created(result: TotalExportPackageZipResult) -> None:
    assert result.zip_created is True
    assert Path(result.zip_path).is_file()


def _assert_zip_failure(
    result: TotalExportPackageZipResult,
    expected_error: str,
) -> None:
    assert result.zip_created is False
    assert any(expected_error in error for error in result.errors)


def run_self_test() -> None:
    with TemporaryDirectory() as temp_dir:
        prepared = _prepare_full_review_package(temp_dir)
        package_folder = prepared.workflow_result.package_result.package_result.package_folder
        package_basename = Path(package_folder).name

        result = create_total_export_package_zip(package_folder)
        _assert_zip_created(result)
        assert result.zip_path == default_total_export_zip_path(package_folder)
        assert result.zip_sha256
        assert result.zip_sha256 == sha256_for_file(result.zip_path)
        assert result.zip_size_bytes == Path(result.zip_path).stat().st_size
        assert result.zipped_file_count == _package_file_count(package_folder)
        assert result.inspection_status == "ok"

        with ZipFile(result.zip_path, "r") as zip_file:
            names = zip_file.namelist()
        assert names == sorted(names)
        assert all(name.startswith(f"{package_basename}/") for name in names)
        assert f"{package_basename}/zip_package_manifest.json" in names
        assert f"{package_basename}/metadata/TOTAL_EXPORT_SUMMARY.txt" in names
        assert f"{package_basename}/README_TOTAL_EXPORT.txt" in names
        assert f"{package_basename}/metadata/SOURCE_CAPTURE_PLAN.txt" in names
        assert f"{package_basename}/metadata/TOTAL_EXPORT_INVENTORY.txt" in names

        existing = create_total_export_package_zip(package_folder)
        _assert_zip_failure(existing, "already exists")

        overwritten = create_total_export_package_zip(package_folder, overwrite=True)
        _assert_zip_created(overwritten)

        custom_zip_path = str(Path(temp_dir) / "custom" / "package.zip")
        custom = create_total_export_package_zip(
            package_folder,
            zip_path=custom_zip_path,
        )
        _assert_zip_created(custom)
        assert custom.zip_path == custom_zip_path

        inside = create_total_export_package_zip(
            package_folder,
            zip_path=str(Path(package_folder) / "inside.zip"),
        )
        _assert_zip_failure(inside, "must not be inside")
        assert inside.errors == ("ZIP path must not be inside the package folder.",)
        assert not (Path(package_folder) / "inside.zip").exists()

        missing = create_total_export_package_zip(str(Path(temp_dir) / "missing_package"))
        _assert_zip_failure(missing, "inspection status")
        assert missing.inspection_status == "missing_package_folder"

        invalid_prepared = _prepare_full_review_package(temp_dir, "invalid zip package")
        invalid_package_folder = (
            invalid_prepared.workflow_result.package_result.package_result.package_folder
        )
        (Path(invalid_package_folder) / "metadata" / "SOURCE_CAPTURE_PLAN.txt").unlink()
        invalid = create_total_export_package_zip(invalid_package_folder)
        _assert_zip_failure(invalid, "inspection status")
        assert invalid.inspection_status == "invalid_manifest"

        as_dict = package_zip_result_to_dict(result)
        assert set(as_dict) == {
            "errors",
            "inspection_manifest_valid",
            "inspection_status",
            "inspection_warnings",
            "manifest_path",
            "package_folder",
            "warnings",
            "zip_created",
            "zip_path",
            "zip_sha256",
            "zip_size_bytes",
            "zipped_file_count",
        }
        assert as_dict["zip_created"] is True
        assert as_dict["zip_sha256"] == result.zip_sha256

        text = build_total_export_package_zip_text(result)
        assert "Total Export package ZIP" in text
        assert "ZIP created: yes" in text
        assert "ZIP SHA-256: " in text
        assert "Inspection status: ok" in text


if __name__ == "__main__":
    run_self_test()
    print("Total Export package ZIP self-test passed.")
