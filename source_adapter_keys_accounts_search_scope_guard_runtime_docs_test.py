from pathlib import Path


def test_docs_cover_operator_and_redaction_boundaries():
    text = Path("SOURCE_ADAPTER_KEYS_ACCOUNTS_SEARCH_SCOPE_GUARD_RUNTIME.md").read_text(encoding="utf-8")
    assert "KEYS Accounts Search Scope Guard" in text
    assert "operator-approved" in text
    assert "Credential" in text or "credential" in text
    assert "redacted" in text
    assert "keys_accounts_search_scope_guard" in text


if __name__ == "__main__":
    test_docs_cover_operator_and_redaction_boundaries()
    print("Source Adapter KEYS Accounts Search Scope Guard Runtime docs self-test passed.")
