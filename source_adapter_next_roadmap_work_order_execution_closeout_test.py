from source_adapter_next_roadmap_work_order_execution_closeout import (
    HANDOFF_STATUS,
    STATUS,
    build_source_adapter_next_roadmap_work_order_execution_closeout,
)
from source_adapter_next_roadmap_section_selection_closeout import example_next_roadmap_section_selection_closeout_package


def main() -> None:
    package = build_source_adapter_next_roadmap_work_order_execution_closeout(
        example_next_roadmap_section_selection_closeout_package(),
        operator_id="tester",
    ).as_dict()
    assert package["next_roadmap_work_order_execution_closeout_status"] == STATUS
    assert package["source_adapter_next_roadmap_execution_ready_handoff"]["handoff_status"] == HANDOFF_STATUS
    assert package["source_adapter_runtime_gui_controller_hardening_manifest"]["keys_accounts_label"] == "KEYS/ACCOUNTS"
    assert package["source_adapter_priority_fixture_pack_authoring_manifest"]["fixture_pack_count"] == 5
    assert package["source_adapter_provider_execution_activation_manifest"]["provider_activation_count"] >= 4
    assert package["source_adapter_regular_regression_promotion_manifest"]["regression_promotion_count"] >= 1
    print("Source Adapter Next Roadmap Work Order Execution Closeout self-test passed.")


if __name__ == "__main__":
    main()
