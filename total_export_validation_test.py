import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory

from total_export_assets import copy_asset_into_package, export_asset_for_file
from total_export_manifest import (
    ASSET_TEXT_EXPORT,
    ExportAsset,
    TotalExportManifest,
    write_manifest_json,
)
from total_export_validation import (
    VALIDATION_LEVEL_INFO,
    ManifestValidationResult,
    validate_manifest_json_file,
    validate_total_export_manifest,
)


def _issue_codes(result: ManifestValidationResult) -> tuple[str, ...]:
    return tuple(issue.code for issue in result.issues)


def run_self_test() -> None:
    with TemporaryDirectory() as temp_dir:
        package_folder = Path(temp_dir) / "package"
        source_file = Path(temp_dir) / "source.txt"
        sample_bytes = b"validation sample\n"
        source_file.write_bytes(sample_bytes)
        expected_hash = hashlib.sha256(sample_bytes).hexdigest()

        copied = copy_asset_into_package(
            source_path=str(source_file),
            package_folder=str(package_folder),
            asset_type=ASSET_TEXT_EXPORT,
            filename="sample.txt",
        )
        valid_manifest = TotalExportManifest(
            package_id="validation-package",
            source_urls=["https://example.com/source"],
            output_folder=str(package_folder),
            capture_options=["comments"],
            assets=[copied.asset],
        )
        valid_result = validate_total_export_manifest(valid_manifest)
        assert not valid_result.has_errors
        assert valid_result.errors == ()
        assert valid_result.warnings == ()

        missing_id = validate_total_export_manifest(
            TotalExportManifest(
                source_urls=["https://example.com/source"],
                output_folder=str(package_folder),
                capture_options=["comments"],
            )
        )
        assert "MISSING_PACKAGE_ID" in _issue_codes(missing_id)
        assert missing_id.has_errors

        missing_asset = validate_total_export_manifest(
            TotalExportManifest(
                package_id="missing-asset",
                source_urls=["https://example.com/source"],
                output_folder=str(package_folder),
                capture_options=["comments"],
                assets=[
                    ExportAsset(
                        asset_type=ASSET_TEXT_EXPORT,
                        path="metadata/missing.txt",
                    )
                ],
            )
        )
        assert _issue_codes(missing_asset) == ("ASSET_FILE_MISSING",)
        assert missing_asset.has_errors

        wrong_size = validate_total_export_manifest(
            TotalExportManifest(
                package_id="wrong-size",
                source_urls=["https://example.com/source"],
                output_folder=str(package_folder),
                capture_options=["comments"],
                assets=[
                    ExportAsset(
                        asset_type=ASSET_TEXT_EXPORT,
                        path=copied.asset.path,
                        sha256=expected_hash,
                        size_bytes=len(sample_bytes) + 1,
                    )
                ],
            )
        )
        assert _issue_codes(wrong_size) == ("ASSET_SIZE_MISMATCH",)
        assert wrong_size.has_errors

        wrong_hash = validate_total_export_manifest(
            TotalExportManifest(
                package_id="wrong-hash",
                source_urls=["https://example.com/source"],
                output_folder=str(package_folder),
                capture_options=["comments"],
                assets=[
                    ExportAsset(
                        asset_type=ASSET_TEXT_EXPORT,
                        path=copied.asset.path,
                        sha256="0" * 64,
                        size_bytes=len(sample_bytes),
                    )
                ],
            )
        )
        assert _issue_codes(wrong_hash) == ("ASSET_SHA256_MISMATCH",)
        assert wrong_hash.has_errors

        relative_asset = export_asset_for_file(
            file_path=str(package_folder / copied.asset.path),
            asset_type=ASSET_TEXT_EXPORT,
            package_folder=str(package_folder),
        )
        relative_result = validate_total_export_manifest(
            TotalExportManifest(
                package_id="relative-asset",
                source_urls=["https://example.com/source"],
                output_folder="",
                capture_options=["comments"],
                assets=[relative_asset],
            ),
            manifest_path=str(package_folder / "manifest.json"),
        )
        assert not relative_result.has_errors
        assert relative_result.package_folder == str(package_folder)

        empty_metadata = validate_total_export_manifest(
            TotalExportManifest(package_id="empty", output_folder=str(package_folder))
        )
        assert _issue_codes(empty_metadata) == ("NO_SOURCE_URLS", "NO_CAPTURE_OPTIONS")
        assert all(issue.level == VALIDATION_LEVEL_INFO for issue in empty_metadata.issues)
        assert not empty_metadata.has_errors

        manifest_path = package_folder / "manifest.json"
        write_manifest_json(valid_manifest, str(manifest_path))
        file_result = validate_manifest_json_file(str(manifest_path))
        assert not file_result.has_errors
        assert file_result.manifest_path == str(manifest_path)

        invalid_path = package_folder / "invalid.json"
        invalid_path.write_text("{not json", encoding="utf-8")
        invalid_result = validate_manifest_json_file(str(invalid_path))
        assert _issue_codes(invalid_result) == ("MANIFEST_READ_FAILED",)
        assert invalid_result.has_errors

        missing_result = validate_manifest_json_file(str(package_folder / "missing.json"))
        assert _issue_codes(missing_result) == ("MANIFEST_READ_FAILED",)
        assert missing_result.has_errors


if __name__ == "__main__":
    run_self_test()
    print("Total Export validation self-test passed.")
