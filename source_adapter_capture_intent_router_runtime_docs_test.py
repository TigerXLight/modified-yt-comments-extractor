from pathlib import Path

doc = Path("SOURCE_ADAPTER_CAPTURE_INTENT_ROUTER_RUNTIME.md").read_text(encoding="utf-8")
assert "# Source Adapter Capture Intent Router Runtime" in doc
assert "KEYS/ACCOUNTS" in doc
assert "SOURCE_ADAPTER_CAPTURE_INTENT_ROUTER_RUNTIME_BUILT" in doc
assert "SOURCE_ADAPTER_CAPTURE_INTENT_ROUTER_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE" in doc
print("Source Adapter Capture Intent Router Runtime docs self-test passed.")
