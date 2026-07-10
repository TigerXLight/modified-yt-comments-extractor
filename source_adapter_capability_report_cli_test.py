import io
import json
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory

from source_adapter_capability_report_cli import main


def _run_cli(argv: list[str]):
    stdout = io.StringIO()
    stderr = io.StringIO()
    with redirect_stdout(stdout), redirect_stderr(stderr):
        code = main(argv)
    return code, stdout.getvalue(), stderr.getvalue()


def run_self_test() -> None:
    code, markdown, stderr = _run_cli([])
    assert code == 0
    assert stderr == ""
    assert "# Source Adapter Capability Report" in markdown
    assert "Adapter ID: youtube" in markdown
    assert "does not fetch URLs" in markdown

    code, text, stderr = _run_cli(["--format", "text"])
    assert code == 0
    assert stderr == ""
    assert "Source adapter capability report" in text
    assert "youtube (YouTube)" in text
    assert "no fetch/capture/network" in text

    code, json_output, stderr = _run_cli(["--format", "json"])
    assert code == 0
    assert stderr == ""
    parsed = json.loads(json_output)
    assert parsed["adapter_count"] == 1
    assert parsed["source_adapters"][0]["adapter_id"] == "youtube"
    assert parsed["source_adapters"][0]["credential_type"] == "api_key"

    code, filtered_json, stderr = _run_cli(
        ["--adapter", " YouTube ", "--adapter", "youtube", "--format", "json"]
    )
    assert code == 0
    assert stderr == ""
    parsed_filtered = json.loads(filtered_json)
    assert parsed_filtered["adapter_count"] == 1
    assert parsed_filtered["source_adapters"][0]["adapter_id"] == "youtube"

    code, stdout, stderr = _run_cli(["--adapter", "missing"])
    assert code == 1
    assert stdout == ""
    assert "unknown source adapter(s): missing" in stderr

    with TemporaryDirectory() as temp_dir:
        output_path = Path(temp_dir) / "SOURCE_ADAPTER_CAPABILITIES.md"
        output_args = ["--output", str(output_path)]
        code, stdout, stderr = _run_cli(output_args)
        assert code == 0
        assert stdout == ""
        assert stderr == ""
        assert output_path.read_text(encoding="utf-8").startswith(
            "# Source Adapter Capability Report"
        )

        code, stdout, stderr = _run_cli(output_args)
        assert code == 1
        assert stdout == ""
        assert "output path already exists" in stderr

        output_path.write_text("old\n", encoding="utf-8")
        code, stdout, stderr = _run_cli([*output_args, "--overwrite"])
        assert code == 0
        assert stdout == ""
        assert stderr == ""
        assert "Adapter ID: youtube" in output_path.read_text(encoding="utf-8")


if __name__ == "__main__":
    run_self_test()
    print("Source adapter capability report CLI self-test passed.")
