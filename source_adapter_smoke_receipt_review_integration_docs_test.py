from __future__ import annotations

from pathlib import Path


def test_docs_cover_smoke_receipt_review_integration() -> None:
    text = Path("SOURCE_ADAPTER_SMOKE_RECEIPT_REVIEW_INTEGRATION.md").read_text(encoding="utf-8")
    required = [
        "implements receipt-review integration",
        "SOURCE_ADAPTER_SMOKE_RECEIPT_REVIEW_INTEGRATION_BUILT",
        "SOURCE_ADAPTER_SMOKE_RECEIPT_REVIEW_READY_FOR_RELEASE_EXPORT_INTEGRATION",
        "source evidence / total export",
        "KEYS/ACCOUNTS",
        "redacted credential-reference hashes",
    ]
    for item in required:
        assert item in text


if __name__ == "__main__":
    test_docs_cover_smoke_receipt_review_integration()
    print("Source Adapter Smoke Receipt Review Integration docs self-test passed.")
