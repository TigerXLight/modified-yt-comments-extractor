from pathlib import Path

doc = Path("SOURCE_ADAPTER_ACCOUNT_PROVIDER_STATE_RUNTIME.md").read_text(encoding="utf-8")
assert "# Source Adapter Account Provider State Runtime" in doc
assert "KEYS/ACCOUNTS" in doc
assert "SOURCE_ADAPTER_ACCOUNT_PROVIDER_STATE_RUNTIME_BUILT" in doc
assert "SOURCE_ADAPTER_ACCOUNT_PROVIDER_STATE_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE" in doc
print("Source Adapter Account Provider State Runtime docs self-test passed.")
