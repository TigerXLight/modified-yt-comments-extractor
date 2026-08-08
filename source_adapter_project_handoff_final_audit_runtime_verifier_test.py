from source_adapter_project_handoff_final_audit_runtime import example_source_adapter_project_handoff_final_audit_runtime_package
from source_adapter_project_handoff_final_audit_runtime_verifier import verify_source_adapter_project_handoff_final_audit_runtime

package = example_source_adapter_project_handoff_final_audit_runtime_package()
verified = verify_source_adapter_project_handoff_final_audit_runtime(package)
assert verified["verified"], verified
broken = dict(package)
broken["status"] = "BROKEN"
assert not verify_source_adapter_project_handoff_final_audit_runtime(broken)["verified"]
print("Source Adapter Project Handoff Final Audit Runtime verifier self-test passed.")
