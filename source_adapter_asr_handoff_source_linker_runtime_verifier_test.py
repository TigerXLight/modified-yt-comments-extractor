from source_adapter_asr_handoff_source_linker_runtime import example_source_adapter_asr_handoff_source_linker_runtime_package
from source_adapter_asr_handoff_source_linker_runtime_verifier import verify_source_adapter_asr_handoff_source_linker_runtime

package = example_source_adapter_asr_handoff_source_linker_runtime_package()
verified = verify_source_adapter_asr_handoff_source_linker_runtime(package)
assert verified["verified"], verified
broken = dict(package)
broken["status"] = "BROKEN"
assert not verify_source_adapter_asr_handoff_source_linker_runtime(broken)["verified"]
print("Source Adapter ASR Handoff Source Linker Runtime verifier self-test passed.")
