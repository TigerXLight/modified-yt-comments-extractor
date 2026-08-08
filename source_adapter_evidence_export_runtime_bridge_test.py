from source_adapter_evidence_export_runtime_bridge import HANDOFF_STATUS, STATUS, example_evidence_export_runtime_bridge_package
from source_adapter_evidence_export_runtime_bridge_verifier import verify_source_adapter_evidence_export_runtime_bridge_package

p = example_evidence_export_runtime_bridge_package()
assert p["evidence_export_runtime_bridge_status"] == STATUS
assert p["source_adapter_evidence_export_runtime_bridge_handoff"]["handoff_status"] == HANDOFF_STATUS
assert p["source_adapter_evidence_export_queue"]["evidence_export_queue_row_count"] == 5
assert p["source_adapter_total_export_source_package"]["total_export_source_row_count"] == 5
assert p["source_adapter_release_index_runtime_package"]["release_index_runtime_row_count"] == 5
assert p["source_adapter_archive_handoff_runtime_package"]["archive_handoff_runtime_row_count"] == 5
v = verify_source_adapter_evidence_export_runtime_bridge_package(p)
assert v["verified"], v
print("Source Adapter Evidence Export Runtime Bridge self-test passed.")
