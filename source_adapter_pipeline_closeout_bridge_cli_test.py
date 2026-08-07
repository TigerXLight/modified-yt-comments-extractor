from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

from source_adapter_pipeline_closeout_bridge_test import fixture_archive_review_bridge


def test_cli_store_and_print() -> None:
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        input_path = root / "archive_review_bridge.json"
        input_path.write_text(json.dumps(fixture_archive_review_bridge()), encoding="utf-8")
        out_dir = root / "out"
        completed = subprocess.run(
            [
                sys.executable,
                "source_adapter_pipeline_closeout_bridge_cli.py",
                "--archive-review-bridge-json",
                str(input_path),
                "--output-dir",
                str(out_dir),
                "--operator-note",
                "CLI closeout",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        data = json.loads(completed.stdout)
        assert data["store_status"] == "STORED"
        assert data["verification"]["verified"] is True
        assert len(list(out_dir.glob("*.json"))) == 5


if __name__ == "__main__":
    test_cli_store_and_print()
    print("Source Adapter Pipeline Closeout Bridge CLI self-test passed.")
