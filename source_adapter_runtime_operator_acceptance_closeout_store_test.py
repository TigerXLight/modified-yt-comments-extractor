from __future__ import annotations

import tempfile
from pathlib import Path

from source_adapter_runtime_operator_acceptance_closeout import build_source_adapter_runtime_operator_acceptance_closeout
from source_adapter_runtime_operator_acceptance_closeout_store import store_source_adapter_runtime_operator_acceptance_closeout
from source_adapter_runtime_operator_acceptance_closeout_test import fixture_runtime_ui_provider_integration_bridge


def test_store_runtime_operator_acceptance_closeout() -> None:
    package = build_source_adapter_runtime_operator_acceptance_closeout(fixture_runtime_ui_provider_integration_bridge())
    with tempfile.TemporaryDirectory() as tmp:
        result = store_source_adapter_runtime_operator_acceptance_closeout(package, tmp)
        assert result["store_status"] == "STORED"
        assert result["output_file_count"] == 10
        assert result["verification"]["verified"] is True
        for item in result["stored_files"]:
            assert (Path(tmp) / item["filename"]).exists()
            assert item["byte_count"] > 0
            assert len(item["sha256"]) == 64


if __name__ == "__main__":
    test_store_runtime_operator_acceptance_closeout()
    print("Source Adapter Runtime Operator Acceptance Closeout store self-test passed.")
