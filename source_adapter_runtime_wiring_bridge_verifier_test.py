from __future__ import annotations

from source_adapter_runtime_wiring_bridge import build_source_adapter_runtime_wiring_bridge
from source_adapter_runtime_wiring_bridge_test import fixture_pipeline_closeout_bridge
from source_adapter_runtime_wiring_bridge_verifier import verify_source_adapter_runtime_wiring_bridge


def test_verifier_accepts_runtime_wiring_bridge() -> None:
    package = build_source_adapter_runtime_wiring_bridge(fixture_pipeline_closeout_bridge(), operator_approval_id="approval.verify.fixture")
    verification = verify_source_adapter_runtime_wiring_bridge(package)
    assert verification["verified"] is True
    assert verification["runtime_action_count"] == 8
    assert verification["runtime_receipt_count"] == 8


def test_verifier_rejects_missing_capability_catalog_entry() -> None:
    package = build_source_adapter_runtime_wiring_bridge(fixture_pipeline_closeout_bridge(), operator_approval_id="approval.verify.fixture")
    package["runtime_capability_catalog"] = [item for item in package["runtime_capability_catalog"] if item["capability_id"] != "archive_submit"]
    verification = verify_source_adapter_runtime_wiring_bridge(package)
    assert verification["verified"] is False
    assert any("missing required capabilities" in issue for issue in verification["issues"])


if __name__ == "__main__":
    test_verifier_accepts_runtime_wiring_bridge()
    test_verifier_rejects_missing_capability_catalog_entry()
    print("Source Adapter Runtime Wiring Bridge verifier self-test passed.")
