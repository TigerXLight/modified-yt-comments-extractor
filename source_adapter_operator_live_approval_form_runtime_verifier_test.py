from source_adapter_operator_live_approval_form_runtime import example_source_adapter_operator_live_approval_form_runtime_package
from source_adapter_operator_live_approval_form_runtime_verifier import verify_source_adapter_operator_live_approval_form_runtime

package = example_source_adapter_operator_live_approval_form_runtime_package()
verified = verify_source_adapter_operator_live_approval_form_runtime(package)
assert verified["verified"], verified
broken = dict(package)
broken["status"] = "BROKEN"
assert not verify_source_adapter_operator_live_approval_form_runtime(broken)["verified"]
print("Source Adapter Operator Live Approval Form Runtime verifier self-test passed.")
