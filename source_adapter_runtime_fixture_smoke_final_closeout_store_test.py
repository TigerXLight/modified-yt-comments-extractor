from __future__ import annotations

import tempfile
from pathlib import Path

from source_adapter_runtime_controller_provider_closeout import build_source_adapter_runtime_controller_provider_closeout
from source_adapter_runtime_controller_provider_closeout_test import fixture_runtime_operator_acceptance_closeout
from source_adapter_runtime_fixture_smoke_final_closeout import build_source_adapter_runtime_fixture_smoke_final_closeout
from source_adapter_runtime_fixture_smoke_final_closeout_store import store_source_adapter_runtime_fixture_smoke_final_closeout


def test_store_fixture_smoke_final_closeout() -> None:
    controller = build_source_adapter_runtime_controller_provider_closeout(fixture_runtime_operator_acceptance_closeout())
    package = build_source_adapter_runtime_fixture_smoke_final_closeout(controller)
    with tempfile.TemporaryDirectory() as td:
        result = store_source_adapter_runtime_fixture_smoke_final_closeout(package, td)
        assert result["store_status"] == "STORED"
        assert result["output_file_count"] == 5
        assert result["verification"]["verified"] is True
        for stored in result["stored_files"]:
            path = Path(td) / stored["filename"]
            assert path.exists()
            assert path.stat().st_size == stored["byte_count"]


if __name__ == "__main__":
    test_store_fixture_smoke_final_closeout()
    print("Source Adapter Runtime Fixture Smoke Final Closeout store self-test passed.")
