from pathlib import Path

text = Path("SOURCE_ADAPTER_END_TO_END_OPERATOR_EXECUTION_ORCHESTRATOR.md").read_text(encoding="utf-8")
assert "KEYS/ACCOUNTS" in text
assert "implementation" in text.lower()
assert "verifier" in text.lower() or "receipt" in text.lower()
print("Source Adapter End-to-End Operator Execution Orchestrator docs self-test passed.")
