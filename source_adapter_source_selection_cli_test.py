from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

from source_adapter_source_selection import demo_rollout_package, write_json


def run_cli(*args: str) -> dict:
    completed = subprocess.run(
        [sys.executable, "source_adapter_source_selection_cli.py", *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(completed.stdout)


def test_cli_prints_package() -> None:
    package = run_cli()
    assert package["selection_status"] == "SOURCE_ADAPTER_SELECTION_READY"
    assert package["adapter_count"] == 1


def test_cli_verify() -> None:
    verification = run_cli("--verify")
    assert verification["verified"] is True
    assert verification["issue_count"] == 0


def test_cli_store_from_file() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = Path(tmpdir) / "rollout.json"
        output_dir = Path(tmpdir) / "out"
        write_json(input_path, demo_rollout_package())
        summary = run_cli("--rollout-package", str(input_path), "--output-dir", str(output_dir))
        assert summary["store_status"] == "STORED"
        assert summary["output_file_count"] == 5


if __name__ == "__main__":
    test_cli_prints_package()
    test_cli_verify()
    test_cli_store_from_file()
    print("Source Adapter Source Selection CLI self-test passed.")
