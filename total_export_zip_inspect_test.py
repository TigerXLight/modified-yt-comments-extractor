from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile
import warnings

from total_export_manifest import sha256_for_file
from total_export_package_zip import create_total_export_package_zip
from total_export_prepare import prepare_total_export_with_summary
from total_export_zip_inspect import (
    ZIP_INSPECTION_STATUS_EMPTY_ZIP,
    ZIP_INSPECTION_STATUS_INVALID_ZIP,
    ZIP_INSPECTION_STATUS_MISSING_MANIFEST,
    ZIP_INSPECTION_STATUS_MISSING_ZIP,
    ZIP_INSPECTION_STATUS_MULTIPLE_MANIFESTS,
    ZIP_INSPECTION_STATUS_OK,
    ZIP_INSPECTION_STATUS_UNSAFE_ENTRIES,
    build_total_export_zip_inspection_text,
    inspect_total_export_zip,
    total_export_zip_inspection_to_dict,
)


VALID_ID = "aB3_dE-9xYz"


def _prepare_zip(temp_dir: str) -> str:
    prepared = prepare_total_export_with_summary(
        base_folder=temp_dir,
        source_url=f"https://www.youtube.com/watch?v={VALID_ID}&t=30s",
        selected_capture_options=["comments"],
        package_id="zip inspect package",
        create_asset_folders=False,
        write_readme=True,
        write_plan_report=True,
        write_inventory_report=True,
    )
    package_folder = prepared.workflow_result.package_result.package_result.package_folder
    zip_result = create_total_export_package_zip(package_folder)
    assert zip_result.zip_created
    return zip_result.zip_path


def _write_zip(path: Path, entries: list[tuple[str, bytes]]) -> None:
    with ZipFile(path, "w") as zip_file:
        for name, data in entries:
            zip_file.writestr(name, data)


def run_self_test() -> None:
    with TemporaryDirectory() as temp_dir:
        zip_path = _prepare_zip(temp_dir)
        result = inspect_total_export_zip(zip_path)
        assert result.status == ZIP_INSPECTION_STATUS_OK
        assert result.zip_found
        assert result.zip_readable
        assert result.zip_sha256
        assert result.zip_sha256 == sha256_for_file(zip_path)
        assert result.file_entry_count >= 5
        assert result.single_top_level_folder
        assert result.manifest_entries
        standard_by_path = {
            entry.relative_path: entry.exists for entry in result.standard_entries
        }
        assert standard_by_path["metadata/TOTAL_EXPORT_SUMMARY.txt"]
        assert standard_by_path["README_TOTAL_EXPORT.txt"]
        assert standard_by_path["metadata/SOURCE_CAPTURE_PLAN.txt"]
        assert standard_by_path["metadata/TOTAL_EXPORT_INVENTORY.txt"]

        text = build_total_export_zip_inspection_text(result)
        assert "Total Export ZIP inspection" in text
        assert "Status: ok" in text
        assert "Manifest entries:" in text
        assert "Standard entries:" in text

        as_dict = total_export_zip_inspection_to_dict(result)
        assert set(as_dict) == {
            "directory_entry_count",
            "duplicate_entries",
            "entries",
            "entry_count",
            "errors",
            "file_entry_count",
            "manifest_entries",
            "single_top_level_folder",
            "standard_entries",
            "status",
            "top_level_name",
            "unsafe_entries",
            "warnings",
            "zip_found",
            "zip_path",
            "zip_readable",
            "zip_sha256",
            "zip_size_bytes",
        }
        assert as_dict["status"] == ZIP_INSPECTION_STATUS_OK
        assert any(
            entry["relative_path"] == "metadata/SOURCE_CAPTURE_PLAN.txt"
            for entry in as_dict["standard_entries"]
        )

        missing = inspect_total_export_zip(str(Path(temp_dir) / "missing.zip"))
        assert missing.status == ZIP_INSPECTION_STATUS_MISSING_ZIP
        assert not missing.zip_found

        invalid_path = Path(temp_dir) / "invalid.zip"
        invalid_path.write_text("not a zip", encoding="utf-8")
        invalid = inspect_total_export_zip(str(invalid_path))
        assert invalid.status == ZIP_INSPECTION_STATUS_INVALID_ZIP
        assert invalid.zip_found
        assert not invalid.zip_readable

        empty_path = Path(temp_dir) / "empty.zip"
        with ZipFile(empty_path, "w"):
            pass
        empty = inspect_total_export_zip(str(empty_path))
        assert empty.status == ZIP_INSPECTION_STATUS_EMPTY_ZIP

        unsafe_path = Path(temp_dir) / "unsafe.zip"
        _write_zip(unsafe_path, [("../evil.txt", b"bad")])
        unsafe = inspect_total_export_zip(str(unsafe_path))
        assert unsafe.status == ZIP_INSPECTION_STATUS_UNSAFE_ENTRIES
        assert "../evil.txt" in unsafe.unsafe_entries

        backslash_path = Path(temp_dir) / "backslash.zip"
        _write_zip(backslash_path, [("bad\\path.txt", b"bad")])
        backslash = inspect_total_export_zip(str(backslash_path))
        assert backslash.status == ZIP_INSPECTION_STATUS_UNSAFE_ENTRIES
        assert "bad\\path.txt" in backslash.unsafe_entries

        duplicate_path = Path(temp_dir) / "duplicate.zip"
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            _write_zip(
                duplicate_path,
                [
                    ("package/package_manifest.json", b"{}"),
                    ("package/file.txt", b"one"),
                    ("package/file.txt", b"two"),
                ],
            )
        duplicate = inspect_total_export_zip(str(duplicate_path))
        assert "package/file.txt" in duplicate.duplicate_entries

        multiple_manifest_path = Path(temp_dir) / "multiple_manifest.zip"
        _write_zip(
            multiple_manifest_path,
            [
                ("package/a_manifest.json", b"{}"),
                ("package/b_manifest.json", b"{}"),
            ],
        )
        multiple_manifest = inspect_total_export_zip(str(multiple_manifest_path))
        assert multiple_manifest.status == ZIP_INSPECTION_STATUS_MULTIPLE_MANIFESTS

        no_manifest_path = Path(temp_dir) / "no_manifest.zip"
        _write_zip(no_manifest_path, [("package/file.txt", b"hello")])
        no_manifest = inspect_total_export_zip(str(no_manifest_path))
        assert no_manifest.status == ZIP_INSPECTION_STATUS_MISSING_MANIFEST

        entries = inspect_total_export_zip(zip_path, include_entries=True)
        entry_names = [entry.name for entry in entries.entries]
        assert entry_names == sorted(entry_names)
        assert entries.entries

        hashed_entries = inspect_total_export_zip(
            zip_path,
            include_entries=True,
            hash_entries=True,
        )
        assert any(entry.sha256 for entry in hashed_entries.entries if not entry.is_dir)


if __name__ == "__main__":
    run_self_test()
    print("Total Export ZIP inspection self-test passed.")
