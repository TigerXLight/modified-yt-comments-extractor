from __future__ import annotations

from copy import deepcopy

from source_adapter_runtime_ui_provider_integration_bridge import build_source_adapter_runtime_ui_provider_integration_bridge
from source_adapter_runtime_ui_provider_integration_bridge_test import fixture_runtime_receipt_review_bridge
from source_adapter_runtime_ui_provider_integration_bridge_verifier import verify_source_adapter_runtime_ui_provider_integration_bridge


def test_verify_runtime_ui_provider_integration_bridge() -> None:
    package = build_source_adapter_runtime_ui_provider_integration_bridge(fixture_runtime_receipt_review_bridge())
    result = verify_source_adapter_runtime_ui_provider_integration_bridge(package)
    assert result["verified"] is True
    assert result["integrated_capability_count"] == 8


def test_verifier_rejects_missing_surface_binding() -> None:
    package = build_source_adapter_runtime_ui_provider_integration_bridge(fixture_runtime_receipt_review_bridge())
    broken = deepcopy(package)
    broken["source_adapter_runtime_ui_provider_integration_batch"]["runtime_ui_provider_integration_rows"][0]["ui_surface_id"] = ""
    result = verify_source_adapter_runtime_ui_provider_integration_bridge(broken)
    assert result["verified"] is False
    assert result["issue_count"] >= 1


if __name__ == "__main__":
    test_verify_runtime_ui_provider_integration_bridge()
    test_verifier_rejects_missing_surface_binding()
    print("Source Adapter Runtime UI Provider Integration Bridge verifier self-test passed.")
