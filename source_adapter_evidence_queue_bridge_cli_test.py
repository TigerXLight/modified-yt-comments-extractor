from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

from source_adapter_evidence_queue_bridge_test import fixture_total_export_bridge


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        input_json = tmp_path / "total_export_bridge.json"
        out_dir = tmp_path / "out"
        input_json.write_text(json.dumps(fixture_total_export_bridge()), encoding="utf-8")
        completed = subprocess.run(
            [
                sys.executable,
                "source_adapter_evidence_queue_bridge_cli.py",
                "--total-export-bridge-json",
                str(input_json),
                "--output-dir",
                str(out_dir),
                "--queue-note",
                "cli",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        data = json.loads(completed.stdout)
        assert data["store_status"] == "STORED"
        assert data["queue_item_count"] == 1
        assert data["verification"]["verified"] is True


if __name__ == "__main__":
    main()
    print("Source Adapter Evidence Queue Bridge CLI self-test passed.")
