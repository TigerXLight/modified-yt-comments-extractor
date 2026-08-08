from pathlib import Path

text = Path("SOURCE_ADAPTER_ARCHIVE_PROVIDER_SUBMISSION_BACKEND.md").read_text(encoding="utf-8")
assert "KEYS/ACCOUNTS" in text
assert "implementation" in text.lower()
assert "verifier" in text.lower() or "receipt" in text.lower()
print("Source Adapter Archive Provider Submission Backend docs self-test passed.")
