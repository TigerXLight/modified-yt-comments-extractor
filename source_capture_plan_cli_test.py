import io
import json
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory

from source_capture_plan_cli import main


VALID_ID = "dQw4w9WgXcQ"


def _run_cli(argv: list[str]):
    stdout = io.StringIO()
    stderr = io.StringIO()
    with redirect_stdout(stdout), redirect_stderr(stderr):
        code = main(argv)
    return code, stdout.getvalue(), stderr.getvalue()


def _write_json(path: Path, data) -> None:
    path.write_text(json.dumps(data), encoding="utf-8")


def run_self_test() -> None:
    with TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        input_path = root / "plan.json"
        _write_json(
            input_path,
            {
                "source_url": f"https://www.youtube.com/watch?v={VALID_ID}&t=30s",
                "source_label": "YouTube clip",
                "title": "Nicolas Cage ZoneX trailer",
                "selected_capture_options": [
                    "comments",
                    "archive_check",
                    "comments",
                    "unknown_option",
                ],
                "user_terms": ["Nyxara", "Freckelston", "Nyxara"],
            },
        )

        code, markdown, stderr = _run_cli(["--input", str(input_path)])
        assert code == 0
        assert stderr == ""
        assert "# Source Capture Plan" in markdown
        assert "Local/manual planning only" in markdown
        assert "Status: ready" in markdown
        assert f"Source ID: {VALID_ID}" in markdown
        assert "Adapter: YouTube" in markdown
        assert "unknown_option" in markdown
        assert "Nyxara" in markdown
        assert "Freckelston" in markdown
        assert "does not fetch URLs" in markdown

        code, text, stderr = _run_cli(
            ["--input", str(input_path), "--format", "text"]
        )
        assert code == 0
        assert stderr == ""
        assert "Source capture plan" in text
        assert "Status: ready" in text
        assert "Selected capture options:" in text
        assert "Context / glossary:" in text
        assert "Glossary term count: 2" in text

        code, json_output, stderr = _run_cli(
            ["--input", str(input_path), "--format", "json"]
        )
        assert code == 0
        assert stderr == ""
        parsed = json.loads(json_output)
        assert list(parsed) == sorted(parsed)
        assert parsed["status"] == "ready"
        assert parsed["source_id"] == VALID_ID
        assert parsed["adapter_name"] == "youtube"
        assert "unknown_option" in parsed["unknown_capture_options"]
        assert "comments" in parsed["duplicate_capture_options"]
        assert parsed["context_result"]["glossary_terms"][0]["text"] == "Nyxara"

        unsupported_input = root / "unsupported.json"
        _write_json(
            unsupported_input,
            {
                "source_url": "https://example.com/article",
                "source_label": "Article",
                "title": "Example Title",
                "selected_capture_options": ["comments"],
                "user_terms": ["ExampleTerm"],
            },
        )
        code, unsupported_json, stderr = _run_cli(
            ["--input", str(unsupported_input), "--format", "json"]
        )
        assert code == 0
        assert stderr == ""
        parsed_unsupported = json.loads(unsupported_json)
        assert parsed_unsupported["status"] == "unsupported_source"
        assert parsed_unsupported["normalized_url"] == ""
        assert parsed_unsupported["context_result"]["glossary_terms"][0]["text"] == "ExampleTerm"
        assert "No source adapter supports the URL" in parsed_unsupported["warnings"][0]

        output_path = root / "SOURCE_CAPTURE_PLAN.md"
        output_args = ["--input", str(input_path), "--output", str(output_path)]
        code, stdout, stderr = _run_cli(output_args)
        assert code == 0
        assert stdout == ""
        assert stderr == ""
        assert output_path.read_text(encoding="utf-8").startswith(
            "# Source Capture Plan"
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
        assert "Source Capture Plan" in output_path.read_text(encoding="utf-8")

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

        missing_url = root / "missing_url.json"
        _write_json(missing_url, {"title": "Missing URL"})
        code, stdout, stderr = _run_cli(["--input", str(missing_url)])
        assert code == 1
        assert stdout == ""
        assert "input JSON must include source_url" in stderr

        bad_options = root / "bad_options.json"
        _write_json(
            bad_options,
            {
                "source_url": f"https://www.youtube.com/watch?v={VALID_ID}",
                "selected_capture_options": "comments",
            },
        )
        code, stdout, stderr = _run_cli(["--input", str(bad_options)])
        assert code == 1
        assert stdout == ""
        assert "selected_capture_options must be a list of strings" in stderr

        bad_terms = root / "bad_terms.json"
        _write_json(
            bad_terms,
            {
                "source_url": f"https://www.youtube.com/watch?v={VALID_ID}",
                "user_terms": "Nyxara",
            },
        )
        code, stdout, stderr = _run_cli(["--input", str(bad_terms)])
        assert code == 1
        assert stdout == ""
        assert "user_terms must be a list of strings" in stderr


if __name__ == "__main__":
    run_self_test()
    print("Source capture plan CLI self-test passed.")
