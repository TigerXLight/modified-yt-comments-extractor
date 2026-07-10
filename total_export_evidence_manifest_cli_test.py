import io
import json
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory

from total_export_evidence_manifest_cli import main


VIDEO_ID = "aB3_dE-9xYz"
CANONICAL_URL = f"https://www.youtube.com/watch?v={VIDEO_ID}"


def _run_cli(argv: list[str]):
    stdout = io.StringIO()
    stderr = io.StringIO()
    with redirect_stdout(stdout), redirect_stderr(stderr):
        code = main(argv)
    return code, stdout.getvalue(), stderr.getvalue()


def run_self_test() -> None:
    with TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        source_only_input = root / "source_only.json"
        source_only_input.write_text(
            json.dumps({"source_urls": [CANONICAL_URL]}),
            encoding="utf-8",
        )

        code, markdown, stderr = _run_cli(["--input", str(source_only_input)])
        assert code == 0
        assert stderr == ""
        assert "# Manual Local Evidence Package Manifest" in markdown
        assert "Entry count: 1" in markdown
        assert "| Source/package | Archive records/statuses" in markdown
        assert "## Safety Notes" in markdown
        assert "does not open, copy, package, or extract" in markdown
        assert tuple(path.name for path in root.iterdir()) == ("source_only.json",)

        fake_media_path = root / "not-created.mp4"
        fake_zip_path = root / "not-created.zip"
        full_input = root / "full.json"
        full_input.write_text(
            json.dumps(
                {
                    "source_urls": [CANONICAL_URL],
                    "manual_archive_records": [
                        {
                            "source_url": f"https://youtu.be/{VIDEO_ID}?t=30",
                            "archive_url": "https://web.archive.org/web/example",
                            "archive_status": "manually_supplied",
                        }
                    ],
                    "local_media_records": [
                        {
                            "source_url": CANONICAL_URL,
                            "package_id": "example-package",
                            "local_media_path": str(fake_media_path),
                            "status": "registered",
                            "local_file_size_bytes": 12345,
                            "local_file_sha256": "0" * 64,
                        }
                    ],
                    "local_media_verification_items": [
                        {
                            "package_id": "example-package",
                            "local_media_path": str(fake_media_path),
                            "status": "missing_local_file",
                            "warnings": ["Local media file missing."],
                            "recommended_actions": ["Re-check local path."],
                        }
                    ],
                    "bundle_reconciliation_items": [
                        {
                            "source_url": CANONICAL_URL,
                            "package_id": "example-package",
                            "expected_zip_path": str(fake_zip_path),
                            "zip_filename": "not-created.zip",
                            "status": "missing_expected_zip",
                            "needs_follow_up": True,
                            "warnings": ["Expected ZIP is missing."],
                            "recommended_actions": ["Locate expected ZIP."],
                        }
                    ],
                    "unexpected_bundle_reconciliation_items": [],
                },
                indent=2,
            ),
            encoding="utf-8",
        )

        code, text, stderr = _run_cli(
            ["--input", str(full_input), "--format", "text"]
        )
        assert code == 0
        assert stderr == ""
        assert "Manual local evidence package manifest" in text
        assert "Archive record count: 1" in text
        assert "Local media record count: 1" in text
        assert "Local media verification count: 1" in text
        assert "Bundle item count: 1" in text
        assert "manually_supplied" in text
        assert "registered" in text
        assert "missing_local_file" in text
        assert "missing_expected_zip" in text
        assert "no file copying, package building, ZIP creation/extraction" in text

        code, full_markdown, stderr = _run_cli(
            ["--input", str(full_input), "--format", "markdown"]
        )
        assert code == 0
        assert stderr == ""
        assert "# Manual Local Evidence Package Manifest" in full_markdown
        assert "## Safety Notes" in full_markdown
        assert "No downloads, fetching, network/API/archive checks" in full_markdown

        code, json_output, stderr = _run_cli(
            ["--input", str(full_input), "--format", "json"]
        )
        assert code == 0
        assert stderr == ""
        parsed = json.loads(json_output)
        assert list(parsed) == sorted(parsed)
        assert parsed["entry_count"] == 1
        assert parsed["archive_record_count"] == 1
        assert parsed["local_media_record_count"] == 1
        assert parsed["local_media_verification_count"] == 1
        assert parsed["bundle_item_count"] == 1
        assert parsed["sources_needing_follow_up_count"] == 1
        assert parsed["entries"][0]["normalized_url"] == CANONICAL_URL
        assert parsed["entries"][0]["local_media_verification_statuses"] == [
            "missing_local_file"
        ]
        assert parsed["entries"][0]["bundle_statuses"] == ["missing_expected_zip"]
        assert fake_media_path.exists() is False
        assert fake_zip_path.exists() is False

        output_path = root / "EVIDENCE_MANIFEST_REPORT.md"
        output_args = ["--input", str(full_input), "--output", str(output_path)]
        code, stdout, stderr = _run_cli(output_args)
        assert code == 0
        assert stdout == ""
        assert stderr == ""
        assert output_path.read_text(encoding="utf-8").startswith(
            "# Manual Local Evidence Package Manifest"
        )

        code, stdout, stderr = _run_cli(output_args)
        assert code == 1
        assert stdout == ""
        assert "Output file already exists" in stderr

        output_path.write_text("old\n", encoding="utf-8")
        code, stdout, stderr = _run_cli([*output_args, "--overwrite"])
        assert code == 0
        assert stdout == ""
        assert stderr == ""
        assert "# Manual Local Evidence Package Manifest" in output_path.read_text(
            encoding="utf-8"
        )

        missing_input = root / "missing.json"
        code, stdout, stderr = _run_cli(["--input", str(missing_input)])
        assert code == 1
        assert stdout == ""
        assert "does not exist" in stderr

        invalid_input = root / "invalid.json"
        invalid_input.write_text("{not json\n", encoding="utf-8")
        code, stdout, stderr = _run_cli(["--input", str(invalid_input)])
        assert code == 1
        assert stdout == ""
        assert "Invalid evidence manifest JSON" in stderr


if __name__ == "__main__":
    run_self_test()
    print("Local evidence manifest CLI self-test passed.")
