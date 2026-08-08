from pathlib import Path

doc = Path("SOURCE_ADAPTER_KEYS_ACCOUNTS_SEARCH_ADDED_RUNTIME.md").read_text(encoding="utf-8")
assert "# Source Adapter KEYS Accounts Search Added Runtime" in doc
assert "KEYS/ACCOUNTS" in doc
assert "SOURCE_ADAPTER_KEYS_ACCOUNTS_SEARCH_ADDED_RUNTIME_BUILT" in doc
assert "SOURCE_ADAPTER_KEYS_ACCOUNTS_SEARCH_ADDED_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE" in doc
print("Source Adapter KEYS Accounts Search Added Runtime docs self-test passed.")
