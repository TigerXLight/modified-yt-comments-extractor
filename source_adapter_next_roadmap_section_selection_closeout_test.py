from source_adapter_next_roadmap_section_selection_closeout import (
    HANDOFF_STATUS,
    STATUS,
    build_source_adapter_next_roadmap_section_selection_closeout,
    example_next_roadmap_section_selection_closeout_package,
)
from source_adapter_release_regression_next_roadmap_closeout import example_release_regression_next_roadmap_closeout_package


def main() -> None:
    package = example_next_roadmap_section_selection_closeout_package()
    assert package["next_roadmap_section_selection_closeout_status"] == STATUS
    assert package["source_adapter_next_roadmap_ready_handoff"]["handoff_status"] == HANDOFF_STATUS
    assert package["source_adapter_next_roadmap_section_selection_index"]["selected_section_count"] == 6
    assert package["source_adapter_next_roadmap_work_order_manifest"]["ready_work_order_count"] == 6
    limited = build_source_adapter_next_roadmap_section_selection_closeout(
        example_release_regression_next_roadmap_closeout_package(),
        selected_sections=["regular_regression_promotion", "documentation_handoff_refresh"],
    ).as_dict()
    assert limited["source_adapter_next_roadmap_section_selection_index"]["selected_section_count"] == 2
    assert limited["operator_summary"]["keys_accounts_label"] == "KEYS/ACCOUNTS"
    print("Source Adapter Next Roadmap Section Selection Closeout self-test passed.")


if __name__ == "__main__":
    main()
