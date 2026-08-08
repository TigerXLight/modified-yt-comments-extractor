from source_adapter_source_receipt_chain_runtime import example_source_adapter_source_receipt_chain_runtime_package
from source_adapter_source_receipt_chain_runtime_verifier import verify_source_adapter_source_receipt_chain_runtime

package = example_source_adapter_source_receipt_chain_runtime_package()
verified = verify_source_adapter_source_receipt_chain_runtime(package)
assert verified["verified"], verified
broken = dict(package)
broken["status"] = "BROKEN"
assert not verify_source_adapter_source_receipt_chain_runtime(broken)["verified"]
print("Source Adapter Source Receipt Chain Runtime verifier self-test passed.")
