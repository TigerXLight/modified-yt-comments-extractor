from __future__ import annotations

import tempfile

from source_adapter_gui_controller_execution_bridge import build_source_adapter_gui_controller_execution_bridge
from source_adapter_gui_controller_execution_bridge_store import store_source_adapter_gui_controller_execution_bridge


def main() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        package = build_source_adapter_gui_controller_execution_bridge(output_dir=tmpdir).as_dict()
        result = store_source_adapter_gui_controller_execution_bridge(package, tmpdir)
    assert result["store_status"] == "STORED"
    assert result["verification"]["verified"] is True
    assert result["route_row_count"] == 4
    assert result["dispatch_receipt_row_count"] == 5
    assert result["output_file_count"] == 5
    print("Source Adapter GUI Controller Execution Bridge store self-test passed.")


if __name__ == "__main__":
    main()
