from source_adapter_gui_live_execution_panel_wiring import STATUS, HANDOFF_STATUS, example_gui_live_execution_panel_wiring_package
from source_adapter_gui_live_execution_panel_wiring_verifier import verify_source_adapter_gui_live_execution_panel_wiring_package

p = example_gui_live_execution_panel_wiring_package()
assert p["status"] == STATUS
assert p["handoff"]["handoff_status"] == HANDOFF_STATUS
assert p["operator_summary"]["keys_accounts_label"] == "KEYS/ACCOUNTS"
assert p["gui_route_row_count"] == 4
assert p["handoff"]["controller_callable_route_count"] == 4
v = verify_source_adapter_gui_live_execution_panel_wiring_package(p)
assert v["verified"], v
print("Source Adapter GUI Live Execution Panel Wiring self-test passed.")
