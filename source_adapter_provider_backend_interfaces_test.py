from __future__ import annotations

import tempfile

from source_adapter_provider_backend_interfaces import HANDOFF_STATUS, RECEIPT_BATCH_STATUS, STATUS, build_source_adapter_provider_backend_interfaces


def main() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        package = build_source_adapter_provider_backend_interfaces(output_dir=tmpdir, operator_id="tester", execution_notes=["provider backend interface test"]).as_dict()
    assert package["provider_backend_interfaces_status"] == STATUS
    assert package["source_adapter_provider_backend_registry"]["provider_backend_row_count"] == 5
    assert package["source_adapter_provider_backend_request_matrix"]["provider_backend_request_row_count"] == 25
    receipt_batch = package["source_adapter_provider_backend_execution_receipt_batch"]
    assert receipt_batch["provider_backend_execution_receipt_batch_status"] == RECEIPT_BATCH_STATUS
    assert receipt_batch["provider_backend_execution_receipt_row_count"] == 25
    assert all(row["execution_performed"] is True for row in receipt_batch["provider_backend_execution_receipt_rows"])
    assert package["source_adapter_provider_backend_interfaces_handoff"]["handoff_status"] == HANDOFF_STATUS
    assert package["operator_summary"]["keys_accounts_label"] == "KEYS/ACCOUNTS"
    print("Source Adapter Provider Backend Interfaces self-test passed.")


if __name__ == "__main__":
    main()
