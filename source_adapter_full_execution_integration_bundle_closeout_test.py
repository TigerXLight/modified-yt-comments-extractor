from source_adapter_full_execution_integration_bundle_closeout import STATUS, HANDOFF_STATUS, example_full_execution_integration_bundle_closeout_package
from source_adapter_full_execution_integration_bundle_closeout_verifier import verify_source_adapter_full_execution_integration_bundle_closeout_package

p = example_full_execution_integration_bundle_closeout_package()
assert p["status"] == STATUS
assert p["handoff"]["handoff_status"] == HANDOFF_STATUS
assert p["operator_summary"]["keys_accounts_label"] == "KEYS/ACCOUNTS"
assert p["implemented_package_count"] == 7
assert p["handoff"]["provider_profile_count"] == 5
v = verify_source_adapter_full_execution_integration_bundle_closeout_package(p)
assert v["verified"], v
print("Source Adapter Full Execution Integration Bundle Closeout self-test passed.")
