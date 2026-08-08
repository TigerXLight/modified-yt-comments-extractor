from __future__ import annotations

from source_adapter_named_site_smoke_execution import example_named_site_smoke_execution_package
from source_adapter_named_site_smoke_execution_verifier import verify_source_adapter_named_site_smoke_execution_package


def test_verifier_accepts_example_package() -> None:
    result = verify_source_adapter_named_site_smoke_execution_package(example_named_site_smoke_execution_package())
    assert result["verified"] is True
    assert result["issue_count"] == 0
    assert result["named_site_provider_action_receipt_row_count"] == 25


def test_verifier_rejects_missing_action_receipts() -> None:
    package = example_named_site_smoke_execution_package()
    package["source_adapter_named_site_provider_action_receipt_batch"]["named_site_provider_action_receipt_rows"] = []
    result = verify_source_adapter_named_site_smoke_execution_package(package)
    assert result["verified"] is False
    assert any(issue["issue_id"] == "unexpected_action_receipt_count" for issue in result["issues"])


if __name__ == "__main__":
    test_verifier_accepts_example_package()
    test_verifier_rejects_missing_action_receipts()
    print("Source Adapter Named-Site Smoke Execution verifier self-test passed.")
