from source_adapter_operator_approval_workflow_runtime import example_source_adapter_operator_approval_workflow_runtime_package
from source_adapter_operator_approval_workflow_runtime_verifier import verify_source_adapter_operator_approval_workflow_runtime

package = example_source_adapter_operator_approval_workflow_runtime_package()
verified = verify_source_adapter_operator_approval_workflow_runtime(package)
assert verified["verified"], verified
broken = dict(package)
broken["status"] = "BROKEN"
assert not verify_source_adapter_operator_approval_workflow_runtime(broken)["verified"]
print("Source Adapter Operator Approval Workflow Runtime verifier self-test passed.")
