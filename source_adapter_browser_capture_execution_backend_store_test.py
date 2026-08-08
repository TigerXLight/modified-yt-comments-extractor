import tempfile
from pathlib import Path

from source_adapter_browser_capture_execution_backend import example_browser_capture_execution_backend_package
from source_adapter_browser_capture_execution_backend_store import store_source_adapter_browser_capture_execution_backend_package

with tempfile.TemporaryDirectory() as tmp:
    result = store_source_adapter_browser_capture_execution_backend_package(example_browser_capture_execution_backend_package(), tmp)
    assert result["store_status"] == "STORED", result
    assert result["output_file_count"] == 3, result
    for row in result["stored_files"]:
        assert Path(row["path"]).exists(), row
        assert row["byte_count"] > 0, row
        assert len(row["sha256"]) == 64, row
print("Source Adapter Browser Capture Execution Backend store self-test passed.")
