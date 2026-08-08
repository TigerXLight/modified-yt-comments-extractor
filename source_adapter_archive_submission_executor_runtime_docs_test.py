from pathlib import Path

doc = Path("SOURCE_ADAPTER_ARCHIVE_SUBMISSION_EXECUTOR_RUNTIME.md").read_text(encoding="utf-8")
assert "# Source Adapter Archive Submission Executor Runtime" in doc
assert "KEYS/ACCOUNTS" in doc
assert "SOURCE_ADAPTER_ARCHIVE_SUBMISSION_EXECUTOR_RUNTIME_BUILT" in doc
assert "SOURCE_ADAPTER_ARCHIVE_SUBMISSION_EXECUTOR_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE" in doc
print("Source Adapter Archive Submission Executor Runtime docs self-test passed.")
