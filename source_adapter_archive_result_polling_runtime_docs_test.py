from pathlib import Path

doc = Path("SOURCE_ADAPTER_ARCHIVE_RESULT_POLLING_RUNTIME.md").read_text(encoding="utf-8")
assert "Source Adapter Archive Result Polling Runtime" in doc
assert "KEYS/ACCOUNTS" in doc
assert "SOURCE_ADAPTER_ARCHIVE_RESULT_POLLING_RUNTIME_BUILT" in doc
assert "SOURCE_ADAPTER_ARCHIVE_RESULT_POLLING_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_STAGE" in doc
print("Source Adapter Archive Result Polling Runtime docs self-test passed.")
