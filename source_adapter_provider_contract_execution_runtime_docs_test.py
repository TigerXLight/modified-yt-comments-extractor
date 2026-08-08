from pathlib import Path

doc = Path("SOURCE_ADAPTER_PROVIDER_CONTRACT_EXECUTION_RUNTIME.md").read_text(encoding="utf-8")
assert "# Source Adapter Provider Contract Execution Runtime" in doc
assert "KEYS/ACCOUNTS" in doc
assert "SOURCE_ADAPTER_PROVIDER_CONTRACT_EXECUTION_RUNTIME_BUILT" in doc
assert "SOURCE_ADAPTER_PROVIDER_CONTRACT_EXECUTION_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE" in doc
print("Source Adapter Provider Contract Execution Runtime docs self-test passed.")
