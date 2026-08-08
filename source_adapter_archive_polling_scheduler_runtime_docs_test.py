from pathlib import Path

doc = Path("SOURCE_ADAPTER_ARCHIVE_POLLING_SCHEDULER_RUNTIME.md").read_text(encoding="utf-8")
assert "# Source Adapter Archive Polling Scheduler Runtime" in doc
assert "KEYS/ACCOUNTS" in doc
assert "SOURCE_ADAPTER_ARCHIVE_POLLING_SCHEDULER_RUNTIME_BUILT" in doc
assert "SOURCE_ADAPTER_ARCHIVE_POLLING_SCHEDULER_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE" in doc
print("Source Adapter Archive Polling Scheduler Runtime docs self-test passed.")
