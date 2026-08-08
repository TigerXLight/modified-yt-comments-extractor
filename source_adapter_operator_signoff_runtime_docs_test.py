from pathlib import Path
text = Path("SOURCE_ADAPTER_OPERATOR_SIGNOFF_RUNTIME.md").read_text(encoding="utf-8")
assert "KEYS/ACCOUNTS" in text
assert "implementation" in text.lower()
assert "runtime" in text.lower()
print("Source Adapter Operator Signoff Runtime docs self-test passed.")
