from __future__ import annotations

from copy import deepcopy

from source_adapter_runtime_receipt_review_bridge import build_source_adapter_runtime_receipt_review_bridge
from source_adapter_runtime_receipt_review_bridge_test import fixture_runtime_wiring_bridge
from source_adapter_runtime_receipt_review_bridge_verifier import verify_source_adapter_runtime_receipt_review_bridge


def test_verifier_accepts_valid_runtime_receipt_review_bridge() -> None:
    package = build_source_adapter_runtime_receipt_review_bridge(fixture_runtime_wiring_bridge())
    assert verify_source_adapter_runtime_receipt_review_bridge(package)["verified"] is True


def test_verifier_rejects_missing_receipt_id() -> None:
    package = build_source_adapter_runtime_receipt_review_bridge(fixture_runtime_wiring_bridge())
    broken = deepcopy(package)
    broken["source_adapter_runtime_receipt_review_batch"]["review_rows"][0]["runtime_action_receipt_id"] = ""
    result = verify_source_adapter_runtime_receipt_review_bridge(broken)
    assert result["verified"] is False
    assert result["issue_count"] >= 1


if __name__ == "__main__":
    test_verifier_accepts_valid_runtime_receipt_review_bridge()
    test_verifier_rejects_missing_receipt_id()
    print("Source Adapter Runtime Receipt Review Bridge verifier self-test passed.")
