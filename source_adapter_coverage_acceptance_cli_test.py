from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

from source_adapter_coverage_acceptance_test import _accepted_closeout


def test_cli_writes_json_store_record() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        closeout_path = root / "closeout.json"
        out_dir = root / "out"
        closeout_path.write_text(json.dumps(_accepted_closeout(), sort_keys=True), encoding="utf-8")
        result = subprocess.run(
            [
                sys.executable,
                "source_adapter_coverage_acceptance_cli.py",
                "--fixture-pipeline-closeout-json",
                str(closeout_path),
                "--output-dir",
                str(out_dir),
                "--json",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        payload = json.loads(result.stdout)
        assert payload["acceptance_status"] == "ADAPTER_COVERAGE_ACCEPTED"
        assert payload["verification"]["verified"] is True


if __name__ == "__main__":
    test_cli_writes_json_store_record()
    print("Source Adapter Coverage Acceptance CLI self-test passed.")
