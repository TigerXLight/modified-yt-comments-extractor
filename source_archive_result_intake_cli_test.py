from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from source_archive_result_intake_test import _handoff_package, _operator_result
from source_archive_result_intake_cli import main


def test_cli_builds_and_stores_result_intake() -> None:
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        handoff_path = root / "archive_handoff.json"
        result_path = root / "archive_result.json"
        output_dir = root / "out"
        handoff_path.write_text(json.dumps(_handoff_package()), encoding="utf-8")
        result_path.write_text(json.dumps(_operator_result()), encoding="utf-8")
        exit_code = main(
            [
                "--archive-handoff-json",
                str(handoff_path),
                "--archive-result-json",
                str(result_path),
                "--operator-id",
                "operator_one",
                "--intake-note",
                "CLI fixture intake.",
                "--output-dir",
                str(output_dir),
            ]
        )
        assert exit_code == 0
        stored_files = list(output_dir.glob("*.json"))
        assert len(stored_files) == 4


if __name__ == "__main__":
    test_cli_builds_and_stores_result_intake()
    print("Source Archive Result Intake CLI self-test passed.")
