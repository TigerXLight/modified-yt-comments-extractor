from pathlib import Path

doc = Path("SOURCE_ADAPTER_GUI_SOURCE_CAPTURE_COMMAND_BAR_RUNTIME.md").read_text(encoding="utf-8")
assert "# Source Adapter GUI Source Capture Command Bar Runtime" in doc
assert "KEYS/ACCOUNTS" in doc
assert "SOURCE_ADAPTER_GUI_SOURCE_CAPTURE_COMMAND_BAR_RUNTIME_BUILT" in doc
assert "SOURCE_ADAPTER_GUI_SOURCE_CAPTURE_COMMAND_BAR_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE" in doc
print("Source Adapter GUI Source Capture Command Bar Runtime docs self-test passed.")
