from source_adapter_gui_provider_picker_runtime import example_source_adapter_gui_provider_picker_runtime_package
from source_adapter_gui_provider_picker_runtime_verifier import verify_source_adapter_gui_provider_picker_runtime

package = example_source_adapter_gui_provider_picker_runtime_package()
verified = verify_source_adapter_gui_provider_picker_runtime(package)
assert verified["verified"], verified
broken = dict(package)
broken["status"] = "BROKEN"
assert not verify_source_adapter_gui_provider_picker_runtime(broken)["verified"]
print("Source Adapter GUI Provider Picker Runtime verifier self-test passed.")
