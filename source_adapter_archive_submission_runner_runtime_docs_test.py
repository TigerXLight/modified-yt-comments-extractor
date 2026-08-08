from pathlib import Path

doc = Path("SOURCE_ADAPTER_ARCHIVE_SUBMISSION_RUNNER_RUNTIME.md").read_text(encoding="utf-8")
assert "# Source Adapter Archive Submission Runner Runtime" in doc
assert "KEYS/ACCOUNTS" in doc
assert "SOURCE_ADAPTER_ARCHIVE_SUBMISSION_RUNNER_RUNTIME_BUILT" in doc
assert "SOURCE_ADAPTER_ARCHIVE_SUBMISSION_RUNNER_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE" in doc
print("Source Adapter Archive Submission Runner Runtime docs self-test passed.")
