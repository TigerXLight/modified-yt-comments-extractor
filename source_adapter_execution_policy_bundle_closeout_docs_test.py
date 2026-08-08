from pathlib import Path

doc = Path("SOURCE_ADAPTER_EXECUTION_POLICY_BUNDLE_CLOSEOUT.md").read_text(encoding="utf-8")
assert "Source Adapter Execution Policy Bundle Closeout" in doc
assert "KEYS/ACCOUNTS" in doc
assert "SOURCE_ADAPTER_EXECUTION_POLICY_BUNDLE_CLOSEOUT_BUILT" in doc
assert "SOURCE_ADAPTER_EXECUTION_POLICY_BUNDLE_CLOSEOUT_READY_FOR_NEXT_IMPLEMENTATION_STAGE" in doc
print("Source Adapter Execution Policy Bundle Closeout docs self-test passed.")
