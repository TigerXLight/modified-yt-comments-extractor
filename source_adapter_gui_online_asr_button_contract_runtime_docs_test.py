from pathlib import Path

doc = Path("SOURCE_ADAPTER_GUI_ONLINE_ASR_BUTTON_CONTRACT_RUNTIME.md").read_text(encoding="utf-8")
assert "# Source Adapter GUI Online ASR Button Contract Runtime" in doc
assert "KEYS/ACCOUNTS" in doc
assert "SOURCE_ADAPTER_GUI_ONLINE_ASR_BUTTON_CONTRACT_RUNTIME_BUILT" in doc
assert "SOURCE_ADAPTER_GUI_ONLINE_ASR_BUTTON_CONTRACT_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE" in doc
print("Source Adapter GUI Online ASR Button Contract Runtime docs self-test passed.")
