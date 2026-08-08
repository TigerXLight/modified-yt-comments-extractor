from source_adapter_gui_live_execution_panel_wiring import example_gui_live_execution_panel_wiring_package
from source_adapter_gui_live_execution_panel_wiring_verifier import verify_source_adapter_gui_live_execution_panel_wiring_package

v = verify_source_adapter_gui_live_execution_panel_wiring_package(example_gui_live_execution_panel_wiring_package())
assert v["verified"], v
assert v["issue_count"] == 0, v
print("Source Adapter GUI Live Execution Panel Wiring verifier self-test passed.")
