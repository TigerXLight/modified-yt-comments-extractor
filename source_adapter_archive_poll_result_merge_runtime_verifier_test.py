from source_adapter_archive_poll_result_merge_runtime import example_source_adapter_archive_poll_result_merge_runtime_package
from source_adapter_archive_poll_result_merge_runtime_verifier import verify_source_adapter_archive_poll_result_merge_runtime

package = example_source_adapter_archive_poll_result_merge_runtime_package()
verified = verify_source_adapter_archive_poll_result_merge_runtime(package)
assert verified["verified"], verified
broken = dict(package)
broken["status"] = "BROKEN"
assert not verify_source_adapter_archive_poll_result_merge_runtime(broken)["verified"]
print("Source Adapter Archive Poll Result Merge Runtime verifier self-test passed.")
