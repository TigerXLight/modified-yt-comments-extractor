from __future__ import annotations

from pathlib import Path


def test_archive_submission_queue_runtime_docs() -> None:
    text = Path("SOURCE_ADAPTER_ARCHIVE_SUBMISSION_QUEUE_RUNTIME.md").read_text(encoding="utf-8")
    assert "Archive Submission Queue Runtime" in text
    assert "KEYS/ACCOUNTS" in text
    assert "SOURCE_ADAPTER_ARCHIVE_SUBMISSION_QUEUE_RUNTIME" in text
    assert "operator" in text.lower()


if __name__ == "__main__":
    test_archive_submission_queue_runtime_docs()
    print("Source Adapter Archive Submission Queue Runtime docs self-test passed.")
