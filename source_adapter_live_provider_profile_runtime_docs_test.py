from pathlib import Path

text = Path("SOURCE_ADAPTER_LIVE_PROVIDER_PROFILE_RUNTIME.md").read_text(encoding="utf-8")
assert "KEYS/ACCOUNTS" in text
assert "implementation" in text.lower()
assert "verifier" in text.lower() or "receipt" in text.lower()
print("Source Adapter Live Provider Profile Runtime docs self-test passed.")
