from pathlib import Path

doc = Path("SOURCE_ADAPTER_FINAL_OPERATOR_HANDOFF_RUNTIME.md").read_text(encoding="utf-8")
assert "# Source Adapter Final Operator Handoff Runtime" in doc
assert "KEYS/ACCOUNTS" in doc
assert "SOURCE_ADAPTER_FINAL_OPERATOR_HANDOFF_RUNTIME_BUILT" in doc
assert "SOURCE_ADAPTER_FINAL_OPERATOR_HANDOFF_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE" in doc
print("Source Adapter Final Operator Handoff Runtime docs self-test passed.")
