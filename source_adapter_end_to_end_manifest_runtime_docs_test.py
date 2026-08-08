from pathlib import Path

doc = Path("SOURCE_ADAPTER_END_TO_END_MANIFEST_RUNTIME.md").read_text(encoding="utf-8")
assert "# Source Adapter End-to-End Manifest Runtime" in doc
assert "KEYS/ACCOUNTS" in doc
assert "SOURCE_ADAPTER_END_TO_END_MANIFEST_RUNTIME_BUILT" in doc
assert "SOURCE_ADAPTER_END_TO_END_MANIFEST_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE" in doc
print("Source Adapter End-to-End Manifest Runtime docs self-test passed.")
