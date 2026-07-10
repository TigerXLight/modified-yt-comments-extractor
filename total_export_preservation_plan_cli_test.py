import io
import json
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory

from total_export_preservation_plan_cli import main


VALID_ID = "aB3_dE-9xYz"
CANONICAL_URL = f"https://www.youtube.com/watch?v={VALID_ID}"


def _write_json(path: Path, data: object) -> None:
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


def _sample_input() -> dict[str, object]:
    return {
        "source_urls": [
            CANONICAL_URL,
            "https://example.com/story",
            "https://example.com/missing-archive",
        ],
        "manual_archive_records": [
            {
                "source_url": f"https://youtu.be/{VALID_ID}?t=30",
                "archive_url": "https://web.archive.org/web/20260710000000/https://www.youtube.com/watch?v=aB3_dE-9xYz",
                "archive_status": "manually_supplied",
                "entered_at_utc": "2026-07-10T10:00:00Z",
            },
            {
                "source_url": "https://example.com/story",
                "archive_status": "manually_checked_not_found",
                "archive_notes": "User manually checked and did not find an archive.",
                "entered_at_utc": "2026-07-10T10:01:00Z",
            },
        ],
        "local_media_records": [
            {
                "source_url": CANONICAL_URL,
                "package_id": "example package",
                "local_media_path": "T:/example/local-file.mp4",
                "status": "registered",
                "exists_at_registration": True,
                "local_file_size_bytes": 12345,
                "local_file_sha256": "abc123",
                "registered_at_utc": "2026-07-10T10:02:00Z",
            },
            {
                "source_url": "https://example.com/story",
                "local_media_path": "T:/example/story.mp4",
                "status": "missing_local_file",
                "exists_at_registration": False,
                "registered_at_utc": "2026-07-10T10:03:00Z",
            },
        ],
    }


def _run_cli(argv: list[str]):
    stdout = io.StringIO()
    stderr = io.StringIO()
    with redirect_stdout(stdout), redirect_stderr(stderr):
        code = main(argv)
    return code, stdout.getvalue(), stderr.getvalue()


def run_self_test() -> None:
    with TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        input_path = root / "preservation_input.json"
        _write_json(input_path, _sample_input())

        code, stdout, stderr = _run_cli(["--input", str(input_path)])
        assert code == 0
        assert stderr == ""
        assert "Local preservation plan report" in stdout
        assert "Source count: 3" in stdout
        assert CANONICAL_URL in stdout
        assert "Add a manually supplied archive URL if one exists." in stdout
        assert "Register a local media file already saved on disk if available." in stdout
        assert "no archive checks, downloads, fetching, scraping" in stdout

        code, markdown, stderr = _run_cli(["--input", str(input_path), "--format", "markdown"])
        assert code == 0
        assert stderr == ""
        assert "# Local Preservation Plan Report" in markdown
        assert "| Source URL | Archive records | Archive statuses | Archive follow-up | Local media records | Local media statuses | Local media follow-up | Recommended actions |" in markdown
        assert "## Safety Notes" in markdown

        code, json_output, stderr = _run_cli(["--input", str(input_path), "--format", "json"])
        assert code == 0
        assert stderr == ""
        parsed = json.loads(json_output)
        assert parsed["source_count"] == 3
        assert parsed["sources_with_archive_count"] == 2
        assert parsed["sources_missing_archive_count"] == 1
        assert parsed["sources_with_local_media_count"] == 2
        assert parsed["sources_missing_local_media_count"] == 1
        assert parsed["items"][0]["normalized_url"] == CANONICAL_URL

        output_path = root / "PRESERVATION_PLAN_REPORT_OUTPUT.md"
        code, stdout, stderr = _run_cli(
            [
                "--input",
                str(input_path),
                "--format",
                "markdown",
                "--output",
                str(output_path),
            ]
        )
        assert code == 0
        assert stdout == ""
        assert stderr == ""
        assert output_path.read_text(encoding="utf-8").startswith("# Local Preservation Plan Report")

        code, stdout, stderr = _run_cli(
            ["--input", str(input_path), "--format", "markdown", "--output", str(output_path)]
        )
        assert code == 1
        assert stdout == ""
        assert "Output file already exists" in stderr

        output_path.write_text("old\n", encoding="utf-8")
        code, stdout, stderr = _run_cli(
            [
                "--input",
                str(input_path),
                "--format",
                "markdown",
                "--output",
                str(output_path),
                "--overwrite",
            ]
        )
        assert code == 0
        assert stdout == ""
        assert stderr == ""
        assert "# Local Preservation Plan Report" in output_path.read_text(encoding="utf-8")

        code, stdout, stderr = _run_cli(["--input", str(root / "missing.json")])
        assert code == 1
        assert stdout == ""
        assert "Input file does not exist" in stderr

        invalid_path = root / "invalid.json"
        invalid_path.write_text("{not json\n", encoding="utf-8")
        code, stdout, stderr = _run_cli(["--input", str(invalid_path)])
        assert code == 1
        assert stdout == ""
        assert "Invalid JSON input" in stderr

        inferred_path = root / "inferred.json"
        inferred_data = {
            "manual_archive_records": [
                {
                    "source_url": f"https://youtu.be/{VALID_ID}?t=30",
                    "archive_url": "https://archive.ph/example",
                }
            ],
            "local_media_records": [
                {
                    "source_url": CANONICAL_URL,
                    "local_media_path": "T:/example/local-file.mp4",
                    "status": "registered",
                    "exists_at_registration": True,
                    "local_file_size_bytes": 12345,
                }
            ],
        }
        _write_json(inferred_path, inferred_data)
        code, json_output, stderr = _run_cli(
            ["--input", str(inferred_path), "--format", "json"]
        )
        assert code == 0
        assert stderr == ""
        inferred = json.loads(json_output)
        assert inferred["source_count"] == 1
        assert inferred["items"][0]["normalized_url"] == CANONICAL_URL

        list_input = root / "source_list.json"
        _write_json(list_input, [CANONICAL_URL, "https://example.com/list-only"])
        code, json_output, stderr = _run_cli(
            ["--input", str(list_input), "--format", "json"]
        )
        assert code == 0
        assert stderr == ""
        list_result = json.loads(json_output)
        assert list_result["source_count"] == 2
        assert list_result["sources_missing_archive_count"] == 2
        assert list_result["sources_missing_local_media_count"] == 2


if __name__ == "__main__":
    run_self_test()
    print("Local preservation plan CLI self-test passed.")
