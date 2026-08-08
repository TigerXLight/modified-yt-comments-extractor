from pathlib import Path

doc = Path("SOURCE_ADAPTER_OPERATOR_LIVE_COMMAND_GATE_RUNTIME.md").read_text(encoding="utf-8")
assert "# Source Adapter Operator Live Command Gate Runtime" in doc
assert "KEYS/ACCOUNTS" in doc
assert "SOURCE_ADAPTER_OPERATOR_LIVE_COMMAND_GATE_RUNTIME_BUILT" in doc
assert "SOURCE_ADAPTER_OPERATOR_LIVE_COMMAND_GATE_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE" in doc
print("Source Adapter Operator Live Command Gate Runtime docs self-test passed.")
