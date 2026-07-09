import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory

from total_export_assets import (
    asset_destination_path,
    copy_asset_into_package,
    export_asset_for_file,
    export_asset_identity,
    manifest_with_asset,
    manifest_has_asset,
    register_asset_in_manifest_file,
    safe_asset_filename,
)
from total_export_manifest import (
    ASSET_MEDIA,
    ASSET_TEXT_EXPORT,
    TotalExportManifest,
    read_manifest_json,
    write_manifest_json,
)


def run_self_test() -> None:
    with TemporaryDirectory() as temp_dir:
        assert safe_asset_filename(" report.txt ") == "report.txt"
        assert safe_asset_filename("folder/name?.txt") == "folder_name_.txt"
        assert safe_asset_filename(r"folder\name:bad|chars.csv") == "folder_name_bad_chars.csv"
        assert safe_asset_filename("   ") == "asset"

        text_destination = asset_destination_path(
            package_folder=temp_dir,
            asset_type=ASSET_TEXT_EXPORT,
            filename="report.txt",
        )
        assert text_destination == str(Path(temp_dir) / "metadata" / "report.txt")
        media_destination = asset_destination_path(
            package_folder=temp_dir,
            asset_type=ASSET_MEDIA,
            filename="clip.mp4",
        )
        assert media_destination == str(Path(temp_dir) / "media" / "clip.mp4")

        source_file = Path(temp_dir) / "source.txt"
        sample_bytes = b"registered evidence\n"
        source_file.write_bytes(sample_bytes)
        expected_hash = hashlib.sha256(sample_bytes).hexdigest()

        standalone_asset = export_asset_for_file(
            file_path=str(source_file),
            asset_type=ASSET_TEXT_EXPORT,
        )
        assert standalone_asset.sha256 == expected_hash
        assert standalone_asset.size_bytes == len(sample_bytes)
        assert standalone_asset.path == str(source_file)

        package_folder = str(Path(temp_dir) / "package")
        copied = copy_asset_into_package(
            source_path=str(source_file),
            package_folder=package_folder,
            asset_type=ASSET_TEXT_EXPORT,
            filename=" copied report.txt ",
        )
        assert copied.copied
        assert copied.source_path == str(source_file)
        assert copied.destination_path == str(
            Path(package_folder) / "metadata" / "copied_report.txt"
        )
        assert Path(copied.destination_path).read_bytes() == sample_bytes
        assert copied.asset.sha256 == expected_hash
        assert copied.asset.path == str(Path("metadata") / "copied_report.txt")
        assert export_asset_identity(copied.asset) == (
            ASSET_TEXT_EXPORT,
            "metadata/copied_report.txt",
        )

        try:
            copy_asset_into_package(
                source_path=str(source_file),
                package_folder=package_folder,
                asset_type=ASSET_TEXT_EXPORT,
                filename="copied_report.txt",
            )
        except FileExistsError:
            pass
        else:
            raise AssertionError("Expected overwrite refusal for existing asset.")

        replacement_bytes = b"replacement\n"
        source_file.write_bytes(replacement_bytes)
        overwritten = copy_asset_into_package(
            source_path=str(source_file),
            package_folder=package_folder,
            asset_type=ASSET_TEXT_EXPORT,
            filename="copied_report.txt",
            overwrite=True,
        )
        assert Path(overwritten.destination_path).read_bytes() == replacement_bytes

        manifest = TotalExportManifest(
            package_id="test-package",
            source_urls=["https://example.com/source"],
            output_folder=package_folder,
            capture_options=["comments"],
            notes="keep me",
        )
        updated_manifest = manifest_with_asset(manifest, copied.asset)
        assert manifest.assets == []
        assert len(updated_manifest.assets) == 1
        assert updated_manifest.assets[0] == copied.asset
        assert manifest_has_asset(updated_manifest, copied.asset)
        assert updated_manifest.package_id == manifest.package_id
        assert updated_manifest.source_urls == manifest.source_urls
        assert updated_manifest.capture_options == manifest.capture_options
        assert updated_manifest.notes == "keep me"

        duplicate_manifest = manifest_with_asset(updated_manifest, copied.asset)
        assert len(duplicate_manifest.assets) == 2

        deduped_manifest = manifest_with_asset(updated_manifest, copied.asset, dedupe=True)
        assert len(deduped_manifest.assets) == 1
        assert deduped_manifest.assets[0] == copied.asset

        manifest_path = Path(package_folder) / "manifest.json"
        write_manifest_json(manifest, str(manifest_path))
        registered_manifest = register_asset_in_manifest_file(
            manifest_path=str(manifest_path),
            asset=copied.asset,
        )
        assert len(registered_manifest.assets) == 1
        assert registered_manifest.assets[0] == copied.asset
        assert registered_manifest.package_id == manifest.package_id
        assert registered_manifest.source_urls == manifest.source_urls
        assert registered_manifest.capture_options == manifest.capture_options

        registered_again = register_asset_in_manifest_file(
            manifest_path=str(manifest_path),
            asset=copied.asset,
        )
        assert len(registered_again.assets) == 1

        registered_duplicate = register_asset_in_manifest_file(
            manifest_path=str(manifest_path),
            asset=copied.asset,
            dedupe=False,
        )
        assert len(registered_duplicate.assets) == 2

        reloaded_manifest = read_manifest_json(str(manifest_path))
        assert len(reloaded_manifest.assets) == 2
        assert reloaded_manifest.assets[0].sha256 == copied.asset.sha256
        assert reloaded_manifest.notes == "keep me"


if __name__ == "__main__":
    run_self_test()
    print("Total Export asset registration self-test passed.")
