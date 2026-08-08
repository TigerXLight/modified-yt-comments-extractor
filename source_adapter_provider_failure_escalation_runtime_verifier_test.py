from source_adapter_provider_failure_escalation_runtime import example_source_adapter_provider_failure_escalation_runtime_package
from source_adapter_provider_failure_escalation_runtime_verifier import verify_source_adapter_provider_failure_escalation_runtime

package = example_source_adapter_provider_failure_escalation_runtime_package()
verified = verify_source_adapter_provider_failure_escalation_runtime(package)
assert verified["verified"], verified
broken = dict(package)
broken["status"] = "BROKEN"
assert not verify_source_adapter_provider_failure_escalation_runtime(broken)["verified"]
print("Source Adapter Provider Failure Escalation Runtime verifier self-test passed.")
