from source_adapter_live_provider_profile_runtime import example_live_provider_profile_runtime_package
from source_adapter_live_provider_profile_runtime_verifier import verify_source_adapter_live_provider_profile_runtime_package

v = verify_source_adapter_live_provider_profile_runtime_package(example_live_provider_profile_runtime_package())
assert v["verified"], v
assert v["issue_count"] == 0, v
print("Source Adapter Live Provider Profile Runtime verifier self-test passed.")
