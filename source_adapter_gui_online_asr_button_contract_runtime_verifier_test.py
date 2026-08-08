from source_adapter_gui_online_asr_button_contract_runtime import example_source_adapter_gui_online_asr_button_contract_runtime_package
from source_adapter_gui_online_asr_button_contract_runtime_verifier import verify_source_adapter_gui_online_asr_button_contract_runtime

package = example_source_adapter_gui_online_asr_button_contract_runtime_package()
verified = verify_source_adapter_gui_online_asr_button_contract_runtime(package)
assert verified["verified"], verified
broken = dict(package)
broken["status"] = "BROKEN"
assert not verify_source_adapter_gui_online_asr_button_contract_runtime(broken)["verified"]
print("Source Adapter GUI Online ASR Button Contract Runtime verifier self-test passed.")
