from pathlib import Path

doc = Path("SOURCE_ADAPTER_EVIDENCE_QUEUE_GUI_BRIDGE_RUNTIME.md").read_text(encoding="utf-8")
assert "# Source Adapter Evidence Queue GUI Bridge Runtime" in doc
assert "KEYS/ACCOUNTS" in doc
assert "SOURCE_ADAPTER_EVIDENCE_QUEUE_GUI_BRIDGE_RUNTIME_BUILT" in doc
assert "SOURCE_ADAPTER_EVIDENCE_QUEUE_GUI_BRIDGE_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE" in doc
print("Source Adapter Evidence Queue GUI Bridge Runtime docs self-test passed.")
