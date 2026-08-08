from source_adapter_keys_accounts_search_added_runtime import example_source_adapter_keys_accounts_search_added_runtime_package
from source_adapter_keys_accounts_search_added_runtime_verifier import verify_source_adapter_keys_accounts_search_added_runtime

package = example_source_adapter_keys_accounts_search_added_runtime_package()
verified = verify_source_adapter_keys_accounts_search_added_runtime(package)
assert verified["verified"], verified
broken = dict(package)
broken["status"] = "BROKEN"
assert not verify_source_adapter_keys_accounts_search_added_runtime(broken)["verified"]
print("Source Adapter KEYS Accounts Search Added Runtime verifier self-test passed.")
