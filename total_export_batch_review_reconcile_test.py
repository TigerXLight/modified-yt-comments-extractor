from pathlib import Path
from tempfile import TemporaryDirectory
import json

from total_export_batch_review_reconcile import (
    BATCH_RECONCILE_STATUS_ERROR,
    BATCH_RECONCILE_STATUS_MISSING_SIDECARS,
    BATCH_RECONCILE_STATUS_MISSING_ZIP,
    BATCH_RECONCILE_STATUS_VERIFY_PASSED,
    TotalExportBatchReviewReconcileResult,
    batch_review_reconcile_to_dict,
    build_total_export_batch_review_reconcile,
    build_total_export_batch_review_reconcile_text,
    write_total_export_batch_review_reconcile_report,
)
from total_export_review_bundle import build_total_export_review_bundle


VALID_ID = "aB3_dE-9xYz"
CANONICAL_URL = f"https://www.youtube.com/watch?v={VALID_ID}"


def _write_batch(path: Path, rows: list[str]) -> None:
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")


def _assert_single_item_status(
    result: TotalExportBatchReviewReconcileResult,
    expected_status: str,
) -> None:
    assert result.row_count == 1
    assert len(result.items) == 1
    assert result.items[0].status == expected_status


def run_self_test() -> None:
    with TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)

        missing = build_total_export_batch_review_reconcile(
            batch_source_file=str(root / "missing.txt"),
            base_folder=str(root / "missing_output"),
        )
        assert missing.row_count == 0
        assert missing.error_count == 1
        assert missing.errors

        batch_file = root / "sources.txt"
        output_folder = root / "batch_output"
        _write_batch(batch_file, [f"{CANONICAL_URL}\treconcile package"])
        no_outputs = build_total_export_batch_review_reconcile(
            batch_source_file=str(batch_file),
            base_folder=str(output_folder),
            selected_capture_options=["comments"],
        )
        _assert_single_item_status(no_outputs, BATCH_RECONCILE_STATUS_MISSING_ZIP)
        assert no_outputs.missing_zip_count == 1
        assert no_outputs.items[0].zip_exists is False
        assert output_folder.exists() is False

        duplicate_file = root / "duplicates.txt"
        _write_batch(
            duplicate_file,
            [
                f"{CANONICAL_URL}\tduplicate package",
                f"{CANONICAL_URL}\tduplicate package",
            ],
        )
        duplicates = build_total_export_batch_review_reconcile(
            batch_source_file=str(duplicate_file),
            base_folder=str(root / "duplicate_output"),
        )
        assert duplicates.duplicate_package_id_count == 2
        assert duplicates.warning_count == 2
        assert all(item.duplicate_package_id for item in duplicates.items)

        empty_file = root / "empty.txt"
        _write_batch(empty_file, ["\tempty package"])
        empty = build_total_export_batch_review_reconcile(
            batch_source_file=str(empty_file),
            base_folder=str(root / "empty_output"),
        )
        _assert_single_item_status(empty, BATCH_RECONCILE_STATUS_ERROR)
        assert empty.error_count == 1

        unsupported_file = root / "unsupported.txt"
        _write_batch(unsupported_file, ["https://example.com/article\tunsupported package"])
        unsupported = build_total_export_batch_review_reconcile(
            batch_source_file=str(unsupported_file),
            base_folder=str(root / "unsupported_output"),
        )
        assert unsupported.row_count == 1
        assert unsupported.warning_count == 1
        assert unsupported.items[0].source_supported is False
        assert "No source adapter supports the URL: https://example.com/article" in unsupported.items[0].warnings

        built_file = root / "built.txt"
        built_output = root / "built_output"
        _write_batch(built_file, [f"{CANONICAL_URL}\tbuilt package"])
        bundle = build_total_export_review_bundle(
            base_folder=str(built_output),
            source_url=CANONICAL_URL,
            package_id="built package",
            selected_capture_options=["comments"],
            create_asset_folders=False,
        )
        built = build_total_export_batch_review_reconcile(
            batch_source_file=str(built_file),
            base_folder=str(built_output),
            selected_capture_options=["comments"],
        )
        _assert_single_item_status(built, BATCH_RECONCILE_STATUS_VERIFY_PASSED)
        assert built.complete_count == 1
        assert built.verification_passed_count == 1
        assert built.items[0].verification_status == "verified"
        assert built.items[0].verification
        assert built.items[0].zip_path == bundle.zip_path

        missing_sidecar_file = root / "missing_sidecar.txt"
        missing_sidecar_output = root / "missing_sidecar_output"
        _write_batch(missing_sidecar_file, [f"{CANONICAL_URL}\tmissing sidecar package"])
        missing_sidecar_bundle = build_total_export_review_bundle(
            base_folder=str(missing_sidecar_output),
            source_url=CANONICAL_URL,
            package_id="missing sidecar package",
            selected_capture_options=["comments"],
            create_asset_folders=False,
        )
        Path(missing_sidecar_bundle.zip_sidecar_sha256_path).unlink()
        missing_sidecar = build_total_export_batch_review_reconcile(
            batch_source_file=str(missing_sidecar_file),
            base_folder=str(missing_sidecar_output),
        )
        _assert_single_item_status(
            missing_sidecar,
            BATCH_RECONCILE_STATUS_MISSING_SIDECARS,
        )
        assert missing_sidecar.missing_sidecar_count == 1
        assert missing_sidecar.items[0].zip_exists is True
        assert missing_sidecar.items[0].sha256_sidecar_exists is False

        as_dict = batch_review_reconcile_to_dict(built)
        assert set(as_dict) == {
            "base_folder",
            "batch_source_file",
            "complete_count",
            "duplicate_package_id_count",
            "error_count",
            "errors",
            "items",
            "missing_sidecar_count",
            "missing_zip_count",
            "report_path",
            "report_written",
            "row_count",
            "verification_failed_count",
            "verification_passed_count",
            "warning_count",
            "warnings",
        }
        assert as_dict["items"][0]["status"] == BATCH_RECONCILE_STATUS_VERIFY_PASSED

        text = build_total_export_batch_review_reconcile_text(built)
        assert "Total Export batch review reconciliation" in text
        assert "Row count: 1" in text
        assert "Verification passed count: 1" in text
        assert "status=verify_passed" in text

        report_path = root / "reconcile_report.json"
        report = write_total_export_batch_review_reconcile_report(
            built,
            report_path=str(report_path),
        )
        assert report.report_written is True
        assert report_path.is_file()
        parsed_report = json.loads(report_path.read_text(encoding="utf-8"))
        assert parsed_report["verification_passed_count"] == 1

        blocked_report = write_total_export_batch_review_reconcile_report(
            built,
            report_path=str(report_path),
        )
        assert blocked_report.report_written is False
        assert blocked_report.error_count == built.error_count + 1
        assert "already exists" in blocked_report.errors[-1]

        overwritten_report = write_total_export_batch_review_reconcile_report(
            built,
            report_path=str(report_path),
            overwrite=True,
        )
        assert overwritten_report.report_written is True


if __name__ == "__main__":
    run_self_test()
    print("Total Export batch review reconcile self-test passed.")
