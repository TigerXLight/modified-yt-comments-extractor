from __future__ import annotations

from pathlib import Path


def test_archive_result_import_runtime_docs() -> None:
    text = Path("SOURCE_ADAPTER_ARCHIVE_RESULT_IMPORT_RUNTIME.md").read_text(encoding="utf-8")
    assert "Archive Result Import Runtime" in text
    assert "KEYS/ACCOUNTS" in text
    assert "SOURCE_ADAPTER_ARCHIVE_RESULT_IMPORT_RUNTIME" in text
    assert "operator" in text.lower()


if __name__ == "__main__":
    test_archive_result_import_runtime_docs()
    print("Source Adapter Archive Result Import Runtime docs self-test passed.")
