from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

from source_adapter_runtime_operator_acceptance_closeout_test import fixture_runtime_ui_provider_integration_bridge


def test_cli_runtime_operator_acceptance_closeout() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        input_path = Path(tmp) / "runtime_ui_provider_integration.json"
        output_dir = Path(tmp) / "out"
        input_path.write_text(json.dumps(fixture_runtime_ui_provider_integration_bridge(), indent=2, sort_keys=True), encoding="utf-8")
        result = subprocess.run(
            [
                sys.executable,
                "source_adapter_runtime_operator_acceptance_closeout_cli.py",
                "--runtime-ui-provider-integration-json",
                str(input_path),
                "--output-dir",
                str(output_dir),
                "--operator-id",
                "operator.fixture",
                "--acceptance-note",
                "accept for manual smoke",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        payload = json.loads(result.stdout)
        assert payload["verification"]["verified"] is True
        assert payload["accepted_capability_count"] == 8
        assert payload["output_file_count"] == 10


if __name__ == "__main__":
    test_cli_runtime_operator_acceptance_closeout()
    print("Source Adapter Runtime Operator Acceptance Closeout CLI self-test passed.")
