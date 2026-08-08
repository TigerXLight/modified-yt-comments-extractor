from pathlib import Path


def test_docs_cover_operator_and_redaction_boundaries():
    text = Path("SOURCE_ADAPTER_ARCHIVE_POLLING_OUTCOME_RECEIPT_RUNTIME.md").read_text(encoding="utf-8")
    assert "Archive Polling Outcome Receipt" in text
    assert "operator-approved" in text
    assert "Credential" in text or "credential" in text
    assert "redacted" in text
    assert "archive_polling_outcome_receipt" in text


if __name__ == "__main__":
    test_docs_cover_operator_and_redaction_boundaries()
    print("Source Adapter Archive Polling Outcome Receipt Runtime docs self-test passed.")
