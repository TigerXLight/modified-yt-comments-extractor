from pathlib import Path
text = Path("SOURCE_ADAPTER_PROVIDER_INTEGRATION_BUNDLE_CLOSEOUT.md").read_text(encoding="utf-8")
assert "KEYS/ACCOUNTS" in text
assert "implementation" in text.lower()
assert "receipt" in text.lower() or "runtime" in text.lower()
print("Source Adapter Provider Integration Bundle Closeout docs self-test passed.")
