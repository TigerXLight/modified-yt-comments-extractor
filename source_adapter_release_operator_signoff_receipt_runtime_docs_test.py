from pathlib import Path


def test_docs_cover_operator_and_redaction_boundaries():
    text = Path("SOURCE_ADAPTER_RELEASE_OPERATOR_SIGNOFF_RECEIPT_RUNTIME.md").read_text(encoding="utf-8")
    assert "Release Operator Signoff Receipt" in text
    assert "operator-approved" in text
    assert "Credential" in text or "credential" in text
    assert "redacted" in text
    assert "release_operator_signoff_receipt" in text


if __name__ == "__main__":
    test_docs_cover_operator_and_redaction_boundaries()
    print("Source Adapter Release Operator Signoff Receipt Runtime docs self-test passed.")
