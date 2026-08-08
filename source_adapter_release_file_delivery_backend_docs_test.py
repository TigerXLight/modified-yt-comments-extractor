from pathlib import Path

text = Path("SOURCE_ADAPTER_RELEASE_FILE_DELIVERY_BACKEND.md").read_text(encoding="utf-8")
assert "KEYS/ACCOUNTS" in text
assert "implementation" in text.lower()
assert "verifier" in text.lower() or "receipt" in text.lower()
print("Source Adapter Release File Delivery Backend docs self-test passed.")
