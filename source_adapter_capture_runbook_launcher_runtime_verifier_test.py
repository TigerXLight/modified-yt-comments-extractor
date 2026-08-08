from source_adapter_capture_runbook_launcher_runtime import example_source_adapter_capture_runbook_launcher_runtime_package
from source_adapter_capture_runbook_launcher_runtime_verifier import verify_source_adapter_capture_runbook_launcher_runtime

package = example_source_adapter_capture_runbook_launcher_runtime_package()
verified = verify_source_adapter_capture_runbook_launcher_runtime(package)
assert verified["verified"], verified
broken = dict(package)
broken["status"] = "BROKEN"
assert not verify_source_adapter_capture_runbook_launcher_runtime(broken)["verified"]
print("Source Adapter Capture Runbook Launcher Runtime verifier self-test passed.")
