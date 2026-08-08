from source_adapter_action_log_hashchain_runtime import example_source_adapter_action_log_hashchain_runtime_package
from source_adapter_action_log_hashchain_runtime_verifier import verify_source_adapter_action_log_hashchain_runtime

package = example_source_adapter_action_log_hashchain_runtime_package()
verified = verify_source_adapter_action_log_hashchain_runtime(package)
assert verified["verified"], verified
broken = dict(package)
broken["status"] = "BROKEN"
assert not verify_source_adapter_action_log_hashchain_runtime(broken)["verified"]
print("Source Adapter Action Log Hashchain Runtime verifier self-test passed.")
