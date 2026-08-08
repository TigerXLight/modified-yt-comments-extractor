from source_adapter_production_runtime_bundle_closeout import STATUS, HANDOFF_STATUS, example_source_adapter_production_runtime_bundle_closeout_package
from source_adapter_production_runtime_bundle_closeout_verifier import verify_source_adapter_production_runtime_bundle_closeout_package

p = example_source_adapter_production_runtime_bundle_closeout_package()
assert p["status"] == STATUS, p
assert p["handoff"]["handoff_status"] == HANDOFF_STATUS, p["handoff"]
assert p["operator_summary"]["keys_accounts_label"] == "KEYS/ACCOUNTS"
assert p["issue_count"] == 0, p.get("issues")
assert p["implemented_package_count"] == 11
v = verify_source_adapter_production_runtime_bundle_closeout_package(p)
assert v["verified"], v
print("Source Adapter Production Runtime Bundle Closeout self-test passed.")
