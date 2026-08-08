from source_adapter_scroll_capture_controller_runtime import example_source_adapter_scroll_capture_controller_runtime_package
from source_adapter_scroll_capture_controller_runtime_verifier import verify_source_adapter_scroll_capture_controller_runtime

package = example_source_adapter_scroll_capture_controller_runtime_package()
verified = verify_source_adapter_scroll_capture_controller_runtime(package)
assert verified["verified"], verified
broken = dict(package)
broken["status"] = "BROKEN"
assert not verify_source_adapter_scroll_capture_controller_runtime(broken)["verified"]
print("Source Adapter Scroll Capture Controller Runtime verifier self-test passed.")
