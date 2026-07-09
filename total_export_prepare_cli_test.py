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


def _package_folder_from_output(output: str) -> str:
    for line in output.splitlines():
        if line.startswith("Package folder: "):
            return line.split(": ", 1)[1]
    raise AssertionError("Package folder was not printed.")


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


def _plan_report_path_from_output(output: str) -> str:
    for line in output.splitlines():
        if line.startswith("Plan report path: "):
            return line.split(": ", 1)[1]
    raise AssertionError("Plan report path was not printed.")


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

        exit_code, list_with_write_flags_output = _run_cli(
            ["--list-capture-options", "--write-plan-report", "--full-review-files"]
        )
        assert exit_code == 0
        assert "Capture options:" in list_with_write_flags_output
        assert list(Path(temp_dir).iterdir()) == []

        exit_code, source_adapter_output = _run_cli(["--list-source-adapters"])
        assert exit_code == 0
        assert "Source adapters:" in source_adapter_output
        assert "- youtube:" in source_adapter_output
        assert "YouTube" in source_adapter_output
        assert list(Path(temp_dir).iterdir()) == []

        exit_code, source_adapter_json_output = _run_cli(["--list-source-adapters", "--json"])
        assert exit_code == 0
        parsed_source_adapters = json.loads(source_adapter_json_output)
        assert set(parsed_source_adapters) == {"source_adapters"}
        assert isinstance(parsed_source_adapters["source_adapters"], list)
        youtube_adapter = next(
            adapter
            for adapter in parsed_source_adapters["source_adapters"]
            if adapter["id"] == "youtube"
        )
        assert youtube_adapter["display_name"] == "YouTube"
        assert youtube_adapter["credential_type"] == "api_key"
        assert youtube_adapter["capabilities"]["supports_comments"] is True
        assert "package_folder" not in parsed_source_adapters
        assert list(Path(temp_dir).iterdir()) == []

        exit_code, asr_provider_output = _run_cli(["--list-asr-providers"])
        assert exit_code == 0
        assert "ASR providers:" in asr_provider_output
        assert "Metadata only" in asr_provider_output
        assert "elevenlabs_scribe" in asr_provider_output
        assert list(Path(temp_dir).iterdir()) == []

        exit_code, asr_provider_json_output = _run_cli(["--list-asr-providers", "--json"])
        assert exit_code == 0
        parsed_asr_providers = json.loads(asr_provider_json_output)
        assert set(parsed_asr_providers) == {"asr_providers"}
        assert isinstance(parsed_asr_providers["asr_providers"], list)
        provider_ids = {provider["id"] for provider in parsed_asr_providers["asr_providers"]}
        assert "elevenlabs_scribe" in provider_ids
        elevenlabs = next(
            provider
            for provider in parsed_asr_providers["asr_providers"]
            if provider["id"] == "elevenlabs_scribe"
        )
        assert elevenlabs["status"] == "candidate"
        assert elevenlabs["credential_type"] == "api_key"
        assert "package_folder" not in parsed_asr_providers
        assert list(Path(temp_dir).iterdir()) == []

        exit_code, metadata_output = _run_cli(["--list-metadata"])
        assert exit_code == 0
        assert "Capture options:" in metadata_output
        assert "Source adapters:" in metadata_output
        assert "ASR providers:" in metadata_output
        assert list(Path(temp_dir).iterdir()) == []

        exit_code, metadata_json_output = _run_cli(["--list-metadata", "--json"])
        assert exit_code == 0
        parsed_metadata = json.loads(metadata_json_output)
        assert set(parsed_metadata) == {
            "asr_providers",
            "capture_options",
            "source_adapters",
        }
        assert list(Path(temp_dir).iterdir()) == []

        error_code, combined_mode_error = _run_cli_error(
            ["--list-capture-options", "--list-source-adapters"]
        )
        assert error_code == 2
        assert "Use only one list/explain mode at a time" in combined_mode_error

        error_code, metadata_combined_error = _run_cli_error(
            ["--list-metadata", "--list-source-adapters"]
        )
        assert error_code == 2
        assert "--list-metadata cannot be combined" in metadata_combined_error

        exit_code, explain_output = _run_cli(
            [
                "--explain-plan",
                "--source-url",
                f"https://www.youtube.com/watch?v={VALID_ID}&t=30s",
                "--source-label",
                "YouTube clip",
                "--title",
                "Clip Title",
                "--capture-option",
                "comments",
                "--capture-option",
                "comments",
                "--capture-option",
                "unknown_option",
                "--term",
                "Caltheris",
            ]
        )
        assert exit_code == 0
        assert "Plan:" in explain_output
        assert "Plan status: ready" in explain_output
        assert f"Normalized URL: {CANONICAL_URL}" in explain_output
        assert "Selected capture options: comments" in explain_output
        assert "Unknown capture options: unknown_option" in explain_output
        assert "Duplicate capture options: comments" in explain_output
        assert "- Caltheris" in explain_output
        assert list(Path(temp_dir).iterdir()) == []

        exit_code, explain_with_write_flags_output = _run_cli(
            [
                "--explain-plan",
                "--source-url",
                f"https://www.youtube.com/watch?v={VALID_ID}",
                "--capture-option",
                "comments",
                "--write-plan-report",
                "--full-review-files",
            ]
        )
        assert exit_code == 0
        assert "Plan:" in explain_with_write_flags_output
        assert list(Path(temp_dir).iterdir()) == []

        exit_code, explain_json_output = _run_cli(
            [
                "--explain-plan",
                "--source-url",
                f"https://www.youtube.com/watch?v={VALID_ID}&t=30s",
                "--source-label",
                "YouTube clip",
                "--title",
                "Clip Title",
                "--capture-option",
                "comments",
                "--term",
                "Caltheris",
                "--json",
            ]
        )
        assert exit_code == 0
        parsed_explain = json.loads(explain_json_output)
        assert parsed_explain["plan_status"] == "ready"
        assert parsed_explain["normalized_url"] == CANONICAL_URL
        assert parsed_explain["adapter_name"] == "youtube"
        assert parsed_explain["adapter_display_name"] == "YouTube"
        assert parsed_explain["selected_capture_options"] == ["comments"]
        assert parsed_explain["source_label"] == "YouTube clip"
        assert parsed_explain["title"] == "Clip Title"
        assert parsed_explain["user_terms"] == ["Caltheris"]
        assert "package_folder" not in parsed_explain
        assert list(Path(temp_dir).iterdir()) == []

        exit_code, explain_unsupported_output = _run_cli(
            [
                "--explain-plan",
                "--source-url",
                "https://example.com/article",
                "--capture-option",
                "comments",
            ]
        )
        assert exit_code == 0
        assert "Plan status: unsupported_source" in explain_unsupported_output
        assert "No source adapter supports the URL: https://example.com/article" in explain_unsupported_output
        assert list(Path(temp_dir).iterdir()) == []

        error_code, explain_missing_source_error = _run_cli_error(["--explain-plan"])
        assert error_code == 2
        assert "--source-url is required when --explain-plan is used" in explain_missing_source_error

        error_code, missing_both_error = _run_cli_error([])
        assert error_code == 2
        assert "--base-folder is required unless a list/explain mode is used" in missing_both_error

        error_code, missing_source_error = _run_cli_error(["--base-folder", temp_dir])
        assert error_code == 2
        assert "--source-url is required unless a list mode is used" in missing_source_error

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
        assert "Plan report path: " not in output
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

        exit_code, plan_report_output = _run_cli(
            [
                "--base-folder",
                temp_dir,
                "--source-url",
                f"https://www.youtube.com/watch?v={VALID_ID}",
                "--package-id",
                "cli plan report",
                "--capture-option",
                "comments",
                "--write-plan-report",
                "--no-create-asset-folders",
            ]
        )
        assert exit_code == 0
        assert "Plan report path: " in plan_report_output
        assert "Registered plan report: yes" in plan_report_output
        assert Path(_plan_report_path_from_output(plan_report_output)).is_file()
        plan_report_manifest = read_manifest_json(_manifest_path_from_output(plan_report_output))
        assert len(plan_report_manifest.assets) == 2

        exit_code, plan_report_no_register_output = _run_cli(
            [
                "--base-folder",
                temp_dir,
                "--source-url",
                f"https://www.youtube.com/watch?v={VALID_ID}",
                "--package-id",
                "cli plan report no register",
                "--capture-option",
                "comments",
                "--write-plan-report",
                "--no-register-plan-report",
                "--no-create-asset-folders",
            ]
        )
        assert exit_code == 0
        assert "Plan report path: " in plan_report_no_register_output
        assert "Registered plan report: no" in plan_report_no_register_output
        assert Path(_plan_report_path_from_output(plan_report_no_register_output)).is_file()
        plan_report_no_register_manifest = read_manifest_json(
            _manifest_path_from_output(plan_report_no_register_output)
        )
        assert len(plan_report_no_register_manifest.assets) == 1

        exit_code, custom_plan_report_output = _run_cli(
            [
                "--base-folder",
                temp_dir,
                "--source-url",
                f"https://www.youtube.com/watch?v={VALID_ID}",
                "--package-id",
                "cli custom plan report",
                "--capture-option",
                "comments",
                "--write-plan-report",
                "--plan-report-filename",
                "Custom Source Plan.txt",
                "--no-register-plan-report",
                "--no-create-asset-folders",
            ]
        )
        assert exit_code == 0
        assert Path(_plan_report_path_from_output(custom_plan_report_output)).name == "Custom_Source_Plan.txt"

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
        assert "Plan report path: " not in review_files_output
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

        exit_code, full_review_files_output = _run_cli(
            [
                "--base-folder",
                temp_dir,
                "--source-url",
                f"https://www.youtube.com/watch?v={VALID_ID}",
                "--package-id",
                "cli full review files",
                "--capture-option",
                "comments",
                "--full-review-files",
                "--no-create-asset-folders",
            ]
        )
        assert exit_code == 0
        assert "README path: " in full_review_files_output
        assert "Registered README: yes" in full_review_files_output
        assert "Plan report path: " in full_review_files_output
        assert "Registered plan report: yes" in full_review_files_output
        assert "Inventory report path: " in full_review_files_output
        assert "Registered inventory report: yes" in full_review_files_output
        assert "Inventory:" in full_review_files_output
        assert "Registered asset count: 4" in full_review_files_output
        assert "Local file count: 5" in full_review_files_output
        full_review_files_manifest = read_manifest_json(
            _manifest_path_from_output(full_review_files_output)
        )
        assert len(full_review_files_manifest.assets) == 4
        assert Path(_plan_report_path_from_output(full_review_files_output)).is_file()

        full_review_package_folder = _package_folder_from_output(full_review_files_output)
        full_review_manifest_path = _manifest_path_from_output(full_review_files_output)
        exit_code, inspect_output = _run_cli(
            [
                "--inspect-package",
                "--package-folder",
                full_review_package_folder,
            ]
        )
        assert exit_code == 0
        assert "Total Export package inspection" in inspect_output
        assert "Status: ok" in inspect_output
        assert "Manifest valid: yes" in inspect_output
        assert "source_plan_report: metadata/SOURCE_CAPTURE_PLAN.txt" in inspect_output
        assert "Registered assets: 4" in inspect_output

        exit_code, inspect_json_output = _run_cli(
            [
                "--inspect-package",
                "--package-folder",
                full_review_package_folder,
                "--json",
            ]
        )
        assert exit_code == 0
        parsed_inspect = json.loads(inspect_json_output)
        assert parsed_inspect["status"] == "ok"
        assert parsed_inspect["manifest_found"] is True
        assert parsed_inspect["manifest_valid"] is True
        assert parsed_inspect["inventory_ran"] is True
        assert parsed_inspect["inventory_registered_asset_count"] == 4
        assert any(
            item["relative_path"] == "metadata/SOURCE_CAPTURE_PLAN.txt"
            for item in parsed_inspect["standard_files"]
        )

        exit_code, inspect_explicit_manifest_json_output = _run_cli(
            [
                "--inspect-package",
                "--package-folder",
                full_review_package_folder,
                "--manifest-path",
                full_review_manifest_path,
                "--json",
            ]
        )
        assert exit_code == 0
        parsed_explicit_inspect = json.loads(inspect_explicit_manifest_json_output)
        assert parsed_explicit_inspect["manifest_path"] == full_review_manifest_path
        assert parsed_explicit_inspect["status"] == "ok"

        exit_code, zip_output = _run_cli(
            [
                "--zip-package",
                "--package-folder",
                full_review_package_folder,
            ]
        )
        assert exit_code == 0
        assert "Total Export package ZIP" in zip_output
        assert "ZIP created: yes" in zip_output
        assert "ZIP SHA-256: " in zip_output
        default_zip_path = Path(f"{full_review_package_folder}.zip")
        assert default_zip_path.is_file()

        exit_code, zip_json_output = _run_cli(
            [
                "--zip-package",
                "--package-folder",
                full_review_package_folder,
                "--json",
                "--overwrite-zip",
            ]
        )
        assert exit_code == 0
        parsed_zip = json.loads(zip_json_output)
        assert parsed_zip["zip_created"] is True
        assert parsed_zip["zip_path"]
        assert parsed_zip["zip_sha256"]
        assert parsed_zip["zipped_file_count"] >= 5
        assert parsed_zip["inspection_status"] == "ok"
        assert Path(parsed_zip["zip_path"]).is_file()

        custom_zip_path = str(Path(temp_dir) / "custom_cli_package.zip")
        exit_code, custom_zip_json_output = _run_cli(
            [
                "--zip-package",
                "--package-folder",
                full_review_package_folder,
                "--zip-path",
                custom_zip_path,
                "--json",
            ]
        )
        assert exit_code == 0
        parsed_custom_zip = json.loads(custom_zip_json_output)
        assert parsed_custom_zip["zip_created"] is True
        assert parsed_custom_zip["zip_path"] == custom_zip_path
        assert Path(custom_zip_path).is_file()

        exit_code, existing_zip_json_output = _run_cli(
            [
                "--zip-package",
                "--package-folder",
                full_review_package_folder,
                "--json",
            ]
        )
        assert exit_code == 0
        parsed_existing_zip = json.loads(existing_zip_json_output)
        assert parsed_existing_zip["zip_created"] is False
        assert any("already exists" in error for error in parsed_existing_zip["errors"])

        exit_code, inspect_zip_output = _run_cli(
            [
                "--inspect-zip",
                "--zip-path",
                str(default_zip_path),
            ]
        )
        assert exit_code == 0
        assert "Total Export ZIP inspection" in inspect_zip_output
        assert "Status: ok" in inspect_zip_output
        assert "_manifest.json" in inspect_zip_output

        exit_code, inspect_zip_json_output = _run_cli(
            [
                "--inspect-zip",
                "--zip-path",
                str(default_zip_path),
                "--json",
            ]
        )
        assert exit_code == 0
        parsed_inspect_zip = json.loads(inspect_zip_json_output)
        assert parsed_inspect_zip["status"] == "ok"
        assert parsed_inspect_zip["zip_found"] is True
        assert parsed_inspect_zip["zip_readable"] is True
        assert parsed_inspect_zip["zip_sha256"]
        assert any(
            entry["relative_path"] == "metadata/SOURCE_CAPTURE_PLAN.txt"
            for entry in parsed_inspect_zip["standard_entries"]
        )

        exit_code, inspect_zip_entries_json_output = _run_cli(
            [
                "--inspect-zip",
                "--zip-path",
                str(default_zip_path),
                "--include-zip-entries",
                "--json",
            ]
        )
        assert exit_code == 0
        parsed_zip_entries = json.loads(inspect_zip_entries_json_output)
        entry_names = [entry["name"] for entry in parsed_zip_entries["entries"]]
        assert entry_names
        assert entry_names == sorted(entry_names)

        exit_code, inspect_zip_hash_entries_json_output = _run_cli(
            [
                "--inspect-zip",
                "--zip-path",
                str(default_zip_path),
                "--include-zip-entries",
                "--hash-zip-entries",
                "--json",
            ]
        )
        assert exit_code == 0
        parsed_zip_hash_entries = json.loads(inspect_zip_hash_entries_json_output)
        assert any(
            entry["sha256"]
            for entry in parsed_zip_hash_entries["entries"]
            if not entry["is_dir"]
        )

        exit_code, sidecar_output = _run_cli(
            [
                "--write-zip-sidecars",
                "--zip-path",
                str(default_zip_path),
            ]
        )
        assert exit_code == 0
        assert "Total Export ZIP sidecars" in sidecar_output
        assert "SHA256 written: yes" in sidecar_output
        assert "JSON written: yes" in sidecar_output
        default_sha256_path = Path(f"{default_zip_path}.sha256")
        default_json_sidecar_path = Path(f"{default_zip_path}.inspection.json")
        assert default_sha256_path.is_file()
        assert default_json_sidecar_path.is_file()

        exit_code, sidecar_json_output = _run_cli(
            [
                "--write-zip-sidecars",
                "--zip-path",
                str(default_zip_path),
                "--json",
                "--overwrite-sidecars",
            ]
        )
        assert exit_code == 0
        parsed_sidecar = json.loads(sidecar_json_output)
        assert parsed_sidecar["sha256_written"] is True
        assert parsed_sidecar["json_written"] is True
        assert parsed_sidecar["zip_sha256"]
        assert parsed_sidecar["zip_status"] == "ok"

        custom_sha256_path = str(Path(temp_dir) / "custom_cli.sha256")
        custom_inspection_json_path = str(Path(temp_dir) / "custom_cli.inspection.json")
        exit_code, custom_sidecar_json_output = _run_cli(
            [
                "--write-zip-sidecars",
                "--zip-path",
                str(default_zip_path),
                "--zip-sha256-path",
                custom_sha256_path,
                "--zip-inspection-json-path",
                custom_inspection_json_path,
                "--json",
            ]
        )
        assert exit_code == 0
        parsed_custom_sidecar = json.loads(custom_sidecar_json_output)
        assert parsed_custom_sidecar["sha256_written"] is True
        assert parsed_custom_sidecar["json_written"] is True
        assert parsed_custom_sidecar["sha256_path"] == custom_sha256_path
        assert parsed_custom_sidecar["json_path"] == custom_inspection_json_path
        assert Path(custom_sha256_path).is_file()
        assert Path(custom_inspection_json_path).is_file()

        exit_code, existing_sidecar_json_output = _run_cli(
            [
                "--write-zip-sidecars",
                "--zip-path",
                str(default_zip_path),
                "--json",
            ]
        )
        assert exit_code == 0
        parsed_existing_sidecar = json.loads(existing_sidecar_json_output)
        assert parsed_existing_sidecar["sha256_written"] is False
        assert parsed_existing_sidecar["json_written"] is False
        assert any("already exists" in error for error in parsed_existing_sidecar["errors"])

        hashed_sidecar_json_path = str(Path(temp_dir) / "hashed_entries.inspection.json")
        exit_code, hashed_sidecar_json_output = _run_cli(
            [
                "--write-zip-sidecars",
                "--zip-path",
                str(default_zip_path),
                "--zip-sha256-path",
                str(Path(temp_dir) / "hashed_entries.sha256"),
                "--zip-inspection-json-path",
                hashed_sidecar_json_path,
                "--include-zip-entries",
                "--hash-zip-entries",
                "--json",
            ]
        )
        assert exit_code == 0
        parsed_hashed_sidecar = json.loads(hashed_sidecar_json_output)
        assert parsed_hashed_sidecar["json_written"] is True
        hashed_sidecar = json.loads(Path(hashed_sidecar_json_path).read_text(encoding="utf-8"))
        assert any(
            entry["sha256"]
            for entry in hashed_sidecar["zip_inspection"]["entries"]
            if not entry["is_dir"]
        )

        exit_code, inspect_missing_zip_json_output = _run_cli(
            [
                "--inspect-zip",
                "--zip-path",
                str(Path(temp_dir) / "missing.zip"),
                "--json",
            ]
        )
        assert exit_code == 0
        assert json.loads(inspect_missing_zip_json_output)["status"] == "missing_zip"

        exit_code, missing_sidecar_json_output = _run_cli(
            [
                "--write-zip-sidecars",
                "--zip-path",
                str(Path(temp_dir) / "missing_sidecar.zip"),
                "--json",
            ]
        )
        assert exit_code == 0
        parsed_missing_sidecar = json.loads(missing_sidecar_json_output)
        assert parsed_missing_sidecar["sha256_written"] is False
        assert parsed_missing_sidecar["json_written"] is False
        assert parsed_missing_sidecar["zip_status"] == "missing_zip"
        assert any("inspection status" in error for error in parsed_missing_sidecar["errors"])

        exit_code, bundle_output = _run_cli(
            [
                "--build-review-bundle",
                "--base-folder",
                temp_dir,
                "--source-url",
                f"https://www.youtube.com/watch?v={VALID_ID}",
                "--package-id",
                "cli review bundle",
                "--capture-option",
                "comments",
            ]
        )
        assert exit_code == 0
        assert "Total Export review bundle" in bundle_output
        assert "ZIP created: yes" in bundle_output
        assert "ZIP SHA256 sidecar written: yes" in bundle_output
        bundle_package_folder = str(Path(temp_dir) / "cli_review_bundle")
        bundle_zip_path = Path(f"{bundle_package_folder}.zip")
        assert Path(bundle_package_folder).is_dir()
        assert bundle_zip_path.is_file()
        assert Path(f"{bundle_zip_path}.sha256").is_file()
        assert Path(f"{bundle_zip_path}.inspection.json").is_file()

        exit_code, bundle_json_output = _run_cli(
            [
                "--build-review-bundle",
                "--base-folder",
                temp_dir,
                "--source-url",
                f"https://www.youtube.com/watch?v={VALID_ID}",
                "--package-id",
                "cli review bundle json",
                "--capture-option",
                "comments",
                "--json",
            ]
        )
        assert exit_code == 0
        parsed_bundle = json.loads(bundle_json_output)
        assert parsed_bundle["zip_created"] is True
        assert parsed_bundle["zip_sha256"]
        assert parsed_bundle["package_inspection_status"] == "ok"
        assert parsed_bundle["zip_inspection_status"] == "ok"
        assert parsed_bundle["zip_sidecar_sha256_written"] is True
        assert parsed_bundle["zip_sidecar_json_written"] is True
        assert Path(parsed_bundle["package_folder"]).is_dir()
        assert Path(parsed_bundle["zip_path"]).is_file()

        custom_bundle_zip_path = str(Path(temp_dir) / "custom_bundle" / "bundle.zip")
        exit_code, custom_bundle_json_output = _run_cli(
            [
                "--build-review-bundle",
                "--base-folder",
                temp_dir,
                "--source-url",
                f"https://www.youtube.com/watch?v={VALID_ID}",
                "--package-id",
                "cli review bundle custom",
                "--capture-option",
                "comments",
                "--bundle-zip-path",
                custom_bundle_zip_path,
                "--json",
            ]
        )
        assert exit_code == 0
        parsed_custom_bundle = json.loads(custom_bundle_json_output)
        assert parsed_custom_bundle["zip_created"] is True
        assert parsed_custom_bundle["zip_path"] == custom_bundle_zip_path
        assert Path(custom_bundle_zip_path).is_file()

        exit_code, no_sidecar_bundle_json_output = _run_cli(
            [
                "--build-review-bundle",
                "--base-folder",
                temp_dir,
                "--source-url",
                f"https://www.youtube.com/watch?v={VALID_ID}",
                "--package-id",
                "cli review bundle no sidecars",
                "--capture-option",
                "comments",
                "--no-bundle-sidecars",
                "--json",
            ]
        )
        assert exit_code == 0
        parsed_no_sidecar_bundle = json.loads(no_sidecar_bundle_json_output)
        assert parsed_no_sidecar_bundle["zip_created"] is True
        assert parsed_no_sidecar_bundle["zip_sidecar_sha256_written"] is False
        assert parsed_no_sidecar_bundle["zip_sidecar_json_written"] is False
        assert parsed_no_sidecar_bundle["zip_sidecar_sha256_path"] == ""
        assert parsed_no_sidecar_bundle["zip_sidecar_json_path"] == ""

        exit_code, existing_bundle_json_output = _run_cli(
            [
                "--build-review-bundle",
                "--base-folder",
                temp_dir,
                "--source-url",
                f"https://www.youtube.com/watch?v={VALID_ID}",
                "--package-id",
                "cli review bundle",
                "--capture-option",
                "comments",
                "--json",
            ]
        )
        assert exit_code == 0
        parsed_existing_bundle = json.loads(existing_bundle_json_output)
        assert parsed_existing_bundle["zip_created"] is False
        assert any("already exists" in error for error in parsed_existing_bundle["errors"])

        exit_code, overwrite_bundle_json_output = _run_cli(
            [
                "--build-review-bundle",
                "--base-folder",
                temp_dir,
                "--source-url",
                f"https://www.youtube.com/watch?v={VALID_ID}",
                "--package-id",
                "cli review bundle",
                "--capture-option",
                "comments",
                "--overwrite-bundle-zip",
                "--overwrite-sidecars",
                "--json",
            ]
        )
        assert exit_code == 0
        parsed_overwrite_bundle = json.loads(overwrite_bundle_json_output)
        assert parsed_overwrite_bundle["zip_created"] is True
        assert parsed_overwrite_bundle["zip_sidecar_sha256_written"] is True
        assert parsed_overwrite_bundle["zip_sidecar_json_written"] is True
        assert parsed_overwrite_bundle["errors"] == []

        hashed_bundle_sidecar_path = str(
            Path(temp_dir) / "cli_review_bundle_hashed.zip.inspection.json"
        )
        exit_code, hashed_bundle_json_output = _run_cli(
            [
                "--build-review-bundle",
                "--base-folder",
                temp_dir,
                "--source-url",
                f"https://www.youtube.com/watch?v={VALID_ID}",
                "--package-id",
                "cli review bundle hashed",
                "--capture-option",
                "comments",
                "--bundle-zip-path",
                str(Path(temp_dir) / "cli_review_bundle_hashed.zip"),
                "--include-zip-entries",
                "--hash-zip-entries",
                "--json",
            ]
        )
        assert exit_code == 0
        parsed_hashed_bundle = json.loads(hashed_bundle_json_output)
        assert parsed_hashed_bundle["zip_sidecar_json_written"] is True
        hashed_bundle_sidecar_path = parsed_hashed_bundle["zip_sidecar_json_path"] or hashed_bundle_sidecar_path
        hashed_bundle_sidecar = json.loads(
            Path(hashed_bundle_sidecar_path).read_text(encoding="utf-8")
        )
        assert any(
            entry["sha256"]
            for entry in hashed_bundle_sidecar["zip_inspection"]["entries"]
            if not entry["is_dir"]
        )

        exit_code, verify_bundle_output = _run_cli(
            [
                "--verify-review-bundle",
                "--zip-path",
                str(bundle_zip_path),
            ]
        )
        assert exit_code == 0
        assert "Total Export review bundle verification" in verify_bundle_output
        assert "Status: verified" in verify_bundle_output
        assert "Hash matches SHA256 sidecar: yes" in verify_bundle_output

        exit_code, verify_bundle_json_output = _run_cli(
            [
                "--verify-review-bundle",
                "--zip-path",
                str(bundle_zip_path),
                "--json",
            ]
        )
        assert exit_code == 0
        parsed_verify_bundle = json.loads(verify_bundle_json_output)
        assert parsed_verify_bundle["status"] == "verified"
        assert parsed_verify_bundle["sha256_sidecar_valid"] is True
        assert parsed_verify_bundle["inspection_json_valid"] is True
        assert parsed_verify_bundle["hash_matches_sha256_sidecar"] is True
        assert parsed_verify_bundle["hash_matches_inspection_json"] is True

        custom_verify_sha_path = Path(temp_dir) / "custom_verify.sha256"
        custom_verify_json_path = Path(temp_dir) / "custom_verify.inspection.json"
        custom_verify_sha_path.write_text(
            Path(f"{bundle_zip_path}.sha256").read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        custom_verify_json_path.write_text(
            Path(f"{bundle_zip_path}.inspection.json").read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        exit_code, custom_verify_json_output = _run_cli(
            [
                "--verify-review-bundle",
                "--zip-path",
                str(bundle_zip_path),
                "--review-bundle-sha256-path",
                str(custom_verify_sha_path),
                "--review-bundle-inspection-json-path",
                str(custom_verify_json_path),
                "--json",
            ]
        )
        assert exit_code == 0
        assert json.loads(custom_verify_json_output)["status"] == "verified"

        exit_code, verify_missing_zip_output = _run_cli(
            [
                "--verify-review-bundle",
                "--zip-path",
                str(Path(temp_dir) / "missing_review_bundle.zip"),
                "--json",
            ]
        )
        assert exit_code == 0
        assert json.loads(verify_missing_zip_output)["status"] == "missing_zip"

        tamper_bundle_json_output = _run_cli(
            [
                "--build-review-bundle",
                "--base-folder",
                temp_dir,
                "--source-url",
                f"https://www.youtube.com/watch?v={VALID_ID}",
                "--package-id",
                "cli verify tamper sha",
                "--capture-option",
                "comments",
                "--json",
            ]
        )[1]
        parsed_tamper_bundle = json.loads(tamper_bundle_json_output)
        Path(parsed_tamper_bundle["zip_sidecar_sha256_path"]).write_text(
            f"{'0' * 64}  {Path(parsed_tamper_bundle['zip_path']).name}\n",
            encoding="utf-8",
        )
        exit_code, verify_tamper_sha_output = _run_cli(
            [
                "--verify-review-bundle",
                "--zip-path",
                parsed_tamper_bundle["zip_path"],
                "--json",
            ]
        )
        assert exit_code == 0
        parsed_verify_tamper_sha = json.loads(verify_tamper_sha_output)
        assert parsed_verify_tamper_sha["status"] == "mismatch"
        assert parsed_verify_tamper_sha["hash_matches_sha256_sidecar"] is False

        tamper_json_bundle_output = _run_cli(
            [
                "--build-review-bundle",
                "--base-folder",
                temp_dir,
                "--source-url",
                f"https://www.youtube.com/watch?v={VALID_ID}",
                "--package-id",
                "cli verify tamper json",
                "--capture-option",
                "comments",
                "--json",
            ]
        )[1]
        parsed_json_tamper_bundle = json.loads(tamper_json_bundle_output)
        tampered_json = json.loads(
            Path(parsed_json_tamper_bundle["zip_sidecar_json_path"]).read_text(encoding="utf-8")
        )
        tampered_json["zip_inspection"]["zip_sha256"] = "0" * 64
        Path(parsed_json_tamper_bundle["zip_sidecar_json_path"]).write_text(
            json.dumps(tampered_json, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        exit_code, verify_tamper_json_output = _run_cli(
            [
                "--verify-review-bundle",
                "--zip-path",
                parsed_json_tamper_bundle["zip_path"],
                "--json",
            ]
        )
        assert exit_code == 0
        parsed_verify_tamper_json = json.loads(verify_tamper_json_output)
        assert parsed_verify_tamper_json["status"] == "mismatch"
        assert parsed_verify_tamper_json["hash_matches_inspection_json"] is False

        error_code, verify_missing_path_error = _run_cli_error(["--verify-review-bundle"])
        assert error_code == 2
        assert "--zip-path is required when --verify-review-bundle is used" in verify_missing_path_error

        error_code, verify_build_bundle_error = _run_cli_error(
            [
                "--verify-review-bundle",
                "--build-review-bundle",
                "--zip-path",
                str(bundle_zip_path),
                "--base-folder",
                temp_dir,
                "--source-url",
                f"https://www.youtube.com/watch?v={VALID_ID}",
            ]
        )
        assert error_code == 2
        assert "Use only one list/explain mode at a time" in verify_build_bundle_error

        error_code, verify_full_review_error = _run_cli_error(
            [
                "--verify-review-bundle",
                "--zip-path",
                str(bundle_zip_path),
                "--full-review-files",
            ]
        )
        assert error_code == 2
        assert "read-only" in verify_full_review_error

        folder_verify_dir = Path(temp_dir) / "folder_verify_cli"
        exit_code, folder_bundle_one_output = _run_cli(
            [
                "--build-review-bundle",
                "--base-folder",
                str(folder_verify_dir),
                "--source-url",
                f"https://www.youtube.com/watch?v={VALID_ID}",
                "--package-id",
                "folder cli one",
                "--capture-option",
                "comments",
                "--json",
            ]
        )
        assert exit_code == 0
        parsed_folder_bundle_one = json.loads(folder_bundle_one_output)
        exit_code, folder_bundle_two_output = _run_cli(
            [
                "--build-review-bundle",
                "--base-folder",
                str(folder_verify_dir),
                "--source-url",
                f"https://www.youtube.com/watch?v={VALID_ID}",
                "--package-id",
                "folder cli two",
                "--capture-option",
                "comments",
                "--json",
            ]
        )
        assert exit_code == 0
        parsed_folder_bundle_two = json.loads(folder_bundle_two_output)
        assert Path(parsed_folder_bundle_one["zip_path"]).is_file()
        assert Path(parsed_folder_bundle_two["zip_path"]).is_file()

        exit_code, folder_verify_output = _run_cli(
            [
                "--verify-review-bundle-folder",
                "--review-bundle-folder",
                str(folder_verify_dir),
            ]
        )
        assert exit_code == 0
        assert "Total Export review bundle folder verification" in folder_verify_output
        assert "ZIP count: 2" in folder_verify_output
        assert "Verified count: 2" in folder_verify_output

        exit_code, folder_verify_json_output = _run_cli(
            [
                "--verify-review-bundle-folder",
                "--review-bundle-folder",
                str(folder_verify_dir),
                "--json",
            ]
        )
        assert exit_code == 0
        parsed_folder_verify = json.loads(folder_verify_json_output)
        assert parsed_folder_verify["zip_count"] == 2
        assert parsed_folder_verify["verified_count"] == 2
        assert parsed_folder_verify["failed_count"] == 0

        exit_code, missing_folder_verify_json_output = _run_cli(
            [
                "--verify-review-bundle-folder",
                "--review-bundle-folder",
                str(Path(temp_dir) / "missing_folder_verify"),
                "--json",
            ]
        )
        assert exit_code == 0
        parsed_missing_folder_verify = json.loads(missing_folder_verify_json_output)
        assert parsed_missing_folder_verify["zip_count"] == 0
        assert parsed_missing_folder_verify["errors"]

        missing_sidecar_folder = Path(temp_dir) / "folder_verify_missing_sidecar"
        exit_code, missing_sidecar_bundle_output = _run_cli(
            [
                "--build-review-bundle",
                "--base-folder",
                str(missing_sidecar_folder),
                "--source-url",
                f"https://www.youtube.com/watch?v={VALID_ID}",
                "--package-id",
                "folder cli missing sidecar",
                "--capture-option",
                "comments",
                "--json",
            ]
        )
        assert exit_code == 0
        parsed_missing_sidecar_bundle = json.loads(missing_sidecar_bundle_output)
        Path(parsed_missing_sidecar_bundle["zip_sidecar_sha256_path"]).unlink()
        exit_code, missing_sidecar_folder_json_output = _run_cli(
            [
                "--verify-review-bundle-folder",
                "--review-bundle-folder",
                str(missing_sidecar_folder),
                "--json",
            ]
        )
        assert exit_code == 0
        parsed_missing_sidecar_folder = json.loads(missing_sidecar_folder_json_output)
        assert parsed_missing_sidecar_folder["missing_sidecar_count"] == 1
        assert parsed_missing_sidecar_folder["failed_count"] == 1

        recursive_folder = Path(temp_dir) / "folder_verify_recursive"
        _run_cli(
            [
                "--build-review-bundle",
                "--base-folder",
                str(recursive_folder),
                "--source-url",
                f"https://www.youtube.com/watch?v={VALID_ID}",
                "--package-id",
                "folder cli recursive direct",
                "--capture-option",
                "comments",
                "--json",
            ]
        )
        nested_recursive_folder = recursive_folder / "nested"
        _run_cli(
            [
                "--build-review-bundle",
                "--base-folder",
                str(nested_recursive_folder),
                "--source-url",
                f"https://www.youtube.com/watch?v={VALID_ID}",
                "--package-id",
                "folder cli recursive nested",
                "--capture-option",
                "comments",
                "--json",
            ]
        )
        exit_code, non_recursive_json_output = _run_cli(
            [
                "--verify-review-bundle-folder",
                "--review-bundle-folder",
                str(recursive_folder),
                "--json",
            ]
        )
        assert exit_code == 0
        assert json.loads(non_recursive_json_output)["zip_count"] == 1
        exit_code, recursive_json_output = _run_cli(
            [
                "--verify-review-bundle-folder",
                "--review-bundle-folder",
                str(recursive_folder),
                "--recursive-review-bundles",
                "--json",
            ]
        )
        assert exit_code == 0
        assert json.loads(recursive_json_output)["zip_count"] == 2

        exit_code, report_json_output = _run_cli(
            [
                "--verify-review-bundle-folder",
                "--review-bundle-folder",
                str(folder_verify_dir),
                "--write-review-bundle-folder-report",
                "--json",
            ]
        )
        assert exit_code == 0
        parsed_report = json.loads(report_json_output)
        assert parsed_report["report_written"] is True
        assert Path(parsed_report["report_path"]).is_file()

        exit_code, existing_report_json_output = _run_cli(
            [
                "--verify-review-bundle-folder",
                "--review-bundle-folder",
                str(folder_verify_dir),
                "--write-review-bundle-folder-report",
                "--json",
            ]
        )
        assert exit_code == 0
        parsed_existing_report = json.loads(existing_report_json_output)
        assert parsed_existing_report["report_written"] is False
        assert parsed_existing_report["errors"]

        exit_code, overwrite_report_json_output = _run_cli(
            [
                "--verify-review-bundle-folder",
                "--review-bundle-folder",
                str(folder_verify_dir),
                "--write-review-bundle-folder-report",
                "--overwrite-review-bundle-folder-report",
                "--json",
            ]
        )
        assert exit_code == 0
        assert json.loads(overwrite_report_json_output)["report_written"] is True

        error_code, folder_verify_missing_folder_arg_error = _run_cli_error(
            ["--verify-review-bundle-folder"]
        )
        assert error_code == 2
        assert (
            "--review-bundle-folder is required when --verify-review-bundle-folder is used"
            in folder_verify_missing_folder_arg_error
        )

        error_code, folder_verify_single_verify_error = _run_cli_error(
            [
                "--verify-review-bundle-folder",
                "--verify-review-bundle",
                "--review-bundle-folder",
                str(folder_verify_dir),
                "--zip-path",
                str(bundle_zip_path),
            ]
        )
        assert error_code == 2
        assert "Use only one list/explain mode at a time" in folder_verify_single_verify_error

        error_code, folder_verify_full_review_error = _run_cli_error(
            [
                "--verify-review-bundle-folder",
                "--review-bundle-folder",
                str(folder_verify_dir),
                "--full-review-files",
            ]
        )
        assert error_code == 2
        assert "read-only" in folder_verify_full_review_error

        batch_plan_source_file = Path(temp_dir) / "batch_plan_sources_cli.txt"
        batch_plan_source_file.write_text(
            "\n".join(
                [
                    "# CLI batch review bundle self-test",
                    "",
                    f"https://www.youtube.com/watch?v={VALID_ID}",
                    f"https://www.youtube.com/watch?v={VALID_ID}\tcli batch two",
                    f"https://www.youtube.com/watch?v={VALID_ID}\tcli batch three\tClip Title",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        batch_plan_output_folder = Path(temp_dir) / "batch_plan_output_cli"
        exit_code, batch_plan_output = _run_cli(
            [
                "--plan-batch-review-bundles",
                "--batch-source-file",
                str(batch_plan_source_file),
                "--batch-output-folder",
                str(batch_plan_output_folder),
                "--capture-option",
                "comments",
            ]
        )
        assert exit_code == 0
        assert "Total Export batch review plan" in batch_plan_output
        assert "Row count: 3" in batch_plan_output
        assert "Ready count: 3" in batch_plan_output
        assert batch_plan_output_folder.exists() is False

        exit_code, batch_plan_json_output = _run_cli(
            [
                "--plan-batch-review-bundles",
                "--batch-source-file",
                str(batch_plan_source_file),
                "--batch-output-folder",
                str(batch_plan_output_folder),
                "--capture-option",
                "comments",
                "--json",
            ]
        )
        assert exit_code == 0
        parsed_batch_plan = json.loads(batch_plan_json_output)
        assert parsed_batch_plan["row_count"] == 3
        assert parsed_batch_plan["ready_count"] == 3
        assert parsed_batch_plan["error_count"] == 0
        assert batch_plan_output_folder.exists() is False

        batch_duplicate_source_file = Path(temp_dir) / "batch_plan_duplicates_cli.txt"
        batch_duplicate_source_file.write_text(
            "\n".join(
                [
                    f"https://www.youtube.com/watch?v={VALID_ID}\tduplicate cli",
                    f"https://www.youtube.com/watch?v={VALID_ID}\tduplicate cli",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        exit_code, batch_duplicate_json_output = _run_cli(
            [
                "--plan-batch-review-bundles",
                "--batch-source-file",
                str(batch_duplicate_source_file),
                "--batch-output-folder",
                str(Path(temp_dir) / "batch_plan_duplicate_output"),
                "--json",
            ]
        )
        assert exit_code == 0
        parsed_batch_duplicates = json.loads(batch_duplicate_json_output)
        assert parsed_batch_duplicates["duplicate_package_id_count"] == 2
        assert all(item["duplicate_package_id"] for item in parsed_batch_duplicates["items"])

        error_code, batch_plan_missing_source_error = _run_cli_error(
            [
                "--plan-batch-review-bundles",
                "--batch-output-folder",
                str(Path(temp_dir) / "batch_plan_missing_source"),
            ]
        )
        assert error_code == 2
        assert (
            "--batch-source-file is required when --plan-batch-review-bundles is used"
            in batch_plan_missing_source_error
        )

        error_code, batch_plan_missing_output_error = _run_cli_error(
            [
                "--plan-batch-review-bundles",
                "--batch-source-file",
                str(batch_plan_source_file),
            ]
        )
        assert error_code == 2
        assert (
            "--batch-output-folder is required when --plan-batch-review-bundles is used"
            in batch_plan_missing_output_error
        )

        error_code, batch_plan_build_conflict_error = _run_cli_error(
            [
                "--plan-batch-review-bundles",
                "--build-batch-review-bundles",
                "--batch-source-file",
                str(batch_plan_source_file),
                "--batch-output-folder",
                str(Path(temp_dir) / "batch_plan_build_conflict"),
            ]
        )
        assert error_code == 2
        assert "Use only one list/explain mode at a time" in batch_plan_build_conflict_error

        error_code, batch_plan_full_review_error = _run_cli_error(
            [
                "--plan-batch-review-bundles",
                "--batch-source-file",
                str(batch_plan_source_file),
                "--batch-output-folder",
                str(Path(temp_dir) / "batch_plan_full_review_conflict"),
                "--full-review-files",
            ]
        )
        assert error_code == 2
        assert "dry-run mode" in batch_plan_full_review_error

        batch_source_file = Path(temp_dir) / "batch_sources_cli.txt"
        batch_source_file.write_text(
            "\n".join(
                [
                    "# CLI batch review bundle self-test",
                    "",
                    f"https://www.youtube.com/watch?v={VALID_ID}",
                    f"https://www.youtube.com/watch?v={VALID_ID}\tcli batch two",
                    f"https://www.youtube.com/watch?v={VALID_ID}\tcli batch three\tClip Title",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        batch_output_folder = Path(temp_dir) / "batch_output_cli"
        exit_code, batch_output = _run_cli(
            [
                "--build-batch-review-bundles",
                "--batch-source-file",
                str(batch_source_file),
                "--batch-output-folder",
                str(batch_output_folder),
                "--capture-option",
                "comments",
                "--no-create-asset-folders",
            ]
        )
        assert exit_code == 0
        assert "Total Export batch review bundles" in batch_output
        assert "Row count: 3" in batch_output
        assert "Success count: 3" in batch_output
        assert "Failed count: 0" in batch_output

        batch_json_output_folder = Path(temp_dir) / "batch_output_cli_json"
        exit_code, batch_json_output = _run_cli(
            [
                "--build-batch-review-bundles",
                "--batch-source-file",
                str(batch_source_file),
                "--batch-output-folder",
                str(batch_json_output_folder),
                "--capture-option",
                "comments",
                "--json",
            ]
        )
        assert exit_code == 0
        parsed_batch = json.loads(batch_json_output)
        assert parsed_batch["row_count"] == 3
        assert parsed_batch["success_count"] == 3
        assert parsed_batch["failed_count"] == 0
        assert parsed_batch["folder_verification_ran"] is True
        assert parsed_batch["folder_verification_verified_count"] == 3

        exit_code, batch_existing_json_output = _run_cli(
            [
                "--build-batch-review-bundles",
                "--batch-source-file",
                str(batch_source_file),
                "--batch-output-folder",
                str(batch_output_folder),
                "--capture-option",
                "comments",
                "--json",
            ]
        )
        assert exit_code == 0
        parsed_batch_existing = json.loads(batch_existing_json_output)
        assert parsed_batch_existing["success_count"] == 0
        assert parsed_batch_existing["failed_count"] == 3
        assert any(item["errors"] for item in parsed_batch_existing["items"])

        exit_code, batch_stop_json_output = _run_cli(
            [
                "--build-batch-review-bundles",
                "--batch-source-file",
                str(batch_source_file),
                "--batch-output-folder",
                str(batch_output_folder),
                "--capture-option",
                "comments",
                "--batch-stop-on-error",
                "--json",
            ]
        )
        assert exit_code == 0
        parsed_batch_stop = json.loads(batch_stop_json_output)
        assert parsed_batch_stop["row_count"] == 3
        assert len(parsed_batch_stop["items"]) == 1
        assert parsed_batch_stop["failed_count"] == 1
        assert parsed_batch_stop["warnings"]

        exit_code, batch_overwrite_json_output = _run_cli(
            [
                "--build-batch-review-bundles",
                "--batch-source-file",
                str(batch_source_file),
                "--batch-output-folder",
                str(batch_output_folder),
                "--capture-option",
                "comments",
                "--overwrite-bundle-zip",
                "--overwrite-sidecars",
                "--json",
            ]
        )
        assert exit_code == 0
        parsed_batch_overwrite = json.loads(batch_overwrite_json_output)
        assert parsed_batch_overwrite["success_count"] == 3
        assert parsed_batch_overwrite["failed_count"] == 0

        batch_report_folder = Path(temp_dir) / "batch_output_cli_report"
        exit_code, batch_report_json_output = _run_cli(
            [
                "--build-batch-review-bundles",
                "--batch-source-file",
                str(batch_source_file),
                "--batch-output-folder",
                str(batch_report_folder),
                "--capture-option",
                "comments",
                "--write-batch-folder-report",
                "--json",
            ]
        )
        assert exit_code == 0
        parsed_batch_report = json.loads(batch_report_json_output)
        assert parsed_batch_report["folder_verification_report_written"] is True
        assert Path(parsed_batch_report["folder_verification_report_path"]).is_file()

        error_code, batch_missing_source_error = _run_cli_error(
            [
                "--build-batch-review-bundles",
                "--batch-output-folder",
                str(Path(temp_dir) / "batch_missing_source"),
            ]
        )
        assert error_code == 2
        assert (
            "--batch-source-file is required when --build-batch-review-bundles is used"
            in batch_missing_source_error
        )

        error_code, batch_missing_output_error = _run_cli_error(
            [
                "--build-batch-review-bundles",
                "--batch-source-file",
                str(batch_source_file),
            ]
        )
        assert error_code == 2
        assert (
            "--batch-output-folder is required when --build-batch-review-bundles is used"
            in batch_missing_output_error
        )

        error_code, batch_folder_verify_error = _run_cli_error(
            [
                "--build-batch-review-bundles",
                "--verify-review-bundle-folder",
                "--batch-source-file",
                str(batch_source_file),
                "--batch-output-folder",
                str(Path(temp_dir) / "batch_conflict"),
                "--review-bundle-folder",
                str(folder_verify_dir),
            ]
        )
        assert error_code == 2
        assert "Use only one list/explain mode at a time" in batch_folder_verify_error

        error_code, batch_full_review_error = _run_cli_error(
            [
                "--build-batch-review-bundles",
                "--batch-source-file",
                str(batch_source_file),
                "--batch-output-folder",
                str(Path(temp_dir) / "batch_full_review_conflict"),
                "--full-review-files",
            ]
        )
        assert error_code == 2
        assert "cannot be combined with manual prepare/write/review flags" in batch_full_review_error

        exit_code, reconcile_text_output = _run_cli(
            [
                "--reconcile-batch-review-bundles",
                "--batch-source-file",
                str(batch_source_file),
                "--batch-output-folder",
                str(batch_output_folder),
                "--capture-option",
                "comments",
            ]
        )
        assert exit_code == 0
        assert "Total Export batch review reconciliation" in reconcile_text_output
        assert "Row count: 3" in reconcile_text_output
        assert "Verification passed count: 3" in reconcile_text_output
        assert "status=verify_passed" in reconcile_text_output

        exit_code, reconcile_json_output = _run_cli(
            [
                "--reconcile-batch-review-bundles",
                "--batch-source-file",
                str(batch_source_file),
                "--batch-output-folder",
                str(batch_output_folder),
                "--capture-option",
                "comments",
                "--json",
            ]
        )
        assert exit_code == 0
        parsed_reconcile = json.loads(reconcile_json_output)
        assert parsed_reconcile["row_count"] == 3
        assert parsed_reconcile["verification_passed_count"] == 3
        assert parsed_reconcile["missing_zip_count"] == 0
        assert parsed_reconcile["missing_sidecar_count"] == 0
        assert parsed_reconcile["report_written"] is False
        assert all(item["status"] == "verify_passed" for item in parsed_reconcile["items"])

        reconcile_missing_output = Path(temp_dir) / "reconcile_missing_output"
        exit_code, reconcile_missing_json_output = _run_cli(
            [
                "--reconcile-batch-review-bundles",
                "--batch-source-file",
                str(batch_source_file),
                "--batch-output-folder",
                str(reconcile_missing_output),
                "--json",
            ]
        )
        assert exit_code == 0
        parsed_reconcile_missing = json.loads(reconcile_missing_json_output)
        assert parsed_reconcile_missing["row_count"] == 3
        assert parsed_reconcile_missing["missing_zip_count"] == 3
        assert all(item["status"] == "missing_zip" for item in parsed_reconcile_missing["items"])
        assert reconcile_missing_output.exists() is False

        reconcile_sidecar_source_file = Path(temp_dir) / "reconcile_sidecar_sources_cli.txt"
        reconcile_sidecar_source_file.write_text(
            f"https://www.youtube.com/watch?v={VALID_ID}\treconcile sidecar\n",
            encoding="utf-8",
        )
        reconcile_sidecar_output = Path(temp_dir) / "reconcile_sidecar_output"
        _run_cli(
            [
                "--build-batch-review-bundles",
                "--batch-source-file",
                str(reconcile_sidecar_source_file),
                "--batch-output-folder",
                str(reconcile_sidecar_output),
                "--capture-option",
                "comments",
            ]
        )
        missing_sha = reconcile_sidecar_output / "reconcile_sidecar.zip.sha256"
        assert missing_sha.is_file()
        missing_sha.unlink()
        exit_code, reconcile_sidecar_json_output = _run_cli(
            [
                "--reconcile-batch-review-bundles",
                "--batch-source-file",
                str(reconcile_sidecar_source_file),
                "--batch-output-folder",
                str(reconcile_sidecar_output),
                "--json",
            ]
        )
        assert exit_code == 0
        parsed_reconcile_sidecar = json.loads(reconcile_sidecar_json_output)
        assert parsed_reconcile_sidecar["missing_sidecar_count"] == 1
        assert parsed_reconcile_sidecar["items"][0]["status"] == "missing_sidecars"

        reconcile_report_path = Path(temp_dir) / "reconcile_report.json"
        exit_code, reconcile_report_json_output = _run_cli(
            [
                "--reconcile-batch-review-bundles",
                "--batch-source-file",
                str(batch_source_file),
                "--batch-output-folder",
                str(batch_output_folder),
                "--write-reconcile-report",
                "--reconcile-report-path",
                str(reconcile_report_path),
                "--json",
            ]
        )
        assert exit_code == 0
        parsed_reconcile_report = json.loads(reconcile_report_json_output)
        assert parsed_reconcile_report["report_written"] is True
        assert Path(parsed_reconcile_report["report_path"]).is_file()

        exit_code, reconcile_report_existing_json_output = _run_cli(
            [
                "--reconcile-batch-review-bundles",
                "--batch-source-file",
                str(batch_source_file),
                "--batch-output-folder",
                str(batch_output_folder),
                "--write-reconcile-report",
                "--reconcile-report-path",
                str(reconcile_report_path),
                "--json",
            ]
        )
        assert exit_code == 0
        parsed_reconcile_report_existing = json.loads(reconcile_report_existing_json_output)
        assert parsed_reconcile_report_existing["report_written"] is False
        assert any("already exists" in error for error in parsed_reconcile_report_existing["errors"])

        exit_code, reconcile_report_overwrite_json_output = _run_cli(
            [
                "--reconcile-batch-review-bundles",
                "--batch-source-file",
                str(batch_source_file),
                "--batch-output-folder",
                str(batch_output_folder),
                "--write-reconcile-report",
                "--reconcile-report-path",
                str(reconcile_report_path),
                "--overwrite-reconcile-report",
                "--json",
            ]
        )
        assert exit_code == 0
        assert json.loads(reconcile_report_overwrite_json_output)["report_written"] is True

        error_code, reconcile_missing_source_error = _run_cli_error(
            [
                "--reconcile-batch-review-bundles",
                "--batch-output-folder",
                str(Path(temp_dir) / "reconcile_missing_source"),
            ]
        )
        assert error_code == 2
        assert (
            "--batch-source-file is required when --reconcile-batch-review-bundles is used"
            in reconcile_missing_source_error
        )

        error_code, reconcile_missing_output_error = _run_cli_error(
            [
                "--reconcile-batch-review-bundles",
                "--batch-source-file",
                str(batch_source_file),
            ]
        )
        assert error_code == 2
        assert (
            "--batch-output-folder is required when --reconcile-batch-review-bundles is used"
            in reconcile_missing_output_error
        )

        error_code, reconcile_plan_conflict_error = _run_cli_error(
            [
                "--reconcile-batch-review-bundles",
                "--plan-batch-review-bundles",
                "--batch-source-file",
                str(batch_source_file),
                "--batch-output-folder",
                str(batch_output_folder),
            ]
        )
        assert error_code == 2
        assert "Use only one list/explain mode at a time" in reconcile_plan_conflict_error

        error_code, reconcile_full_review_error = _run_cli_error(
            [
                "--reconcile-batch-review-bundles",
                "--batch-source-file",
                str(batch_source_file),
                "--batch-output-folder",
                str(batch_output_folder),
                "--full-review-files",
            ]
        )
        assert error_code == 2
        assert "cannot be combined" in reconcile_full_review_error

        error_code, bundle_missing_base_error = _run_cli_error(
            [
                "--build-review-bundle",
                "--source-url",
                f"https://www.youtube.com/watch?v={VALID_ID}",
            ]
        )
        assert error_code == 2
        assert "--base-folder is required when --build-review-bundle is used" in bundle_missing_base_error

        error_code, bundle_missing_source_error = _run_cli_error(
            ["--build-review-bundle", "--base-folder", temp_dir]
        )
        assert error_code == 2
        assert "--source-url is required when --build-review-bundle is used" in bundle_missing_source_error

        error_code, bundle_inspect_zip_error = _run_cli_error(
            [
                "--build-review-bundle",
                "--inspect-zip",
                "--base-folder",
                temp_dir,
                "--source-url",
                f"https://www.youtube.com/watch?v={VALID_ID}",
                "--zip-path",
                str(default_zip_path),
            ]
        )
        assert error_code == 2
        assert "Use only one list/explain mode at a time" in bundle_inspect_zip_error

        error_code, bundle_full_review_error = _run_cli_error(
            [
                "--build-review-bundle",
                "--base-folder",
                temp_dir,
                "--source-url",
                f"https://www.youtube.com/watch?v={VALID_ID}",
                "--full-review-files",
            ]
        )
        assert error_code == 2
        assert "implies full review files" in bundle_full_review_error

        error_code, inspect_zip_missing_path_error = _run_cli_error(["--inspect-zip"])
        assert error_code == 2
        assert "--zip-path is required when --inspect-zip is used" in inspect_zip_missing_path_error

        error_code, sidecar_missing_path_error = _run_cli_error(["--write-zip-sidecars"])
        assert error_code == 2
        assert "--zip-path is required when --write-zip-sidecars is used" in sidecar_missing_path_error

        error_code, inspect_zip_zip_package_error = _run_cli_error(
            [
                "--inspect-zip",
                "--zip-package",
                "--zip-path",
                str(default_zip_path),
                "--package-folder",
                full_review_package_folder,
            ]
        )
        assert error_code == 2
        assert "Use only one list/explain mode at a time" in inspect_zip_zip_package_error

        error_code, sidecar_inspect_zip_error = _run_cli_error(
            [
                "--write-zip-sidecars",
                "--inspect-zip",
                "--zip-path",
                str(default_zip_path),
            ]
        )
        assert error_code == 2
        assert "Use only one list/explain mode at a time" in sidecar_inspect_zip_error

        error_code, inspect_zip_write_flag_error = _run_cli_error(
            [
                "--inspect-zip",
                "--zip-path",
                str(default_zip_path),
                "--full-review-files",
            ]
        )
        assert error_code == 2
        assert "read-only" in inspect_zip_write_flag_error

        error_code, sidecar_write_flag_error = _run_cli_error(
            [
                "--write-zip-sidecars",
                "--zip-path",
                str(default_zip_path),
                "--full-review-files",
            ]
        )
        assert error_code == 2
        assert "cannot be combined with prepare/write/review flags" in sidecar_write_flag_error

        extra_file = Path(full_review_package_folder) / "extra_local_note.txt"
        extra_file.write_text("local note", encoding="utf-8")
        exit_code, inspect_extra_json_output = _run_cli(
            [
                "--inspect-package",
                "--package-folder",
                full_review_package_folder,
                "--json",
            ]
        )
        assert exit_code == 0
        parsed_extra_inspect = json.loads(inspect_extra_json_output)
        assert "extra_local_note.txt" in parsed_extra_inspect["inventory_unregistered_files"]

        plan_report_path = Path(full_review_package_folder) / "metadata" / "SOURCE_CAPTURE_PLAN.txt"
        plan_report_path.unlink()
        exit_code, inspect_missing_asset_json_output = _run_cli(
            [
                "--inspect-package",
                "--package-folder",
                full_review_package_folder,
                "--json",
            ]
        )
        assert exit_code == 0
        parsed_missing_asset_inspect = json.loads(inspect_missing_asset_json_output)
        assert parsed_missing_asset_inspect["status"] == "invalid_manifest"
        assert "metadata/SOURCE_CAPTURE_PLAN.txt" in parsed_missing_asset_inspect[
            "inventory_missing_registered_assets"
        ]
        assert any(
            "ASSET_FILE_MISSING" in error
            for error in parsed_missing_asset_inspect["validation_errors"]
        )

        exit_code, invalid_zip_json_output = _run_cli(
            [
                "--zip-package",
                "--package-folder",
                full_review_package_folder,
                "--zip-path",
                str(Path(temp_dir) / "invalid_package.zip"),
                "--json",
            ]
        )
        assert exit_code == 0
        parsed_invalid_zip = json.loads(invalid_zip_json_output)
        assert parsed_invalid_zip["zip_created"] is False
        assert parsed_invalid_zip["inspection_status"] == "invalid_manifest"
        assert any("inspection status" in error for error in parsed_invalid_zip["errors"])

        exit_code, inspect_missing_package_output = _run_cli(
            [
                "--inspect-package",
                "--package-folder",
                str(Path(temp_dir) / "missing_package"),
                "--json",
            ]
        )
        assert exit_code == 0
        assert json.loads(inspect_missing_package_output)["status"] == "missing_package_folder"

        empty_package = Path(temp_dir) / "empty_package"
        empty_package.mkdir()
        exit_code, inspect_missing_manifest_output = _run_cli(
            [
                "--inspect-package",
                "--package-folder",
                str(empty_package),
                "--json",
            ]
        )
        assert exit_code == 0
        assert json.loads(inspect_missing_manifest_output)["status"] == "missing_manifest"

        multiple_package = Path(temp_dir) / "multiple_manifest_package"
        multiple_package.mkdir()
        (multiple_package / "a_manifest.json").write_text("{}", encoding="utf-8")
        (multiple_package / "b_manifest.json").write_text("{}", encoding="utf-8")
        exit_code, inspect_multiple_manifest_output = _run_cli(
            [
                "--inspect-package",
                "--package-folder",
                str(multiple_package),
                "--json",
            ]
        )
        assert exit_code == 0
        assert json.loads(inspect_multiple_manifest_output)["status"] == "multiple_manifests"

        error_code, inspect_missing_folder_error = _run_cli_error(["--inspect-package"])
        assert error_code == 2
        assert "--package-folder is required when --inspect-package is used" in inspect_missing_folder_error

        error_code, inspect_explain_error = _run_cli_error(
            [
                "--inspect-package",
                "--package-folder",
                full_review_package_folder,
                "--explain-plan",
                "--source-url",
                f"https://www.youtube.com/watch?v={VALID_ID}",
            ]
        )
        assert error_code == 2
        assert "Use only one list/explain mode at a time" in inspect_explain_error

        error_code, inspect_write_flag_error = _run_cli_error(
            [
                "--inspect-package",
                "--package-folder",
                full_review_package_folder,
                "--full-review-files",
            ]
        )
        assert error_code == 2
        assert "read-only" in inspect_write_flag_error

        error_code, zip_missing_folder_error = _run_cli_error(["--zip-package"])
        assert error_code == 2
        assert "--package-folder is required when --zip-package is used" in zip_missing_folder_error

        error_code, zip_inspect_error = _run_cli_error(
            [
                "--zip-package",
                "--inspect-package",
                "--package-folder",
                full_review_package_folder,
            ]
        )
        assert error_code == 2
        assert "Use only one list/explain mode at a time" in zip_inspect_error

        error_code, zip_write_flag_error = _run_cli_error(
            [
                "--zip-package",
                "--package-folder",
                full_review_package_folder,
                "--full-review-files",
            ]
        )
        assert error_code == 2
        assert "cannot be combined with prepare/write/review flags" in zip_write_flag_error

        exit_code, full_review_no_plan_register_output = _run_cli(
            [
                "--base-folder",
                temp_dir,
                "--source-url",
                f"https://www.youtube.com/watch?v={VALID_ID}",
                "--package-id",
                "cli full review no plan register",
                "--capture-option",
                "comments",
                "--full-review-files",
                "--no-register-plan-report",
                "--no-create-asset-folders",
            ]
        )
        assert exit_code == 0
        assert "Registered plan report: no" in full_review_no_plan_register_output
        assert "Registered asset count: 3" in full_review_no_plan_register_output
        full_review_no_plan_register_manifest = read_manifest_json(
            _manifest_path_from_output(full_review_no_plan_register_output)
        )
        assert len(full_review_no_plan_register_manifest.assets) == 3
        assert Path(_plan_report_path_from_output(full_review_no_plan_register_output)).is_file()

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
            "plan_report_path",
            "readme_path",
            "registered_inventory_report",
            "registered_plan_report",
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
        assert parsed["plan_report_path"] == ""
        assert parsed["registered_plan_report"] is False
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

        exit_code, json_plan_report_output = _run_cli(
            [
                "--base-folder",
                temp_dir,
                "--source-url",
                f"https://www.youtube.com/watch?v={VALID_ID}",
                "--package-id",
                "cli json plan report",
                "--capture-option",
                "comments",
                "--write-plan-report",
                "--json",
            ]
        )
        assert exit_code == 0
        parsed_plan_report = json.loads(json_plan_report_output)
        assert parsed_plan_report["plan_report_path"]
        assert parsed_plan_report["registered_plan_report"] is True
        assert Path(parsed_plan_report["plan_report_path"]).is_file()
        json_plan_report_manifest = read_manifest_json(parsed_plan_report["manifest_path"])
        assert len(json_plan_report_manifest.assets) == 2

        exit_code, json_plan_report_no_register_output = _run_cli(
            [
                "--base-folder",
                temp_dir,
                "--source-url",
                f"https://www.youtube.com/watch?v={VALID_ID}",
                "--package-id",
                "cli json plan report no register",
                "--capture-option",
                "comments",
                "--write-plan-report",
                "--no-register-plan-report",
                "--json",
            ]
        )
        assert exit_code == 0
        parsed_plan_report_no_register = json.loads(json_plan_report_no_register_output)
        assert parsed_plan_report_no_register["plan_report_path"]
        assert parsed_plan_report_no_register["registered_plan_report"] is False
        json_plan_report_no_register_manifest = read_manifest_json(
            parsed_plan_report_no_register["manifest_path"]
        )
        assert len(json_plan_report_no_register_manifest.assets) == 1

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
        assert parsed_review_files["plan_report_path"] == ""
        assert parsed_review_files["registered_plan_report"] is False
        assert parsed_review_files["inventory_report_path"]
        assert parsed_review_files["registered_inventory_report"] is True
        assert parsed_review_files["inventory_ran"] is True
        assert parsed_review_files["inventory_registered_asset_count"] == 3
        assert parsed_review_files["inventory_local_file_count"] >= 4
        json_review_files_manifest = read_manifest_json(parsed_review_files["manifest_path"])
        assert len(json_review_files_manifest.assets) == 3

        exit_code, json_full_review_files_output = _run_cli(
            [
                "--base-folder",
                temp_dir,
                "--source-url",
                f"https://www.youtube.com/watch?v={VALID_ID}",
                "--package-id",
                "cli json full review files",
                "--capture-option",
                "comments",
                "--full-review-files",
                "--json",
            ]
        )
        assert exit_code == 0
        parsed_full_review_files = json.loads(json_full_review_files_output)
        assert parsed_full_review_files["readme_path"]
        assert parsed_full_review_files["registered_readme"] is True
        assert parsed_full_review_files["plan_report_path"]
        assert parsed_full_review_files["registered_plan_report"] is True
        assert parsed_full_review_files["inventory_report_path"]
        assert parsed_full_review_files["registered_inventory_report"] is True
        assert parsed_full_review_files["inventory_ran"] is True
        assert parsed_full_review_files["inventory_registered_asset_count"] == 4
        assert parsed_full_review_files["inventory_local_file_count"] >= 5
        json_full_review_files_manifest = read_manifest_json(
            parsed_full_review_files["manifest_path"]
        )
        assert len(json_full_review_files_manifest.assets) == 4

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
