from __future__ import annotations

import json
import tempfile
from pathlib import Path

from source_adapter_runtime_controller_provider_closeout import build_source_adapter_runtime_controller_provider_closeout
from source_adapter_runtime_controller_provider_closeout_test import fixture_runtime_operator_acceptance_closeout
from source_adapter_runtime_fixture_smoke_final_closeout_cli import main


def test_cli_fixture_smoke_final_closeout_store() -> None:
    controller = build_source_adapter_runtime_controller_provider_closeout(fixture_runtime_operator_acceptance_closeout())
    with tempfile.TemporaryDirectory() as td:
        input_path = Path(td) / "controller_provider_closeout.json"
        out_dir = Path(td) / "out"
        input_path.write_text(json.dumps(controller, sort_keys=True), encoding="utf-8")
        code = main([
            "--controller-provider-closeout-json",
            str(input_path),
            "--output-dir",
            str(out_dir),
            "--operator-id",
            "operator.fixture",
            "--closeout-note",
            "cli fixture smoke closeout",
        ])
        assert code == 0
        assert len(list(out_dir.glob("*.json"))) == 5


def test_cli_capability_subset() -> None:
    controller = build_source_adapter_runtime_controller_provider_closeout(fixture_runtime_operator_acceptance_closeout())
    with tempfile.TemporaryDirectory() as td:
        input_path = Path(td) / "controller_provider_closeout.json"
        input_path.write_text(json.dumps(controller, sort_keys=True), encoding="utf-8")
        code = main([
            "--controller-provider-closeout-json",
            str(input_path),
            "--capability",
            "archive_submit",
            "--capability",
            "credential_lookup",
        ])
        assert code == 0


if __name__ == "__main__":
    test_cli_fixture_smoke_final_closeout_store()
    test_cli_capability_subset()
    print("Source Adapter Runtime Fixture Smoke Final Closeout CLI self-test passed.")
