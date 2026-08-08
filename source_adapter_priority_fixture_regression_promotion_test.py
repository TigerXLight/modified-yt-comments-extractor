from __future__ import annotations

from source_adapter_priority_fixture_pack_implementation import example_priority_fixture_pack_implementation_package
from source_adapter_priority_fixture_regression_promotion import (
    GUI_CALL_SITE_PLAN_STATUS,
    HANDOFF_STATUS,
    NAMED_SITE_SMOKE_GATE_STATUS,
    REGRESSION_QUEUE_STATUS,
    STATUS,
    build_source_adapter_priority_fixture_regression_promotion,
)


def main() -> None:
    package = build_source_adapter_priority_fixture_regression_promotion(
        example_priority_fixture_pack_implementation_package(),
        operator_id="tester",
        promotion_notes=["local regular regression promotion"],
    ).as_dict()
    assert package["priority_fixture_regression_promotion_status"] == STATUS
    assert package["source_adapter_priority_fixture_regression_promotion_handoff"]["handoff_status"] == HANDOFF_STATUS
    queue = package["source_adapter_priority_fixture_regression_queue"]
    gui_plan = package["source_adapter_gui_controller_call_site_installation_plan"]
    smoke_gate = package["source_adapter_named_site_smoke_operator_approval_gate"]
    assert queue["regression_queue_status"] == REGRESSION_QUEUE_STATUS
    assert queue["fixture_pack_count"] == 5
    assert queue["source_dispatch_receipt_count"] == 20
    assert queue["promoted_regression_queue_row_count"] == 20
    assert {row["execution_mode"] for row in queue["promoted_regression_queue_rows"]} == {"dry_run"}
    assert not any(row["live_execution_allowed"] for row in queue["promoted_regression_queue_rows"])
    assert gui_plan["gui_controller_call_site_installation_plan_status"] == GUI_CALL_SITE_PLAN_STATUS
    assert gui_plan["call_site_installation_row_count"] >= 4
    assert smoke_gate["named_site_smoke_approval_gate_status"] == NAMED_SITE_SMOKE_GATE_STATUS
    assert smoke_gate["named_site_smoke_gate_row_count"] == 5
    assert not any(row["smoke_executed"] for row in smoke_gate["named_site_smoke_gate_rows"])
    assert package["operator_summary"]["keys_accounts_label"] == "KEYS/ACCOUNTS"
    print("Source Adapter Priority Fixture Regression Promotion self-test passed.")


if __name__ == "__main__":
    main()
