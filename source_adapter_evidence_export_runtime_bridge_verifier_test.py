from source_adapter_evidence_export_runtime_bridge import example_evidence_export_runtime_bridge_package
from source_adapter_evidence_export_runtime_bridge_verifier import verify_source_adapter_evidence_export_runtime_bridge_package

v = verify_source_adapter_evidence_export_runtime_bridge_package(example_evidence_export_runtime_bridge_package())
assert v["issue_count"] == 0, v
assert v["verified"] is True
print("Source Adapter Evidence Export Runtime Bridge verifier self-test passed.")
