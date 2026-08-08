from source_adapter_file_library_delivery_queue_runtime import example_source_adapter_file_library_delivery_queue_runtime_package
from source_adapter_file_library_delivery_queue_runtime_verifier import verify_source_adapter_file_library_delivery_queue_runtime

package = example_source_adapter_file_library_delivery_queue_runtime_package()
verified = verify_source_adapter_file_library_delivery_queue_runtime(package)
assert verified["verified"], verified
broken = dict(package)
broken["status"] = "BROKEN"
assert not verify_source_adapter_file_library_delivery_queue_runtime(broken)["verified"]
print("Source Adapter File Library Delivery Queue Runtime verifier self-test passed.")
