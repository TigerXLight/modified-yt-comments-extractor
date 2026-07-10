import io
import json
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory

from asr_term_coverage_summary_cli import main


ROOT = Path(__file__).resolve().parent
SEED_JSON = ROOT / "ASR_MANUAL_RESULTS_SEED.json"


def _run_cli(argv: list[str]):
    stdout = io.StringIO()
    stderr = io.StringIO()
    with redirect_stdout(stdout), redirect_stderr(stderr):
        code = main(argv)
    return code, stdout.getvalue(), stderr.getvalue()


def _load_seed():
    with SEED_JSON.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def run_self_test() -> None:
    seed = _load_seed()

    code, markdown, stderr = _run_cli(["--input", str(SEED_JSON)])
    assert code == 0
    assert stderr == ""
    assert "# ASR Term Coverage / Gap Summary" in markdown
    assert "Tracked term count: 7" in markdown
    assert "Blocked rows excluded from term rates: 1" in markdown
    assert "External/user-observation leads excluded" in markdown
    assert "does not call providers" in markdown

    with TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)

        object_input = root / "seed_object.json"
        object_input.write_text(json.dumps(seed), encoding="utf-8")

        code, text, stderr = _run_cli(
            ["--input", str(object_input), "--format", "text"]
        )
        assert code == 0
        assert stderr == ""
        assert "ASR term coverage / gap summary" in text
        assert "Tracked term count: 7" in text
        assert "Blocked rows excluded from term rates: 1" in text
        assert "ElevenLabs / Scribe v2 with keyterms: missed Kingman" in text
        assert "ASR output remains draft" in text

        list_input = root / "seed_list.json"
        list_input.write_text(json.dumps(seed["records"]), encoding="utf-8")
        code, list_markdown, stderr = _run_cli(["--input", str(list_input)])
        assert code == 0
        assert stderr == ""
        assert "# ASR Term Coverage / Gap Summary" in list_markdown
        assert "Known phrase hits: 1" in list_markdown

        code, json_output, stderr = _run_cli(
            ["--input", str(object_input), "--format", "json"]
        )
        assert code == 0
        assert stderr == ""
        parsed = json.loads(json_output)
        assert list(parsed) == sorted(parsed)
        assert parsed["record_count"] == len(seed["records"])
        assert parsed["project_scored_count"] == 11
        assert parsed["blocked_count"] == 1
        assert parsed["external_lead_count"] == 13
        assert parsed["tracked_term_count"] == 7
        assert parsed["known_phrase_hit_count"] == 1
        assert "Kingman" in parsed["consistently_missed_terms"]
        assert "Nicolas Cage" in parsed["mixed_terms"]

        output_path = root / "ASR_TERM_COVERAGE_REPORT.md"
        output_args = ["--input", str(object_input), "--output", str(output_path)]
        code, stdout, stderr = _run_cli(output_args)
        assert code == 0
        assert stdout == ""
        assert stderr == ""
        assert output_path.read_text(encoding="utf-8").startswith(
            "# ASR Term Coverage / Gap Summary"
        )

        code, stdout, stderr = _run_cli(output_args)
        assert code == 1
        assert stdout == ""
        assert "output path already exists" in stderr
        assert output_path.read_text(encoding="utf-8").startswith(
            "# ASR Term Coverage / Gap Summary"
        )

        output_path.write_text("old\n", encoding="utf-8")
        code, stdout, stderr = _run_cli([*output_args, "--overwrite"])
        assert code == 0
        assert stdout == ""
        assert stderr == ""
        assert "Tracked term count: 7" in output_path.read_text(encoding="utf-8")

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


if __name__ == "__main__":
    run_self_test()
    print("ASR term coverage summary CLI self-test passed.")
