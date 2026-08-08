from source_adapter_page_capture_recipe_runtime import example_source_adapter_page_capture_recipe_runtime_package
from source_adapter_page_capture_recipe_runtime_verifier import verify_source_adapter_page_capture_recipe_runtime

package = example_source_adapter_page_capture_recipe_runtime_package()
verified = verify_source_adapter_page_capture_recipe_runtime(package)
assert verified["verified"], verified
broken = dict(package)
broken["status"] = "BROKEN"
assert not verify_source_adapter_page_capture_recipe_runtime(broken)["verified"]
print("Source Adapter Page Capture Recipe Runtime verifier self-test passed.")
