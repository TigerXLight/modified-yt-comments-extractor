from source_adapter_keys_accounts_runtime_router import example_source_adapter_keys_accounts_runtime_router_package
from source_adapter_keys_accounts_runtime_router_verifier import verify_source_adapter_keys_accounts_runtime_router

package = example_source_adapter_keys_accounts_runtime_router_package()
verified = verify_source_adapter_keys_accounts_runtime_router(package)
assert verified["verified"], verified
broken = dict(package)
broken["status"] = "BROKEN"
assert not verify_source_adapter_keys_accounts_runtime_router(broken)["verified"]
print("Source Adapter KEYS Accounts Runtime Router verifier self-test passed.")
