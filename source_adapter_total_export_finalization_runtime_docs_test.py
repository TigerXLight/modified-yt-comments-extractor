from pathlib import Path
text = Path("SOURCE_ADAPTER_TOTAL_EXPORT_FINALIZATION_RUNTIME.md").read_text(encoding="utf-8")
assert "KEYS/ACCOUNTS" in text
assert "implementation" in text.lower()
assert "receipt" in text.lower() or "runtime" in text.lower()
print("Source Adapter Total Export Finalization Runtime docs self-test passed.")
