from __future__ import annotations

from pathlib import Path


def test_runtime_receipt_review_bridge_docs_cover_runtime_surfaces() -> None:
    text = Path("SOURCE_ADAPTER_RUNTIME_RECEIPT_REVIEW_BRIDGE.md").read_text(encoding="utf-8")
    assert "URL fetch/load" in text
    assert "browser launch" in text
    assert "credential lookup" in text
    assert "archive submission" in text
    assert "app/registry mutation" in text
    assert "operator approval" in text


if __name__ == "__main__":
    test_runtime_receipt_review_bridge_docs_cover_runtime_surfaces()
    print("Source Adapter Runtime Receipt Review Bridge docs self-test passed.")
