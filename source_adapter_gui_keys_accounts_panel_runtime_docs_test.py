from pathlib import Path

doc = Path("SOURCE_ADAPTER_GUI_KEYS_ACCOUNTS_PANEL_RUNTIME.md").read_text(encoding="utf-8")
assert "# Source Adapter GUI KEYS Accounts Panel Runtime" in doc
assert "KEYS/ACCOUNTS" in doc
assert "SOURCE_ADAPTER_GUI_KEYS_ACCOUNTS_PANEL_RUNTIME_BUILT" in doc
assert "SOURCE_ADAPTER_GUI_KEYS_ACCOUNTS_PANEL_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE" in doc
print("Source Adapter GUI KEYS Accounts Panel Runtime docs self-test passed.")
