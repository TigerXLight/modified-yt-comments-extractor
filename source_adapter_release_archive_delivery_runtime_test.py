from source_adapter_release_archive_delivery_runtime import HANDOFF_STATUS, STATUS, example_release_archive_delivery_runtime_package
from source_adapter_release_archive_delivery_runtime_verifier import verify_source_adapter_release_archive_delivery_runtime_package

p = example_release_archive_delivery_runtime_package()
assert p["release_archive_delivery_runtime_status"] == STATUS
assert p["source_adapter_release_archive_delivery_runtime_handoff"]["handoff_status"] == HANDOFF_STATUS
assert p["source_adapter_release_archive_delivery_plan"]["delivery_plan_row_count"] == 20
assert p["source_adapter_release_archive_delivery_receipt_batch"]["delivery_receipt_row_count"] == 20
assert p["source_adapter_release_archive_delivery_receipt_batch"]["delivered_named_site_count"] == 5
v = verify_source_adapter_release_archive_delivery_runtime_package(p)
assert v["verified"], v
print("Source Adapter Release Archive Delivery Runtime self-test passed.")
