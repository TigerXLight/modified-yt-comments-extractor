from pathlib import Path


def test_docs_cover_operator_and_redaction_boundaries():
    text = Path("SOURCE_ADAPTER_GUI_KEYS_ACCOUNTS_ACCEPTANCE_STATE_RUNTIME.md").read_text(encoding="utf-8")
    assert "GUI KEYS Accounts Acceptance State" in text
    assert "operator-approved" in text
    assert "Credential" in text or "credential" in text
    assert "redacted" in text
    assert "gui_keys_accounts_acceptance_state" in text


if __name__ == "__main__":
    test_docs_cover_operator_and_redaction_boundaries()
    print("Source Adapter GUI KEYS Accounts Acceptance State Runtime docs self-test passed.")
