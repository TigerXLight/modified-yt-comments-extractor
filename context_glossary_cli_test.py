import io
import json
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory

from context_glossary_cli import main


def _run_cli(argv: list[str]):
    stdout = io.StringIO()
    stderr = io.StringIO()
    with redirect_stdout(stdout), redirect_stderr(stderr):
        code = main(argv)
    return code, stdout.getvalue(), stderr.getvalue()

def _assert_cli_failure(argv: list[str], expected_error: str) -> str:
    code, stdout, stderr = _run_cli(argv)
    assert code == 1
    assert stdout == ""
    assert expected_error in stderr
    return stderr



def _write_json(path: Path, data) -> None:
    path.write_text(json.dumps(data), encoding="utf-8")


def run_self_test() -> None:
    with TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        input_path = root / "context.json"
        _write_json(
            input_path,
            {
                "source_label": "YouTube clip",
                "source_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                "title": "Nicolas Cage ZoneX trailer",
                "user_terms": ["Nyxara", "Freckelston", "Nyxara"],
            },
        )

        code, markdown, stderr = _run_cli(["--input", str(input_path)])
        assert code == 0
        assert stderr == ""
        assert "# Context / Glossary Report" in markdown
        assert "Local/manual context and glossary normalization only" in markdown
        assert "Source label: YouTube clip" in markdown
        assert "Context hint count: 3" in markdown
        assert "Glossary term count: 2" in markdown
        assert "Phrase prompt term count: 2" in markdown
        assert "Nyxara" in markdown
        assert "Freckelston" in markdown
        assert "User review is required" in markdown
        assert "does not fetch URLs" in markdown

        code, text, stderr = _run_cli(
            ["--input", str(input_path), "--format", "text"]
        )
        assert code == 0
        assert stderr == ""
        assert "Context / glossary report" in text
        assert "Context hint count: 3" in text
        assert "Glossary term count: 2" in text
        assert "Phrase prompt terms:" in text
        assert "User review required" in text

        code, json_output, stderr = _run_cli(
            ["--input", str(input_path), "--format", "json"]
        )
        assert code == 0
        assert stderr == ""
        parsed = json.loads(json_output)
        assert list(parsed) == sorted(parsed)
        assert parsed["source_label"] == "YouTube clip"
        assert parsed["source_url"] == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        assert len(parsed["context_hints"]) == 3
        assert parsed["glossary_terms"][0]["text"] == "Nyxara"
        assert parsed["phrase_prompt_terms"] == ["Nyxara", "Freckelston"]
        assert "no fetch" in parsed["scope"]

        minimal_input = root / "minimal.json"
        _write_json(minimal_input, {})
        code, minimal_json, stderr = _run_cli(
            ["--input", str(minimal_input), "--format", "json"]
        )
        assert code == 0
        assert stderr == ""
        parsed_minimal = json.loads(minimal_json)
        assert parsed_minimal["source_label"] == ""
        assert parsed_minimal["source_url"] == ""
        assert parsed_minimal["context_hints"] == []
        assert parsed_minimal["glossary_terms"] == []

        output_path = root / "CONTEXT_GLOSSARY_REPORT.md"
        output_args = ["--input", str(input_path), "--output", str(output_path)]
        code, stdout, stderr = _run_cli(output_args)
        assert code == 0
        assert stdout == ""
        assert stderr == ""
        assert output_path.read_text(encoding="utf-8").startswith(
            "# Context / Glossary Report"
        )

        _assert_cli_failure(output_args, 'output path already exists')

        output_path.write_text("old\n", encoding="utf-8")
        code, stdout, stderr = _run_cli([*output_args, "--overwrite"])
        assert code == 0
        assert stdout == ""
        assert stderr == ""
        assert "Context / Glossary Report" in output_path.read_text(
            encoding="utf-8"
        )

        missing_input = root / "missing.json"
        _assert_cli_failure(["--input", str(missing_input)], 'input file not found')

        invalid_input = root / "invalid.json"
        invalid_input.write_text("{not json\n", encoding="utf-8")
        _assert_cli_failure(["--input", str(invalid_input)], 'invalid JSON')

        list_input = root / "list.json"
        _write_json(list_input, [])
        _assert_cli_failure(["--input", str(list_input)], 'input JSON must be an object')

        bad_terms = root / "bad_terms.json"
        _write_json(bad_terms, {"user_terms": "Nyxara"})
        _assert_cli_failure(["--input", str(bad_terms)], 'user_terms must be a list of strings')


if __name__ == "__main__":
    run_self_test()
    print("Context glossary CLI self-test passed.")
