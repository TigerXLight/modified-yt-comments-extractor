from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        cmd = [
            sys.executable,
            "source_adapter_roadmap_audit_final_closeout_cli.py",
            "--output-dir",
            tmp,
            "--operator-id",
            "cli_operator",
            "--release-note",
            "CLI release note.",
        ]
        completed = subprocess.run(cmd, check=True, capture_output=True, text=True)
        result = json.loads(completed.stdout)
        assert result["store_status"] == "STORED"
        assert result["verification"]["verified"] is True
        assert len(list(Path(tmp).glob("*.json"))) == 5
    print("Source Adapter Roadmap Audit Final Closeout CLI self-test passed.")


if __name__ == "__main__":
    main()
