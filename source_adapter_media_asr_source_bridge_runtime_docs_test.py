from pathlib import Path

doc = Path("SOURCE_ADAPTER_MEDIA_ASR_SOURCE_BRIDGE_RUNTIME.md").read_text(encoding="utf-8")
assert "# Source Adapter Media ASR Source Bridge Runtime" in doc
assert "KEYS/ACCOUNTS" in doc
assert "SOURCE_ADAPTER_MEDIA_ASR_SOURCE_BRIDGE_RUNTIME_BUILT" in doc
assert "SOURCE_ADAPTER_MEDIA_ASR_SOURCE_BRIDGE_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE" in doc
print("Source Adapter Media ASR Source Bridge Runtime docs self-test passed.")
