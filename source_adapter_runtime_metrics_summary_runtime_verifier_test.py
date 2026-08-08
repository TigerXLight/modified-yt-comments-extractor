from source_adapter_runtime_metrics_summary_runtime import example_source_adapter_runtime_metrics_summary_runtime_package
from source_adapter_runtime_metrics_summary_runtime_verifier import verify_source_adapter_runtime_metrics_summary_runtime

package = example_source_adapter_runtime_metrics_summary_runtime_package()
verified = verify_source_adapter_runtime_metrics_summary_runtime(package)
assert verified["verified"], verified
broken = dict(package)
broken["status"] = "BROKEN"
assert not verify_source_adapter_runtime_metrics_summary_runtime(broken)["verified"]
print("Source Adapter Runtime Metrics Summary Runtime verifier self-test passed.")
