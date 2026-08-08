from pathlib import Path

doc = Path("SOURCE_ADAPTER_KEYS_ACCOUNTS_ADD_PROVIDER_WIZARD_RUNTIME.md").read_text(encoding="utf-8")
assert "# Source Adapter KEYS Accounts Add Provider Wizard Runtime" in doc
assert "KEYS/ACCOUNTS" in doc
assert "SOURCE_ADAPTER_KEYS_ACCOUNTS_ADD_PROVIDER_WIZARD_RUNTIME_BUILT" in doc
assert "SOURCE_ADAPTER_KEYS_ACCOUNTS_ADD_PROVIDER_WIZARD_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE" in doc
print("Source Adapter KEYS Accounts Add Provider Wizard Runtime docs self-test passed.")
