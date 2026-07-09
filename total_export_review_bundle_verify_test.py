from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile
import json

from total_export_review_bundle import build_total_export_review_bundle
from total_export_review_bundle_verify import (
    REVIEW_BUNDLE_VERIFY_STATUS_INVALID_SIDECAR,
    REVIEW_BUNDLE_VERIFY_STATUS_MISMATCH,
    REVIEW_BUNDLE_VERIFY_STATUS_MISSING_SIDECAR,
    REVIEW_BUNDLE_VERIFY_STATUS_MISSING_ZIP,
    REVIEW_BUNDLE_VERIFY_STATUS_UNSAFE_ZIP,
    REVIEW_BUNDLE_VERIFY_STATUS_VERIFIED,
    build_total_export_review_bundle_verification_text,
    default_review_bundle_inspection_json_path,
    default_review_bundle_sha256_path,
    parse_sha256_sidecar_text,
    review_bundle_verification_to_dict,
    verify_total_export_review_bundle,
)
from total_export_zip_inspect import inspect_total_export_zip
from total_export_zip_sidecar import (
    build_zip_inspection_sidecar_dict,
    build_zip_sha256_sidecar_text,
)


VALID_ID = "aB3_dE-9xYz"


def _write_zip(path: Path, entries: list[tuple[str, bytes]]) -> None:
    with ZipFile(path, "w") as zip_file:
        for name, data in entries:
            zip_file.writestr(name, data)


def _write_matching_sidecars(zip_path: str) -> tuple[str, str]:
    inspection = inspect_total_export_zip(zip_path, include_entries=True, hash_entries=True)
    sha_path = default_review_bundle_sha256_path(zip_path)
    json_path = default_review_bundle_inspection_json_path(zip_path)
    Path(sha_path).write_text(
        build_zip_sha256_sidecar_text(zip_path, inspection.zip_sha256),
        encoding="utf-8",
    )
    Path(json_path).write_text(
        json.dumps(build_zip_inspection_sidecar_dict(inspection), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return sha_path, json_path


def _tamper_inspection_json(json_path: str, field: str, value) -> None:
    data = json.loads(Path(json_path).read_text(encoding="utf-8"))
    data["zip_inspection"][field] = value
    Path(json_path).write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run_self_test() -> None:
    with TemporaryDirectory() as temp_dir:
        bundle = build_total_export_review_bundle(
            base_folder=temp_dir,
            source_url=f"https://www.youtube.com/watch?v={VALID_ID}&t=30s",
            package_id="verify bundle package",
            selected_capture_options=["comments"],
            create_asset_folders=False,
        )
        result = verify_total_export_review_bundle(bundle.zip_path)
        assert result.status == REVIEW_BUNDLE_VERIFY_STATUS_VERIFIED
        assert result.zip_found is True
        assert result.zip_readable is True
        assert result.zip_sha256
        assert result.sha256_sidecar_found is True
        assert result.sha256_sidecar_valid is True
        assert result.inspection_json_found is True
        assert result.inspection_json_readable is True
        assert result.inspection_json_valid is True
        assert result.hash_matches_sha256_sidecar is True
        assert result.hash_matches_inspection_json is True
        assert result.size_matches_inspection_json is True
        assert result.entry_count_matches_inspection_json is True
        assert result.status_matches_inspection_json is True
        assert result.standard_entries_ok is True
        assert result.errors == ()

        parsed_sha, parsed_name = parse_sha256_sidecar_text(
            Path(bundle.zip_sidecar_sha256_path).read_text(encoding="utf-8")
        )
        assert parsed_sha == result.zip_sha256
        assert parsed_name == Path(bundle.zip_path).name

        text = build_total_export_review_bundle_verification_text(result)
        assert "Total Export review bundle verification" in text
        assert "Status: verified" in text
        assert "Hash matches SHA256 sidecar: yes" in text

        as_dict = review_bundle_verification_to_dict(result)
        assert set(as_dict) == {
            "current_entry_count",
            "current_file_entry_count",
            "duplicate_entries",
            "entry_count_matches_inspection_json",
            "errors",
            "hash_matches_inspection_json",
            "hash_matches_sha256_sidecar",
            "inspection_json_entry_count",
            "inspection_json_found",
            "inspection_json_path",
            "inspection_json_readable",
            "inspection_json_valid",
            "inspection_json_zip_sha256",
            "inspection_json_zip_size_bytes",
            "inspection_json_zip_status",
            "sha256_path",
            "sha256_sidecar_filename",
            "sha256_sidecar_found",
            "sha256_sidecar_sha256",
            "sha256_sidecar_valid",
            "size_matches_inspection_json",
            "standard_entries_ok",
            "status",
            "status_matches_inspection_json",
            "unsafe_entries",
            "warnings",
            "zip_found",
            "zip_path",
            "zip_readable",
            "zip_sha256",
            "zip_size_bytes",
            "zip_status",
        }
        assert as_dict["status"] == REVIEW_BUNDLE_VERIFY_STATUS_VERIFIED

        missing_zip = verify_total_export_review_bundle(str(Path(temp_dir) / "missing.zip"))
        assert missing_zip.status == REVIEW_BUNDLE_VERIFY_STATUS_MISSING_ZIP

        missing_sha_bundle = build_total_export_review_bundle(
            base_folder=temp_dir,
            source_url=f"https://www.youtube.com/watch?v={VALID_ID}",
            package_id="verify missing sha",
            selected_capture_options=["comments"],
            create_asset_folders=False,
        )
        Path(missing_sha_bundle.zip_sidecar_sha256_path).unlink()
        missing_sha = verify_total_export_review_bundle(missing_sha_bundle.zip_path)
        assert missing_sha.status == REVIEW_BUNDLE_VERIFY_STATUS_MISSING_SIDECAR
        assert missing_sha.sha256_sidecar_found is False

        missing_json_bundle = build_total_export_review_bundle(
            base_folder=temp_dir,
            source_url=f"https://www.youtube.com/watch?v={VALID_ID}",
            package_id="verify missing json",
            selected_capture_options=["comments"],
            create_asset_folders=False,
        )
        Path(missing_json_bundle.zip_sidecar_json_path).unlink()
        missing_json = verify_total_export_review_bundle(missing_json_bundle.zip_path)
        assert missing_json.status == REVIEW_BUNDLE_VERIFY_STATUS_MISSING_SIDECAR
        assert missing_json.inspection_json_found is False

        malformed_sha_bundle = build_total_export_review_bundle(
            base_folder=temp_dir,
            source_url=f"https://www.youtube.com/watch?v={VALID_ID}",
            package_id="verify malformed sha",
            selected_capture_options=["comments"],
            create_asset_folders=False,
        )
        Path(malformed_sha_bundle.zip_sidecar_sha256_path).write_text("not a sha\n", encoding="utf-8")
        malformed_sha = verify_total_export_review_bundle(malformed_sha_bundle.zip_path)
        assert malformed_sha.status == REVIEW_BUNDLE_VERIFY_STATUS_INVALID_SIDECAR
        assert malformed_sha.sha256_sidecar_valid is False

        sha_mismatch_bundle = build_total_export_review_bundle(
            base_folder=temp_dir,
            source_url=f"https://www.youtube.com/watch?v={VALID_ID}",
            package_id="verify sha mismatch",
            selected_capture_options=["comments"],
            create_asset_folders=False,
        )
        Path(sha_mismatch_bundle.zip_sidecar_sha256_path).write_text(
            f"{'0' * 64}  {Path(sha_mismatch_bundle.zip_path).name}\n",
            encoding="utf-8",
        )
        sha_mismatch = verify_total_export_review_bundle(sha_mismatch_bundle.zip_path)
        assert sha_mismatch.status == REVIEW_BUNDLE_VERIFY_STATUS_MISMATCH
        assert sha_mismatch.hash_matches_sha256_sidecar is False

        filename_mismatch_bundle = build_total_export_review_bundle(
            base_folder=temp_dir,
            source_url=f"https://www.youtube.com/watch?v={VALID_ID}",
            package_id="verify filename mismatch",
            selected_capture_options=["comments"],
            create_asset_folders=False,
        )
        Path(filename_mismatch_bundle.zip_sidecar_sha256_path).write_text(
            f"{filename_mismatch_bundle.zip_sha256}  other.zip\n",
            encoding="utf-8",
        )
        filename_mismatch = verify_total_export_review_bundle(filename_mismatch_bundle.zip_path)
        assert filename_mismatch.status == REVIEW_BUNDLE_VERIFY_STATUS_INVALID_SIDECAR
        assert filename_mismatch.sha256_sidecar_valid is False

        malformed_json_bundle = build_total_export_review_bundle(
            base_folder=temp_dir,
            source_url=f"https://www.youtube.com/watch?v={VALID_ID}",
            package_id="verify malformed json",
            selected_capture_options=["comments"],
            create_asset_folders=False,
        )
        Path(malformed_json_bundle.zip_sidecar_json_path).write_text("{not json", encoding="utf-8")
        malformed_json = verify_total_export_review_bundle(malformed_json_bundle.zip_path)
        assert malformed_json.status == REVIEW_BUNDLE_VERIFY_STATUS_INVALID_SIDECAR
        assert malformed_json.inspection_json_readable is False

        json_hash_bundle = build_total_export_review_bundle(
            base_folder=temp_dir,
            source_url=f"https://www.youtube.com/watch?v={VALID_ID}",
            package_id="verify json hash mismatch",
            selected_capture_options=["comments"],
            create_asset_folders=False,
        )
        _tamper_inspection_json(json_hash_bundle.zip_sidecar_json_path, "zip_sha256", "0" * 64)
        json_hash_mismatch = verify_total_export_review_bundle(json_hash_bundle.zip_path)
        assert json_hash_mismatch.status == REVIEW_BUNDLE_VERIFY_STATUS_MISMATCH
        assert json_hash_mismatch.hash_matches_inspection_json is False

        json_size_bundle = build_total_export_review_bundle(
            base_folder=temp_dir,
            source_url=f"https://www.youtube.com/watch?v={VALID_ID}",
            package_id="verify json size mismatch",
            selected_capture_options=["comments"],
            create_asset_folders=False,
        )
        _tamper_inspection_json(json_size_bundle.zip_sidecar_json_path, "zip_size_bytes", 1)
        json_size_mismatch = verify_total_export_review_bundle(json_size_bundle.zip_path)
        assert json_size_mismatch.status == REVIEW_BUNDLE_VERIFY_STATUS_MISMATCH
        assert json_size_mismatch.size_matches_inspection_json is False

        json_count_bundle = build_total_export_review_bundle(
            base_folder=temp_dir,
            source_url=f"https://www.youtube.com/watch?v={VALID_ID}",
            package_id="verify json count mismatch",
            selected_capture_options=["comments"],
            create_asset_folders=False,
        )
        _tamper_inspection_json(json_count_bundle.zip_sidecar_json_path, "entry_count", 1)
        json_count_mismatch = verify_total_export_review_bundle(json_count_bundle.zip_path)
        assert json_count_mismatch.status == REVIEW_BUNDLE_VERIFY_STATUS_MISMATCH
        assert json_count_mismatch.entry_count_matches_inspection_json is False

        unsafe_zip_path = str(Path(temp_dir) / "unsafe.zip")
        _write_zip(Path(unsafe_zip_path), [("../evil.txt", b"bad")])
        _write_matching_sidecars(unsafe_zip_path)
        unsafe = verify_total_export_review_bundle(unsafe_zip_path)
        assert unsafe.status == REVIEW_BUNDLE_VERIFY_STATUS_UNSAFE_ZIP
        assert "../evil.txt" in unsafe.unsafe_entries

        with_entries = verify_total_export_review_bundle(
            bundle.zip_path,
            include_zip_entries=True,
            hash_zip_entries=True,
        )
        assert with_entries.status == REVIEW_BUNDLE_VERIFY_STATUS_VERIFIED


if __name__ == "__main__":
    run_self_test()
    print("Total Export review bundle verification self-test passed.")
