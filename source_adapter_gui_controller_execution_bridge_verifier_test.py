from __future__ import annotations

from copy import deepcopy

from source_adapter_gui_controller_execution_bridge import build_source_adapter_gui_controller_execution_bridge
from source_adapter_gui_controller_execution_bridge_verifier import verify_source_adapter_gui_controller_execution_bridge


def main() -> None:
    package = build_source_adapter_gui_controller_execution_bridge().as_dict()
    result = verify_source_adapter_gui_controller_execution_bridge(package)
    assert result["verified"] is True
    assert result["issue_count"] == 0
    assert result["dispatch_receipt_row_count"] == 5
    bad = deepcopy(package)
    bad["source_adapter_gui_controller_execution_dispatch_receipt_batch"]["gui_controller_dispatch_receipt_rows"][0]["raw_credential"] = "not allowed"
    bad_result = verify_source_adapter_gui_controller_execution_bridge(bad)
    assert bad_result["verified"] is False
    assert any(issue["issue_id"] == "secret_like_material_present" for issue in bad_result["issues"])
    print("Source Adapter GUI Controller Execution Bridge verifier self-test passed.")


if __name__ == "__main__":
    main()
