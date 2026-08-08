from pathlib import Path


def test_docs_cover_operator_and_redaction_boundaries():
    text = Path("SOURCE_ADAPTER_MSN_ARTICLE_CAPTURE_RECEIPT_RUNTIME.md").read_text(encoding="utf-8")
    assert "MSN Article Capture Receipt" in text
    assert "operator-approved" in text
    assert "Credential" in text or "credential" in text
    assert "redacted" in text
    assert "msn_article_capture_receipt" in text


if __name__ == "__main__":
    test_docs_cover_operator_and_redaction_boundaries()
    print("Source Adapter MSN Article Capture Receipt Runtime docs self-test passed.")
