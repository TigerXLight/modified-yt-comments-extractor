from pathlib import Path

doc = Path("SOURCE_ADAPTER_OPERATOR_AUDIT_TRAIL_RUNTIME.md").read_text(encoding="utf-8")
assert "Source Adapter Operator Audit Trail Runtime" in doc
assert "KEYS/ACCOUNTS" in doc
assert "SOURCE_ADAPTER_OPERATOR_AUDIT_TRAIL_RUNTIME_BUILT" in doc
assert "SOURCE_ADAPTER_OPERATOR_AUDIT_TRAIL_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_STAGE" in doc
print("Source Adapter Operator Audit Trail Runtime docs self-test passed.")
