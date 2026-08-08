import tempfile
from pathlib import Path

from source_adapter_gui_live_execution_panel_wiring import example_gui_live_execution_panel_wiring_package
from source_adapter_gui_live_execution_panel_wiring_store import store_source_adapter_gui_live_execution_panel_wiring_package

with tempfile.TemporaryDirectory() as tmp:
    result = store_source_adapter_gui_live_execution_panel_wiring_package(example_gui_live_execution_panel_wiring_package(), tmp)
    assert result["store_status"] == "STORED", result
    assert result["output_file_count"] == 3, result
    for row in result["stored_files"]:
        assert Path(row["path"]).exists(), row
        assert row["byte_count"] > 0, row
        assert len(row["sha256"]) == 64, row
print("Source Adapter GUI Live Execution Panel Wiring store self-test passed.")
