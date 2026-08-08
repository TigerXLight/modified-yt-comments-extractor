from pathlib import Path


def test_docs_cover_operator_and_redaction_boundaries():
    text = Path("SOURCE_ADAPTER_KEYS_ACCOUNTS_ADD_PROVIDER_RECEIPT_RUNTIME.md").read_text(encoding="utf-8")
    assert "KEYS Accounts Add Provider Receipt" in text
    assert "operator-approved" in text
    assert "Credential" in text or "credential" in text
    assert "redacted" in text
    assert "keys_accounts_add_provider_receipt" in text


if __name__ == "__main__":
    test_docs_cover_operator_and_redaction_boundaries()
    print("Source Adapter KEYS Accounts Add Provider Receipt Runtime docs self-test passed.")
