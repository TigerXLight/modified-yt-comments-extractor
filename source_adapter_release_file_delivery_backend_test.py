from source_adapter_release_file_delivery_backend import STATUS, HANDOFF_STATUS, example_release_file_delivery_backend_package
from source_adapter_release_file_delivery_backend_verifier import verify_source_adapter_release_file_delivery_backend_package

p = example_release_file_delivery_backend_package()
assert p["status"] == STATUS
assert p["handoff"]["handoff_status"] == HANDOFF_STATUS
assert p["operator_summary"]["keys_accounts_label"] == "KEYS/ACCOUNTS"
assert p["release_file_delivery_row_count"] == 10
assert p["handoff"]["release_upload_count"] == 5
assert p["handoff"]["file_library_publish_count"] == 5
v = verify_source_adapter_release_file_delivery_backend_package(p)
assert v["verified"], v
print("Source Adapter Release File Delivery Backend self-test passed.")
