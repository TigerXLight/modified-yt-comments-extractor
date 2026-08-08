from pathlib import Path
text = Path("SOURCE_ADAPTER_OPERATOR_SESSION_EXECUTION_RUNTIME.md").read_text(encoding="utf-8")
assert "KEYS/ACCOUNTS" in text
assert "implementation" in text.lower()
assert "runtime" in text.lower()
print("Source Adapter Operator Session Execution Runtime docs self-test passed.")
