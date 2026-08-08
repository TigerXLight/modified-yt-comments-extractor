from source_adapter_secret_scope_runtime import example_source_adapter_secret_scope_runtime_package
from source_adapter_secret_scope_runtime_verifier import verify_source_adapter_secret_scope_runtime

package = example_source_adapter_secret_scope_runtime_package()
verified = verify_source_adapter_secret_scope_runtime(package)
assert verified["verified"], verified
broken = dict(package)
broken["status"] = "BROKEN"
assert not verify_source_adapter_secret_scope_runtime(broken)["verified"]
print("Source Adapter Secret Scope Runtime verifier self-test passed.")
