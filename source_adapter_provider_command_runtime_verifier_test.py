from __future__ import annotations

from source_adapter_provider_command_runtime import example_provider_command_runtime_package
from source_adapter_provider_command_runtime_verifier import verify_source_adapter_provider_command_runtime_package


def test_verifier_accepts_example_package() -> None:
    result = verify_source_adapter_provider_command_runtime_package(example_provider_command_runtime_package())
    assert result["verified"] is True
    assert result["issue_count"] == 0
    assert result["provider_command_execution_receipt_row_count"] == 25


def test_verifier_rejects_missing_receipts() -> None:
    package = example_provider_command_runtime_package()
    package["source_adapter_provider_command_execution_receipt_batch"]["provider_command_execution_receipt_rows"] = []
    result = verify_source_adapter_provider_command_runtime_package(package)
    assert result["verified"] is False
    assert any(issue["issue_id"] == "unexpected_receipt_count" for issue in result["issues"])


if __name__ == "__main__":
    test_verifier_accepts_example_package()
    test_verifier_rejects_missing_receipts()
    print("Source Adapter Provider Command Runtime verifier self-test passed.")
