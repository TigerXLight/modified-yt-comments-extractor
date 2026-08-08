from pathlib import Path

doc = Path("SOURCE_ADAPTER_FAILURE_RETRY_EXECUTOR_RUNTIME.md").read_text(encoding="utf-8")
assert "# Source Adapter Failure Retry Executor Runtime" in doc
assert "KEYS/ACCOUNTS" in doc
assert "SOURCE_ADAPTER_FAILURE_RETRY_EXECUTOR_RUNTIME_BUILT" in doc
assert "SOURCE_ADAPTER_FAILURE_RETRY_EXECUTOR_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE" in doc
print("Source Adapter Failure Retry Executor Runtime docs self-test passed.")
