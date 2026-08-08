from source_adapter_release_bundle_storage_runtime import example_source_adapter_release_bundle_storage_runtime_package
from source_adapter_release_bundle_storage_runtime_verifier import verify_source_adapter_release_bundle_storage_runtime

package = example_source_adapter_release_bundle_storage_runtime_package()
verified = verify_source_adapter_release_bundle_storage_runtime(package)
assert verified["verified"], verified
broken = dict(package)
broken["status"] = "BROKEN"
assert not verify_source_adapter_release_bundle_storage_runtime(broken)["verified"]
print("Source Adapter Release Bundle Storage Runtime verifier self-test passed.")
