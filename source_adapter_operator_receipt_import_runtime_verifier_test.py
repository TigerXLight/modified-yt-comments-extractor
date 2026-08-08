from source_adapter_operator_receipt_import_runtime import example_source_adapter_operator_receipt_import_runtime_package
from source_adapter_operator_receipt_import_runtime_verifier import verify_source_adapter_operator_receipt_import_runtime

package = example_source_adapter_operator_receipt_import_runtime_package()
verified = verify_source_adapter_operator_receipt_import_runtime(package)
assert verified["verified"], verified
broken = dict(package)
broken["status"] = "BROKEN"
assert not verify_source_adapter_operator_receipt_import_runtime(broken)["verified"]
print("Source Adapter Operator Receipt Import Runtime verifier self-test passed.")
