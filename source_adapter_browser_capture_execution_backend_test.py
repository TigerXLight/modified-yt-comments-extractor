from source_adapter_browser_capture_execution_backend import STATUS, HANDOFF_STATUS, example_browser_capture_execution_backend_package
from source_adapter_browser_capture_execution_backend_verifier import verify_source_adapter_browser_capture_execution_backend_package

p = example_browser_capture_execution_backend_package()
assert p["status"] == STATUS
assert p["handoff"]["handoff_status"] == HANDOFF_STATUS
assert p["operator_summary"]["keys_accounts_label"] == "KEYS/ACCOUNTS"
assert p["browser_capture_row_count"] == 5
assert p["captured_artifact_count"] == 15
v = verify_source_adapter_browser_capture_execution_backend_package(p)
assert v["verified"], v
print("Source Adapter Browser Capture Execution Backend self-test passed.")
