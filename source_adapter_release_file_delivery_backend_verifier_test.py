from source_adapter_release_file_delivery_backend import example_release_file_delivery_backend_package
from source_adapter_release_file_delivery_backend_verifier import verify_source_adapter_release_file_delivery_backend_package

v = verify_source_adapter_release_file_delivery_backend_package(example_release_file_delivery_backend_package())
assert v["verified"], v
assert v["issue_count"] == 0, v
print("Source Adapter Release File Delivery Backend verifier self-test passed.")
