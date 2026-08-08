from pathlib import Path

doc = Path("SOURCE_ADAPTER_EVIDENCE_SOURCE_LINKING_RUNTIME.md").read_text(encoding="utf-8")
assert "# Source Adapter Evidence Source Linking Runtime" in doc
assert "KEYS/ACCOUNTS" in doc
assert "SOURCE_ADAPTER_EVIDENCE_SOURCE_LINKING_RUNTIME_BUILT" in doc
assert "SOURCE_ADAPTER_EVIDENCE_SOURCE_LINKING_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE" in doc
print("Source Adapter Evidence Source Linking Runtime docs self-test passed.")
