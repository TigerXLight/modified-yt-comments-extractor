from pathlib import Path


def test_docs_cover_operator_and_redaction_boundaries():
    text = Path("SOURCE_ADAPTER_X_POST_ARCHIVE_RECEIPT_RUNTIME.md").read_text(encoding="utf-8")
    assert "X Post Archive Receipt" in text
    assert "operator-approved" in text
    assert "Credential" in text or "credential" in text
    assert "redacted" in text
    assert "x_post_archive_receipt" in text


if __name__ == "__main__":
    test_docs_cover_operator_and_redaction_boundaries()
    print("Source Adapter X Post Archive Receipt Runtime docs self-test passed.")
