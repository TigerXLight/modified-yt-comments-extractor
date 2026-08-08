from pathlib import Path

doc = Path("SOURCE_ADAPTER_RUNTIME_ACCEPTANCE_SUMMARY_RUNTIME.md").read_text(encoding="utf-8")
assert "# Source Adapter Runtime Acceptance Summary Runtime" in doc
assert "KEYS/ACCOUNTS" in doc
assert "SOURCE_ADAPTER_RUNTIME_ACCEPTANCE_SUMMARY_RUNTIME_BUILT" in doc
assert "SOURCE_ADAPTER_RUNTIME_ACCEPTANCE_SUMMARY_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE" in doc
print("Source Adapter Runtime Acceptance Summary Runtime docs self-test passed.")
