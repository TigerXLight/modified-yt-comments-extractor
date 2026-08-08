from pathlib import Path

doc = Path("SOURCE_ADAPTER_ACTION_LOG_HASHCHAIN_RUNTIME.md").read_text(encoding="utf-8")
assert "# Source Adapter Action Log Hashchain Runtime" in doc
assert "KEYS/ACCOUNTS" in doc
assert "SOURCE_ADAPTER_ACTION_LOG_HASHCHAIN_RUNTIME_BUILT" in doc
assert "SOURCE_ADAPTER_ACTION_LOG_HASHCHAIN_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE" in doc
print("Source Adapter Action Log Hashchain Runtime docs self-test passed.")
