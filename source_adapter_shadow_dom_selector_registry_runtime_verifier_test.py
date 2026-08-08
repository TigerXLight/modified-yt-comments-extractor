from source_adapter_shadow_dom_selector_registry_runtime import example_source_adapter_shadow_dom_selector_registry_runtime_package
from source_adapter_shadow_dom_selector_registry_runtime_verifier import verify_source_adapter_shadow_dom_selector_registry_runtime

package = example_source_adapter_shadow_dom_selector_registry_runtime_package()
verified = verify_source_adapter_shadow_dom_selector_registry_runtime(package)
assert verified["verified"], verified
broken = dict(package)
broken["status"] = "BROKEN"
assert not verify_source_adapter_shadow_dom_selector_registry_runtime(broken)["verified"]
print("Source Adapter Shadow DOM Selector Registry Runtime verifier self-test passed.")
