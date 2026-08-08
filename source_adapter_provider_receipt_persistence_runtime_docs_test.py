from pathlib import Path
text = Path("SOURCE_ADAPTER_PROVIDER_RECEIPT_PERSISTENCE_RUNTIME.md").read_text(encoding="utf-8")
assert "KEYS/ACCOUNTS" in text
assert "implementation" in text.lower()
assert "runtime" in text.lower()
print("Source Adapter Provider Receipt Persistence Runtime docs self-test passed.")
