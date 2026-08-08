from __future__ import annotations

from source_adapter_runtime_queue_closeout_audit import (
    COVERAGE_MATRIX_STATUS,
    OPERATOR_HANDOFF_STATUS,
    RELEASE_GATE_STATUS,
    ROADMAP_STATE_STATUS,
    STATUS,
    build_source_adapter_runtime_queue_closeout_audit,
)
from source_adapter_regression_queue_runtime_wiring import example_regression_queue_runtime_wiring_package


def main() -> None:
    package = build_source_adapter_runtime_queue_closeout_audit(
        example_regression_queue_runtime_wiring_package(),
        operator_id="tester",
        closeout_notes=["local closeout audit"],
    ).as_dict()
    assert package["runtime_queue_closeout_audit_status"] == STATUS
    coverage = package["source_adapter_runtime_queue_closeout_coverage_matrix"]
    roadmap = package["source_adapter_runtime_queue_closeout_roadmap_state"]
    release_gate = package["source_adapter_runtime_queue_closeout_release_gate"]
    handoff = package["source_adapter_runtime_queue_closeout_operator_handoff"]
    assert coverage["coverage_matrix_status"] == COVERAGE_MATRIX_STATUS
    assert coverage["coverage_row_count"] >= 6
    assert coverage["local_runner_queue_row_count"] == 20
    assert coverage["expanded_binding_row_count"] == 20
    assert coverage["acceptance_receipt_row_count"] == 20
    assert coverage["named_site_smoke_gate_row_count"] == 5
    assert roadmap["roadmap_state_status"] == ROADMAP_STATE_STATUS
    assert roadmap["roadmap_projection"]["runtime_closeout_audit_recorded"] is True
    assert release_gate["release_gate_status"] == RELEASE_GATE_STATUS
    assert release_gate["ready_for_operator_named_site_selection"] is True
    assert release_gate["ready_for_live_smoke_execution"] is False
    assert release_gate["ready_for_network_or_provider_calls"] is False
    assert handoff["handoff_status"] == OPERATOR_HANDOFF_STATUS
    assert handoff["named_site_smoke_still_approval_gated"] is True
    assert package["operator_summary"]["keys_accounts_label"] == "KEYS/ACCOUNTS"
    print("Source Adapter Runtime Queue Closeout Audit self-test passed.")


if __name__ == "__main__":
    main()
