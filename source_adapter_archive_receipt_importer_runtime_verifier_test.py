from source_adapter_archive_receipt_importer_runtime import example_source_adapter_archive_receipt_importer_runtime_package
from source_adapter_archive_receipt_importer_runtime_verifier import verify_source_adapter_archive_receipt_importer_runtime

package = example_source_adapter_archive_receipt_importer_runtime_package()
verified = verify_source_adapter_archive_receipt_importer_runtime(package)
assert verified["verified"], verified
broken = dict(package)
broken["status"] = "BROKEN"
assert not verify_source_adapter_archive_receipt_importer_runtime(broken)["verified"]
print("Source Adapter Archive Receipt Importer Runtime verifier self-test passed.")
