import io
import json
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory

from preservation_backend_plan_cli import main


def _run_cli(argv: list[str]):
    stdout = io.StringIO()
    stderr = io.StringIO()
    with redirect_stdout(stdout), redirect_stderr(stderr):
        code = main(argv)
    return code, stdout.getvalue(), stderr.getvalue()


def _write_json(path: Path, data) -> None:
    path.write_text(json.dumps(data), encoding="utf-8")


def run_self_test() -> None:
    code, markdown, stderr = _run_cli([])
    assert code == 0
    assert stderr == ""
    assert "# Preservation Backend Plan" in markdown
    assert "Status: needs_selection" in markdown
    assert "Manual local files" in markdown
    assert "ArchiveBox-style self-hosted store" in markdown
    assert "does not fetch URLs" in markdown
    assert "Media preservation choice: none" in markdown

    code, text, stderr = _run_cli(["--format", "text"])
    assert code == 0
    assert stderr == ""
    assert "Preservation backend plan" in text
    assert "manual_local_files" in text
    assert "archivebox_self_hosted" in text
    assert "no fetch/capture/network" in text
    assert "media_preservation_choice: none" in text

    code, json_output, stderr = _run_cli(["--format", "json"])
    assert code == 0
    assert stderr == ""
    parsed = json.loads(json_output)
    assert parsed["status"] == "needs_selection"
    assert parsed["selected_backend_ids"] == []
    assert parsed["selected_format_ids"] == []
    assert parsed["media_preservation_choice"] == "none"
    assert any(
        item["backend_id"] == "archivebox_self_hosted"
        for item in parsed["available_backends"]
    )
    assert any(item["format_id"] == "warc" for item in parsed["available_formats"])

    with TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        input_path = root / "preservation_plan.json"
        _write_json(
            input_path,
            {
                "source_url": "https://www.telegraph.co.uk/news/example/?utm=x",
                "selected_backend_ids": [
                    "manual_local_files",
                    "archivebox_self_hosted",
                    "manual_local_files",
                    "unknown_backend",
                ],
                "selected_format_ids": ["html", "pdf", "warc", "html"],
                "media_preservation_choice": "select",
                "notes": "User wants backup metadata only.",
            },
        )

        code, plan_json, stderr = _run_cli(
            ["--input", str(input_path), "--format", "json"]
        )
        assert code == 0
        assert stderr == ""
        parsed_plan = json.loads(plan_json)
        assert parsed_plan["status"] == "ready"
        assert parsed_plan["selected_backend_ids"] == [
            "manual_local_files",
            "archivebox_self_hosted",
        ]
        assert parsed_plan["selected_format_ids"] == ["html", "pdf", "warc"]
        assert parsed_plan["unknown_backend_ids"] == ["unknown_backend"]
        assert parsed_plan["duplicate_backend_ids"] == ["manual_local_files"]
        assert parsed_plan["duplicate_format_ids"] == ["html"]
        assert parsed_plan["media_preservation_choice"] == "select"

        output_path = root / "PRESERVATION_BACKEND_PLAN.md"
        output_args = ["--input", str(input_path), "--output", str(output_path)]
        code, stdout, stderr = _run_cli(output_args)
        assert code == 0
        assert stdout == ""
        assert stderr == ""
        assert output_path.read_text(encoding="utf-8").startswith(
            "# Preservation Backend Plan"
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
        assert "Selected backends: manual_local_files, archivebox_self_hosted" in (
            output_path.read_text(encoding="utf-8")
        )

        missing_input = root / "missing.json"
        code, stdout, stderr = _run_cli(["--input", str(missing_input)])
        assert code == 1
        assert stdout == ""
        assert "input file not found" in stderr

        invalid_input = root / "invalid.json"
        invalid_input.write_text("{not json\n", encoding="utf-8")
        code, stdout, stderr = _run_cli(["--input", str(invalid_input)])
        assert code == 1
        assert stdout == ""
        assert "invalid JSON" in stderr

        list_input = root / "list.json"
        _write_json(list_input, [])
        code, stdout, stderr = _run_cli(["--input", str(list_input)])
        assert code == 1
        assert stdout == ""
        assert "input JSON must be an object" in stderr

        bad_backends = root / "bad_backends.json"
        _write_json(bad_backends, {"selected_backend_ids": "manual_local_files"})
        code, stdout, stderr = _run_cli(["--input", str(bad_backends)])
        assert code == 1
        assert stdout == ""
        assert "selected_backend_ids must be a list of strings" in stderr

        bad_formats = root / "bad_formats.json"
        _write_json(bad_formats, {"selected_format_ids": "html"})
        code, stdout, stderr = _run_cli(["--input", str(bad_formats)])
        assert code == 1
        assert stdout == ""
        assert "selected_format_ids must be a list of strings" in stderr

        bad_media_choice = root / "bad_media_choice.json"
        _write_json(bad_media_choice, {"media_preservation_choice": "everything"})
        code, stdout, stderr = _run_cli(["--input", str(bad_media_choice)])
        assert code == 1
        assert stdout == ""
        assert "expected one of none, select, all" in stderr


if __name__ == "__main__":
    run_self_test()
    print("Preservation backend plan CLI self-test passed.")
