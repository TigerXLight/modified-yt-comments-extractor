from pathlib import Path

doc = Path("SOURCE_ADAPTER_OPERATOR_ACCEPTANCE_CHECKLIST_RUNTIME.md").read_text(encoding="utf-8")
assert "# Source Adapter Operator Acceptance Checklist Runtime" in doc
assert "KEYS/ACCOUNTS" in doc
assert "SOURCE_ADAPTER_OPERATOR_ACCEPTANCE_CHECKLIST_RUNTIME_BUILT" in doc
assert "SOURCE_ADAPTER_OPERATOR_ACCEPTANCE_CHECKLIST_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE" in doc
print("Source Adapter Operator Acceptance Checklist Runtime docs self-test passed.")
