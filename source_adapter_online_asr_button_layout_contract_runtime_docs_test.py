from pathlib import Path

doc = Path("SOURCE_ADAPTER_ONLINE_ASR_BUTTON_LAYOUT_CONTRACT_RUNTIME.md").read_text(encoding="utf-8")
assert "# Source Adapter Online ASR Button Layout Contract Runtime" in doc
assert "KEYS/ACCOUNTS" in doc
assert "Online ASR" in doc
assert "large-v3 Vulkan" in doc
assert "SOURCE_ADAPTER_ONLINE_ASR_BUTTON_LAYOUT_CONTRACT_RUNTIME_BUILT" in doc
assert "SOURCE_ADAPTER_ONLINE_ASR_BUTTON_LAYOUT_CONTRACT_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE" in doc
print("Source Adapter Online ASR Button Layout Contract Runtime docs self-test passed.")
