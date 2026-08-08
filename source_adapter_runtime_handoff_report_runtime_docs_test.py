from pathlib import Path

doc = Path("SOURCE_ADAPTER_RUNTIME_HANDOFF_REPORT_RUNTIME.md").read_text(encoding="utf-8")
assert "# Source Adapter Runtime Handoff Report Runtime" in doc
assert "KEYS/ACCOUNTS" in doc
assert "SOURCE_ADAPTER_RUNTIME_HANDOFF_REPORT_RUNTIME_BUILT" in doc
assert "SOURCE_ADAPTER_RUNTIME_HANDOFF_REPORT_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE" in doc
print("Source Adapter Runtime Handoff Report Runtime docs self-test passed.")
