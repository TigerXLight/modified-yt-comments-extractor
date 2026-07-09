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

        error_code, inspect_zip_missing_path_error = _run_cli_error(["--inspect-zip"])
        assert error_code == 2
        assert "--zip-path is required when --inspect-zip is used" in inspect_zip_missing_path_error

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
