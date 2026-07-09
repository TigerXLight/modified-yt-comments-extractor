from contextlib import redirect_stdout
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


def run_self_test() -> None:
    with TemporaryDirectory() as temp_dir:
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
        assert "Final validation: ok" in output
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
            "manifest_path",
            "normalized_url",
            "package_folder",
            "plan_status",
            "readme_path",
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
                "--json",
            ]
        )
        assert exit_code == 0
        parsed_readme = json.loads(json_readme_output)
        assert parsed_readme["readme_path"]
        assert parsed_readme["registered_readme"] is True
        assert parsed_readme["final_validation_ran"] is True
        assert parsed_readme["final_validation_issue_count"] == 0
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
        assert parsed_unsupported["final_validation_ran"] is True
        assert parsed_unsupported["final_validation_issue_count"] == 0
        assert parsed_unsupported["warnings"] == [
            "No source adapter supports the URL: https://example.com/article",
        ]


if __name__ == "__main__":
    run_self_test()
    print("Total Export prepare CLI self-test passed.")
