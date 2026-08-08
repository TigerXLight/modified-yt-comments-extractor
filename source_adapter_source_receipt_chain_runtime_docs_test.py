from pathlib import Path

doc = Path("SOURCE_ADAPTER_SOURCE_RECEIPT_CHAIN_RUNTIME.md").read_text(encoding="utf-8")
assert "# Source Adapter Source Receipt Chain Runtime" in doc
assert "KEYS/ACCOUNTS" in doc
assert "SOURCE_ADAPTER_SOURCE_RECEIPT_CHAIN_RUNTIME_BUILT" in doc
assert "SOURCE_ADAPTER_SOURCE_RECEIPT_CHAIN_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE" in doc
print("Source Adapter Source Receipt Chain Runtime docs self-test passed.")
