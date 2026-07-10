import contextlib
import io
import json
import tempfile
from pathlib import Path

import asr_comparison_report_cli as cli
from asr_comparison_report import default_asr_key_terms


ROOT = Path(__file__).resolve().parent
SEED_JSON = ROOT / "ASR_MANUAL_RESULTS_SEED.json"


def _run_cli(args):
    stdout = io.StringIO()
    stderr = io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        code = cli.main(args)
    return code, stdout.getvalue(), stderr.getvalue()


def run_self_test() -> None:
    code, stdout, stderr = _run_cli(["--input", str(SEED_JSON)])
    assert code == 0, stderr
    assert "ASR comparison report" in stdout
    assert "ElevenLabs / Scribe v2 with keyterms" in stdout
    assert "whisper.cpp" in stdout
    assert "GPT-4o Transcribe" in stdout
    assert "External leaderboard records" in stdout
    assert "ASR output remains draft" in stdout
    assert stderr == ""

    code, stdout, stderr = _run_cli([
        "--input",
        str(SEED_JSON),
        "--format",
        "markdown",
    ])
    assert code == 0, stderr
    assert "| Provider | Model | Status | Source | Reference accuracy |" in stdout
    assert "| ElevenLabs | Scribe v2 with keyterms |" in stdout
    assert "| GPT-4o Transcribe | Voicewriter raw/formatted WER overall |" in stdout

    code, stdout, stderr = _run_cli([
        "--input",
        str(SEED_JSON),
        "--format",
        "json",
    ])
    assert code == 0, stderr
    report = json.loads(stdout)
    assert report["record_count"] >= 20
    assert report["project_key_terms"] == list(default_asr_key_terms())
    assert report["records"][0]["provider"] == "ElevenLabs"

    code, stdout, stderr = _run_cli([
        "--input",
        str(SEED_JSON),
        "--format",
        "json",
        "--metric",
        "raw_wer_percent",
    ])
    assert code == 0, stderr
    raw_report = json.loads(stdout)
    assert raw_report["records"][0]["provider"] == "Gemini 2.5 Pro"
    assert raw_report["records"][0]["raw_wer_percent"] == 4.0

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        output_path = temp_path / "ASR_MANUAL_RESULTS_REPORT.md"
        code, stdout, stderr = _run_cli([
            "--input",
            str(SEED_JSON),
            "--format",
            "markdown",
            "--output",
            str(output_path),
        ])
        assert code == 0, stderr
        assert stdout == ""
        assert output_path.exists()
        assert "# ASR Comparison Report" in output_path.read_text(encoding="utf-8")

        code, stdout, stderr = _run_cli([
            "--input",
            str(SEED_JSON),
            "--format",
            "markdown",
            "--output",
            str(output_path),
        ])
        assert code == 1
        assert stdout == ""
        assert "already exists" in stderr

        code, stdout, stderr = _run_cli([
            "--input",
            str(SEED_JSON),
            "--format",
            "text",
            "--output",
            str(output_path),
            "--overwrite",
        ])
        assert code == 0, stderr
        assert "ASR comparison report" in output_path.read_text(encoding="utf-8")

        bare_list_path = temp_path / "bare_records.json"
        seed = json.loads(SEED_JSON.read_text(encoding="utf-8"))
        bare_list_path.write_text(
            json.dumps(seed["records"][:2], indent=2),
            encoding="utf-8",
        )
        code, stdout, stderr = _run_cli([
            "--input",
            str(bare_list_path),
            "--format",
            "json",
        ])
        assert code == 0, stderr
        assert json.loads(stdout)["record_count"] == 2

        invalid_path = temp_path / "invalid.json"
        invalid_path.write_text("{not valid json", encoding="utf-8")
        code, stdout, stderr = _run_cli(["--input", str(invalid_path)])
        assert code == 1
        assert stdout == ""
        assert "invalid JSON" in stderr

    missing_path = ROOT / "DOES_NOT_EXIST_ASR_RECORDS.json"
    code, stdout, stderr = _run_cli(["--input", str(missing_path)])
    assert code == 1
    assert stdout == ""
    assert "input file not found" in stderr

    stderr = io.StringIO()
    with contextlib.redirect_stderr(stderr):
        try:
            cli.main([])
        except SystemExit as exc:
            assert exc.code == 2
        else:
            raise AssertionError("missing --input should raise SystemExit")
    assert "--input" in stderr.getvalue()


if __name__ == "__main__":
    run_self_test()
    print("ASR comparison report CLI self-test passed.")
