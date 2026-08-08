from pathlib import Path

doc = Path("SOURCE_ADAPTER_GUI_TOTAL_EXPORT_RELEASE_PANEL_RUNTIME.md").read_text(encoding="utf-8")
assert "# Source Adapter GUI Total Export Release Panel Runtime" in doc
assert "KEYS/ACCOUNTS" in doc
assert "SOURCE_ADAPTER_GUI_TOTAL_EXPORT_RELEASE_PANEL_RUNTIME_BUILT" in doc
assert "SOURCE_ADAPTER_GUI_TOTAL_EXPORT_RELEASE_PANEL_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE" in doc
print("Source Adapter GUI Total Export Release Panel Runtime docs self-test passed.")
