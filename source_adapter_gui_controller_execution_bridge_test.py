from __future__ import annotations

import tempfile

from source_adapter_gui_controller_execution_bridge import DISPATCH_BATCH_STATUS, HANDOFF_STATUS, ROUTE_REGISTRY_STATUS, STATUS, build_source_adapter_gui_controller_execution_bridge


def main() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        package = build_source_adapter_gui_controller_execution_bridge(output_dir=tmpdir, operator_id="tester", execution_notes=["gui controller bridge test"]).as_dict()
    assert package["gui_controller_execution_bridge_status"] == STATUS
    registry = package["source_adapter_gui_controller_execution_route_registry"]
    assert registry["route_registry_status"] == ROUTE_REGISTRY_STATUS
    assert registry["route_row_count"] == 4
    batch = package["source_adapter_gui_controller_execution_dispatch_receipt_batch"]
    assert batch["gui_controller_execution_dispatch_receipt_batch_status"] == DISPATCH_BATCH_STATUS
    assert batch["dispatch_receipt_row_count"] == 5
    assert all(row["dispatch_performed"] is True for row in batch["gui_controller_dispatch_receipt_rows"])
    assert package["source_adapter_gui_controller_execution_bridge_handoff"]["handoff_status"] == HANDOFF_STATUS
    assert package["operator_summary"]["keys_accounts_label"] == "KEYS/ACCOUNTS"
    print("Source Adapter GUI Controller Execution Bridge self-test passed.")


if __name__ == "__main__":
    main()
