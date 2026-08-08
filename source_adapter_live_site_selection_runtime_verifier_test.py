from source_adapter_live_site_selection_runtime import example_source_adapter_live_site_selection_runtime_package
from source_adapter_live_site_selection_runtime_verifier import verify_source_adapter_live_site_selection_runtime

package = example_source_adapter_live_site_selection_runtime_package()
verified = verify_source_adapter_live_site_selection_runtime(package)
assert verified["verified"], verified
broken = dict(package)
broken["status"] = "BROKEN"
assert not verify_source_adapter_live_site_selection_runtime(broken)["verified"]
print("Source Adapter Live Site Selection Runtime verifier self-test passed.")
