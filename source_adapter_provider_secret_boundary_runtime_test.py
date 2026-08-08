from source_adapter_provider_secret_boundary_runtime import STATUS, HANDOFF_STATUS, example_source_adapter_provider_secret_boundary_runtime_package
from source_adapter_provider_secret_boundary_runtime_verifier import verify_source_adapter_provider_secret_boundary_runtime_package

p = example_source_adapter_provider_secret_boundary_runtime_package()
assert p["status"] == STATUS, p
assert p["handoff"]["handoff_status"] == HANDOFF_STATUS, p["handoff"]
assert p["operator_summary"]["keys_accounts_label"] == "KEYS/ACCOUNTS"
assert p["issue_count"] == 0, p.get("issues")
assert p["secret_boundary_row_count"] == 5
v = verify_source_adapter_provider_secret_boundary_runtime_package(p)
assert v["verified"], v
print("Source Adapter Provider Secret Boundary Runtime self-test passed.")
