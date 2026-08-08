from __future__ import annotations

from pathlib import Path


def test_release_publish_receipt_runtime_docs() -> None:
    text = Path("SOURCE_ADAPTER_RELEASE_PUBLISH_RECEIPT_RUNTIME.md").read_text(encoding="utf-8")
    assert "Release Publish Receipt Runtime" in text
    assert "KEYS/ACCOUNTS" in text
    assert "SOURCE_ADAPTER_RELEASE_PUBLISH_RECEIPT_RUNTIME" in text
    assert "operator" in text.lower()


if __name__ == "__main__":
    test_release_publish_receipt_runtime_docs()
    print("Source Adapter Release Publish Receipt Runtime docs self-test passed.")
