from pathlib import Path


def test_docs_cover_operator_and_redaction_boundaries():
    text = Path("SOURCE_ADAPTER_EVIDENCE_DATABASE_RELEASE_RECEIPT_RUNTIME.md").read_text(encoding="utf-8")
    assert "Evidence Database Release Receipt" in text
    assert "operator-approved" in text
    assert "Credential" in text or "credential" in text
    assert "redacted" in text
    assert "evidence_database_release_receipt" in text


if __name__ == "__main__":
    test_docs_cover_operator_and_redaction_boundaries()
    print("Source Adapter Evidence Database Release Receipt Runtime docs self-test passed.")
