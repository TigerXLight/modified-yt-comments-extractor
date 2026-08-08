from source_adapter_account_provider_state_runtime import example_source_adapter_account_provider_state_runtime_package
from source_adapter_account_provider_state_runtime_verifier import verify_source_adapter_account_provider_state_runtime

package = example_source_adapter_account_provider_state_runtime_package()
verified = verify_source_adapter_account_provider_state_runtime(package)
assert verified["verified"], verified
broken = dict(package)
broken["status"] = "BROKEN"
assert not verify_source_adapter_account_provider_state_runtime(broken)["verified"]
print("Source Adapter Account Provider State Runtime verifier self-test passed.")
