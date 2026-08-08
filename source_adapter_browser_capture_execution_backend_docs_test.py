from pathlib import Path

text = Path("SOURCE_ADAPTER_BROWSER_CAPTURE_EXECUTION_BACKEND.md").read_text(encoding="utf-8")
assert "KEYS/ACCOUNTS" in text
assert "implementation" in text.lower()
assert "verifier" in text.lower() or "receipt" in text.lower()
print("Source Adapter Browser Capture Execution Backend docs self-test passed.")
