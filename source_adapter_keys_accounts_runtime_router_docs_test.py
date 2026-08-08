from pathlib import Path

doc = Path("SOURCE_ADAPTER_KEYS_ACCOUNTS_RUNTIME_ROUTER.md").read_text(encoding="utf-8")
assert "# Source Adapter KEYS Accounts Runtime Router" in doc
assert "KEYS/ACCOUNTS" in doc
assert "SOURCE_ADAPTER_KEYS_ACCOUNTS_RUNTIME_ROUTER_BUILT" in doc
assert "SOURCE_ADAPTER_KEYS_ACCOUNTS_RUNTIME_ROUTER_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE" in doc
print("Source Adapter KEYS Accounts Runtime Router docs self-test passed.")
