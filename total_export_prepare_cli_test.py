from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from total_export_manifest import read_manifest_json
from total_export_prepare_cli import main


VALID_ID = "aB3_dE-9xYz"
CANONICAL_URL = f"https://www.youtube.com/watch?v={VALID_ID}"


def _run_cli(argv: list[str]) -> tuple[int, str]:
    output = StringIO()
    with redirect_stdout(output):
        exit_code = main(argv)
    return exit_code, output.getvalue()


def _run_cli_error(argv: list[str]) -> tuple[int, str]:
    output = StringIO()
    try:
        with redirect_stderr(output):
            main(argv)
    except SystemExit as exc:
        return int(exc.code), output.getvalue()
    raise AssertionError("Expected argparse SystemExit.")


def _manifest_path_from_output(output: str) -> str:
    for line in output.splitlines():
        if line.startswith("Manifest path: "):
            return line.split(": ", 1)[1]
    raise AssertionError("Manifest path was not printed.")


def _summary_path_from_output(output: str) -> str:
    for line in output.splitlines():
        if line.startswith("Summary path: "):
            return line.split(": ", 1)[1]
    raise AssertionError("Summary path was not printed.")


def _inventory_report_path_from_output(output: str) -> str:
    for line in output.splitlines():
        if line.startswith("Inventory report path: "):
            return line.split(": ", 1)[1]
    raise AssertionError("Inventory report path was not printed.")


def run_self_test() -> None:
    with TemporaryDirectory() as temp_dir:
        exit_code, list_output = _run_cli(["--list-capture-options"])
        assert exit_code == 0
        assert "Capture options:" in list_output
        assert "- comments:" in list_output
        assert "- archive_check:" in list_output
        assert list(Path(temp_dir).iterdir()) == []

        exit_code, list_json_output = _run_cli(["--list-capture-options", "--json"])
        assert exit_code == 0
        parsed_options = json.loads(list_json_output)
        assert set(parsed_options) == {"capture_options"}
        assert isinstance(parsed_options["capture_options"], list)
        option_ids = {option["id"] for option in parsed_options["capture_options"]}
        assert "comments" in option_ids
        assert "archive_check" in option_ids
        comments_option = next(
            option for option in parsed_options["capture_options"] if option["id"] == "comments"
        )
        assert comments_option["label"] == "Comments"
        assert comments_option["description"]
        assert "package_folder" not in parsed_options
        assert list(Path(temp_dir).iterdir()) == []

        error_code, missing_both_error = _run_cli_error([])
        assert error_code == 2
        assert "--base-folder is required unless --list-capture-options is used" in missing_both_error

        error_code, missing_source_error = _run_cli_error(["--base-folder", temp_dir])
        assert error_code == 2
        assert "--source-url is required unless --list-capture-options is used" in missing_source_error

        exit_code, output = _run_cli(
            [
                "--base-folder",
                temp_dir,
                "--source-url",
                f"https://www.youtube.com/watch?v={VALID_ID}&t=30s",
                "--source-label",
                "YouTube clip",
                "--title",
                "Clip Title",
                "--package-id",
                "cli package",
                "--capture-option",
                "comments",
                "--capture-option",
                "archive_check",
                "--capture-option",
                "comments",
                "--capture-option",
                "unknown_option",
                "--term",
                "Caltheris",
                "--no-create-asset-folders",
            ]
        )
        assert exit_code == 0
        assert "Package folder: " in output
        assert "Manifest path: " in output
        assert "Summary path: " in output
        assert "Plan status: ready" in output
        assert "Registered summary: yes" in output
        assert "README path: " not in output
        assert "Inventory report path: " not in output
        assert "Final validation: ok" in output
        assert "Inventory:" not in output
        assert "Unknown capture options ignored: unknown_option" in output
        assert "Duplicate capture options ignored: comments" in output

        manifest_path = _manifest_path_from_output(output)
        summary_path = _summary_path_from_output(output)
        assert Path(summary_path).is_file()
        manifest = read_manifest_json(manifest_path)
        assert manifest.source_urls == [CANONICAL_URL]
        assert manifest.capture_options == ["comments", "archive_check"]
        assert len(manifest.assets) == 1

        exit_code, no_register_output = _run_cli(
            [
                "--base-folder",
                temp_dir,
                "--source-url",
                f"https://www.youtube.com/watch?v={VALID_ID}",
                "--package-id",
                "cli no register",
                "--capture-option",
                "comments",
                "--no-register-summary",
                "--no-create-asset-folders",
            ]
        )
        assert exit_code == 0
        assert "Registered summary: no" in no_register_output
        no_register_manifest = read_manifest_json(_manifest_path_from_output(no_register_output))
        assert no_register_manifest.assets == []
        assert Path(_summary_path_from_output(no_register_output)).is_file()

        exit_code, no_final_output = _run_cli(
            [
                "--base-folder",
                temp_dir,
                "--source-url",
                f"https://www.youtube.com/watch?v={VALID_ID}",
                "--package-id",
                "cli no final",
                "--capture-option",
                "comments",
                "--no-final-validation",
                "--no-create-asset-folders",
            ]
        )
        assert exit_code == 0
        assert "Final validation: skipped" in no_final_output

        exit_code, inventory_output = _run_cli(
            [
                "--base-folder",
                temp_dir,
                "--source-url",
                f"https://www.youtube.com/watch?v={VALID_ID}",
                "--package-id",
                "cli inventory",
                "--capture-option",
                "comments",
                "--include-inventory",
                "--no-create-asset-folders",
            ]
        )
        assert exit_code == 0
        assert "Inventory:" in inventory_output
        assert "Registered asset count: 1" in inventory_output
        assert "Local file count: 2" in inventory_output
        assert "Unregistered files:" in inventory_output
        assert "_manifest.json" in inventory_output or "manifest.json" in inventory_output
        assert "Missing registered assets:" in inventory_output

        exit_code, unsupported_output = _run_cli(
            [
                "--base-folder",
                temp_dir,
                "--source-url",
                "https://example.com/article",
                "--package-id",
                "cli unsupported",
                "--capture-option",
                "comments",
                "--no-create-asset-folders",
            ]
        )
        assert exit_code == 0
        assert "Plan status: unsupported_source" in unsupported_output
        assert "No source adapter supports the URL: https://example.com/article" in unsupported_output
        assert Path(_summary_path_from_output(unsupported_output)).is_file()

        exit_code, readme_output = _run_cli(
            [
                "--base-folder",
                temp_dir,
                "--source-url",
                f"https://www.youtube.com/watch?v={VALID_ID}",
                "--package-id",
                "cli readme",
                "--capture-option",
                "comments",
                "--write-readme",
                "--no-create-asset-folders",
            ]
        )
        assert exit_code == 0
        assert "README path: " in readme_output
        assert "Registered README: yes" in readme_output
        readme_manifest = read_manifest_json(_manifest_path_from_output(readme_output))
        assert len(readme_manifest.assets) == 2

        exit_code, readme_no_register_output = _run_cli(
            [
                "--base-folder",
                temp_dir,
                "--source-url",
                f"https://www.youtube.com/watch?v={VALID_ID}",
                "--package-id",
                "cli readme no register",
                "--capture-option",
                "comments",
                "--write-readme",
                "--no-register-readme",
                "--no-create-asset-folders",
            ]
        )
        assert exit_code == 0
        assert "README path: " in readme_no_register_output
        assert "Registered README: no" in readme_no_register_output
        readme_no_register_manifest = read_manifest_json(_manifest_path_from_output(readme_no_register_output))
        assert len(readme_no_register_manifest.assets) == 1

        exit_code, inventory_report_output = _run_cli(
            [
                "--base-folder",
                temp_dir,
                "--source-url",
                f"https://www.youtube.com/watch?v={VALID_ID}",
                "--package-id",
                "cli inventory report",
                "--capture-option",
                "comments",
                "--write-inventory-report",
                "--include-inventory",
                "--no-create-asset-folders",
            ]
        )
        assert exit_code == 0
        assert "Inventory report path: " in inventory_report_output
        assert "Registered inventory report: yes" in inventory_report_output
        assert "Inventory:" in inventory_report_output
        assert "Registered asset count: 2" in inventory_report_output
        assert "Local file count: 3" in inventory_report_output
        assert Path(_inventory_report_path_from_output(inventory_report_output)).is_file()
        inventory_report_manifest = read_manifest_json(_manifest_path_from_output(inventory_report_output))
        assert len(inventory_report_manifest.assets) == 2

        exit_code, inventory_report_no_register_output = _run_cli(
            [
                "--base-folder",
                temp_dir,
                "--source-url",
                f"https://www.youtube.com/watch?v={VALID_ID}",
                "--package-id",
                "cli inventory report no register",
                "--capture-option",
                "comments",
                "--write-inventory-report",
                "--no-register-inventory-report",
                "--no-create-asset-folders",
            ]
        )
        assert exit_code == 0
        assert "Inventory report path: " in inventory_report_no_register_output
        assert "Registered inventory report: no" in inventory_report_no_register_output
        assert Path(_inventory_report_path_from_output(inventory_report_no_register_output)).is_file()
        inventory_report_no_register_manifest = read_manifest_json(
            _manifest_path_from_output(inventory_report_no_register_output)
        )
        assert len(inventory_report_no_register_manifest.assets) == 1

        exit_code, review_files_output = _run_cli(
            [
                "--base-folder",
                temp_dir,
                "--source-url",
                f"https://www.youtube.com/watch?v={VALID_ID}",
                "--package-id",
                "cli review files",
                "--capture-option",
                "comments",
                "--review-files",
                "--no-create-asset-folders",
            ]
        )
        assert exit_code == 0
        assert "README path: " in review_files_output
        assert "Registered README: yes" in review_files_output
        assert "Inventory report path: " in review_files_output
        assert "Registered inventory report: yes" in review_files_output
        assert "Inventory:" in review_files_output
        assert "Registered asset count: 3" in review_files_output
        assert "Local file count: 4" in review_files_output
        review_files_manifest = read_manifest_json(_manifest_path_from_output(review_files_output))
        assert len(review_files_manifest.assets) == 3
        assert Path(_inventory_report_path_from_output(review_files_output)).is_file()

        exit_code, review_files_no_register_output = _run_cli(
            [
                "--base-folder",
                temp_dir,
                "--source-url",
                f"https://www.youtube.com/watch?v={VALID_ID}",
                "--package-id",
                "cli review files no register",
                "--capture-option",
                "comments",
                "--review-files",
                "--no-register-readme",
                "--no-register-inventory-report",
                "--no-create-asset-folders",
            ]
        )
        assert exit_code == 0
        assert "README path: " in review_files_no_register_output
        assert "Registered README: no" in review_files_no_register_output
        assert "Inventory report path: " in review_files_no_register_output
        assert "Registered inventory report: no" in review_files_no_register_output
        assert "Inventory:" in review_files_no_register_output
        assert "Registered asset count: 1" in review_files_no_register_output
        review_files_no_register_manifest = read_manifest_json(
            _manifest_path_from_output(review_files_no_register_output)
        )
        assert len(review_files_no_register_manifest.assets) == 1
        assert Path(_inventory_report_path_from_output(review_files_no_register_output)).is_file()

        exit_code, json_output = _run_cli(
            [
                "--base-folder",
                temp_dir,
                "--source-url",
                f"https://www.youtube.com/watch?v={VALID_ID}&t=30s",
                "--package-id",
                "cli json",
                "--capture-option",
                "comments",
                "--capture-option",
                "archive_check",
                "--capture-option",
                "comments",
                "--capture-option",
                "unknown_option",
                "--no-create-asset-folders",
                "--json",
            ]
        )
        assert exit_code == 0
        parsed = json.loads(json_output)
        assert set(parsed) == {
            "duplicate_capture_options",
            "final_validation_errors",
            "final_validation_issue_count",
            "final_validation_ran",
            "final_validation_warnings",
            "inventory_local_file_count",
            "inventory_missing_registered_assets",
            "inventory_ran",
            "inventory_registered_asset_count",
            "inventory_unregistered_files",
            "inventory_report_path",
            "manifest_path",
            "normalized_url",
            "package_folder",
            "plan_status",
            "readme_path",
            "registered_inventory_report",
            "registered_readme",
            "registered_summary",
            "selected_capture_options",
            "source_url",
            "summary_path",
            "unknown_capture_options",
            "warnings",
        }
        assert parsed["plan_status"] == "ready"
        assert parsed["normalized_url"] == CANONICAL_URL
        assert parsed["readme_path"] == ""
        assert parsed["registered_readme"] is False
        assert parsed["final_validation_ran"] is True
        assert parsed["final_validation_issue_count"] == 0
        assert parsed["final_validation_errors"] == []
        assert parsed["final_validation_warnings"] == []
        assert parsed["inventory_ran"] is False
        assert parsed["inventory_registered_asset_count"] == 0
        assert parsed["inventory_local_file_count"] == 0
        assert parsed["inventory_unregistered_files"] == []
        assert parsed["inventory_missing_registered_assets"] == []
        assert parsed["inventory_report_path"] == ""
        assert parsed["registered_inventory_report"] is False
        assert parsed["registered_summary"] is True
        assert parsed["selected_capture_options"] == ["comments", "archive_check"]
        assert parsed["unknown_capture_options"] == ["unknown_option"]
        assert parsed["duplicate_capture_options"] == ["comments"]
        assert parsed["warnings"] == [
            "Unknown capture options ignored: unknown_option",
            "Duplicate capture options ignored: comments",
        ]
        assert Path(parsed["summary_path"]).is_file()

        exit_code, json_no_register_output = _run_cli(
            [
                "--base-folder",
                temp_dir,
                "--source-url",
                f"https://www.youtube.com/watch?v={VALID_ID}",
                "--package-id",
                "cli json no register",
                "--capture-option",
                "comments",
                "--no-register-summary",
                "--no-create-asset-folders",
                "--json",
            ]
        )
        assert exit_code == 0
        parsed_no_register = json.loads(json_no_register_output)
        assert parsed_no_register["registered_summary"] is False
        assert parsed_no_register["readme_path"] == ""
        assert parsed_no_register["registered_readme"] is False
        assert parsed_no_register["final_validation_ran"] is True
        assert parsed_no_register["final_validation_issue_count"] == 0
        json_no_register_manifest = read_manifest_json(parsed_no_register["manifest_path"])
        assert json_no_register_manifest.assets == []

        exit_code, json_no_final_output = _run_cli(
            [
                "--base-folder",
                temp_dir,
                "--source-url",
                f"https://www.youtube.com/watch?v={VALID_ID}",
                "--package-id",
                "cli json no final",
                "--capture-option",
                "comments",
                "--no-final-validation",
                "--json",
            ]
        )
        assert exit_code == 0
        parsed_no_final = json.loads(json_no_final_output)
        assert parsed_no_final["final_validation_ran"] is False
        assert parsed_no_final["final_validation_issue_count"] == 0
        assert parsed_no_final["final_validation_errors"] == []
        assert parsed_no_final["final_validation_warnings"] == []

        exit_code, json_inventory_output = _run_cli(
            [
                "--base-folder",
                temp_dir,
                "--source-url",
                f"https://www.youtube.com/watch?v={VALID_ID}",
                "--package-id",
                "cli json inventory",
                "--capture-option",
                "comments",
                "--include-inventory",
                "--json",
            ]
        )
        assert exit_code == 0
        parsed_inventory = json.loads(json_inventory_output)
        assert parsed_inventory["inventory_ran"] is True
        assert parsed_inventory["inventory_registered_asset_count"] == 1
        assert parsed_inventory["inventory_local_file_count"] >= 2
        assert any(
            path.endswith("_manifest.json") or path == "manifest.json"
            for path in parsed_inventory["inventory_unregistered_files"]
        )
        assert parsed_inventory["inventory_missing_registered_assets"] == []

        exit_code, json_readme_output = _run_cli(
            [
                "--base-folder",
                temp_dir,
                "--source-url",
                f"https://www.youtube.com/watch?v={VALID_ID}",
                "--package-id",
                "cli json readme",
                "--capture-option",
                "comments",
                "--write-readme",
                "--include-inventory",
                "--json",
            ]
        )
        assert exit_code == 0
        parsed_readme = json.loads(json_readme_output)
        assert parsed_readme["readme_path"]
        assert parsed_readme["registered_readme"] is True
        assert parsed_readme["final_validation_ran"] is True
        assert parsed_readme["final_validation_issue_count"] == 0
        assert parsed_readme["inventory_ran"] is True
        assert parsed_readme["inventory_registered_asset_count"] == 2
        assert Path(parsed_readme["readme_path"]).is_file()
        json_readme_manifest = read_manifest_json(parsed_readme["manifest_path"])
        assert len(json_readme_manifest.assets) == 2

        exit_code, json_readme_no_register_output = _run_cli(
            [
                "--base-folder",
                temp_dir,
                "--source-url",
                f"https://www.youtube.com/watch?v={VALID_ID}",
                "--package-id",
                "cli json readme no register",
                "--capture-option",
                "comments",
                "--write-readme",
                "--no-register-readme",
                "--json",
            ]
        )
        assert exit_code == 0
        parsed_readme_no_register = json.loads(json_readme_no_register_output)
        assert parsed_readme_no_register["readme_path"]
        assert parsed_readme_no_register["registered_readme"] is False
        json_readme_no_register_manifest = read_manifest_json(parsed_readme_no_register["manifest_path"])
        assert len(json_readme_no_register_manifest.assets) == 1

        exit_code, json_inventory_report_output = _run_cli(
            [
                "--base-folder",
                temp_dir,
                "--source-url",
                f"https://www.youtube.com/watch?v={VALID_ID}",
                "--package-id",
                "cli json inventory report",
                "--capture-option",
                "comments",
                "--write-inventory-report",
                "--include-inventory",
                "--json",
            ]
        )
        assert exit_code == 0
        parsed_inventory_report = json.loads(json_inventory_report_output)
        assert parsed_inventory_report["inventory_report_path"]
        assert parsed_inventory_report["registered_inventory_report"] is True
        assert parsed_inventory_report["inventory_ran"] is True
        assert parsed_inventory_report["inventory_registered_asset_count"] == 2
        assert parsed_inventory_report["inventory_local_file_count"] >= 3
        assert Path(parsed_inventory_report["inventory_report_path"]).is_file()
        json_inventory_report_manifest = read_manifest_json(
            parsed_inventory_report["manifest_path"]
        )
        assert len(json_inventory_report_manifest.assets) == 2

        exit_code, json_inventory_report_no_register_output = _run_cli(
            [
                "--base-folder",
                temp_dir,
                "--source-url",
                f"https://www.youtube.com/watch?v={VALID_ID}",
                "--package-id",
                "cli json inventory report no register",
                "--capture-option",
                "comments",
                "--write-inventory-report",
                "--no-register-inventory-report",
                "--json",
            ]
        )
        assert exit_code == 0
        parsed_inventory_report_no_register = json.loads(json_inventory_report_no_register_output)
        assert parsed_inventory_report_no_register["inventory_report_path"]
        assert parsed_inventory_report_no_register["registered_inventory_report"] is False
        json_inventory_report_no_register_manifest = read_manifest_json(
            parsed_inventory_report_no_register["manifest_path"]
        )
        assert len(json_inventory_report_no_register_manifest.assets) == 1

        exit_code, json_review_files_output = _run_cli(
            [
                "--base-folder",
                temp_dir,
                "--source-url",
                f"https://www.youtube.com/watch?v={VALID_ID}",
                "--package-id",
                "cli json review files",
                "--capture-option",
                "comments",
                "--review-files",
                "--json",
            ]
        )
        assert exit_code == 0
        parsed_review_files = json.loads(json_review_files_output)
        assert parsed_review_files["readme_path"]
        assert parsed_review_files["registered_readme"] is True
        assert parsed_review_files["inventory_report_path"]
        assert parsed_review_files["registered_inventory_report"] is True
        assert parsed_review_files["inventory_ran"] is True
        assert parsed_review_files["inventory_registered_asset_count"] == 3
        assert parsed_review_files["inventory_local_file_count"] >= 4
        json_review_files_manifest = read_manifest_json(parsed_review_files["manifest_path"])
        assert len(json_review_files_manifest.assets) == 3

        exit_code, json_unsupported_output = _run_cli(
            [
                "--base-folder",
                temp_dir,
                "--source-url",
                "https://example.com/article",
                "--package-id",
                "cli json unsupported",
                "--capture-option",
                "comments",
                "--write-readme",
                "--write-inventory-report",
                "--include-inventory",
                "--no-create-asset-folders",
                "--json",
            ]
        )
        assert exit_code == 0
        parsed_unsupported = json.loads(json_unsupported_output)
        assert parsed_unsupported["plan_status"] == "unsupported_source"
        assert parsed_unsupported["source_url"] == "https://example.com/article"
        assert parsed_unsupported["normalized_url"] == ""
        assert parsed_unsupported["readme_path"]
        assert parsed_unsupported["registered_readme"] is True
        assert parsed_unsupported["inventory_report_path"]
        assert parsed_unsupported["registered_inventory_report"] is True
        assert parsed_unsupported["final_validation_ran"] is True
        assert parsed_unsupported["final_validation_issue_count"] == 0
        assert parsed_unsupported["inventory_ran"] is True
        assert parsed_unsupported["inventory_registered_asset_count"] == 3
        assert parsed_unsupported["warnings"] == [
            "No source adapter supports the URL: https://example.com/article",
        ]


if __name__ == "__main__":
    run_self_test()
    print("Total Export prepare CLI self-test passed.")
