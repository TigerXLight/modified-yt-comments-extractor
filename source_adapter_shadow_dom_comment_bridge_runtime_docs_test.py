from pathlib import Path

doc = Path("SOURCE_ADAPTER_SHADOW_DOM_COMMENT_BRIDGE_RUNTIME.md").read_text(encoding="utf-8")
assert "# Source Adapter Shadow DOM Comment Bridge Runtime" in doc
assert "KEYS/ACCOUNTS" in doc
assert "SOURCE_ADAPTER_SHADOW_DOM_COMMENT_BRIDGE_RUNTIME_BUILT" in doc
assert "SOURCE_ADAPTER_SHADOW_DOM_COMMENT_BRIDGE_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE" in doc
print("Source Adapter Shadow DOM Comment Bridge Runtime docs self-test passed.")
