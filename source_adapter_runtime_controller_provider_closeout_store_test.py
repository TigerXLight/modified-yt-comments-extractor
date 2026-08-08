from __future__ import annotations

import tempfile
from pathlib import Path

from source_adapter_runtime_controller_provider_closeout import build_source_adapter_runtime_controller_provider_closeout
from source_adapter_runtime_controller_provider_closeout_store import store_source_adapter_runtime_controller_provider_closeout
from source_adapter_runtime_controller_provider_closeout_test import fixture_runtime_operator_acceptance_closeout


def test_store_outputs() -> None:
    package = build_source_adapter_runtime_controller_provider_closeout(fixture_runtime_operator_acceptance_closeout())
    with tempfile.TemporaryDirectory() as td:
        result = store_source_adapter_runtime_controller_provider_closeout(package, td)
        assert result["store_status"] == "STORED"
        assert result["output_file_count"] == 5
        assert result["verification"]["verified"] is True
        for item in result["stored_files"]:
            assert (Path(td) / item["filename"]).exists()
            assert item["byte_count"] > 0
            assert item["sha256"]


if __name__ == "__main__":
    test_store_outputs()
    print("Source Adapter Runtime Controller Provider Closeout store self-test passed.")
