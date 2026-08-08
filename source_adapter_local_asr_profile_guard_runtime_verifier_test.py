from source_adapter_local_asr_profile_guard_runtime import example_source_adapter_local_asr_profile_guard_runtime_package
from source_adapter_local_asr_profile_guard_runtime_verifier import verify_source_adapter_local_asr_profile_guard_runtime

package = example_source_adapter_local_asr_profile_guard_runtime_package()
verified = verify_source_adapter_local_asr_profile_guard_runtime(package)
assert verified["verified"], verified
broken = dict(package)
broken["status"] = "BROKEN"
assert not verify_source_adapter_local_asr_profile_guard_runtime(broken)["verified"]
print("Source Adapter Local ASR Profile Guard Runtime verifier self-test passed.")
