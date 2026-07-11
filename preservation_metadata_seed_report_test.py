import io
import json
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory

from preservation_metadata_seed_report import (
    DEFAULT_SEED_PATH,
    build_preservation_metadata_seed_report,
    load_preservation_metadata_seed,
    main,
    preservation_metadata_seed_report_to_dict,
)


def _run_cli(argv: list[str]):
    stdout = io.StringIO()
    stderr = io.StringIO()
    with redirect_stdout(stdout), redirect_stderr(stderr):
        code = main(argv)
    return code, stdout.getvalue(), stderr.getvalue()

def _assert_cli_failure(argv: list[str], expected_error: str) -> None:
    code, stdout, stderr = _run_cli(argv)
    assert code == 1
    assert stdout == ""
    assert expected_error in stderr



def run_self_test() -> None:
    seed = load_preservation_metadata_seed(DEFAULT_SEED_PATH)
    assert seed["metadata"]["schema"] == "local_preservation_metadata_seed"

    result = build_preservation_metadata_seed_report()
    assert result.seed_path == DEFAULT_SEED_PATH
    assert result.source_count == 5
    assert result.manual_archive_record_count == 3
    assert result.local_media_record_count == 3
    assert result.preservation_plan.sources_needing_follow_up_count == 4
    assert any("example local metadata" in warning for warning in result.warnings)
    assert any("No archive checks" in warning for warning in result.warnings)

    as_dict = preservation_metadata_seed_report_to_dict(result)
    assert list(as_dict) == [
        "errors",
        "local_media_record_count",
        "manual_archive_record_count",
        "preservation_plan",
        "seed_path",
        "source_count",
        "warnings",
    ]

    code, markdown, stderr = _run_cli([])
    assert code == 0
    assert stderr == ""
    assert "# Preservation Metadata Seed Report" in markdown
    assert "Seed file: `PRESERVATION_METADATA_SEED.json`" in markdown
    assert "Source count: 5" in markdown
    assert "Manual archive record count: 3" in markdown
    assert "Local media record count: 3" in markdown
    assert "# Local Preservation Plan Report" not in markdown
    assert "| Source URL | Archive records" in markdown
    assert "example local metadata only" in markdown
    assert "No archive checks, downloads, network/API calls" in markdown

    code, text, stderr = _run_cli(["--format", "text"])
    assert code == 0
    assert stderr == ""
    assert "Preservation metadata seed report" in text
    assert "Local preservation plan report" in text
    assert "Sources needing follow-up: 4" in text

    code, json_output, stderr = _run_cli(["--format", "json"])
    assert code == 0
    assert stderr == ""
    parsed = json.loads(json_output)
    assert list(parsed) == sorted(parsed)
    assert parsed["seed_path"] == DEFAULT_SEED_PATH
    assert parsed["source_count"] == 5
    assert parsed["manual_archive_record_count"] == 3
    assert parsed["local_media_record_count"] == 3
    assert parsed["preservation_plan"]["sources_needing_follow_up_count"] == 4

    with TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        output_path = root / "seed_report.md"
        output_args = ["--output", str(output_path)]

        code, stdout, stderr = _run_cli(output_args)
        assert code == 0
        assert stdout == ""
        assert stderr == ""
        assert output_path.read_text(encoding="utf-8").startswith(
            "# Preservation Metadata Seed Report"
        )

        _assert_cli_failure(output_args, 'Output file already exists')

        output_path.write_text("old\n", encoding="utf-8")
        code, stdout, stderr = _run_cli([*output_args, "--overwrite"])
        assert code == 0
        assert stdout == ""
        assert stderr == ""
        assert "# Preservation Metadata Seed Report" in output_path.read_text(encoding="utf-8")

        missing_path = root / "missing.json"
        _assert_cli_failure(['--input', str(missing_path)], 'does not exist')

        invalid_path = root / "invalid.json"
        invalid_path.write_text("{not json\n", encoding="utf-8")
        _assert_cli_failure(['--input', str(invalid_path)], 'Invalid seed JSON input')


if __name__ == "__main__":
    run_self_test()
    print("Preservation metadata seed report self-test passed.")
