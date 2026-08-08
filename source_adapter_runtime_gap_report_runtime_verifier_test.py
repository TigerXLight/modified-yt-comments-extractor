from source_adapter_runtime_gap_report_runtime import example_source_adapter_runtime_gap_report_runtime_package
from source_adapter_runtime_gap_report_runtime_verifier import verify_source_adapter_runtime_gap_report_runtime

package = example_source_adapter_runtime_gap_report_runtime_package()
verified = verify_source_adapter_runtime_gap_report_runtime(package)
assert verified["verified"], verified
broken = dict(package)
broken["status"] = "BROKEN"
assert not verify_source_adapter_runtime_gap_report_runtime(broken)["verified"]
print("Source Adapter Runtime Gap Report Runtime verifier self-test passed.")
