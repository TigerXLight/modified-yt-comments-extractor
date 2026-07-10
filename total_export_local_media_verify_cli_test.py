import hashlib
import io
import json
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory

from total_export_local_media_verify import (
    LOCAL_MEDIA_VERIFY_STATUS_MISSING_LOCAL_FILE,
    LOCAL_MEDIA_VERIFY_STATUS_NEEDS_REVIEW,
    LOCAL_MEDIA_VERIFY_STATUS_VERIFIED,
)
from total_export_local_media_verify_cli import main


def _write_json(path: Path, data: object) -> None:
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


def _run_cli(argv: list[str]):
    stdout = io.StringIO()
    stderr = io.StringIO()
    with redirect_stdout(stdout), redirect_stderr(stderr):
        code = main(argv)
    return code, stdout.getvalue(), stderr.getvalue()


def _sample_input(local_path: Path, sample_bytes: bytes) -> dict[str, object]:
    return {
        "local_media_records": [
            {
                "source_url": "https://example.com/source",
                "package_id": "verification package",
                "local_media_path": str(local_path),
                "status": "registered",
                "exists_at_registration": True,
                "local_file_size_bytes": len(sample_bytes),
                "local_file_sha256": hashlib.sha256(sample_bytes).hexdigest(),
                "registered_at_utc": "2026-07-10T10:00:00Z",
            }
        ]
    }


def run_self_test() -> None:
    with TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        sample_bytes = b"local media verification cli sample\n"
        media_path = root / "sample_clip.mp4"
        media_path.write_bytes(sample_bytes)
        input_path = root / "local_media_records.json"
        _write_json(input_path, _sample_input(media_path, sample_bytes))

        code, stdout, stderr = _run_cli(["--input", str(input_path)])
        assert code == 0
        assert stderr == ""
        assert "Local media verification report" in stdout
        assert "Record count: 1" in stdout
        assert LOCAL_MEDIA_VERIFY_STATUS_VERIFIED in stdout
        assert str(media_path) in stdout
        assert "no downloads, fetching" in stdout

        code, markdown, stderr = _run_cli(
            ["--input", str(input_path), "--format", "markdown"]
        )
        assert code == 0
        assert stderr == ""
        assert "# Local Media Verification Report" in markdown
        assert "| Local path | Status | Current exists | Recorded size | Current size | Size match | SHA-256 match | Warnings |" in markdown
        assert "## Safety Notes" in markdown

        code, json_output, stderr = _run_cli(
            ["--input", str(input_path), "--format", "json"]
        )
        assert code == 0
        assert stderr == ""
        parsed = json.loads(json_output)
        assert parsed["record_count"] == 1
        assert parsed["checked_count"] == 1
        assert parsed["missing_count"] == 0
        assert parsed["size_mismatch_count"] == 0
        assert parsed["sha256_mismatch_count"] == 0
        assert parsed["items"][0]["status"] == LOCAL_MEDIA_VERIFY_STATUS_VERIFIED
        assert parsed["items"][0]["local_media_path"] == str(media_path)

        code, no_hash_output, stderr = _run_cli(
            ["--input", str(input_path), "--no-compute-hash"]
        )
        assert code == 0
        assert stderr == ""
        assert LOCAL_MEDIA_VERIFY_STATUS_NEEDS_REVIEW in no_hash_output
        assert "SHA-256 was not computed" in no_hash_output

        output_path = root / "LOCAL_MEDIA_VERIFICATION_REPORT_OUTPUT.md"
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
        assert output_path.read_text(encoding="utf-8").startswith("# Local Media Verification Report")

        code, stdout, stderr = _run_cli(
            ["--input", str(input_path), "--output", str(output_path)]
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
        assert "# Local Media Verification Report" in output_path.read_text(encoding="utf-8")

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

        list_input = root / "bare_list.json"
        _write_json(
            list_input,
            [
                {
                    "source_url": "https://example.com/source",
                    "local_media_path": str(media_path),
                    "status": "registered",
                    "exists_at_registration": True,
                    "local_file_size_bytes": len(sample_bytes),
                    "local_file_sha256": hashlib.sha256(sample_bytes).hexdigest(),
                }
            ],
        )
        code, json_output, stderr = _run_cli(
            ["--input", str(list_input), "--format", "json"]
        )
        assert code == 0
        assert stderr == ""
        list_result = json.loads(json_output)
        assert list_result["record_count"] == 1
        assert list_result["items"][0]["status"] == LOCAL_MEDIA_VERIFY_STATUS_VERIFIED

        seed_path = Path("PRESERVATION_METADATA_SEED.json")
        code, json_output, stderr = _run_cli(
            ["--input", str(seed_path), "--format", "json", "--no-compute-hash"]
        )
        assert code == 0
        assert stderr == ""
        seed_result = json.loads(json_output)
        assert seed_result["record_count"] == 3
        assert seed_result["missing_count"] == 3
        assert seed_result["items"][0]["status"] == LOCAL_MEDIA_VERIFY_STATUS_MISSING_LOCAL_FILE
        assert "Hash computation was disabled" in seed_result["warnings"][1]


if __name__ == "__main__":
    run_self_test()
    print("Local media verification CLI self-test passed.")
