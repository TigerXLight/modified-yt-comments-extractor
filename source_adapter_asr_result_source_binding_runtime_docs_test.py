from pathlib import Path

doc = Path("SOURCE_ADAPTER_ASR_RESULT_SOURCE_BINDING_RUNTIME.md").read_text(encoding="utf-8")
assert "# Source Adapter ASR Result Source Binding Runtime" in doc
assert "KEYS/ACCOUNTS" in doc
assert "Online ASR" in doc
assert "large-v3 Vulkan" in doc
assert "SOURCE_ADAPTER_ASR_RESULT_SOURCE_BINDING_RUNTIME_BUILT" in doc
assert "SOURCE_ADAPTER_ASR_RESULT_SOURCE_BINDING_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE" in doc
print("Source Adapter ASR Result Source Binding Runtime docs self-test passed.")
