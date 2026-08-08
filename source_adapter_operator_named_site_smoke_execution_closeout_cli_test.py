from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


def main() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        completed = subprocess.run(
            [sys.executable, "source_adapter_operator_named_site_smoke_execution_closeout_cli.py", "--output-dir", temp_dir, "--operator-id", "cli_operator"],
            check=True,
            capture_output=True,
            text=True,
        )
        result = json.loads(completed.stdout)
        assert result["store_status"] == "STORED"
        assert result["verification"]["verified"], result
        assert len(list(Path(temp_dir).glob("*.json"))) == result["output_file_count"]
    print("Source Adapter Operator Named Site Smoke Execution Closeout CLI self-test passed.")


if __name__ == "__main__":
    main()
