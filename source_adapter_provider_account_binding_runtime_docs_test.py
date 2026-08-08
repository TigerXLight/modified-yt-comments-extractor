from pathlib import Path

doc = Path("SOURCE_ADAPTER_PROVIDER_ACCOUNT_BINDING_RUNTIME.md").read_text(encoding="utf-8")
assert "# Source Adapter Provider Account Binding Runtime" in doc
assert "KEYS/ACCOUNTS" in doc
assert "SOURCE_ADAPTER_PROVIDER_ACCOUNT_BINDING_RUNTIME_BUILT" in doc
assert "SOURCE_ADAPTER_PROVIDER_ACCOUNT_BINDING_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE" in doc
print("Source Adapter Provider Account Binding Runtime docs self-test passed.")
