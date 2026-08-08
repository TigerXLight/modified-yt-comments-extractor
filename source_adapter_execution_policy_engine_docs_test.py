from pathlib import Path

doc = Path("SOURCE_ADAPTER_EXECUTION_POLICY_ENGINE.md").read_text(encoding="utf-8")
assert "Source Adapter Execution Policy Engine" in doc
assert "KEYS/ACCOUNTS" in doc
assert "SOURCE_ADAPTER_EXECUTION_POLICY_ENGINE_BUILT" in doc
assert "SOURCE_ADAPTER_EXECUTION_POLICY_ENGINE_READY_FOR_NEXT_IMPLEMENTATION_STAGE" in doc
print("Source Adapter Execution Policy Engine docs self-test passed.")
