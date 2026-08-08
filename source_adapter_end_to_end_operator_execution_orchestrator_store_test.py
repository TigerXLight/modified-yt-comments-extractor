import tempfile
from pathlib import Path

from source_adapter_end_to_end_operator_execution_orchestrator import example_end_to_end_operator_execution_orchestrator_package
from source_adapter_end_to_end_operator_execution_orchestrator_store import store_source_adapter_end_to_end_operator_execution_orchestrator_package

with tempfile.TemporaryDirectory() as tmp:
    result = store_source_adapter_end_to_end_operator_execution_orchestrator_package(example_end_to_end_operator_execution_orchestrator_package(), tmp)
    assert result["store_status"] == "STORED", result
    assert result["output_file_count"] == 3, result
    for row in result["stored_files"]:
        assert Path(row["path"]).exists(), row
        assert row["byte_count"] > 0, row
        assert len(row["sha256"]) == 64, row
print("Source Adapter End-to-End Operator Execution Orchestrator store self-test passed.")
