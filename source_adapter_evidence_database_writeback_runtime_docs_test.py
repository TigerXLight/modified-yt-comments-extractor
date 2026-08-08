from pathlib import Path
text = Path("SOURCE_ADAPTER_EVIDENCE_DATABASE_WRITEBACK_RUNTIME.md").read_text(encoding="utf-8")
assert "KEYS/ACCOUNTS" in text
assert "implementation" in text.lower()
assert "runtime" in text.lower()
print("Source Adapter Evidence Database Writeback Runtime docs self-test passed.")
