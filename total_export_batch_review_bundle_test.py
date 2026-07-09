from pathlib import Path
from tempfile import TemporaryDirectory
import json

from total_export_batch_review_bundle import (
    batch_review_bundle_result_to_dict,
    build_total_export_batch_review_bundle_text,
    build_total_export_batch_review_bundles,
    parse_total_export_batch_rows,
)


VALID_ID = "aB3_dE-9xYz"


def _write_batch(path: Path, rows: list[str]) -> None:
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")


def run_self_test() -> None:
    with TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        batch_file = root / "sources.txt"
        _write_batch(
            batch_file,
            [
                "# local batch review bundle self-test",
                "",
                f"https://www.youtube.com/watch?v={VALID_ID}",
                f"https://www.youtube.com/watch?v={VALID_ID}\tbatch package two",
                f"https://www.youtube.com/watch?v={VALID_ID}\tbatch package three\tClip Title",
            ],
        )
        rows = parse_total_export_batch_rows(str(batch_file))
        assert len(rows) == 3
        assert rows[0].source_url == f"https://www.youtube.com/watch?v={VALID_ID}"
        assert rows[0].package_id == ""
        assert rows[1].package_id == "batch package two"
        assert rows[2].title == "Clip Title"

        output_folder = root / "batch_output"
        result = build_total_export_batch_review_bundles(
            batch_source_file=str(batch_file),
            base_folder=str(output_folder),
            selected_capture_options=["comments"],
            user_terms=["Caltheris"],
            create_asset_folders=False,
        )
        assert result.row_count == 3
        assert result.success_count == 3
        assert result.failed_count == 0
        assert result.folder_verification_ran is True
        assert result.folder_verification_zip_count == 3
        assert result.folder_verification_verified_count == 3
        assert result.folder_verification_failed_count == 0
        assert result.errors == ()
        for item in result.items:
            assert item.zip_created is True
            assert item.zip_sha256
            assert item.zip_sidecar_sha256_written is True
            assert item.zip_sidecar_json_written is True
            assert Path(item.zip_path).is_file()
            assert Path(f"{item.zip_path}.sha256").is_file()
            assert Path(f"{item.zip_path}.inspection.json").is_file()

        text = build_total_export_batch_review_bundle_text(result)
        assert "Total Export batch review bundles" in text
        assert "Row count: 3" in text
        assert "Success count: 3" in text
        assert "Failed count: 0" in text

        as_dict = batch_review_bundle_result_to_dict(result)
        assert set(as_dict) == {
            "base_folder",
            "batch_source_file",
            "continue_on_error",
            "errors",
            "failed_count",
            "folder_verification_failed_count",
            "folder_verification_ran",
            "folder_verification_report_path",
            "folder_verification_report_written",
            "folder_verification_verified_count",
            "folder_verification_zip_count",
            "items",
            "row_count",
            "success_count",
            "warnings",
        }
        assert len(as_dict["items"]) == 3

        missing = build_total_export_batch_review_bundles(
            batch_source_file=str(root / "missing.txt"),
            base_folder=str(root / "missing_output"),
        )
        assert missing.row_count == 0
        assert missing.success_count == 0
        assert missing.failed_count == 0
        assert missing.errors

        repeated = build_total_export_batch_review_bundles(
            batch_source_file=str(batch_file),
            base_folder=str(output_folder),
            selected_capture_options=["comments"],
            create_asset_folders=False,
        )
        assert repeated.row_count == 3
        assert repeated.success_count == 0
        assert repeated.failed_count == 3
        assert any(item.errors for item in repeated.items)

        overwritten = build_total_export_batch_review_bundles(
            batch_source_file=str(batch_file),
            base_folder=str(output_folder),
            selected_capture_options=["comments"],
            create_asset_folders=False,
            overwrite_zip=True,
            overwrite_sidecars=True,
        )
        assert overwritten.success_count == 3
        assert overwritten.failed_count == 0

        stop_folder = root / "stop_output"
        initial_stop = build_total_export_batch_review_bundles(
            batch_source_file=str(batch_file),
            base_folder=str(stop_folder),
            selected_capture_options=["comments"],
            create_asset_folders=False,
        )
        assert initial_stop.success_count == 3
        stopped = build_total_export_batch_review_bundles(
            batch_source_file=str(batch_file),
            base_folder=str(stop_folder),
            selected_capture_options=["comments"],
            create_asset_folders=False,
            continue_on_error=False,
        )
        assert len(stopped.items) == 1
        assert stopped.failed_count == 1
        assert stopped.warnings

        report_folder = root / "report_output"
        report = build_total_export_batch_review_bundles(
            batch_source_file=str(batch_file),
            base_folder=str(report_folder),
            selected_capture_options=["comments"],
            create_asset_folders=False,
            write_folder_report=True,
        )
        assert report.folder_verification_report_written is True
        assert Path(report.folder_verification_report_path).is_file()
        report_json = json.loads(
            Path(report.folder_verification_report_path).read_text(encoding="utf-8")
        )
        assert report_json["zip_count"] == 3

        entries_folder = root / "entries_output"
        entries = build_total_export_batch_review_bundles(
            batch_source_file=str(batch_file),
            base_folder=str(entries_folder),
            selected_capture_options=["comments"],
            create_asset_folders=False,
            include_zip_entries=True,
            hash_zip_entries=True,
        )
        assert entries.success_count == 3
        assert entries.folder_verification_verified_count == 3

        unsupported_file = root / "unsupported.txt"
        _write_batch(
            unsupported_file,
            ["https://example.com/article\tunsupported package\tUnsupported Title"],
        )
        unsupported = build_total_export_batch_review_bundles(
            batch_source_file=str(unsupported_file),
            base_folder=str(root / "unsupported_output"),
            selected_capture_options=["comments"],
            create_asset_folders=False,
        )
        assert unsupported.row_count == 1
        assert unsupported.success_count == 1
        assert unsupported.failed_count == 0
        assert "No source adapter supports the URL: https://example.com/article" in unsupported.items[0].warnings


if __name__ == "__main__":
    run_self_test()
    print("Total Export batch review bundle self-test passed.")
