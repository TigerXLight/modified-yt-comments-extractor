from source_adapter_archive_evidence_normalizer_runtime import example_source_adapter_archive_evidence_normalizer_runtime_package
from source_adapter_archive_evidence_normalizer_runtime_verifier import verify_source_adapter_archive_evidence_normalizer_runtime

package = example_source_adapter_archive_evidence_normalizer_runtime_package()
verified = verify_source_adapter_archive_evidence_normalizer_runtime(package)
assert verified["verified"], verified
broken = dict(package)
broken["status"] = "BROKEN"
assert not verify_source_adapter_archive_evidence_normalizer_runtime(broken)["verified"]
print("Source Adapter Archive Evidence Normalizer Runtime verifier self-test passed.")
