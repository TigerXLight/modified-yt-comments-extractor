import tempfile
from pathlib import Path

from source_adapter_media_capture_runner_runtime import example_source_adapter_media_capture_runner_runtime_package
from source_adapter_media_capture_runner_runtime_store import store_source_adapter_media_capture_runner_runtime_package

with tempfile.TemporaryDirectory() as tmp:
    result = store_source_adapter_media_capture_runner_runtime_package(example_source_adapter_media_capture_runner_runtime_package(), tmp)
    assert result["store_status"] == "STORED", result
    assert result["output_file_count"] == 3, result
    for row in result["stored_files"]:
        assert Path(row["path"]).exists(), row
        assert row["byte_count"] > 0, row
        assert len(row["sha256"]) == 64, row
print("Source Adapter Media Capture Runner Runtime store self-test passed.")
