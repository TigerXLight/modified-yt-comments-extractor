from source_adapter_evidence_sync_runtime import example_source_adapter_evidence_sync_runtime_package
from source_adapter_evidence_sync_runtime_verifier import verify_source_adapter_evidence_sync_runtime_package
v = verify_source_adapter_evidence_sync_runtime_package(example_source_adapter_evidence_sync_runtime_package())
assert v["verified"], v
assert v["issue_count"] == 0, v
print("Source Adapter Evidence Sync Runtime verifier self-test passed.")
