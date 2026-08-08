from __future__ import annotations

from source_adapter_smoke_receipt_review_integration import build_source_adapter_smoke_receipt_review_integration
from source_adapter_smoke_receipt_review_integration_verifier import verify_source_adapter_smoke_receipt_review_integration_package


def test_smoke_receipt_review_integration_accepts_receipts() -> None:
    package = build_source_adapter_smoke_receipt_review_integration().as_dict()
    decisions = package["source_adapter_smoke_receipt_review_decision_batch"]
    integration = package["source_adapter_smoke_receipt_evidence_integration"]
    assert package["smoke_receipt_review_integration_status"] == "SOURCE_ADAPTER_SMOKE_RECEIPT_REVIEW_INTEGRATION_BUILT"
    assert decisions["smoke_receipt_review_decision_row_count"] == 25
    assert decisions["accepted_review_decision_count"] == 25
    assert integration["smoke_receipt_evidence_integration_row_count"] == 5
    assert package["source_adapter_smoke_receipt_release_export_gate"]["ready_for_release_export_integration"] is True
    verification = verify_source_adapter_smoke_receipt_review_integration_package(package)
    assert verification["verified"] is True


if __name__ == "__main__":
    test_smoke_receipt_review_integration_accepts_receipts()
    print("Source Adapter Smoke Receipt Review Integration self-test passed.")
