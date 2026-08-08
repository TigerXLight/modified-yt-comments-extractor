from pathlib import Path

doc = Path("SOURCE_ADAPTER_OPERATOR_HANDOFF_PACKET_RUNTIME.md").read_text(encoding="utf-8")
assert "# Source Adapter Operator Handoff Packet Runtime" in doc
assert "KEYS/ACCOUNTS" in doc
assert "SOURCE_ADAPTER_OPERATOR_HANDOFF_PACKET_RUNTIME_BUILT" in doc
assert "SOURCE_ADAPTER_OPERATOR_HANDOFF_PACKET_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE" in doc
print("Source Adapter Operator Handoff Packet Runtime docs self-test passed.")
