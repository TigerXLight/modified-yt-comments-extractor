from source_adapter_evidence_database_commit_runtime import example_source_adapter_evidence_database_commit_runtime_package
from source_adapter_evidence_database_commit_runtime_verifier import verify_source_adapter_evidence_database_commit_runtime

package = example_source_adapter_evidence_database_commit_runtime_package()
verified = verify_source_adapter_evidence_database_commit_runtime(package)
assert verified["verified"], verified
broken = dict(package)
broken["status"] = "BROKEN"
assert not verify_source_adapter_evidence_database_commit_runtime(broken)["verified"]
print("Source Adapter Evidence Database Commit Runtime verifier self-test passed.")
