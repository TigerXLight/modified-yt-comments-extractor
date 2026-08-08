from source_adapter_gui_source_capture_command_bar_runtime import example_source_adapter_gui_source_capture_command_bar_runtime_package
from source_adapter_gui_source_capture_command_bar_runtime_verifier import verify_source_adapter_gui_source_capture_command_bar_runtime

package = example_source_adapter_gui_source_capture_command_bar_runtime_package()
verified = verify_source_adapter_gui_source_capture_command_bar_runtime(package)
assert verified["verified"], verified
broken = dict(package)
broken["status"] = "BROKEN"
assert not verify_source_adapter_gui_source_capture_command_bar_runtime(broken)["verified"]
print("Source Adapter GUI Source Capture Command Bar Runtime verifier self-test passed.")
