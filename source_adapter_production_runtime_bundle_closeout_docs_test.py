from pathlib import Path
text = Path("SOURCE_ADAPTER_PRODUCTION_RUNTIME_BUNDLE_CLOSEOUT.md").read_text(encoding="utf-8")
assert "KEYS/ACCOUNTS" in text
assert "implementation" in text.lower()
assert "runtime" in text.lower()
print("Source Adapter Production Runtime Bundle Closeout docs self-test passed.")
