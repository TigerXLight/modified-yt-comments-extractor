from pathlib import Path

text = Path("SOURCE_ADAPTER_KEYS_ACCOUNTS_CREDENTIAL_REFERENCE_RUNTIME.md").read_text(encoding="utf-8")
assert "KEYS/ACCOUNTS" in text
assert "implementation" in text.lower()
assert "verifier" in text.lower() or "receipt" in text.lower()
print("Source Adapter KEYS/ACCOUNTS Credential Reference Runtime docs self-test passed.")
