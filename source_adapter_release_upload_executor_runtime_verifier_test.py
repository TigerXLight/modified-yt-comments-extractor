from source_adapter_release_upload_executor_runtime import example_source_adapter_release_upload_executor_runtime_package
from source_adapter_release_upload_executor_runtime_verifier import verify_source_adapter_release_upload_executor_runtime

package = example_source_adapter_release_upload_executor_runtime_package()
verified = verify_source_adapter_release_upload_executor_runtime(package)
assert verified["verified"], verified
broken = dict(package)
broken["status"] = "BROKEN"
assert not verify_source_adapter_release_upload_executor_runtime(broken)["verified"]
print("Source Adapter Release Upload Executor Runtime verifier self-test passed.")
