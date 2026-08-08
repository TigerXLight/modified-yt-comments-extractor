from source_adapter_release_regression_next_roadmap_closeout import (
    HANDOFF_STATUS,
    STATUS,
    example_release_regression_next_roadmap_closeout_package,
)


def main() -> None:
    package = example_release_regression_next_roadmap_closeout_package()
    assert package["release_regression_next_roadmap_closeout_status"] == STATUS
    assert package["source_adapter_next_roadmap_handoff"]["handoff_status"] == HANDOFF_STATUS
    assert package["source_adapter_release_notes_manifest"]["section_count"] >= 1
    assert package["source_adapter_regular_regression_promotion_queue"]["ready_queue_row_count"] >= 1
    assert package["source_adapter_operator_live_execution_monitor_manifest"]["ready_monitor_row_count"] >= 1
    assert package["operator_summary"]["keys_accounts_label"] == "KEYS/ACCOUNTS"
    print("Source Adapter Release Regression Next Roadmap Closeout self-test passed.")


if __name__ == "__main__":
    main()
