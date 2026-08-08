from source_adapter_end_to_end_verification_runtime import example_source_adapter_end_to_end_verification_runtime_package
from source_adapter_end_to_end_verification_runtime_verifier import verify_source_adapter_end_to_end_verification_runtime

package = example_source_adapter_end_to_end_verification_runtime_package()
verified = verify_source_adapter_end_to_end_verification_runtime(package)
assert verified["verified"], verified
broken = dict(package)
broken["status"] = "BROKEN"
assert not verify_source_adapter_end_to_end_verification_runtime(broken)["verified"]
print("Source Adapter End-to-End Verification Runtime verifier self-test passed.")
