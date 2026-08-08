from source_adapter_browser_capture_execution_backend import example_browser_capture_execution_backend_package
from source_adapter_browser_capture_execution_backend_verifier import verify_source_adapter_browser_capture_execution_backend_package

v = verify_source_adapter_browser_capture_execution_backend_package(example_browser_capture_execution_backend_package())
assert v["verified"], v
assert v["issue_count"] == 0, v
print("Source Adapter Browser Capture Execution Backend verifier self-test passed.")
