from source_adapter_release_index_publish_runtime import example_source_adapter_release_index_publish_runtime_package
from source_adapter_release_index_publish_runtime_verifier import verify_source_adapter_release_index_publish_runtime

package = example_source_adapter_release_index_publish_runtime_package()
verified = verify_source_adapter_release_index_publish_runtime(package)
assert verified["verified"], verified
broken = dict(package)
broken["status"] = "BROKEN"
assert not verify_source_adapter_release_index_publish_runtime(broken)["verified"]
print("Source Adapter Release Index Publish Runtime verifier self-test passed.")
