from __future__ import annotations

from source_adapter_smoke_receipt_review_integration import example_smoke_receipt_review_integration_package
from source_adapter_smoke_receipt_review_integration_verifier import verify_source_adapter_smoke_receipt_review_integration_package


def test_verifier_accepts_example_package() -> None:
    result = verify_source_adapter_smoke_receipt_review_integration_package(example_smoke_receipt_review_integration_package())
    assert result["verified"] is True
    assert result["issue_count"] == 0
    assert result["smoke_receipt_review_decision_row_count"] == 25


def test_verifier_rejects_missing_decisions() -> None:
    package = example_smoke_receipt_review_integration_package()
    package["source_adapter_smoke_receipt_review_decision_batch"]["smoke_receipt_review_decision_rows"] = []
    result = verify_source_adapter_smoke_receipt_review_integration_package(package)
    assert result["verified"] is False
    assert any(issue["issue_id"] == "unexpected_decision_count" for issue in result["issues"])


if __name__ == "__main__":
    test_verifier_accepts_example_package()
    test_verifier_rejects_missing_decisions()
    print("Source Adapter Smoke Receipt Review Integration verifier self-test passed.")
