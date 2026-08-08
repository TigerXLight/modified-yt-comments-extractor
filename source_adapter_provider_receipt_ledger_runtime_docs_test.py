from pathlib import Path
text = Path("SOURCE_ADAPTER_PROVIDER_RECEIPT_LEDGER_RUNTIME.md").read_text(encoding="utf-8")
assert "KEYS/ACCOUNTS" in text
assert "implementation" in text.lower()
assert "receipt" in text.lower() or "runtime" in text.lower()
print("Source Adapter Provider Receipt Ledger Runtime docs self-test passed.")
