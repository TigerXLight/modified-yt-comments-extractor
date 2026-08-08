from source_adapter_shadow_root_extraction_plan_runtime import example_source_adapter_shadow_root_extraction_plan_runtime_package
from source_adapter_shadow_root_extraction_plan_runtime_verifier import verify_source_adapter_shadow_root_extraction_plan_runtime

package = example_source_adapter_shadow_root_extraction_plan_runtime_package()
verified = verify_source_adapter_shadow_root_extraction_plan_runtime(package)
assert verified["verified"], verified
broken = dict(package)
broken["status"] = "BROKEN"
assert not verify_source_adapter_shadow_root_extraction_plan_runtime(broken)["verified"]
print("Source Adapter Shadow Root Extraction Plan Runtime verifier self-test passed.")
