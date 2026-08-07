from __future__ import annotations

import json
import tempfile
from pathlib import Path

from source_adapter_runtime_wiring_bridge import build_source_adapter_runtime_wiring_bridge
from source_adapter_runtime_wiring_bridge_store import store_source_adapter_runtime_wiring_bridge
from source_adapter_runtime_wiring_bridge_test import fixture_pipeline_closeout_bridge


def test_store_runtime_wiring_bridge_outputs() -> None:
    package = build_source_adapter_runtime_wiring_bridge(fixture_pipeline_closeout_bridge(), operator_approval_id="approval.store.fixture")
    with tempfile.TemporaryDirectory() as tmp:
        result = store_source_adapter_runtime_wiring_bridge(package, tmp)
        assert result["store_status"] == "STORED"
        assert result["output_file_count"] == 5
        assert result["verification"]["verified"] is True
        for item in result["stored_files"]:
            path = Path(tmp) / item["filename"]
            assert path.exists()
            assert item["byte_count"] == len(path.read_bytes())
            assert json.loads(path.read_text(encoding="utf-8")) is not None


if __name__ == "__main__":
    test_store_runtime_wiring_bridge_outputs()
    print("Source Adapter Runtime Wiring Bridge store self-test passed.")
