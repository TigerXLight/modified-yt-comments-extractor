from pathlib import Path
from tempfile import TemporaryDirectory

from total_export_batch_review_plan import (
    batch_review_plan_to_dict,
    build_total_export_batch_review_plan,
    build_total_export_batch_review_plan_text,
)


VALID_ID = "aB3_dE-9xYz"
CANONICAL_URL = f"https://www.youtube.com/watch?v={VALID_ID}"


def _write_batch(path: Path, rows: list[str]) -> None:
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")


def run_self_test() -> None:
    with TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        batch_file = root / "sources.txt"
        output_folder = root / "batch_plan_output"
        _write_batch(
            batch_file,
            [
                "# local batch review plan self-test",
                "",
                f"https://www.youtube.com/watch?v={VALID_ID}",
                f"https://www.youtube.com/watch?v={VALID_ID}\tplan package two",
                f"https://www.youtube.com/watch?v={VALID_ID}\tplan package three\tClip Title",
            ],
        )

        plan = build_total_export_batch_review_plan(
            batch_source_file=str(batch_file),
            base_folder=str(output_folder),
            selected_capture_options=["comments"],
        )
        assert plan.row_count == 3
        assert plan.ready_count == 3
        assert plan.error_count == 0
        assert plan.items[0].package_id.startswith("batch_line_3_")
        assert plan.items[1].package_id == "plan package two"
        assert plan.items[2].title == "Clip Title"
        assert plan.items[0].normalized_url == CANONICAL_URL
        assert plan.items[0].zip_path.endswith(".zip")
        assert plan.items[0].sha256_sidecar_path.endswith(".zip.sha256")
        assert plan.items[0].inspection_json_path.endswith(".zip.inspection.json")
        assert output_folder.exists() is False

        text = build_total_export_batch_review_plan_text(plan)
        assert "Total Export batch review plan" in text
        assert "Row count: 3" in text
        assert "Ready count: 3" in text

        as_dict = batch_review_plan_to_dict(plan)
        assert set(as_dict) == {
            "base_folder",
            "batch_source_file",
            "duplicate_package_id_count",
            "error_count",
            "errors",
            "existing_zip_count",
            "items",
            "ready_count",
            "row_count",
            "warning_count",
            "warnings",
        }
        assert len(as_dict["items"]) == 3

        missing = build_total_export_batch_review_plan(
            batch_source_file=str(root / "missing.txt"),
            base_folder=str(root / "missing_output"),
        )
        assert missing.row_count == 0
        assert missing.error_count == 1
        assert missing.errors

        duplicate_file = root / "duplicates.txt"
        _write_batch(
            duplicate_file,
            [
                f"https://www.youtube.com/watch?v={VALID_ID}\tduplicate package",
                f"https://www.youtube.com/watch?v={VALID_ID}\tduplicate package",
            ],
        )
        duplicates = build_total_export_batch_review_plan(
            batch_source_file=str(duplicate_file),
            base_folder=str(root / "duplicate_output"),
        )
        assert duplicates.row_count == 2
        assert duplicates.duplicate_package_id_count == 2
        assert all(item.duplicate_package_id for item in duplicates.items)
        assert duplicates.warning_count == 2

        empty_file = root / "empty_source.txt"
        _write_batch(empty_file, ["\tempty package"])
        empty = build_total_export_batch_review_plan(
            batch_source_file=str(empty_file),
            base_folder=str(root / "empty_output"),
        )
        assert empty.row_count == 1
        assert empty.error_count == 1
        assert empty.items[0].errors

        unsupported_file = root / "unsupported.txt"
        _write_batch(unsupported_file, ["https://example.com/article\tunsupported package"])
        unsupported = build_total_export_batch_review_plan(
            batch_source_file=str(unsupported_file),
            base_folder=str(root / "unsupported_output"),
        )
        assert unsupported.row_count == 1
        assert unsupported.ready_count == 1
        assert unsupported.error_count == 0
        assert unsupported.warning_count == 1
        assert unsupported.items[0].source_supported is False
        assert "No source adapter supports the URL: https://example.com/article" in unsupported.items[0].warnings

        existing_file = root / "existing.txt"
        _write_batch(existing_file, [f"https://www.youtube.com/watch?v={VALID_ID}\texisting package"])
        existing_first = build_total_export_batch_review_plan(
            batch_source_file=str(existing_file),
            base_folder=str(root / "existing_output"),
        )
        existing_item = existing_first.items[0]
        Path(existing_item.package_folder).mkdir(parents=True)
        Path(existing_item.zip_path).parent.mkdir(parents=True, exist_ok=True)
        Path(existing_item.zip_path).write_bytes(b"dummy zip")
        Path(existing_item.sha256_sidecar_path).write_text("dummy\n", encoding="utf-8")
        Path(existing_item.inspection_json_path).write_text("{}\n", encoding="utf-8")
        existing_second = build_total_export_batch_review_plan(
            batch_source_file=str(existing_file),
            base_folder=str(root / "existing_output"),
        )
        assert existing_second.existing_zip_count == 1
        assert existing_second.items[0].existing_package_folder is True
        assert existing_second.items[0].existing_zip is True
        assert existing_second.items[0].existing_sha256_sidecar is True
        assert existing_second.items[0].existing_inspection_json_sidecar is True
        assert existing_second.items[0].warnings


if __name__ == "__main__":
    run_self_test()
    print("Total Export batch review plan self-test passed.")
