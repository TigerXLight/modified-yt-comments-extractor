import tempfile

from source_adapter_next_roadmap_work_order_execution_closeout import example_next_roadmap_work_order_execution_closeout_package
from source_adapter_next_roadmap_work_order_execution_closeout_store import store_source_adapter_next_roadmap_work_order_execution_closeout


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        result = store_source_adapter_next_roadmap_work_order_execution_closeout(example_next_roadmap_work_order_execution_closeout_package(), tmp)
        assert result["store_status"] == "STORED"
        assert result["output_file_count"] == 10
        assert result["verification"]["verified"] is True
    print("Source Adapter Next Roadmap Work Order Execution Closeout store self-test passed.")


if __name__ == "__main__":
    main()
