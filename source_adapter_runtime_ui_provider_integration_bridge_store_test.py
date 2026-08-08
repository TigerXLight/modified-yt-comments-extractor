from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from source_adapter_runtime_ui_provider_integration_bridge_store import store_source_adapter_runtime_ui_provider_integration_bridge
from source_adapter_runtime_ui_provider_integration_bridge_test import fixture_runtime_receipt_review_bridge
from source_adapter_runtime_ui_provider_integration_bridge import build_source_adapter_runtime_ui_provider_integration_bridge


def test_store_runtime_ui_provider_integration_bridge() -> None:
    package = build_source_adapter_runtime_ui_provider_integration_bridge(fixture_runtime_receipt_review_bridge())
    with TemporaryDirectory() as tmp:
        receipt = store_source_adapter_runtime_ui_provider_integration_bridge(package, tmp)
        assert receipt["store_status"] == "STORED"
        assert receipt["output_file_count"] == 5
        assert receipt["verification"]["verified"] is True
        assert len(list(Path(tmp).glob("*.json"))) == 5


if __name__ == "__main__":
    test_store_runtime_ui_provider_integration_bridge()
    print("Source Adapter Runtime UI Provider Integration Bridge store self-test passed.")
