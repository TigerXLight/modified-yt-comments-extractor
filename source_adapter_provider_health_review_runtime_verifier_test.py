from source_adapter_provider_health_review_runtime import example_source_adapter_provider_health_review_runtime_package
from source_adapter_provider_health_review_runtime_verifier import verify_source_adapter_provider_health_review_runtime

package = example_source_adapter_provider_health_review_runtime_package()
verified = verify_source_adapter_provider_health_review_runtime(package)
assert verified["verified"], verified
broken = dict(package)
broken["status"] = "BROKEN"
assert not verify_source_adapter_provider_health_review_runtime(broken)["verified"]
print("Source Adapter Provider Health Review Runtime verifier self-test passed.")
