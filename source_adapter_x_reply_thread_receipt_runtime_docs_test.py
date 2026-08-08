from pathlib import Path


def test_docs_cover_operator_and_redaction_boundaries():
    text = Path("SOURCE_ADAPTER_X_REPLY_THREAD_RECEIPT_RUNTIME.md").read_text(encoding="utf-8")
    assert "X Reply Thread Receipt" in text
    assert "operator-approved" in text
    assert "Credential" in text or "credential" in text
    assert "redacted" in text
    assert "x_reply_thread_receipt" in text


if __name__ == "__main__":
    test_docs_cover_operator_and_redaction_boundaries()
    print("Source Adapter X Reply Thread Receipt Runtime docs self-test passed.")
