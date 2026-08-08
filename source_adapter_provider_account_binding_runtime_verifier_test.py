from source_adapter_provider_account_binding_runtime import example_source_adapter_provider_account_binding_runtime_package
from source_adapter_provider_account_binding_runtime_verifier import verify_source_adapter_provider_account_binding_runtime

package = example_source_adapter_provider_account_binding_runtime_package()
verified = verify_source_adapter_provider_account_binding_runtime(package)
assert verified["verified"], verified
broken = dict(package)
broken["status"] = "BROKEN"
assert not verify_source_adapter_provider_account_binding_runtime(broken)["verified"]
print("Source Adapter Provider Account Binding Runtime verifier self-test passed.")
