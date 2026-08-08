from source_adapter_comment_tree_materializer_runtime import example_source_adapter_comment_tree_materializer_runtime_package
from source_adapter_comment_tree_materializer_runtime_verifier import verify_source_adapter_comment_tree_materializer_runtime

package = example_source_adapter_comment_tree_materializer_runtime_package()
verified = verify_source_adapter_comment_tree_materializer_runtime(package)
assert verified["verified"], verified
broken = dict(package)
broken["status"] = "BROKEN"
assert not verify_source_adapter_comment_tree_materializer_runtime(broken)["verified"]
print("Source Adapter Comment Tree Materializer Runtime verifier self-test passed.")
