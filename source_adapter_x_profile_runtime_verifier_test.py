from source_adapter_x_profile_runtime import example_source_adapter_x_profile_runtime_package
from source_adapter_x_profile_runtime_verifier import verify_source_adapter_x_profile_runtime

package = example_source_adapter_x_profile_runtime_package()
verified = verify_source_adapter_x_profile_runtime(package)
assert verified["verified"], verified
broken = dict(package)
broken["status"] = "BROKEN"
assert not verify_source_adapter_x_profile_runtime(broken)["verified"]
print("Source Adapter X Twitter Profile Runtime verifier self-test passed.")
