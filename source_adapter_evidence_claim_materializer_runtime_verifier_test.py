from source_adapter_evidence_claim_materializer_runtime import example_source_adapter_evidence_claim_materializer_runtime_package
from source_adapter_evidence_claim_materializer_runtime_verifier import verify_source_adapter_evidence_claim_materializer_runtime

package = example_source_adapter_evidence_claim_materializer_runtime_package()
verified = verify_source_adapter_evidence_claim_materializer_runtime(package)
assert verified["verified"], verified
broken = dict(package)
broken["status"] = "BROKEN"
assert not verify_source_adapter_evidence_claim_materializer_runtime(broken)["verified"]
print("Source Adapter Evidence Claim Materializer Runtime verifier self-test passed.")
