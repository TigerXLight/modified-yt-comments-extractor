from pathlib import Path
text = Path("SOURCE_ADAPTER_LIVE_RUN_PERMISSION_RUNTIME.md").read_text(encoding="utf-8")
assert "KEYS/ACCOUNTS" in text
assert "implementation" in text.lower()
assert "runtime" in text.lower()
print("Source Adapter Live Run Permission Runtime docs self-test passed.")
