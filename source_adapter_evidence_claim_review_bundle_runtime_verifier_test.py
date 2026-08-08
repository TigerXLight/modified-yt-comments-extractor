from source_adapter_evidence_claim_review_bundle_runtime import example_source_adapter_evidence_claim_review_bundle_runtime_package
from source_adapter_evidence_claim_review_bundle_runtime_verifier import verify_source_adapter_evidence_claim_review_bundle_runtime

package = example_source_adapter_evidence_claim_review_bundle_runtime_package()
verified = verify_source_adapter_evidence_claim_review_bundle_runtime(package)
assert verified["verified"], verified
broken = dict(package)
broken["status"] = "BROKEN"
assert not verify_source_adapter_evidence_claim_review_bundle_runtime(broken)["verified"]
print("Source Adapter Evidence Claim Review Bundle Runtime verifier self-test passed.")
