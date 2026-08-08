from source_adapter_provider_capability_docs_runtime import example_source_adapter_provider_capability_docs_runtime_package
from source_adapter_provider_capability_docs_runtime_verifier import verify_source_adapter_provider_capability_docs_runtime

package = example_source_adapter_provider_capability_docs_runtime_package()
verified = verify_source_adapter_provider_capability_docs_runtime(package)
assert verified["verified"], verified
broken = dict(package)
broken["status"] = "BROKEN"
assert not verify_source_adapter_provider_capability_docs_runtime(broken)["verified"]
print("Source Adapter Provider Capability Docs Runtime verifier self-test passed.")
