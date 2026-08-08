from __future__ import annotations

from tempfile import TemporaryDirectory

from source_adapter_runtime_receipt_review_bridge import build_source_adapter_runtime_receipt_review_bridge
from source_adapter_runtime_receipt_review_bridge_store import store_source_adapter_runtime_receipt_review_bridge
from source_adapter_runtime_receipt_review_bridge_test import fixture_runtime_wiring_bridge


def test_store_runtime_receipt_review_bridge() -> None:
    package = build_source_adapter_runtime_receipt_review_bridge(fixture_runtime_wiring_bridge())
    with TemporaryDirectory() as tmp:
        result = store_source_adapter_runtime_receipt_review_bridge(package, tmp)
    assert result["store_status"] == "STORED"
    assert result["output_file_count"] == 5
    assert result["verification"]["verified"] is True


if __name__ == "__main__":
    test_store_runtime_receipt_review_bridge()
    print("Source Adapter Runtime Receipt Review Bridge store self-test passed.")
