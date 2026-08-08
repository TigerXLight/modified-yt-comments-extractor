from source_adapter_evidence_source_linking_runtime import example_source_adapter_evidence_source_linking_runtime_package
from source_adapter_evidence_source_linking_runtime_verifier import verify_source_adapter_evidence_source_linking_runtime

package = example_source_adapter_evidence_source_linking_runtime_package()
verified = verify_source_adapter_evidence_source_linking_runtime(package)
assert verified["verified"], verified
broken = dict(package)
broken["status"] = "BROKEN"
assert not verify_source_adapter_evidence_source_linking_runtime(broken)["verified"]
print("Source Adapter Evidence Source Linking Runtime verifier self-test passed.")
