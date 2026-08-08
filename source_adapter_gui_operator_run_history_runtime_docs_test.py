from pathlib import Path
text = Path("SOURCE_ADAPTER_GUI_OPERATOR_RUN_HISTORY_RUNTIME.md").read_text(encoding="utf-8")
assert "KEYS/ACCOUNTS" in text
assert "implementation" in text.lower()
assert "receipt" in text.lower() or "runtime" in text.lower()
print("Source Adapter GUI Operator Run History Runtime docs self-test passed.")
