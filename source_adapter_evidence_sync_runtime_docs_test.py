from pathlib import Path
text = Path("SOURCE_ADAPTER_EVIDENCE_SYNC_RUNTIME.md").read_text(encoding="utf-8")
assert "KEYS/ACCOUNTS" in text
assert "implementation" in text.lower()
assert "receipt" in text.lower() or "runtime" in text.lower()
print("Source Adapter Evidence Sync Runtime docs self-test passed.")
