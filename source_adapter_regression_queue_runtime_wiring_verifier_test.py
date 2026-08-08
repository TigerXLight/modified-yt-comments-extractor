from __future__ import annotations

from copy import deepcopy

from source_adapter_regression_queue_runtime_wiring import example_regression_queue_runtime_wiring_package
from source_adapter_regression_queue_runtime_wiring_verifier import verify_source_adapter_regression_queue_runtime_wiring


def main() -> None:
    package = example_regression_queue_runtime_wiring_package()
    verification = verify_source_adapter_regression_queue_runtime_wiring(package)
    assert verification["verified"] is True
    assert verification["issue_count"] == 0
    assert verification["local_runner_queue_row_count"] == 20
    assert verification["expanded_binding_row_count"] == 20
    assert verification["acceptance_receipt_row_count"] == 20

    live_package = deepcopy(package)
    live_row = live_package["source_adapter_local_regression_runner_queue_installation"]["local_runner_queue_rows"][0]
    live_row["execution_mode"] = "live"
    live_row["network_allowed"] = True
    live_verification = verify_source_adapter_regression_queue_runtime_wiring(live_package)
    assert live_verification["verified"] is False
    assert any(issue["issue_id"] in {"local_runner_row_not_dry_run", "local_runner_network_allowed_not_false"} for issue in live_verification["issues"])

    receipt_package = deepcopy(package)
    receipt_row = receipt_package["source_adapter_local_regression_acceptance_receipt_batch"]["local_regression_acceptance_receipt_rows"][0]
    receipt_row["provider_call_performed"] = True
    receipt_verification = verify_source_adapter_regression_queue_runtime_wiring(receipt_package)
    assert receipt_verification["verified"] is False
    assert any(issue["issue_id"] == "acceptance_receipt_provider_call_performed_not_false" for issue in receipt_verification["issues"])

    smoke_package = deepcopy(package)
    smoke_package["source_adapter_named_site_smoke_gate_carry_forward"]["smoke_gate_carry_forward_rows"][0]["smoke_executed"] = True
    smoke_verification = verify_source_adapter_regression_queue_runtime_wiring(smoke_package)
    assert smoke_verification["verified"] is False
    assert any(issue["issue_id"] == "smoke_gate_smoke_executed_not_false" for issue in smoke_verification["issues"])

    keys_package = deepcopy(package)
    keys_package["operator_summary"]["keys_accounts_label"] = "KEYS"
    keys_verification = verify_source_adapter_regression_queue_runtime_wiring(keys_package)
    assert keys_verification["verified"] is False
    assert any(issue["issue_id"] == "keys_accounts_label_changed" for issue in keys_verification["issues"])
    print("Source Adapter Regression Queue Runtime Wiring verifier self-test passed.")


if __name__ == "__main__":
    main()
