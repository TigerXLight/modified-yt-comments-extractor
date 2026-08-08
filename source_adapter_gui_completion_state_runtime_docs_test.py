from pathlib import Path
text = Path("SOURCE_ADAPTER_GUI_COMPLETION_STATE_RUNTIME.md").read_text(encoding="utf-8")
assert "KEYS/ACCOUNTS" in text
assert "implementation" in text.lower()
assert "runtime" in text.lower()
print("Source Adapter GUI Completion State Runtime docs self-test passed.")
