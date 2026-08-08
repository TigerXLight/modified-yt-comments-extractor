from source_adapter_source_lineage_audit_matrix_runtime import example_source_adapter_source_lineage_audit_matrix_runtime_package
from source_adapter_source_lineage_audit_matrix_runtime_verifier import verify_source_adapter_source_lineage_audit_matrix_runtime

package = example_source_adapter_source_lineage_audit_matrix_runtime_package()
verified = verify_source_adapter_source_lineage_audit_matrix_runtime(package)
assert verified["verified"], verified
broken = dict(package)
broken["status"] = "BROKEN"
assert not verify_source_adapter_source_lineage_audit_matrix_runtime(broken)["verified"]
print("Source Adapter Source Lineage Audit Matrix Runtime verifier self-test passed.")
