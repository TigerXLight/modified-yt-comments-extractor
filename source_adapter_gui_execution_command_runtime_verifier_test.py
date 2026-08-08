from source_adapter_gui_execution_command_runtime import example_source_adapter_gui_execution_command_runtime_package
from source_adapter_gui_execution_command_runtime_verifier import verify_source_adapter_gui_execution_command_runtime

package = example_source_adapter_gui_execution_command_runtime_package()
verified = verify_source_adapter_gui_execution_command_runtime(package)
assert verified["verified"], verified
broken = dict(package)
broken["status"] = "BROKEN"
assert not verify_source_adapter_gui_execution_command_runtime(broken)["verified"]
print("Source Adapter GUI Execution Command Runtime verifier self-test passed.")
