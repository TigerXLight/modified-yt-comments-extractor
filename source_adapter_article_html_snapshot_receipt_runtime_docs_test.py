from pathlib import Path


def test_docs_cover_operator_and_redaction_boundaries():
    text = Path("SOURCE_ADAPTER_ARTICLE_HTML_SNAPSHOT_RECEIPT_RUNTIME.md").read_text(encoding="utf-8")
    assert "Article HTML Snapshot Receipt" in text
    assert "operator-approved" in text
    assert "Credential" in text or "credential" in text
    assert "redacted" in text
    assert "article_html_snapshot_receipt" in text


if __name__ == "__main__":
    test_docs_cover_operator_and_redaction_boundaries()
    print("Source Adapter Article HTML Snapshot Receipt Runtime docs self-test passed.")
