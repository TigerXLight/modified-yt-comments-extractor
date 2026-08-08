from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

from source_adapter_runtime_operator_acceptance_closeout import build_source_adapter_runtime_operator_acceptance_closeout
from source_adapter_runtime_operator_acceptance_closeout_test import fixture_runtime_ui_provider_integration_bridge


def test_cli_store_outputs() -> None:
    accepted = build_source_adapter_runtime_operator_acceptance_closeout(fixture_runtime_ui_provider_integration_bridge())
    with tempfile.TemporaryDirectory() as td:
        src = Path(td) / "operator_acceptance_closeout.json"
        out = Path(td) / "out"
        src.write_text(json.dumps(accepted, sort_keys=True), encoding="utf-8")
        proc = subprocess.run(
            [
                sys.executable,
                "source_adapter_runtime_controller_provider_closeout_cli.py",
                "--operator-acceptance-closeout-json",
                str(src),
                "--output-dir",
                str(out),
                "--operator-id",
                "operator.fixture",
                "--capability",
                "credential_lookup",
                "--capability",
                "archive_submit",
            ],
            text=True,
            capture_output=True,
            check=True,
        )
        result = json.loads(proc.stdout)
        assert result["store_status"] == "STORED"
        assert result["capability_count"] == 2
        assert result["verification"]["verified"] is True


if __name__ == "__main__":
    test_cli_store_outputs()
    print("Source Adapter Runtime Controller Provider Closeout CLI self-test passed.")
