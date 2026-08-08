from source_adapter_live_provider_profile_runtime import STATUS, HANDOFF_STATUS, example_live_provider_profile_runtime_package
from source_adapter_live_provider_profile_runtime_verifier import verify_source_adapter_live_provider_profile_runtime_package

p = example_live_provider_profile_runtime_package()
assert p["status"] == STATUS
assert p["handoff"]["handoff_status"] == HANDOFF_STATUS
assert p["operator_summary"]["keys_accounts_label"] == "KEYS/ACCOUNTS"
assert p["provider_profile_count"] == 5
assert all(row["live_capable"] for row in p["provider_profile_rows"])
v = verify_source_adapter_live_provider_profile_runtime_package(p)
assert v["verified"], v
print("Source Adapter Live Provider Profile Runtime self-test passed.")
