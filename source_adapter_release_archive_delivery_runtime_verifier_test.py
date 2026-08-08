from source_adapter_release_archive_delivery_runtime import example_release_archive_delivery_runtime_package
from source_adapter_release_archive_delivery_runtime_verifier import verify_source_adapter_release_archive_delivery_runtime_package
v = verify_source_adapter_release_archive_delivery_runtime_package(example_release_archive_delivery_runtime_package())
assert v["issue_count"] == 0, v
assert v["verified"] is True
print("Source Adapter Release Archive Delivery Runtime verifier self-test passed.")
