import io
import json
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory

from asr_decision_summary_cli import main


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
    assert "# ASR Decision Summary" in markdown
    assert "Strict project threshold: 95.00%" in markdown
    assert "Accepted: 0" in markdown
    assert "Blocked: 1" in markdown
    assert "Best project-scored result: ElevenLabs / Scribe v2 with keyterms" in markdown
    assert "External leaderboard/research leads" in markdown

    with TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)

        object_input = root / "seed_object.json"
        object_input.write_text(json.dumps(seed), encoding="utf-8")

        code, text, stderr = _run_cli(
            ["--input", str(object_input), "--format", "text"]
        )
        assert code == 0
        assert stderr == ""
        assert "ASR decision summary" in text
        assert "Project-scored count: 11" in text
        assert "External-lead count: 13" in text
        assert "AWS Transcribe / Batch transcription with custom vocabulary" in text
        assert "Keep ASR output as draft text" in text

        list_input = root / "seed_list.json"
        list_input.write_text(json.dumps(seed["records"]), encoding="utf-8")
        code, list_markdown, stderr = _run_cli(["--input", str(list_input)])
        assert code == 0
        assert stderr == ""
        assert "# ASR Decision Summary" in list_markdown
        assert "Candidate: 7" in list_markdown

        code, json_output, stderr = _run_cli(
            ["--input", str(object_input), "--format", "json"]
        )
        assert code == 0
        assert stderr == ""
        parsed = json.loads(json_output)
        assert list(parsed) == sorted(parsed)
        assert parsed["record_count"] == len(seed["records"])
        assert parsed["project_scored_count"] == 11
        assert parsed["accepted_count"] == 0
        assert parsed["blocked_count"] == 1
        assert parsed["external_lead_count"] == 13
        assert parsed["below_threshold_count"] == 11
        assert parsed["best_scored_label"] == "ElevenLabs / Scribe v2 with keyterms"
        assert parsed["best_scored_accuracy_percent"] == 84.95
        assert parsed["best_local_label"] == "whisper.cpp / Vulkan large-v3-turbo phrase prompt"
        assert parsed["best_local_accuracy_percent"] == 74.19

        output_path = root / "ASR_DECISION_SUMMARY_REPORT.md"
        output_args = ["--input", str(object_input), "--output", str(output_path)]
        code, stdout, stderr = _run_cli(output_args)
        assert code == 0
        assert stdout == ""
        assert stderr == ""
        assert output_path.read_text(encoding="utf-8").startswith(
            "# ASR Decision Summary"
        )

        code, stdout, stderr = _run_cli(output_args)
        assert code == 1
        assert stdout == ""
        assert "output path already exists" in stderr
        assert output_path.read_text(encoding="utf-8").startswith(
            "# ASR Decision Summary"
        )

        output_path.write_text("old\n", encoding="utf-8")
        code, stdout, stderr = _run_cli([*output_args, "--overwrite"])
        assert code == 0
        assert stdout == ""
        assert stderr == ""
        assert "Strict project threshold: 95.00%" in output_path.read_text(
            encoding="utf-8"
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


if __name__ == "__main__":
    run_self_test()
    print("ASR decision summary CLI self-test passed.")
