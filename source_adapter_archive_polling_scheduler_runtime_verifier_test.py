from source_adapter_archive_polling_scheduler_runtime import example_source_adapter_archive_polling_scheduler_runtime_package
from source_adapter_archive_polling_scheduler_runtime_verifier import verify_source_adapter_archive_polling_scheduler_runtime

package = example_source_adapter_archive_polling_scheduler_runtime_package()
verified = verify_source_adapter_archive_polling_scheduler_runtime(package)
assert verified["verified"], verified
broken = dict(package)
broken["status"] = "BROKEN"
assert not verify_source_adapter_archive_polling_scheduler_runtime(broken)["verified"]
print("Source Adapter Archive Polling Scheduler Runtime verifier self-test passed.")
