from pathlib import Path

doc = Path("SOURCE_ADAPTER_EVIDENCE_DATABASE_IMPORT_GATE_RUNTIME.md").read_text(encoding="utf-8")
assert "# Source Adapter Evidence Database Import Gate Runtime" in doc
assert "KEYS/ACCOUNTS" in doc
assert "SOURCE_ADAPTER_EVIDENCE_DATABASE_IMPORT_GATE_RUNTIME_BUILT" in doc
assert "SOURCE_ADAPTER_EVIDENCE_DATABASE_IMPORT_GATE_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE" in doc
print("Source Adapter Evidence Database Import Gate Runtime docs self-test passed.")
