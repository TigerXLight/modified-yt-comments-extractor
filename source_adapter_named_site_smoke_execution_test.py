from __future__ import annotations

from pathlib import Path

from source_adapter_named_site_smoke_execution import build_source_adapter_named_site_smoke_execution
from source_adapter_named_site_smoke_execution_verifier import verify_source_adapter_named_site_smoke_execution_package


def test_named_site_smoke_execution_records_receipts() -> None:
    package = build_source_adapter_named_site_smoke_execution().as_dict()
    matrix = package["source_adapter_named_site_smoke_execution_matrix"]
    batch = package["source_adapter_named_site_provider_action_receipt_batch"]
    assert package["named_site_smoke_execution_status"] == "SOURCE_ADAPTER_NAMED_SITE_SMOKE_EXECUTION_BUILT"
    assert matrix["named_site_execution_site_count"] == 5
    assert batch["named_site_provider_action_receipt_row_count"] == 25
    assert batch["successful_action_receipt_count"] == 25
    assert Path(package["source_adapter_named_site_smoke_execution_manifest"]["manifest_path"]).exists()
    verification = verify_source_adapter_named_site_smoke_execution_package(package)
    assert verification["verified"] is True


if __name__ == "__main__":
    test_named_site_smoke_execution_records_receipts()
    print("Source Adapter Named-Site Smoke Execution self-test passed.")
