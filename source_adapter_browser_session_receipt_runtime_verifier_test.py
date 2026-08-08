from source_adapter_browser_session_receipt_runtime import example_source_adapter_browser_session_receipt_runtime_package
from source_adapter_browser_session_receipt_runtime_verifier import verify_source_adapter_browser_session_receipt_runtime

package = example_source_adapter_browser_session_receipt_runtime_package()
verified = verify_source_adapter_browser_session_receipt_runtime(package)
assert verified["verified"], verified
broken = dict(package)
broken["status"] = "BROKEN"
assert not verify_source_adapter_browser_session_receipt_runtime(broken)["verified"]
print("Source Adapter Browser Session Receipt Runtime verifier self-test passed.")
