from pathlib import Path

doc = Path("SOURCE_ADAPTER_ASR_HANDOFF_SOURCE_LINKER_RUNTIME.md").read_text(encoding="utf-8")
assert "# Source Adapter ASR Handoff Source Linker Runtime" in doc
assert "KEYS/ACCOUNTS" in doc
assert "SOURCE_ADAPTER_ASR_HANDOFF_SOURCE_LINKER_RUNTIME_BUILT" in doc
assert "SOURCE_ADAPTER_ASR_HANDOFF_SOURCE_LINKER_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE" in doc
print("Source Adapter ASR Handoff Source Linker Runtime docs self-test passed.")
