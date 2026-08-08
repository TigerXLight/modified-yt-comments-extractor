from source_adapter_online_asr_provider_flow_runtime import example_source_adapter_online_asr_provider_flow_runtime_package
from source_adapter_online_asr_provider_flow_runtime_verifier import verify_source_adapter_online_asr_provider_flow_runtime

package = example_source_adapter_online_asr_provider_flow_runtime_package()
verified = verify_source_adapter_online_asr_provider_flow_runtime(package)
assert verified["verified"], verified
broken = dict(package)
broken["status"] = "BROKEN"
assert not verify_source_adapter_online_asr_provider_flow_runtime(broken)["verified"]
print("Source Adapter Online ASR Provider Flow Runtime verifier self-test passed.")
