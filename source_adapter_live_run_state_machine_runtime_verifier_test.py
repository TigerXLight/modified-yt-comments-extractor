from source_adapter_live_run_state_machine_runtime import example_source_adapter_live_run_state_machine_runtime_package
from source_adapter_live_run_state_machine_runtime_verifier import verify_source_adapter_live_run_state_machine_runtime

package = example_source_adapter_live_run_state_machine_runtime_package()
verified = verify_source_adapter_live_run_state_machine_runtime(package)
assert verified["verified"], verified
broken = dict(package)
broken["status"] = "BROKEN"
assert not verify_source_adapter_live_run_state_machine_runtime(broken)["verified"]
print("Source Adapter Live Run State Machine Runtime verifier self-test passed.")
