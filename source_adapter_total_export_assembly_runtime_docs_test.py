from pathlib import Path

doc = Path("SOURCE_ADAPTER_TOTAL_EXPORT_ASSEMBLY_RUNTIME.md").read_text(encoding="utf-8")
assert "# Source Adapter Total Export Assembly Runtime" in doc
assert "KEYS/ACCOUNTS" in doc
assert "SOURCE_ADAPTER_TOTAL_EXPORT_ASSEMBLY_RUNTIME_BUILT" in doc
assert "SOURCE_ADAPTER_TOTAL_EXPORT_ASSEMBLY_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE" in doc
print("Source Adapter Total Export Assembly Runtime docs self-test passed.")
