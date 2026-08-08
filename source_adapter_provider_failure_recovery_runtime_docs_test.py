from pathlib import Path

doc = Path("SOURCE_ADAPTER_PROVIDER_FAILURE_RECOVERY_RUNTIME.md").read_text(encoding="utf-8")
assert "Source Adapter Provider Failure Recovery Runtime" in doc
assert "KEYS/ACCOUNTS" in doc
assert "SOURCE_ADAPTER_PROVIDER_FAILURE_RECOVERY_RUNTIME_BUILT" in doc
assert "SOURCE_ADAPTER_PROVIDER_FAILURE_RECOVERY_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_STAGE" in doc
print("Source Adapter Provider Failure Recovery Runtime docs self-test passed.")
