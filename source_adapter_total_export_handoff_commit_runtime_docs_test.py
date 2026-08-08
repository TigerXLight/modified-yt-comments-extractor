from pathlib import Path
text = Path("SOURCE_ADAPTER_TOTAL_EXPORT_HANDOFF_COMMIT_RUNTIME.md").read_text(encoding="utf-8")
assert "KEYS/ACCOUNTS" in text
assert "implementation" in text.lower()
assert "runtime" in text.lower()
print("Source Adapter Total Export Handoff Commit Runtime docs self-test passed.")
