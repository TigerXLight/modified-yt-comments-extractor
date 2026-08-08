from __future__ import annotations

from source_adapter_priority_fixture_regression_promotion import example_priority_fixture_regression_promotion_package
from source_adapter_regression_queue_runtime_wiring import (
    ACCEPTANCE_RECEIPT_BATCH_STATUS,
    EXPANDED_BINDING_STATUS,
    GUI_CALL_SITE_WIRING_STATUS,
    HANDOFF_STATUS,
    LOCAL_RUNNER_QUEUE_STATUS,
    SMOKE_GATE_CARRY_FORWARD_STATUS,
    STATUS,
    build_source_adapter_regression_queue_runtime_wiring,
)
from source_adapter_runtime_gui_provider_implementation import example_runtime_gui_provider_implementation_package


def main() -> None:
    package = build_source_adapter_regression_queue_runtime_wiring(
        example_priority_fixture_regression_promotion_package(),
        example_runtime_gui_provider_implementation_package(),
        operator_id="tester",
        wiring_notes=["local runtime wiring"],
    ).as_dict()
    assert package["regression_queue_runtime_wiring_status"] == STATUS
    assert package["source_adapter_regression_queue_runtime_wiring_handoff"]["handoff_status"] == HANDOFF_STATUS
    local_queue = package["source_adapter_local_regression_runner_queue_installation"]
    bindings = package["source_adapter_runtime_controller_provider_expanded_binding_matrix"]
    gui_wiring = package["source_adapter_gui_controller_call_site_runtime_wiring"]
    receipts = package["source_adapter_local_regression_acceptance_receipt_batch"]
    smoke_gate = package["source_adapter_named_site_smoke_gate_carry_forward"]
    assert local_queue["local_runner_queue_status"] == LOCAL_RUNNER_QUEUE_STATUS
    assert local_queue["local_runner_queue_row_count"] == 20
    assert local_queue["installed_queue_row_count"] == 20
    assert bindings["expanded_binding_matrix_status"] == EXPANDED_BINDING_STATUS
    assert bindings["expanded_binding_row_count"] == 20
    assert gui_wiring["gui_call_site_runtime_wiring_status"] == GUI_CALL_SITE_WIRING_STATUS
    assert gui_wiring["call_site_wiring_row_count"] >= 4
    assert receipts["acceptance_receipt_batch_status"] == ACCEPTANCE_RECEIPT_BATCH_STATUS
    assert receipts["acceptance_receipt_row_count"] == 20
    assert smoke_gate["smoke_gate_carry_forward_status"] == SMOKE_GATE_CARRY_FORWARD_STATUS
    assert smoke_gate["named_site_smoke_gate_row_count"] == 5
    assert not any(row["provider_call_performed"] for row in local_queue["local_runner_queue_rows"])
    assert not any(row["live_execution_allowed"] for row in receipts["local_regression_acceptance_receipt_rows"])
    assert not any(row["smoke_executed"] for row in smoke_gate["smoke_gate_carry_forward_rows"])
    assert package["operator_summary"]["keys_accounts_label"] == "KEYS/ACCOUNTS"
    print("Source Adapter Regression Queue Runtime Wiring self-test passed.")


if __name__ == "__main__":
    main()
