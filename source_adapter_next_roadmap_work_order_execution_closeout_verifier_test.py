from source_adapter_next_roadmap_work_order_execution_closeout import example_next_roadmap_work_order_execution_closeout_package
from source_adapter_next_roadmap_work_order_execution_closeout_verifier import verify_source_adapter_next_roadmap_work_order_execution_closeout


def main() -> None:
    result = verify_source_adapter_next_roadmap_work_order_execution_closeout(example_next_roadmap_work_order_execution_closeout_package())
    assert result["verified"] is True
    assert result["issue_count"] == 0
    assert result["provider_activation_count"] >= 4
    print("Source Adapter Next Roadmap Work Order Execution Closeout verifier self-test passed.")


if __name__ == "__main__":
    main()
