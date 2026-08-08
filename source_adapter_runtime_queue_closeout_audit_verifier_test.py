from __future__ import annotations

from copy import deepcopy

from source_adapter_runtime_queue_closeout_audit import example_runtime_queue_closeout_audit_package
from source_adapter_runtime_queue_closeout_audit_verifier import verify_source_adapter_runtime_queue_closeout_audit


def main() -> None:
    package = example_runtime_queue_closeout_audit_package()
    verification = verify_source_adapter_runtime_queue_closeout_audit(package)
    assert verification["verified"] is True
    assert verification["issue_count"] == 0
    assert verification["local_runner_queue_row_count"] == 20
    assert verification["expanded_binding_row_count"] == 20
    assert verification["acceptance_receipt_row_count"] == 20

    live_package = deepcopy(package)
    live_package["source_adapter_runtime_queue_closeout_release_gate"]["ready_for_live_smoke_execution"] = True
    live_verification = verify_source_adapter_runtime_queue_closeout_audit(live_package)
    assert live_verification["verified"] is False
    assert any(issue["issue_id"] == "release_gate_ready_for_live_smoke_execution_not_false" for issue in live_verification["issues"])

    count_package = deepcopy(package)
    count_package["source_adapter_runtime_queue_closeout_coverage_matrix"]["local_runner_queue_row_count"] = 19
    count_verification = verify_source_adapter_runtime_queue_closeout_audit(count_package)
    assert count_verification["verified"] is False
    assert any(issue["issue_id"] == "local_runner_queue_count_mismatch" for issue in count_verification["issues"])

    keys_package = deepcopy(package)
    keys_package["operator_summary"]["keys_accounts_label"] = "KEYS"
    keys_verification = verify_source_adapter_runtime_queue_closeout_audit(keys_package)
    assert keys_verification["verified"] is False
    assert any(issue["issue_id"] == "summary_keys_accounts_label_changed" for issue in keys_verification["issues"])

    roadmap_package = deepcopy(package)
    roadmap_package["source_adapter_runtime_queue_closeout_roadmap_state"]["roadmap_projection"]["named_site_smoke_still_operator_approval_gated"] = False
    roadmap_verification = verify_source_adapter_runtime_queue_closeout_audit(roadmap_package)
    assert roadmap_verification["verified"] is False
    assert any(issue["issue_id"] == "roadmap_projection_incomplete" for issue in roadmap_verification["issues"])
    print("Source Adapter Runtime Queue Closeout Audit verifier self-test passed.")


if __name__ == "__main__":
    main()
