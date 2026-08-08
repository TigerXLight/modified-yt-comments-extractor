from __future__ import annotations

import tempfile

from source_adapter_operator_approved_execution_runtime import (
    APPROVAL_PACKET_STATUS,
    EXECUTION_QUEUE_STATUS,
    HANDOFF_STATUS,
    PROVIDER_RECEIPT_BATCH_STATUS,
    STATUS,
    build_source_adapter_operator_approved_execution_runtime,
    example_operator_inputs,
)
from source_adapter_regression_queue_runtime_wiring import example_regression_queue_runtime_wiring_package
from source_adapter_runtime_queue_closeout_audit import example_runtime_queue_closeout_audit_package


def main() -> None:
    runtime_wiring = example_regression_queue_runtime_wiring_package()
    with tempfile.TemporaryDirectory() as tmpdir:
        operator_inputs = example_operator_inputs(runtime_wiring, receipt_root=tmpdir)
        package = build_source_adapter_operator_approved_execution_runtime(
            example_runtime_queue_closeout_audit_package(),
            runtime_wiring,
            operator_inputs=operator_inputs,
            output_dir=tmpdir,
            operator_id="tester",
            execution_notes=["actual local adapter execution"],
        ).as_dict()
    assert package["operator_approved_execution_runtime_status"] == STATUS
    approval_packet = package["source_adapter_operator_approval_packet"]
    execution_queue = package["source_adapter_operator_approved_execution_queue"]
    receipt_batch = package["source_adapter_provider_execution_receipt_batch"]
    handoff = package["source_adapter_operator_approved_execution_runtime_handoff"]
    assert approval_packet["operator_approval_packet_status"] == APPROVAL_PACKET_STATUS
    assert approval_packet["approval_packet_row_count"] == 5
    assert approval_packet["approved_row_count"] == 5
    assert execution_queue["execution_queue_status"] == EXECUTION_QUEUE_STATUS
    assert execution_queue["execution_queue_row_count"] == 5
    assert len(package["source_adapter_operator_approved_execution_rows"]) == 5
    assert all(row["execution_performed"] is True for row in package["source_adapter_operator_approved_execution_rows"])
    assert receipt_batch["provider_receipt_batch_status"] == PROVIDER_RECEIPT_BATCH_STATUS
    assert receipt_batch["provider_receipt_row_count"] == 25
    assert package["source_adapter_redacted_credential_reference_ledger"]["credential_reference_ledger_row_count"] == 5
    assert handoff["handoff_status"] == HANDOFF_STATUS
    assert handoff["provider_adapter_interfaces_ready"] is True
    assert package["execution_runtime_logic"]["actual_callable_runtime_built"] is True
    assert package["execution_runtime_logic"]["all_capabilities_remain_implementation_scope"] is True
    assert package["operator_summary"]["keys_accounts_label"] == "KEYS/ACCOUNTS"
    print("Source Adapter Operator Approved Execution Runtime self-test passed.")


if __name__ == "__main__":
    main()
