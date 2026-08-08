from source_adapter_end_to_end_receipt_auditor_runtime import example_source_adapter_end_to_end_receipt_auditor_runtime_package
from source_adapter_end_to_end_receipt_auditor_runtime_verifier import verify_source_adapter_end_to_end_receipt_auditor_runtime

package = example_source_adapter_end_to_end_receipt_auditor_runtime_package()
verified = verify_source_adapter_end_to_end_receipt_auditor_runtime(package)
assert verified["verified"], verified
broken = dict(package)
broken["status"] = "BROKEN"
assert not verify_source_adapter_end_to_end_receipt_auditor_runtime(broken)["verified"]
print("Source Adapter End-to-End Receipt Auditor Runtime verifier self-test passed.")
