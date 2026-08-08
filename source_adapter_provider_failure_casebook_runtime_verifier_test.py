from source_adapter_provider_failure_casebook_runtime import example_source_adapter_provider_failure_casebook_runtime_package
from source_adapter_provider_failure_casebook_runtime_verifier import verify_source_adapter_provider_failure_casebook_runtime

package = example_source_adapter_provider_failure_casebook_runtime_package()
verified = verify_source_adapter_provider_failure_casebook_runtime(package)
assert verified["verified"], verified
broken = dict(package)
broken["status"] = "BROKEN"
assert not verify_source_adapter_provider_failure_casebook_runtime(broken)["verified"]
print("Source Adapter Provider Failure Casebook Runtime verifier self-test passed.")
