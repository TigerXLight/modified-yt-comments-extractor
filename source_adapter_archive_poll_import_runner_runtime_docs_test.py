from pathlib import Path

doc = Path("SOURCE_ADAPTER_ARCHIVE_POLL_IMPORT_RUNNER_RUNTIME.md").read_text(encoding="utf-8")
assert "# Source Adapter Archive Poll Import Runner Runtime" in doc
assert "KEYS/ACCOUNTS" in doc
assert "SOURCE_ADAPTER_ARCHIVE_POLL_IMPORT_RUNNER_RUNTIME_BUILT" in doc
assert "SOURCE_ADAPTER_ARCHIVE_POLL_IMPORT_RUNNER_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE" in doc
print("Source Adapter Archive Poll Import Runner Runtime docs self-test passed.")
