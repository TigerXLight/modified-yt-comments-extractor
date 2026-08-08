from pathlib import Path

text = Path("SOURCE_ADAPTER_GUI_LIVE_EXECUTION_PANEL_WIRING.md").read_text(encoding="utf-8")
assert "KEYS/ACCOUNTS" in text
assert "implementation" in text.lower()
assert "verifier" in text.lower() or "receipt" in text.lower()
print("Source Adapter GUI Live Execution Panel Wiring docs self-test passed.")
