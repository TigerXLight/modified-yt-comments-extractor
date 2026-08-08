from pathlib import Path


def test_docs_cover_operator_and_redaction_boundaries():
    text = Path("SOURCE_ADAPTER_TOTAL_EXPORT_PACKAGE_RECEIPT_RUNTIME.md").read_text(encoding="utf-8")
    assert "Total Export Package Receipt" in text
    assert "operator-approved" in text
    assert "Credential" in text or "credential" in text
    assert "redacted" in text
    assert "total_export_package_receipt" in text


if __name__ == "__main__":
    test_docs_cover_operator_and_redaction_boundaries()
    print("Source Adapter Total Export Package Receipt Runtime docs self-test passed.")
