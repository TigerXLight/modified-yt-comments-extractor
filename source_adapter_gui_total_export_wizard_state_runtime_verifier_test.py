from source_adapter_gui_total_export_wizard_state_runtime import example_source_adapter_gui_total_export_wizard_state_runtime_package
from source_adapter_gui_total_export_wizard_state_runtime_verifier import verify_source_adapter_gui_total_export_wizard_state_runtime

package = example_source_adapter_gui_total_export_wizard_state_runtime_package()
verified = verify_source_adapter_gui_total_export_wizard_state_runtime(package)
assert verified["verified"], verified
broken = dict(package)
broken["status"] = "BROKEN"
assert not verify_source_adapter_gui_total_export_wizard_state_runtime(broken)["verified"]
print("Source Adapter GUI Total Export Wizard State Runtime verifier self-test passed.")
