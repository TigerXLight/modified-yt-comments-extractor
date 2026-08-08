from source_adapter_live_smoke_plan_runner_runtime import example_source_adapter_live_smoke_plan_runner_runtime_package
from source_adapter_live_smoke_plan_runner_runtime_verifier import verify_source_adapter_live_smoke_plan_runner_runtime

package = example_source_adapter_live_smoke_plan_runner_runtime_package()
verified = verify_source_adapter_live_smoke_plan_runner_runtime(package)
assert verified["verified"], verified
broken = dict(package)
broken["status"] = "BROKEN"
assert not verify_source_adapter_live_smoke_plan_runner_runtime(broken)["verified"]
print("Source Adapter Live Smoke Plan Runner Runtime verifier self-test passed.")
