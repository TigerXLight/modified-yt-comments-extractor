from pathlib import Path
from tempfile import TemporaryDirectory
import json

from total_export_review_bundle import build_total_export_review_bundle
from total_export_review_bundle_folder_verify import (
    build_total_export_review_bundle_folder_verification_text,
    default_review_bundle_folder_report_path,
    discover_review_bundle_zip_paths,
    review_bundle_folder_verification_to_dict,
    verify_total_export_review_bundle_folder,
)


VALID_ID = "aB3_dE-9xYz"


def _build_bundle(base_folder: Path, package_id: str):
    return build_total_export_review_bundle(
        base_folder=str(base_folder),
        source_url=f"https://www.youtube.com/watch?v={VALID_ID}&t=30s",
        package_id=package_id,
        selected_capture_options=["comments"],
        create_asset_folders=False,
    )

def _assert_folder_counts(
    result,
    *,
    zip_count: int,
    verified_count: int | None = None,
    failed_count: int | None = None,
    missing_sidecar_count: int | None = None,
    mismatch_count: int | None = None,
) -> None:
    assert result.zip_count == zip_count
    if verified_count is not None:
        assert result.verified_count == verified_count
    if failed_count is not None:
        assert result.failed_count == failed_count
    if missing_sidecar_count is not None:
        assert result.missing_sidecar_count == missing_sidecar_count
    if mismatch_count is not None:
        assert result.mismatch_count == mismatch_count



def run_self_test() -> None:
    with TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)

        valid_folder = root / "valid"
        valid_folder.mkdir()
        _build_bundle(valid_folder, "folder valid one")
        _build_bundle(valid_folder, "folder valid two")
        discovered = discover_review_bundle_zip_paths(str(valid_folder))
        assert len(discovered) == 2
        assert discovered == tuple(sorted(discovered, key=lambda value: Path(value).name))

        valid = verify_total_export_review_bundle_folder(str(valid_folder))
        _assert_folder_counts(valid, zip_count=2, verified_count=2, failed_count=0)
        assert valid.report_written is False
        text = build_total_export_review_bundle_folder_verification_text(valid)
        assert "Total Export review bundle folder verification" in text
        assert "ZIP count: 2" in text
        assert "Verified count: 2" in text

        as_dict = review_bundle_folder_verification_to_dict(valid)
        assert set(as_dict) == {
            "errors",
            "failed_count",
            "folder_path",
            "invalid_sidecar_count",
            "invalid_zip_count",
            "items",
            "mismatch_count",
            "missing_sidecar_count",
            "missing_zip_count",
            "recursive",
            "report_path",
            "report_written",
            "unsafe_zip_count",
            "verified_count",
            "verified_with_warnings_count",
            "warnings",
            "zip_count",
        }
        assert len(as_dict["items"]) == 2

        missing_folder = verify_total_export_review_bundle_folder(str(root / "missing"))
        assert missing_folder.zip_count == 0
        assert missing_folder.errors

        missing_sidecar_folder = root / "missing_sidecar"
        missing_sidecar_folder.mkdir()
        missing_bundle = _build_bundle(missing_sidecar_folder, "folder missing sidecar")
        Path(missing_bundle.zip_sidecar_sha256_path).unlink()
        missing_sidecar = verify_total_export_review_bundle_folder(str(missing_sidecar_folder))
        _assert_folder_counts(missing_sidecar, zip_count=1, failed_count=1, missing_sidecar_count=1)

        mismatch_folder = root / "mismatch"
        mismatch_folder.mkdir()
        mismatch_bundle = _build_bundle(mismatch_folder, "folder mismatch")
        Path(mismatch_bundle.zip_sidecar_sha256_path).write_text(
            f"{'0' * 64}  {Path(mismatch_bundle.zip_path).name}\n",
            encoding="utf-8",
        )
        mismatch = verify_total_export_review_bundle_folder(str(mismatch_folder))
        _assert_folder_counts(mismatch, zip_count=1, failed_count=1, mismatch_count=1)

        recursive_folder = root / "recursive"
        recursive_folder.mkdir()
        _build_bundle(recursive_folder, "folder recursive direct")
        nested_folder = recursive_folder / "nested"
        nested_folder.mkdir()
        _build_bundle(nested_folder, "folder recursive nested")
        non_recursive = verify_total_export_review_bundle_folder(str(recursive_folder))
        recursive = verify_total_export_review_bundle_folder(str(recursive_folder), recursive=True)
        assert non_recursive.zip_count == 1
        assert recursive.zip_count == 2

        report_folder = root / "report"
        report_folder.mkdir()
        _build_bundle(report_folder, "folder report one")
        default_report_path = default_review_bundle_folder_report_path(str(report_folder))
        report = verify_total_export_review_bundle_folder(
            str(report_folder),
            write_report=True,
        )
        assert report.report_written is True
        assert report.report_path == default_report_path
        assert Path(default_report_path).is_file()
        report_json = json.loads(Path(default_report_path).read_text(encoding="utf-8"))
        assert report_json["zip_count"] == 1
        assert report_json["report_written"] is True

        existing_report = verify_total_export_review_bundle_folder(
            str(report_folder),
            write_report=True,
        )
        assert existing_report.report_written is False
        assert existing_report.errors

        overwritten_report = verify_total_export_review_bundle_folder(
            str(report_folder),
            write_report=True,
            overwrite_report=True,
        )
        assert overwritten_report.report_written is True
        assert overwritten_report.errors == ()

        custom_report_path = str(root / "custom_report.json")
        custom_report = verify_total_export_review_bundle_folder(
            str(report_folder),
            write_report=True,
            report_path=custom_report_path,
        )
        assert custom_report.report_written is True
        assert custom_report.report_path == custom_report_path
        assert Path(custom_report_path).is_file()

        empty_folder = root / "empty"
        empty_folder.mkdir()
        empty = verify_total_export_review_bundle_folder(str(empty_folder))
        _assert_folder_counts(empty, zip_count=0, failed_count=0)
        assert empty.errors == ()

        with_entries = verify_total_export_review_bundle_folder(
            str(valid_folder),
            include_zip_entries=True,
            hash_zip_entries=True,
        )
        _assert_folder_counts(with_entries, zip_count=2, verified_count=2)


if __name__ == "__main__":
    run_self_test()
    print("Total Export review bundle folder verification self-test passed.")
