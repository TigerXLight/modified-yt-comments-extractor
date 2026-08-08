from source_adapter_operator_runbook_packager_runtime import example_source_adapter_operator_runbook_packager_runtime_package
from source_adapter_operator_runbook_packager_runtime_verifier import verify_source_adapter_operator_runbook_packager_runtime

package = example_source_adapter_operator_runbook_packager_runtime_package()
verified = verify_source_adapter_operator_runbook_packager_runtime(package)
assert verified["verified"], verified
broken = dict(package)
broken["status"] = "BROKEN"
assert not verify_source_adapter_operator_runbook_packager_runtime(broken)["verified"]
print("Source Adapter Operator Runbook Packager Runtime verifier self-test passed.")
